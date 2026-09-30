"""批4 应用与关系网断言（REQ-2026-005）：admin clients + 公共元数据 + me/tenants/switch。

语义镜像 saas-identity-platform-springboot（AdminClientsController / ClientsController /
MeController），逐条对应 REQ-2026-005 §1 端点表；响应形状与参照 DTO 一致
（OAuthClient 含 id/审计列但无 clientSecret；SwitchTenantResponse 四字段）。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.entities import (
    OauthClient,
    OauthRefreshToken,
    SysRole,
    TenantApplication,
    TenantMember,
)
from tests.conftest import (
    ALICE,
    BOB,
    CLIENT_ID,
    ROLE1,
    ROLE2,
    SECOND_CLIENT_ID,
    TENANT1,
    TENANT2,
    _bearer,
)

T1 = str(TENANT1)
T2 = str(TENANT2)
ADMIN = "/api/v1/admin/clients"
BOB_AUTH = {"username": "bob", "password": "bobpass123"}
_NOW = datetime.now(UTC)


def _db(client: TestClient) -> Session:
    return Session(client.app.state.engine)


def _new_client_payload(client_id: str) -> dict[str, object]:
    return {
        "clientId": client_id,
        "clientName": "批四应用",
        "clientSecret": "s3cret-value",
        "grantTypes": "authorization_code,refresh_token",
        "redirectUris": "http://localhost:9999/callback",
    }


# ---------------------------------------------------------------- M04.F01 应用维护


@pytest.mark.fn("M04.F01.I01")
def test_admin_clients_list_pagination_defaults(client: TestClient) -> None:
    headers = _bearer(client)  # 无角色门：普通成员 JWT 即可（镜像参照 anyRequest authenticated）
    resp = client.get(ADMIN, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page"] == 0 and body["pageSize"] == 20  # 缺省回显
    seed_ids = {item["clientId"] for item in body["items"]}
    assert {CLIENT_ID, SECOND_CLIENT_ID} <= seed_ids
    assert body["total"] == len(body["items"])
    # 响应镜像参照 toDto：含 id/审计列，永不含 secret
    assert set(body["items"][0]) == {
        "id",
        "clientId",
        "clientName",
        "grantTypes",
        "redirectUris",
        "scopes",
        "accessTokenValidity",
        "refreshTokenValidity",
        "autoApprove",
        "status",
        "createdAt",
        "updatedAt",
    }
    page1 = client.get(ADMIN, headers=headers, params={"page": 1, "pageSize": 1})
    assert page1.status_code == 200, page1.text
    assert len(page1.json()["items"]) == 1  # 分页裁剪


@pytest.mark.fn("M04.F01.I02")
def test_admin_clients_create_defaults_and_dup_400(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(ADMIN, headers=headers, json=_new_client_payload("batch4-app"))
    assert resp.status_code == 200, resp.text  # 200 非 201（镜像参照）
    body = resp.json()
    assert body["accessTokenValidity"] == 3600  # 应用层缺省（非 DB 列 7200）
    assert body["refreshTokenValidity"] == 86400
    assert body["autoApprove"] is False and body["status"] == 1
    # 显式 ≤0 同样落缺省（springboot :56-63 口径）
    zero = client.post(
        ADMIN,
        headers=headers,
        json={**_new_client_payload("batch4-zero"), "accessTokenValidity": 0},
    )
    assert zero.status_code == 200, zero.text
    assert zero.json()["accessTokenValidity"] == 3600
    # clientId 撞 unique → 400 constraint violation（非 409）
    dup = client.post(ADMIN, headers=headers, json=_new_client_payload("batch4-app"))
    assert dup.status_code == 400, dup.text
    assert "constraint violation" in dup.json()["message"]
    # 契约必填字段缺失 → 422（springboot @Valid→400 的校验层差异，§4 以契约为准）
    missing = client.post(ADMIN, headers=headers, json={"clientId": "x"})
    assert missing.status_code == 422, missing.text


@pytest.mark.fn("M04.F01.I03")
def test_admin_clients_get_hides_secret(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"{ADMIN}/{CLIENT_ID}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clientId"] == CLIENT_ID
    assert "clientSecret" not in body  # DTO 无 secret 字段（admin get 也不回）
    unknown = client.get(f"{ADMIN}/no-such-app", headers=headers)
    assert unknown.status_code == 404, unknown.text


@pytest.mark.fn("M04.F01.I04")
def test_admin_clients_update_three_fields_only(client: TestClient) -> None:
    headers = _bearer(client)
    made = client.post(ADMIN, headers=headers, json=_new_client_payload("batch4-edit"))
    assert made.status_code == 200, made.text
    with _db(client) as session:
        before = session.query(OauthClient).filter_by(client_id="batch4-edit").one().updated_at
    resp = client.patch(
        f"{ADMIN}/batch4-edit",
        headers=headers,
        json={
            "clientName": "改名",
            "redirectUris": "http://localhost:8888/callback",
            "scopes": "openid profile",
            # 以下字段参照实现全部忽略
            "grantTypes": "password",
            "accessTokenValidity": 1,
            "refreshTokenValidity": 1,
            "autoApprove": True,
            "status": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clientName"] == "改名"
    assert body["redirectUris"] == "http://localhost:8888/callback"
    assert body["scopes"] == "openid profile"
    assert body["grantTypes"] == "authorization_code,refresh_token"  # 忽略
    assert body["accessTokenValidity"] == 3600 and body["status"] == 1  # 忽略
    assert body["autoApprove"] is False  # 忽略
    with _db(client) as session:
        after = session.query(OauthClient).filter_by(client_id="batch4-edit").one().updated_at
    assert after == before  # 不 touch updatedAt（参照无 @PreUpdate、handler 不 set）


@pytest.mark.fn("M04.F01.I05")
def test_admin_clients_delete_cascade_and_404(client: TestClient) -> None:
    headers = _bearer(client)
    made = client.post(ADMIN, headers=headers, json=_new_client_payload("batch4-del"))
    assert made.status_code == 200, made.text
    client_id = "batch4-del"
    created = datetime.now(UTC)
    with _db(client) as session:
        session.add(
            SysRole(
                id=uuid.uuid4(),
                tenant_id=TENANT1,
                client_id=client_id,
                role_code="r",
                role_name="r",
                is_preset=False,
                status=1,
                created_at=created,
            )
        )
        session.add(
            TenantApplication(
                id=uuid.uuid4(),
                tenant_id=TENANT2,
                client_id=client_id,
                status=1,
                created_at=created,
            )
        )
        session.commit()
    resp = client.delete(f"{ADMIN}/{client_id}", headers=headers)
    assert resp.status_code == 204, resp.text
    with _db(client) as session:
        assert session.query(SysRole).filter_by(client_id=client_id).count() == 0  # DB 级联
        assert session.query(TenantApplication).filter_by(client_id=client_id).count() == 0
    again = client.delete(f"{ADMIN}/{client_id}", headers=headers)
    assert again.status_code == 404, again.text  # 非幂等（先 resolve）


@pytest.mark.fn("M04.F01.I06")
def test_public_client_metadata_anonymous(client: TestClient) -> None:
    # 匿名可读（SecurityConfig permitAll 严格匹配 /api/v1/clients/*）
    resp = client.get(f"/api/v1/clients/{CLIENT_ID}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"clientId", "clientName", "status"}  # 绝无 secret/redirectUris
    assert body["clientId"] == CLIENT_ID and body["status"] == 1
    # 带 Bearer 同样 200
    with_bearer = client.get(f"/api/v1/clients/{CLIENT_ID}", headers=_bearer(client))
    assert with_bearer.status_code == 200, with_bearer.text
    unknown = client.get("/api/v1/clients/no-such-app")
    assert unknown.status_code == 404, unknown.text


# ---------------------------------------------------------------- M04.F02 应用启停


@pytest.mark.fn("M04.F02.I01")
def test_admin_clients_set_status_no_range_check(client: TestClient) -> None:
    headers = _bearer(client)
    off = client.patch(f"{ADMIN}/{SECOND_CLIENT_ID}/status", headers=headers, json={"status": 0})
    assert off.status_code == 200, off.text
    assert off.json()["status"] == 0
    weird = client.patch(f"{ADMIN}/{SECOND_CLIENT_ID}/status", headers=headers, json={"status": 7})
    assert weird.status_code == 200, weird.text
    assert weird.json()["status"] == 7  # 无值域校验（镜像参照）
    unknown = client.patch(f"{ADMIN}/no-such-app/status", headers=headers, json={"status": 1})
    assert unknown.status_code == 404, unknown.text
    missing = client.patch(f"{ADMIN}/{SECOND_CLIENT_ID}/status", headers=headers, json={})
    assert missing.status_code == 422, missing.text  # 契约 status 必填


# ---------------------------------------------------------------- M01.F03 我的租户与切换


@pytest.mark.fn("M01.F03.I01")
def test_me_tenants_listing_order_and_roles(client: TestClient) -> None:
    headers = _bearer(client)  # alice：T1 owner（MEM_ALICE_T1）+ T2 成员（MEM_ALICE_T2）
    resp = client.get("/api/v1/me/tenants", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [m["tenantId"] for m in body] == [T1, T2]  # created_at ASC（种子 T2 晚 1s）
    first = body[0]
    assert set(first) == {"id", "userId", "tenantId", "roleIds", "status", "joinedAt"}
    assert first["status"] == "active" and first["userId"] == str(ALICE)
    # roleIds 跨租户原样吐出（MEM_ALICE_T1 绑 ROLE1@T1 + ROLE2@T2——ROLE2 属 T2 也照回）
    assert set(first["roleIds"]) == {str(ROLE1), str(ROLE2)}
    assert body[1]["roleIds"] == []  # alice@T2 成员无角色绑定（种子只绑 MEM_ALICE_T1）
    # query clientId 收但忽略
    scoped = client.get(
        "/api/v1/me/tenants", headers=headers, params={"clientId": SECOND_CLIENT_ID}
    )
    assert scoped.status_code == 200, scoped.text
    assert scoped.json() == body
    # bob 只有 T1
    bob_list = client.get("/api/v1/me/tenants", headers=_bearer(client, **BOB_AUTH))
    assert bob_list.status_code == 200, bob_list.text
    assert [m["tenantId"] for m in bob_list.json()] == [T1]


@pytest.mark.fn("M01.F03.I01")
def test_me_tenants_no_status_filter(client: TestClient) -> None:
    headers = _bearer(client, **BOB_AUTH)
    with _db(client) as session:
        member = session.query(TenantMember).filter_by(user_id=BOB).one()
        member.status = 3  # suspended：参照不过滤，四值全回
        session.commit()
    resp = client.get("/api/v1/me/tenants", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["status"] == "suspended"


@pytest.mark.fn("M01.F03.I02")
def test_switch_tenant_success_claim_and_no_db_write(client: TestClient) -> None:
    headers = _bearer(client)  # alice
    resp = client.post(f"/api/v1/me/tenants/{T2}/switch", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"accessToken", "refreshToken", "expiresAt", "tenantId"}  # 参照四字段
    assert body["tenantId"] == T2
    # 新 access 的 tenant_id claim = T2：whoami currentTenantId 应指向 T2
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me.status_code == 200, me.text
    assert me.json()["currentTenantId"] == T2
    # refresh 不落库（参照 generateRefreshToken 纯构造，rotate 语义归 /auth/refresh）：
    # 登录本身会落 1 条 refresh 行，断言的是 switch 前后计数不变
    with _db(client) as session:
        assert session.query(OauthRefreshToken).count() == 1


@pytest.mark.fn("M01.F03.I02")
def test_switch_tenant_guards(client: TestClient) -> None:
    # bob 不是 T2 成员 → 404（不是 403）
    bob = _bearer(client, **BOB_AUTH)
    no_member = client.post(f"/api/v1/me/tenants/{T2}/switch", headers=bob)
    assert no_member.status_code == 404, no_member.text
    assert "not an active member" in no_member.json()["message"]
    # 坏 tenantId UUID → 400
    bad = client.post("/api/v1/me/tenants/not-a-uuid/switch", headers=_bearer(client))
    assert bad.status_code == 400, bad.text
    # 合法 UUID 但租户不存在 → 404
    ghost = client.post(f"/api/v1/me/tenants/{uuid.uuid4()}/switch", headers=_bearer(client))
    assert ghost.status_code == 404, ghost.text
    # disabled（status=0）成员不可切 → 404
    with _db(client) as session:
        session.add(
            TenantMember(
                id=uuid.uuid4(),
                tenant_id=TENANT2,
                user_id=BOB,
                is_owner=False,
                status=0,
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
        session.commit()
    disabled = client.post(f"/api/v1/me/tenants/{T2}/switch", headers=bob)
    assert disabled.status_code == 404, disabled.text


@pytest.mark.fn("M01.F03.I02")
def test_switch_tenant_invited_member_can_switch(client: TestClient) -> None:
    # S5 口径：非 disabled（invited=2）即可切
    with _db(client) as session:
        session.add(
            TenantMember(
                id=uuid.uuid4(),
                tenant_id=TENANT2,
                user_id=BOB,
                is_owner=False,
                status=2,
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
        session.commit()
    bob = _bearer(client, **BOB_AUTH)
    ok = client.post(f"/api/v1/me/tenants/{T2}/switch", headers=bob)
    assert ok.status_code == 200, ok.text


@pytest.mark.fn("M04.F01.I01")
@pytest.mark.fn("M01.F03.I02")
def test_bare_requests_401(client: TestClient) -> None:
    assert client.get(ADMIN).status_code == 401
    assert client.get("/api/v1/me/tenants").status_code == 401
    assert client.post(f"/api/v1/me/tenants/{T1}/switch").status_code == 401
