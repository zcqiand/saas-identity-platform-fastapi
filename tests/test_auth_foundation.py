"""批1 认证底座断言（REQ-2026-002；语义参照 saas-identity-platform-springboot）。

sqlite 内存种子直连 ASGI app（无网/无真库/无真端口，仓铁律 mock-friendly）；
家族 dev 约定：密码列可存 ``plain:{password}`` 占位，bcrypt 哈希为回退分支。
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import httpx
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from saas_identity_platform_fastapi.app import create_app
from saas_identity_platform_fastapi.entities import (
    Base,
    OauthClient,
    OauthCode,
    OauthRefreshToken,
    SysRole,
    SysUser,
    Tenant,
    TenantApplication,
    TenantMember,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.config import AppConfig

TEST_CONFIG = AppConfig(
    database_url="sqlite://",
    jwt_signing_key="test-signing-key-32-bytes-minimum!",
    jwt_issuer="saas-identity-platform",
    jwt_audience="saas-identity-platform-clients",
    jwt_ttl_seconds=3600,
)

CLIENT_ID = "saas-console"
REDIRECT = "http://localhost:5101/callback"

TENANT1 = uuid.uuid4()
TENANT2 = uuid.uuid4()
ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CAROL = uuid.uuid4()
BOB_MEMBER = uuid.uuid4()
MEM_ALICE_T1 = uuid.uuid4()
MEM_ALICE_T2 = uuid.uuid4()
MEM_CAROL_T2 = uuid.uuid4()
ROLE1 = uuid.uuid4()
ROLE2 = uuid.uuid4()

_T0 = datetime(2026, 9, 29, 8, 0, 0, tzinfo=UTC)


def _make_engine() -> Engine:
    # sqlite 无 PG 方言 server_default（uuid_generate_v4() / 'Bearer'::character varying）——
    # 测试侧元数据适配：剥离 PG 专属默认值（mock-friendly；种子显式赋值，不依赖任何默认）
    for table in Base.metadata.tables.values():
        for column in table.columns:
            default_text = (
                str(column.server_default.arg) if column.server_default is not None else ""
            )
            if "::" in default_text or "uuid_generate_v4" in default_text:
                column.server_default = None
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _seed(engine: Engine) -> None:
    """家族 dev 种子镜像（nextjs seed-db.mjs 约定）：alice/dev123456 + saas-console。"""
    values: dict[type[Any], list[dict[str, Any]]] = {
        Tenant: [
            {
                "id": TENANT1,
                "tenant_key": "t1",
                "name": "租户一",
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": TENANT2,
                "tenant_key": "t2",
                "name": "租户二",
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        SysUser: [
            {
                "id": ALICE,
                "username": "alice",
                "password": "plain:dev123456",
                "status": 1,
                "failed_attempts": 0,
                "email": "alice@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": BOB,
                "username": "bob",
                "password": bcrypt.hashpw(b"bobpass123", bcrypt.gensalt(rounds=4)).decode(),
                "status": 1,
                "failed_attempts": 0,
                "email": "bob@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": CAROL,
                "username": "carol",
                "password": "plain:carolpass",
                "status": 1,
                "failed_attempts": 0,
                "email": "carol@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        OauthClient: [
            {
                "id": uuid.uuid4(),
                "client_id": CLIENT_ID,
                "client_secret": "dev-secret",
                "client_name": "SaaS Console",
                "grant_types": "authorization_code,refresh_token",
                "redirect_uris": f"{REDIRECT},http://localhost:3000/callback",
                "access_token_validity": 7200,
                "refresh_token_validity": 2592000,
                "auto_approve": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        TenantApplication: [
            {
                "id": uuid.uuid4(),
                "tenant_id": TENANT1,
                "client_id": CLIENT_ID,
                "status": 1,
                "created_at": _T0,
            },
            {
                "id": uuid.uuid4(),
                "tenant_id": TENANT2,
                "client_id": CLIENT_ID,
                "status": 1,
                "created_at": _T0,
            },
        ],
        TenantMember: [
            {
                "id": BOB_MEMBER,
                "tenant_id": TENANT1,
                "user_id": BOB,
                "is_owner": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": MEM_ALICE_T1,
                "tenant_id": TENANT1,
                "user_id": ALICE,
                "is_owner": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": MEM_ALICE_T2,
                "tenant_id": TENANT2,
                "user_id": ALICE,
                "is_owner": False,
                "status": 1,
                "created_at": _T0 + timedelta(seconds=1),
                "updated_at": _T0,
            },
            {
                "id": MEM_CAROL_T2,
                "tenant_id": TENANT2,
                "user_id": CAROL,
                "is_owner": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        SysRole: [
            {
                "id": ROLE1,
                "tenant_id": TENANT1,
                "client_id": CLIENT_ID,
                "role_code": "admin",
                "role_name": "管理员",
                "is_preset": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": ROLE2,
                "tenant_id": TENANT2,
                "client_id": CLIENT_ID,
                "role_code": "member",
                "role_name": "成员",
                "is_preset": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        t_tenant_member_role: [
            # 跨租户绑定原样吐出（家族约定：member 绑定即真值，视图层不按 tenant_id 过滤）
            {"member_id": MEM_ALICE_T1, "role_id": ROLE1},
            {"member_id": MEM_ALICE_T1, "role_id": ROLE2},
            {"member_id": MEM_CAROL_T2, "role_id": ROLE2},
        ],
    }
    member_role_rows = values.pop(t_tenant_member_role)
    with Session(engine) as session:
        for model, rows in values.items():
            for row in rows:
                session.add(model(**row))
        # join 表是 secondary Table（无 ORM 类），走核心 insert
        session.execute(t_tenant_member_role.insert(), member_role_rows)
        session.commit()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = _make_engine()
    _seed(engine)
    yield TestClient(create_app(TEST_CONFIG, engine=engine))


def _db(engine: Engine) -> Session:
    return Session(engine)


def _login(
    client: TestClient,
    username: str = "alice",
    password: str = "dev123456",
    client_id: str = CLIENT_ID,
) -> httpx.Response:
    return client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
            "clientId": client_id,
        },
    )


def _bearer(client: TestClient, username: str = "alice") -> dict[str, str]:
    resp = _login(client, username=username)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['accessToken']}"}


def _authorize(
    client: TestClient, headers: dict[str, str], redirect_uri: str = REDIRECT
) -> httpx.Response:
    return client.post(
        "/api/v1/oauth/authorize",
        headers=headers,
        json={
            "clientId": CLIENT_ID,
            "redirectUri": redirect_uri,
            "responseType": "code",
            "state": "st-123",
        },
    )


# ---------------------------------------------------------------- M01.F04.I01 密码登录


@pytest.mark.fn("M01.F04.I01")
def test_login_success_full_shape(client: TestClient) -> None:
    resp = _login(client)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tokenType"] == "Bearer"
    assert body["expiresIn"] == 3600
    assert body["refreshToken"].startswith("rt_")
    assert body["clientId"] == CLIENT_ID
    assert body["userId"] == str(ALICE)
    assert body["currentTenantId"] == str(TENANT1)
    assert body["user"]["username"] == "alice"
    assert body["user"]["email"] == "alice@example.com"
    # availableTenants = active membership ∩ tenant_application 订阅（本种子全部订阅）
    tenants = sorted(m["tenantId"] for m in body["availableTenants"])
    assert tenants == sorted([str(TENANT1), str(TENANT2)])
    membership_t1 = next(m for m in body["availableTenants"] if m["tenantId"] == str(TENANT1))
    assert sorted(membership_t1["roleIds"]) == sorted([str(ROLE1), str(ROLE2)])
    assert membership_t1["status"] == "active"
    # HS256 JWT 可解码：sub/tenant_id/iss/aud
    claims = pyjwt.decode(
        body["accessToken"],
        key=TEST_CONFIG.jwt_signing_key,
        algorithms=["HS256"],
        audience=TEST_CONFIG.jwt_audience,
        issuer=TEST_CONFIG.jwt_issuer,
    )
    assert claims["sub"] == str(ALICE)
    assert claims["tenant_id"] == str(TENANT1)


@pytest.mark.fn("M01.F04.I01")
def test_login_bcrypt_password_branch(client: TestClient) -> None:
    resp = _login(client, username="bob", password="bobpass123")
    assert resp.status_code == 200, resp.text
    assert resp.json()["userId"] == str(BOB)


@pytest.mark.fn("M01.F04.I01")
def test_login_unknown_user_and_wrong_password_same_401(client: TestClient) -> None:
    unknown = _login(client, username="nobody", password="x")
    wrong = _login(client, password="wrong-pass")
    for resp in (unknown, wrong):
        assert resp.status_code == 401, resp.text
        assert resp.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.fn("M01.F04.I01")
def test_login_unknown_client_400(client: TestClient) -> None:
    resp = _login(client, client_id="no-such-client")
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "BAD_REQUEST"


# ---------------------------------------------------------------- M01.F04.I02 失败锁定


@pytest.mark.fn("M01.F04.I02")
def test_failed_attempts_increment_then_reset(client: TestClient) -> None:
    assert _login(client, password="bad-1").status_code == 401
    assert _login(client, password="bad-2").status_code == 401
    with _db(client.app.state.engine) as session:
        user = session.get(SysUser, ALICE)
        assert user is not None and user.failed_attempts == 2
    assert _login(client).status_code == 200
    with _db(client.app.state.engine) as session:
        user = session.get(SysUser, ALICE)
        assert user is not None
        assert user.failed_attempts == 0
        assert user.locked_until is None


@pytest.mark.fn("M01.F04.I02")
def test_lockout_423_after_five_failures(client: TestClient) -> None:
    for i in range(5):
        resp = _login(client, password=f"bad-{i}")
        assert resp.status_code == 401, resp.text
    # 第 5 次错已置 locked_until；此后即使密码正确也 423（body 空，springboot 参照 body(null)）
    locked = _login(client)
    assert locked.status_code == 423
    assert locked.text == ""
    with _db(client.app.state.engine) as session:
        user = session.get(SysUser, ALICE)
        assert user is not None and user.locked_until is not None


# ---------------------------------------------------------------- M01.F04.I06 登出


@pytest.mark.fn("M01.F04.I06")
def test_logout_204(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    assert resp.text == ""


# ---------------------------------------------------------------- M04.F03.I01 授权码签发


@pytest.mark.fn("M04.F03.I01")
def test_authorize_issues_code(client: TestClient) -> None:
    resp = _authorize(client, _bearer(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"].startswith("ac_")
    assert body["state"] == "st-123"
    with _db(client.app.state.engine) as session:
        row = session.query(OauthCode).filter_by(code=body["code"]).one_or_none()
        assert row is not None
        assert row.user_id == ALICE and row.tenant_id == TENANT1
        assert row.redirect_uri == REDIRECT


@pytest.mark.fn("M04.F03.I01")
def test_authorize_requires_bearer(client: TestClient) -> None:
    resp = _authorize(client, {})
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.fn("M04.F03.I01")
def test_authorize_rejects_redirect_not_whitelisted(client: TestClient) -> None:
    headers = _bearer(client)
    evil = _authorize(client, headers, redirect_uri="http://evil.example.com/callback")
    assert evil.status_code == 400, evil.text
    # 子路径不算匹配（白名单条目必须精确相等或前缀 + '?' 边界）
    subpath = _authorize(client, headers, redirect_uri=REDIRECT + "/extra")
    assert subpath.status_code == 400, subpath.text
    # 前缀 + '?' 边界算匹配（lab 前端回跳带 ?from= 的家族形状）
    with_qs = _authorize(client, headers, redirect_uri=REDIRECT + "?from=/tenants")
    assert with_qs.status_code == 200, with_qs.text


# ---------------------------------------------------------------- M04.F03.I02 令牌交换


@pytest.mark.fn("M04.F03.I02")
def test_token_code_exchange_once(client: TestClient) -> None:
    headers = _bearer(client)
    code = _authorize(client, headers).json()["code"]
    resp = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tokenType"] == "Bearer"
    assert body["userId"] == str(ALICE)
    assert body["clientId"] == CLIENT_ID
    assert body["tenantId"] == str(TENANT1)
    assert body["refreshToken"].startswith("rt_")
    claims = pyjwt.decode(
        body["accessToken"],
        key=TEST_CONFIG.jwt_signing_key,
        algorithms=["HS256"],
        audience=TEST_CONFIG.jwt_audience,
        issuer=TEST_CONFIG.jwt_issuer,
    )
    assert claims["sub"] == str(ALICE)
    # 一次性消费：重放 → 400
    replay = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
        },
    )
    assert replay.status_code == 400, replay.text
    assert replay.json()["code"] == "BAD_REQUEST"


@pytest.mark.fn("M04.F03.I02")
def test_token_expired_code_rejected(client: TestClient) -> None:
    headers = _bearer(client)
    code = _authorize(client, headers).json()["code"]
    with _db(client.app.state.engine) as session:
        row = session.query(OauthCode).filter_by(code=code).one()
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
    resp = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
        },
    )
    assert resp.status_code == 400, resp.text
    # 过期 code 行已删：随后正确交换也 400
    again = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT,
        },
    )
    assert again.status_code == 400, again.text


@pytest.mark.fn("M04.F03.I02")
def test_token_redirect_mismatch_rejected(client: TestClient) -> None:
    headers = _bearer(client)
    code = _authorize(client, headers).json()["code"]
    resp = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": code,
            "clientId": CLIENT_ID,
            "redirectUri": "http://localhost:3000/callback",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "BAD_REQUEST"


@pytest.mark.fn("M04.F03.I02")
def test_token_unknown_client_400(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "authorization_code",
            "code": "ac_nope",
            "clientId": "no-such-client",
            "redirectUri": REDIRECT,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "BAD_REQUEST"


# ---------------------------------------------------------------- M04.F03.I03 令牌刷新


@pytest.mark.fn("M04.F03.I03")
def test_refresh_rotates_and_old_reuse_rejected(client: TestClient) -> None:
    first = _login(client).json()
    r1 = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "refresh_token",
            "refreshToken": first["refreshToken"],
            "clientId": CLIENT_ID,
        },
    )
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["refreshToken"].startswith("rt_")
    assert body["refreshToken"] != first["refreshToken"]
    assert body["userId"] == str(ALICE)
    assert body["tenantId"] == str(TENANT1)
    # 旧 refreshToken 已 rotate（revoked）→ 复用 400
    reuse = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "refresh_token",
            "refreshToken": first["refreshToken"],
            "clientId": CLIENT_ID,
        },
    )
    assert reuse.status_code == 400, reuse.text
    # 新 refreshToken 可继续轮换
    r2 = client.post(
        "/api/v1/oauth/token",
        json={
            "grantType": "refresh_token",
            "refreshToken": body["refreshToken"],
            "clientId": CLIENT_ID,
        },
    )
    assert r2.status_code == 200, r2.text
    with _db(client.app.state.engine) as session:
        revoked = (
            session.query(OauthRefreshToken).filter_by(refresh_token=first["refreshToken"]).one()
        )
        assert revoked.revoked is True


# ---------------------------------------------------------------- M01.F01.I01 whoami


@pytest.mark.fn("M01.F01.I01")
def test_whoami_full_shape(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get("/api/v1/me", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == str(ALICE)
    assert body["email"] == "alice@example.com"
    # currentTenantId 优先取 JWT tenant_id claim
    assert body["currentTenantId"] == str(TENANT1)
    by_tenant = {m["tenantId"]: m for m in body["memberships"]}
    assert set(by_tenant) == {str(TENANT1), str(TENANT2)}
    # roleIds 真 join 原样吐出（跨租户绑定不过滤）
    assert sorted(by_tenant[str(TENANT1)]["roleIds"]) == sorted([str(ROLE1), str(ROLE2)])
    assert by_tenant[str(TENANT2)]["roleIds"] == []
    assert by_tenant[str(TENANT1)]["joinedAt"].startswith("2026-09-29")


@pytest.mark.fn("M01.F01.I01")
def test_whoami_requires_bearer(client: TestClient) -> None:
    missing = client.get("/api/v1/me")
    assert missing.status_code == 401, missing.text
    garbage = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert garbage.status_code == 401, garbage.text
