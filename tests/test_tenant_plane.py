"""批2 租户面断言（REQ-2026-003；语义参照 saas-identity-platform-springboot）。

三组端点：admin tenants（平台域）+ tenant members + tenant applications（租户守卫）。
scratch/PG 基建见 tests/conftest.py。家族语义：重复/冲突一律 400（无 409）；
DELETE 不对称——租户/订阅幂等 204、成员先 resolve 404；成员排序 created_at DESC。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.entities import (
    SysUser,
    Tenant,
    TenantApplication,
    TenantMember,
    t_tenant_member_role,
)
from tests.conftest import (
    ALICE,
    BOB,
    CAROL,
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


def _db(client: TestClient) -> Session:
    return Session(client.app.state.engine)


# ---------------------------------------------------------------- M00.F01 租户维护


@pytest.mark.fn("M00.F01.I01")
def test_admin_tenants_list_paginated(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get("/api/v1/admin/tenants", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page"] == 0 and body["pageSize"] == 20
    assert body["total"] == 2
    keys = {item["tenantKey"] for item in body["items"]}
    assert keys == {"t1", "t2"}
    one = body["items"][0]
    assert set(one) == {"id", "tenantKey", "name", "status", "createdAt", "updatedAt"}
    assert one["status"] == "active"  # springboot 参照：读路径恒 active（96 行语义）
    # 分页裁剪：pageSize=1 只吐一行，total 仍是过滤后全量
    paged = client.get("/api/v1/admin/tenants", headers=headers, params={"page": 0, "pageSize": 1})
    assert paged.status_code == 200, paged.text
    assert len(paged.json()["items"]) == 1
    assert paged.json()["total"] == 2


@pytest.mark.fn("M00.F01.I01")
def test_admin_tenants_requires_bearer(client: TestClient) -> None:
    resp = client.get("/api/v1/admin/tenants")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.fn("M00.F01.I02")
def test_admin_create_tenant_roundtrip_and_duplicate_key(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(
        "/api/v1/admin/tenants", headers=headers, json={"tenantKey": "acme", "name": "Acme"}
    )
    assert resp.status_code == 200, resp.text  # springboot 参照：create 返回 200 非 201
    body = resp.json()
    assert body["tenantKey"] == "acme" and body["name"] == "Acme"
    assert body["status"] == "active"
    uuid.UUID(body["id"])  # 合法 UUID
    dup = client.post(
        "/api/v1/admin/tenants", headers=headers, json={"tenantKey": "acme", "name": "Again"}
    )
    assert dup.status_code == 400, dup.text  # unique 撞 → 400 constraint violation（无 409）
    assert dup.json()["code"] == "BAD_REQUEST"


@pytest.mark.fn("M00.F01.I03")
def test_admin_get_tenant_and_unknown_404(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"/api/v1/admin/tenants/{T1}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tenantKey"] == "t1"
    missing = client.get(f"/api/v1/admin/tenants/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404, missing.text
    assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.fn("M00.F01.I04")
def test_admin_patch_tenant_partial_update(client: TestClient) -> None:
    headers = _bearer(client)
    # 只改 name：status 不动
    resp = client.patch(f"/api/v1/admin/tenants/{T1}", headers=headers, json={"name": "租户一号"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "租户一号"
    assert resp.json()["status"] == "active"
    # 再改 status=suspended：落库 smallint 0（springboot ACTIVE→1/其他→0）
    resp2 = client.patch(
        f"/api/v1/admin/tenants/{T1}", headers=headers, json={"status": "suspended"}
    )
    assert resp2.status_code == 200, resp2.text
    with _db(client) as session:
        t = session.get(Tenant, TENANT1)
        assert t is not None
        assert t.status == 0
        assert t.name == "租户一号"  # 部分更新互不覆盖


@pytest.mark.fn("M00.F01.I05")
def test_admin_delete_tenant_idempotent_204(client: TestClient) -> None:
    headers = _bearer(client)
    created = client.post(
        "/api/v1/admin/tenants", headers=headers, json={"tenantKey": "gone", "name": "将删"}
    )
    tid = created.json()["id"]
    first = client.delete(f"/api/v1/admin/tenants/{tid}", headers=headers)
    assert first.status_code == 204, first.text
    assert first.text == ""
    # 幂等：不存在也 204（springboot deleteById 语义）
    again = client.delete(f"/api/v1/admin/tenants/{tid}", headers=headers)
    assert again.status_code == 204, again.text


# ---------------------------------------------------------------- M00.F02 租户守卫


@pytest.mark.fn("M00.F02.I01")
def test_member_endpoints_reject_wrong_tenant_and_missing_bearer(client: TestClient) -> None:
    # 无 Bearer → 401（fail-fast，家族语义：身份字段缺失必须 401）
    resp = client.get(f"/api/v1/tenants/{T1}/members")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "INVALID_CREDENTIALS"
    # 路径 tenantId ≠ JWT tenant_id claim → 403 FORBIDDEN（springboot TenantGuard 参照）
    headers = _bearer(client)  # alice 默认落 T1
    cross = client.get(f"/api/v1/tenants/{T2}/members", headers=headers)
    assert cross.status_code == 403, cross.text
    assert cross.json()["code"] == "FORBIDDEN"
    # 同租户 → 200
    ok = client.get(f"/api/v1/tenants/{T1}/members", headers=headers)
    assert ok.status_code == 200, ok.text


# ---------------------------------------------------------------- M00.F02.I01 成员列表


@pytest.mark.fn("M00.F02.I01")
def test_member_list_shape_pagination_and_desc_order(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"/api/v1/tenants/{T1}/members", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page"] == 0 and body["pageSize"] == 20 and body["total"] == 2
    usernames = {item["username"] for item in body["items"]}
    assert usernames == {"alice", "bob"}
    one = body["items"][0]
    assert set(one) == {
        "id",
        "tenantId",
        "username",
        "email",
        "status",
        "roleIds",
        "createdAt",
        "updatedAt",
    }
    # 排序 created_at DESC：新建成员时间更新 → 排最前
    created = client.post(
        f"/api/v1/tenants/{T1}/members",
        headers=headers,
        json={"username": "dave", "password": "davepass123", "email": "dave@example.com"},
    )
    assert created.status_code == 200, created.text
    after = client.get(f"/api/v1/tenants/{T1}/members", headers=headers).json()
    assert after["total"] == 3
    assert after["items"][0]["username"] == "dave"
    # 分页裁剪
    paged = client.get(
        f"/api/v1/tenants/{T1}/members", headers=headers, params={"page": 0, "pageSize": 2}
    )
    assert len(paged.json()["items"]) == 2 and paged.json()["total"] == 3


@pytest.mark.fn("M00.F02.I01")
def test_member_list_status_filter_db_level(client: TestClient) -> None:
    headers = _bearer(client)
    # 先把 bob 停用（双写端点，见 I08 测试）
    st = client.patch(
        f"/api/v1/tenants/{T1}/members/{BOB}/status", headers=headers, json={"status": "suspended"}
    )
    assert st.status_code == 200, st.text
    active = client.get(
        f"/api/v1/tenants/{T1}/members", headers=headers, params={"status": "active"}
    ).json()
    assert active["total"] == 1  # 只有 alice
    suspended = client.get(
        f"/api/v1/tenants/{T1}/members", headers=headers, params={"status": "suspended"}
    ).json()
    assert suspended["total"] == 1
    assert suspended["items"][0]["username"] == "bob"


# ---------------------------------------------------------------- M00.F02.I02 创建成员


@pytest.mark.fn("M00.F02.I02")
def test_member_create_builds_user_and_member_rows(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(
        f"/api/v1/tenants/{T1}/members",
        headers=headers,
        json={
            "username": "dave",
            "password": "davepass123",
            "email": "dave@example.com",
            "mobile": "13800000001",
        },
    )
    assert resp.status_code == 200, resp.text  # 扁平视图（springboot 参照非 201）
    body = resp.json()
    dave_id = body["id"]
    assert body["tenantId"] == T1
    assert body["username"] == "dave"
    assert body["email"] == "dave@example.com"
    assert body["status"] == "active"
    assert body["roleIds"] == []
    with _db(client) as session:
        user = session.get(SysUser, uuid.UUID(dave_id))
        assert user is not None
        assert user.password == "plain:davepass123"  # 家族 dev 约定
        assert user.status == 1
        member = (
            session.query(TenantMember).filter_by(tenant_id=TENANT1, user_id=user.id).one_or_none()
        )
        assert member is not None
        assert member.member_name == "dave" and member.is_owner is False and member.status == 1
    # username 撞 unique → 400 constraint violation
    dup = client.post(
        f"/api/v1/tenants/{T1}/members",
        headers=headers,
        json={"username": "dave", "password": "whatever123", "email": "other@example.com"},
    )
    assert dup.status_code == 400, dup.text
    assert dup.json()["code"] == "BAD_REQUEST"


@pytest.mark.fn("M00.F02.I02")
def test_member_create_requires_email(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(
        f"/api/v1/tenants/{T1}/members",
        headers=headers,
        json={"username": "noemail", "password": "noemail123"},
    )
    assert resp.status_code == 400, resp.text  # springboot 参照：username+email 非空校验
    assert resp.json()["code"] == "BAD_REQUEST"


# ---------------------------------------------------------------- M00.F02.I03 成员详情


@pytest.mark.fn("M00.F02.I03")
def test_member_get_flat_view_with_raw_role_join(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"/api/v1/tenants/{T1}/members/{ALICE}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == str(ALICE)
    assert body["tenantId"] == T1
    assert body["username"] == "alice"
    assert body["status"] == "active"  # 读 member 行（S1 语义），不是 user 行
    # roleIds 真 join 原样吐出（含跨租户 ROLE2，不按租户过滤——家族 2026-09-12 教训）
    assert sorted(body["roleIds"]) == sorted([str(ROLE1), str(ROLE2)])
    # 本租户非成员（carol 只在 T2）→ 404
    not_member = client.get(f"/api/v1/tenants/{T1}/members/{CAROL}", headers=headers)
    assert not_member.status_code == 404, not_member.text
    unknown = client.get(f"/api/v1/tenants/{T1}/members/{uuid.uuid4()}", headers=headers)
    assert unknown.status_code == 404, unknown.text


# ---------------------------------------------------------------- M00.F02.I04 更新成员


@pytest.mark.fn("M00.F02.I04")
def test_member_patch_updates_email_mobile_only(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"/api/v1/tenants/{T1}/members/{BOB}",
        headers=headers,
        json={"email": "bob-new@example.com", "mobile": "13900000002"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "bob-new@example.com"
    with _db(client) as session:
        user = session.get(SysUser, BOB)
        assert user is not None
        assert user.email == "bob-new@example.com"
        assert user.mobile == "13900000002"


# ---------------------------------------------------------------- M00.F02.I05 删除成员


@pytest.mark.fn("M00.F02.I05")
def test_member_delete_breaks_membership_keeps_user(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.delete(f"/api/v1/tenants/{T1}/members/{BOB}", headers=headers)
    assert resp.status_code == 204, resp.text
    assert resp.text == ""
    with _db(client) as session:
        # membership 断了
        assert (
            session.query(TenantMember).filter_by(tenant_id=TENANT1, user_id=BOB).one_or_none()
            is None
        )
        # 全局 sys_user 保留（springboot：删除只断 membership）
        assert session.get(SysUser, BOB) is not None
    # 再删 → 404（先 resolve，与租户/订阅的幂等 DELETE 不对称）
    again = client.delete(f"/api/v1/tenants/{T1}/members/{BOB}", headers=headers)
    assert again.status_code == 404, again.text


# ---------------------------------------------------------------- M00.F02.I06 邀请成员


@pytest.mark.fn("M00.F02.I06")
def test_invite_creates_invited_user_active_member_nested_view(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(
        f"/api/v1/tenants/{T1}/members/invitations",
        headers=headers,
        json={"email": "newbie@example.com"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 嵌套视图 {member, user, roles}；roles 恒 []
    assert body["roles"] == []
    assert body["user"]["username"] == "newbie@example.com"
    assert body["user"]["status"] == "invited"  # user 行 invited（无凭据不可登录）
    assert body["member"]["status"] == "active"  # member 立即生效（I42 裁决）
    assert body["member"]["memberName"] == "newbie@example.com"
    assert body["member"]["tenantId"] == T1
    with _db(client) as session:
        user = session.get(SysUser, uuid.UUID(body["user"]["id"]))
        assert user is not None
        assert user.password == ""  # 无凭据
        assert user.status == 2
    # email trim 后空 → 400
    blank = client.post(
        f"/api/v1/tenants/{T1}/members/invitations", headers=headers, json={"email": "   "}
    )
    assert blank.status_code == 400, blank.text
    assert blank.json()["code"] == "BAD_REQUEST"
    # 已占邮箱 → 400（unique 撞，constraint violation 口径）
    dup = client.post(
        f"/api/v1/tenants/{T1}/members/invitations",
        headers=headers,
        json={"email": "alice@example.com"},
    )
    assert dup.status_code == 400, dup.text


# ---------------------------------------------------------------- M00.F02.I08 状态切换


@pytest.mark.fn("M00.F02.I08")
def test_member_status_dual_writes_member_and_user(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"/api/v1/tenants/{T1}/members/{BOB}/status", headers=headers, json={"status": "suspended"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "suspended"  # 扁平视图读 member 行
    with _db(client) as session:
        member = session.query(TenantMember).filter_by(tenant_id=TENANT1, user_id=BOB).one()
        user = session.get(SysUser, BOB)
        assert member.status == 3  # 双写：member 行
        assert user is not None and user.status == 3  # 双写：user 行
    # 切回 active
    back = client.patch(
        f"/api/v1/tenants/{T1}/members/{BOB}/status", headers=headers, json={"status": "active"}
    )
    assert back.status_code == 200 and back.json()["status"] == "active"


# ---------------------------------------------------------------- M01.F02.I01 分配角色


@pytest.mark.fn("M01.F02.I01")
def test_assign_roles_full_replace_ignores_foreign_roles(client: TestClient) -> None:
    headers = _bearer(client)
    # alice(T1) 当前绑定 [ROLE1, ROLE2]；全量替换为 [ROLE1]
    resp = client.put(
        f"/api/v1/tenants/{T1}/members/{ALICE}/roles",
        headers=headers,
        json={"roleIds": [str(ROLE1)]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["roleIds"] == [str(ROLE1)]
    # 外来租户 roleId（ROLE2 属 T2）静默忽略 → 空绑定
    foreign = client.put(
        f"/api/v1/tenants/{T1}/members/{ALICE}/roles",
        headers=headers,
        json={"roleIds": [str(ROLE2)]},
    )
    assert foreign.status_code == 200, foreign.text
    assert foreign.json()["roleIds"] == []
    # 混合：本租户的留下，外来的丢
    mixed = client.put(
        f"/api/v1/tenants/{T1}/members/{ALICE}/roles",
        headers=headers,
        json={"roleIds": [str(ROLE1), str(ROLE2)]},
    )
    assert mixed.status_code == 200 and mixed.json()["roleIds"] == [str(ROLE1)]
    with _db(client) as session:
        member = session.query(TenantMember).filter_by(tenant_id=TENANT1, user_id=ALICE).one()
        rows = session.query(t_tenant_member_role).filter_by(member_id=member.id).all()
        assert {str(r.role_id) for r in rows} == {str(ROLE1)}
    # 未知成员 → 404
    missing = client.put(
        f"/api/v1/tenants/{T1}/members/{uuid.uuid4()}/roles",
        headers=headers,
        json={"roleIds": [str(ROLE1)]},
    )
    assert missing.status_code == 404, missing.text


# ---------------------------------------------------------------- M00.F05 租户应用


@pytest.mark.fn("M00.F05.I01")
def test_tenant_applications_list(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"/api/v1/tenants/{T1}/applications", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page"] == 0 and body["pageSize"] == 20 and body["total"] == 1
    app = body["items"][0]
    assert app["clientId"] == CLIENT_ID
    assert app["tenantId"] == T1
    assert app["status"] == 1
    assert app["expireTime"] is None
    assert set(app) == {"id", "tenantId", "clientId", "status", "expireTime", "createdAt"}


@pytest.mark.fn("M00.F05.I02")
def test_subscribe_unknown_client_404_duplicate_400(client: TestClient) -> None:
    headers = _bearer(client)
    # 未知 clientId → 404（springboot 2026-09-12 修复：先查存在避免 FK 500）
    unknown = client.post(
        f"/api/v1/tenants/{T1}/applications",
        headers=headers,
        json={"clientId": "no-such-app"},
    )
    assert unknown.status_code == 404, unknown.text
    assert unknown.json()["code"] == "NOT_FOUND"
    # 正常订阅（expireTime 请求可带，但 springboot 参照不落库 → 响应 null）
    ok = client.post(
        f"/api/v1/tenants/{T1}/applications",
        headers=headers,
        json={"clientId": SECOND_CLIENT_ID, "expireTime": "2027-01-01T00:00:00Z"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["clientId"] == SECOND_CLIENT_ID
    assert ok.json()["status"] == 1
    assert "expireTime" not in ok.json()  # null 不落 JSON（NON_NULL 镜像，2026-10-03 裁定向家族对齐）
    # 重复订阅 → 400 constraint violation（无 409）
    dup = client.post(
        f"/api/v1/tenants/{T1}/applications",
        headers=headers,
        json={"clientId": CLIENT_ID},
    )
    assert dup.status_code == 400, dup.text
    assert dup.json()["code"] == "BAD_REQUEST"


@pytest.mark.fn("M00.F05.I03")
def test_application_patch_partial_and_404(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"/api/v1/tenants/{T1}/applications/{CLIENT_ID}",
        headers=headers,
        json={"status": 0, "expireTime": "2027-06-30T00:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == 0
    assert resp.json()["expireTime"] == "2027-06-30T00:00:00Z"
    missing = client.patch(
        f"/api/v1/tenants/{T1}/applications/no-such-app",
        headers=headers,
        json={"status": 1},
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.fn("M00.F05.I04")
def test_application_remove_idempotent_204(client: TestClient) -> None:
    headers = _bearer(client)
    first = client.delete(f"/api/v1/tenants/{T1}/applications/{CLIENT_ID}", headers=headers)
    assert first.status_code == 204, first.text
    assert first.text == ""
    with _db(client) as session:
        rows = session.execute(
            select(TenantApplication).where(
                TenantApplication.tenant_id == TENANT1,
                TenantApplication.client_id == CLIENT_ID,
            )
        ).all()
        assert rows == []
    # 幂等：不存在也 204
    again = client.delete(f"/api/v1/tenants/{T1}/applications/{CLIENT_ID}", headers=headers)
    assert again.status_code == 204, again.text


# ---------------------------------------------------------------- 守卫横切（应用面）


@pytest.mark.fn("M00.F05.I01")
def test_application_endpoints_guard_tenant(client: TestClient) -> None:
    headers = _bearer(client)  # alice 落 T1
    cross = client.get(f"/api/v1/tenants/{T2}/applications", headers=headers)
    assert cross.status_code == 403, cross.text
    assert cross.json()["code"] == "FORBIDDEN"
