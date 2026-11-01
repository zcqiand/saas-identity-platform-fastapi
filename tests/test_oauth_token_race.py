"""5.123①② 竞态机制钉（tracker：rails 先行定形状，fastapi 同形镜像）。

② rotate 必须原子：撤销旧行与签发新对同 commit——签发段失败回滚恢复旧行，
  同一 refresh 可重试（修前 revoke 先行落库，签发段故障留「旧废新未落」半态）。
① code claim 影响行数判定：并发输家（读到行但删 0 行）必须 400 拒签且不签发
  新对——PG read committed 每语句独立快照，赢家先 commit 的物理删除让输家的
  DELETE 影响 0 行（真交错投影，非桩件；修前 session.delete 静默删 0 → 200 照签）。
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import saas_identity_platform_fastapi.impl.oauth_impl as oauth_impl
from saas_identity_platform_fastapi.entities import OauthRefreshToken
from saas_identity_platform_fastapi.impl.errors import BadRequestError
from saas_identity_platform_fastapi.impl.security import TokenIssuer
from tests.conftest import CLIENT_ID, REDIRECT, _bearer, _login


def _db(engine: Engine) -> Session:
    return Session(engine)


def _authorize(client: TestClient, headers: dict[str, str]) -> httpx.Response:
    return client.post(
        "/api/v1/oauth/authorize",
        headers=headers,
        json={
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
            "responseType": "code",
            "state": "st-123",
        },
    )


def _exchange(client: TestClient, code: str) -> httpx.Response:
    return client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
        },
    )


def _refresh(client: TestClient, refresh_token: str) -> httpx.Response:
    return client.post(
        "/api/v1/oauth/token",
        json={"grantType": "refresh_token", "refreshToken": refresh_token, "clientId": CLIENT_ID},
    )


@pytest.mark.fn("M04.F03.I02")
def test_code_claim_loser_gets_zero_rows_issues_nothing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bearer(client)
    code = _authorize(client, headers).json()["code"]
    with _db(client.app.state.engine) as session:
        pairs_before = session.query(OauthRefreshToken).count()

    real_discard = oauth_impl._discard_code

    def winner_consumes_first(session: Session, c: str) -> int:
        # 并发赢家经独立连接物理删行并 commit；输家的读已见行、删时快照刷新 → 删 0 行。
        with _db(client.app.state.engine) as winner:
            real_discard(winner, c)
            winner.commit()
        return real_discard(session, c)

    monkeypatch.setattr(oauth_impl, "_discard_code", winner_consumes_first)
    resp = _exchange(client, code)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "BAD_REQUEST"
    # 输家不得签发新 token 对
    with _db(client.app.state.engine) as session:
        assert session.query(OauthRefreshToken).count() == pairs_before


@pytest.mark.fn("M04.F03.I03")
def test_refresh_rotation_failure_restores_old_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    refresh_token = _login(client).json()["refreshToken"]

    def boom(_self: TokenIssuer, *_args: object, **_kwargs: object) -> str:
        raise BadRequestError("db fault mid-rotation")

    monkeypatch.setattr(TokenIssuer, "persist_token_pair", boom)
    resp = _refresh(client, refresh_token)
    assert resp.status_code >= 400, resp.text

    monkeypatch.undo()  # 故障排除：同一 refresh 必须可重试（轮换段已回滚）
    retry = _refresh(client, refresh_token)
    assert retry.status_code == 200, retry.text
