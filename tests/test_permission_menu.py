"""批3 权限与菜单断言（REQ-2026-004；语义参照 saas-identity-platform-springboot）。

三组端点：tenant roles（TenantGuard+跨租户 404）+ tenant role-menus（全量替换+幂等清空）
+ client menus（无租户守卫）+ me/menus（四跳 join 组树）。scratch/PG 基建见 conftest.py。
家族语义：冲突一律 400（无 409）；DELETE 不对称——role 先 resolve 404、
role-menus clear 与 menu 删除幂等 204；roles 排序 created_at ASC（与成员面 DESC 相反）。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.entities import (
    SysMenu,
    SysRole,
    t_sys_role_menu,
    t_tenant_member_role,
)
from tests.conftest import (
    CLIENT_ID,
    MENU_DASH,
    MENU_DIR,
    MENU_ORPHAN,
    MENU_ORPHAN_PARENT,
    MENU_USERS,
    ROLE1,
    ROLE2,
    SECOND_CLIENT_ID,
    TENANT1,
    TENANT2,
    ZERO_UUID,
    _bearer,
)

T1 = str(TENANT1)
T2 = str(TENANT2)
ROLES = "/api/v1/tenants"


def _db(client: TestClient) -> Session:
    return Session(client.app.state.engine)


# ---------------------------------------------------------------- M00.F03 租户角色


@pytest.mark.fn("M00.F03.I01")
def test_roles_list_asc_order_and_clientid_param_ignored(client: TestClient) -> None:
    headers = _bearer(client)
    # 种子 ROLE1（created_at 最早）+ 新建两个 → ASC：ROLE1 在前，两个新角色按创建序
    for code in ("role_a", "role_b"):
        made = client.post(
            f"{ROLES}/{T1}/roles",
            headers=headers,
            json={"clientId": CLIENT_ID, "roleCode": code, "roleName": code},
        )
        assert made.status_code == 200, made.text
    resp = client.get(f"{ROLES}/{T1}/roles", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3 and body["page"] == 0 and body["pageSize"] == 20
    codes = [item["roleCode"] for item in body["items"]]
    assert codes == ["admin", "role_a", "role_b"]
    one = body["items"][0]
    assert set(one) == {
        "id",
        "tenantId",
        "clientId",
        "roleCode",
        "roleName",
        "description",
        "isPreset",
        "status",
        "createdAt",
        "updatedAt",
    }
    # query clientId 被接收但完全不过滤（springboot 参照：只按 path tenantId 过滤）
    filtered = client.get(
        f"{ROLES}/{T1}/roles", headers=headers, params={"clientId": SECOND_CLIENT_ID}
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["total"] == 3
    # 分页裁剪
    paged = client.get(f"{ROLES}/{T1}/roles", headers=headers, params={"page": 1, "pageSize": 2})
    assert len(paged.json()["items"]) == 1
    assert paged.json()["total"] == 3


@pytest.mark.fn("M00.F03.I01")
def test_roles_requires_bearer_and_tenant_guard(client: TestClient) -> None:
    resp = client.get(f"{ROLES}/{T1}/roles")
    assert resp.status_code == 401, resp.text
    headers = _bearer(client)  # alice claim tenant=T1
    foreign = client.get(f"{ROLES}/{T2}/roles", headers=headers)
    assert foreign.status_code == 403, foreign.text
    assert foreign.json()["code"] == "FORBIDDEN"


@pytest.mark.fn("M00.F03.I02")
def test_roles_create_defaults_and_conflicts(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.post(
        f"{ROLES}/{T1}/roles",
        headers=headers,
        json={"clientId": CLIENT_ID, "roleCode": "editor", "roleName": "编辑者"},
    )
    assert resp.status_code == 200, resp.text  # create 返回 200 非 201
    body = resp.json()
    assert body["roleCode"] == "editor" and body["status"] == 1
    assert body["isPreset"] is False  # isPreset 缺省 false
    assert body["tenantId"] == T1
    assert "description" not in body  # null 不落 JSON（NON_NULL 镜像，2026-10-03 裁定向家族对齐）
    explicit = client.post(
        f"{ROLES}/{T1}/roles",
        headers=headers,
        json={
            "clientId": CLIENT_ID,
            "roleCode": "viewer",
            "roleName": "观察者",
            "description": "只读",
            "isPreset": True,
        },
    )
    assert explicit.status_code == 200, explicit.text
    assert explicit.json()["isPreset"] is True and explicit.json()["description"] == "只读"
    # clientId 不校验租户订阅关系——已注册未订阅的 SECOND_CLIENT_ID 也成功（springboot 参照）
    unsub = client.post(
        f"{ROLES}/{T1}/roles",
        headers=headers,
        json={"clientId": SECOND_CLIENT_ID, "roleCode": "x", "roleName": "x"},
    )
    assert unsub.status_code == 200, unsub.text
    # roleCode 撞 uk(tenant,client,role_code) → 400 constraint violation（无 409）
    dup = client.post(
        f"{ROLES}/{T1}/roles",
        headers=headers,
        json={"clientId": CLIENT_ID, "roleCode": "editor", "roleName": "重复"},
    )
    assert dup.status_code == 400, dup.text
    assert dup.json()["code"] == "BAD_REQUEST"
    # 未注册 clientId 撞 FK → 400（不是 404）
    fk = client.post(
        f"{ROLES}/{T1}/roles",
        headers=headers,
        json={"clientId": "no-such-app", "roleCode": "y", "roleName": "y"},
    )
    assert fk.status_code == 400, fk.text


@pytest.mark.fn("M00.F03.I03")
def test_roles_get_unknown_and_cross_tenant_both_404(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"{ROLES}/{T1}/roles/{ROLE1}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["roleCode"] == "admin"
    missing = client.get(f"{ROLES}/{T1}/roles/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404, missing.text
    # 跨租户角色经本租户路径访问 → 404（不泄露存在性，与 TenantGuard 403 是两回事）
    cross = client.get(f"{ROLES}/{T1}/roles/{ROLE2}", headers=headers)
    assert cross.status_code == 404, cross.text


@pytest.mark.fn("M00.F03.I04")
def test_roles_patch_applies_name_description_ignores_status(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"{ROLES}/{T1}/roles/{ROLE1}",
        headers=headers,
        json={"roleName": "超级管理员", "description": "改过", "status": 0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["roleName"] == "超级管理员" and body["description"] == "改过"
    assert body["status"] == 1  # status 字段被忽略（springboot 参照只应用 roleName/description）
    assert body["roleCode"] == "admin"  # roleCode 不可改


@pytest.mark.fn("M00.F03.I05")
def test_roles_delete_resolves_then_cascades(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.delete(f"{ROLES}/{T1}/roles/{ROLE1}", headers=headers)
    assert resp.status_code == 204, resp.text
    again = client.delete(f"{ROLES}/{T1}/roles/{ROLE1}", headers=headers)
    assert again.status_code == 404, again.text  # 先 resolve → 非幂等
    with _db(client) as session:
        # 级联清 sys_role_menu + tenant_member_role（DB FK CASCADE）
        assert (
            session.execute(select(t_sys_role_menu).where(t_sys_role_menu.c.role_id == ROLE1)).all()
            == []
        )
        assert (
            session.execute(
                select(t_tenant_member_role).where(t_tenant_member_role.c.role_id == ROLE1)
            ).all()
            == []
        )


# ---------------------------------------------------------------- M00.F04 角色权限（role↔menu）


@pytest.mark.fn("M00.F04.I02")
def test_role_menus_get_sorted_grants(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"{ROLES}/{T1}/roles/{ROLE1}/menus", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["roleId"] == str(ROLE1) and body["tenantId"] == T1
    assert body["menuIds"] == sorted(
        [str(MENU_DIR), str(MENU_USERS), str(MENU_DASH), str(MENU_ORPHAN)]
    )
    missing = client.get(f"{ROLES}/{T1}/roles/{uuid.uuid4()}/menus", headers=headers)
    assert missing.status_code == 404, missing.text


@pytest.mark.fn("M00.F04.I03")
def test_role_menus_put_full_replace_and_fk_400(client: TestClient) -> None:
    headers = _bearer(client)
    with _db(client) as session:
        before = session.get(SysRole, ROLE1).updated_at
    resp = client.put(
        f"{ROLES}/{T1}/roles/{ROLE1}/menus",
        headers=headers,
        json={"menuIds": [str(MENU_DASH), str(MENU_USERS)]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 响应直接从请求集合构造（sorted、不回读 DB）
    assert body["menuIds"] == sorted([str(MENU_DASH), str(MENU_USERS)])
    with _db(client) as session:
        rows = (
            session.execute(
                select(t_sys_role_menu.c.menu_id).where(t_sys_role_menu.c.role_id == ROLE1)
            )
            .scalars()
            .all()
        )
        assert set(rows) == {MENU_DASH, MENU_USERS}  # 差量替换：DIR/ORPHAN 被删
        after = session.get(SysRole, ROLE1).updated_at
    assert after > before  # PUT touch sys_role.updated_at（聚合 updatedAt 来源）
    # 不存在的 menuId 撞 FK → 400（不是静默忽略）
    fk = client.put(
        f"{ROLES}/{T1}/roles/{ROLE1}/menus",
        headers=headers,
        json={"menuIds": [str(uuid.uuid4())]},
    )
    assert fk.status_code == 400, fk.text
    assert fk.json()["code"] == "BAD_REQUEST"
    # 坏 UUID menuId → 400
    bad = client.put(
        f"{ROLES}/{T1}/roles/{ROLE1}/menus", headers=headers, json={"menuIds": ["nope"]}
    )
    assert bad.status_code == 400, bad.text
    # 空 menuIds = 合法清空
    empty = client.put(f"{ROLES}/{T1}/roles/{ROLE1}/menus", headers=headers, json={"menuIds": []})
    assert empty.status_code == 200, empty.text
    assert empty.json()["menuIds"] == []
    with _db(client) as session:
        assert (
            session.execute(select(t_sys_role_menu).where(t_sys_role_menu.c.role_id == ROLE1)).all()
            == []
        )


@pytest.mark.fn("M00.F04.I04")
def test_role_menus_clear_idempotent_no_touch(client: TestClient) -> None:
    headers = _bearer(client)
    with _db(client) as session:
        before = session.get(SysRole, ROLE1).updated_at
    resp = client.delete(f"{ROLES}/{T1}/roles/{ROLE1}/menus", headers=headers)
    assert resp.status_code == 204, resp.text
    again = client.delete(f"{ROLES}/{T1}/roles/{ROLE1}/menus", headers=headers)
    assert again.status_code == 204, again.text  # 纯 bulk delete 幂等
    unknown = client.delete(f"{ROLES}/{T1}/roles/{uuid.uuid4()}/menus", headers=headers)
    assert unknown.status_code == 204, unknown.text  # 不 resolve role，不存在也 204
    with _db(client) as session:
        assert session.get(SysRole, ROLE1).updated_at == before  # DELETE 不 touch updatedAt


# ---------------------------------------------------------------- M04.F04 菜单管理（client menus）


@pytest.mark.fn("M04.F04.I01")
def test_client_menus_list_flat_and_auth(client: TestClient) -> None:
    bare = client.get(f"/api/v1/clients/{CLIENT_ID}/menus")
    assert bare.status_code == 401, bare.text
    headers = _bearer(client)
    resp = client.get(f"/api/v1/clients/{CLIENT_ID}/menus", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert {m["id"] for m in items} == {
        str(MENU_DIR),
        str(MENU_USERS),
        str(MENU_DASH),
        str(MENU_ORPHAN),
    }  # 扁平不分页、不含第二应用菜单
    one = next(m for m in items if m["id"] == str(MENU_USERS))
    assert one["parentId"] == str(MENU_DIR) and one["type"] == "menu"
    assert one["perms"] == "sys:user:list"


@pytest.mark.fn("M04.F04.I02")
def test_client_menus_create_defaults(client: TestClient) -> None:
    headers = _bearer(client)
    # 生成契约 CreateSysMenuRequest.type 必填（springboot DTO 容 null 的差异点）——
    # 校验层 422 由组合根收口成家族契约 400 BAD_REQUEST（REQ-2026-006 批5 live 实裁）
    missing_type = client.post(
        f"/api/v1/clients/{CLIENT_ID}/menus", headers=headers, json={"title": "新建"}
    )
    assert missing_type.status_code == 400, missing_type.text
    assert missing_type.json()["code"] == "BAD_REQUEST"
    resp = client.post(
        f"/api/v1/clients/{CLIENT_ID}/menus",
        headers=headers,
        json={"title": "新建", "type": "directory"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["parentId"] == str(ZERO_UUID)  # parentId null → 零值 UUID
    assert body["type"] == "directory"
    assert body["sortOrder"] == 0 and body["status"] == 1
    assert body["clientId"] == CLIENT_ID
    # type 枚举 + parent 不校验存在（parent_id 无 FK，镜像参照）
    child = client.post(
        f"/api/v1/clients/{CLIENT_ID}/menus",
        headers=headers,
        json={"title": "按钮", "type": "button", "parentId": str(uuid.uuid4()), "sortOrder": 7},
    )
    assert child.status_code == 200, child.text
    assert child.json()["type"] == "button" and child.json()["sortOrder"] == 7


@pytest.mark.fn("M04.F04.I03")
def test_client_menus_get_cross_client_readable(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.get(f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_DASH}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "仪表盘"
    missing = client.get(f"/api/v1/clients/{CLIENT_ID}/menus/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404, missing.text
    # 不比对 clientId（跨 client 路径可读，镜像参照）
    cross = client.get(f"/api/v1/clients/{SECOND_CLIENT_ID}/menus/{MENU_DASH}", headers=headers)
    assert cross.status_code == 200, cross.text
    assert cross.json()["clientId"] == CLIENT_ID  # 行归属仍是原 client


@pytest.mark.fn("M04.F04.I04")
def test_client_menus_patch_applies_five_ignores_rest(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_USERS}",
        headers=headers,
        json={
            "title": "用户管理",
            "path": "/members",
            "component": "members/index",
            "perms": "sys:member:list",
            "icon": "users",
            "sortOrder": 9,
            "parentId": str(MENU_DASH),
            "type": "button",
            "status": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "用户管理" and body["path"] == "/members"
    assert body["component"] == "members/index" and body["perms"] == "sys:member:list"
    assert body["icon"] == "users" and body["sortOrder"] == 9
    # parentId/type/status 三个字段被忽略（springboot 参照只应用五字段）
    assert body["parentId"] == str(MENU_DIR)
    assert body["type"] == "menu" and body["status"] == 1


@pytest.mark.fn("M04.F04.I05")
def test_client_menus_delete_idempotent_cascade_scope(client: TestClient) -> None:
    headers = _bearer(client)
    # 先建父+子：删除父只清授权不清子（parent_id 无 FK，镜像参照）
    parent = client.post(
        f"/api/v1/clients/{CLIENT_ID}/menus",
        headers=headers,
        json={"title": "父", "type": "menu"},
    ).json()
    child = client.post(
        f"/api/v1/clients/{CLIENT_ID}/menus",
        headers=headers,
        json={"title": "子", "type": "menu", "parentId": parent["id"]},
    ).json()
    resp = client.delete(f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_DASH}", headers=headers)
    assert resp.status_code == 204, resp.text
    again = client.delete(f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_DASH}", headers=headers)
    assert again.status_code == 204, again.text  # 幂等（不 resolve 404）
    with _db(client) as session:
        # 级联只清 sys_role_menu 授权（MENU_DASH 原本授权给 ROLE1）
        assert (
            session.execute(
                select(t_sys_role_menu).where(
                    t_sys_role_menu.c.role_id == ROLE1,
                    t_sys_role_menu.c.menu_id == MENU_DASH,
                )
            ).all()
            == []
        )
        assert session.get(SysMenu, child["id"]) is not None  # 子菜单不级联


@pytest.mark.fn("M04.F04.I06")
def test_client_menus_reorder_writes_only_target(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.put(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_DASH}/reorder",
        headers=headers,
        json={"orderedMenuIds": [str(MENU_ORPHAN), str(MENU_DASH), str(MENU_DIR)]},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert {m["id"] for m in items} >= {str(MENU_DIR), str(MENU_USERS), str(MENU_DASH)}
    by_id = {m["id"]: m for m in items}
    assert by_id[str(MENU_DASH)]["sortOrder"] == 1  # 目标 menu 的 sortOrder = 其在列表中的下标
    assert by_id[str(MENU_DIR)]["sortOrder"] == 2  # 列表内其他 menu 的 sortOrder 不写库
    assert by_id[str(MENU_USERS)]["sortOrder"] == 0  # 列表外 menu 完全不动
    # 目标不在列表 → 不动（idx<0 跳过）
    untouched = client.put(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_DASH}/reorder",
        headers=headers,
        json={"orderedMenuIds": [str(MENU_DIR)]},
    )
    assert untouched.status_code == 200, untouched.text
    still = {m["id"]: m for m in untouched.json()}
    assert still[str(MENU_DASH)]["sortOrder"] == 1
    missing = client.put(
        f"/api/v1/clients/{CLIENT_ID}/menus/{uuid.uuid4()}/reorder",
        headers=headers,
        json={"orderedMenuIds": [str(MENU_DIR)]},
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.fn("M04.F04.I07")
def test_client_menus_move_parent(client: TestClient) -> None:
    headers = _bearer(client)
    resp = client.patch(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_USERS}/parent",
        headers=headers,
        json={"parentId": str(MENU_DASH)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parentId"] == str(MENU_DASH)
    # parentId null → 不改（springboot 参照：非 null 才应用）
    keep = client.patch(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_USERS}/parent",
        headers=headers,
        json={"parentId": None},
    )
    assert keep.status_code == 200, keep.text
    assert keep.json()["parentId"] == str(MENU_DASH)
    # 坏 UUID → 400
    bad = client.patch(
        f"/api/v1/clients/{CLIENT_ID}/menus/{MENU_USERS}/parent",
        headers=headers,
        json={"parentId": "not-a-uuid"},
    )
    assert bad.status_code == 400, bad.text
    missing = client.patch(
        f"/api/v1/clients/{CLIENT_ID}/menus/{uuid.uuid4()}/parent",
        headers=headers,
        json={"parentId": str(MENU_DIR)},
    )
    assert missing.status_code == 404, missing.text


# ---------------------------------------------------------------- M04.F04.I08 当前用户菜单


@pytest.mark.fn("M04.F04.I08")
def test_me_menus_tree_grouping_orphan_and_order(client: TestClient) -> None:
    headers = _bearer(client)  # alice@T1，ROLE1 授权 DIR/USERS/DASH/ORPHAN
    resp = client.get("/api/v1/me/menus", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 授权只覆盖 saas-console 菜单 → 第二应用不出现在分组里
    assert set(body) == {CLIENT_ID}
    tree = body[CLIENT_ID]
    # roots 按 sortOrder 升序：DASH(1)、DIR(2，带子 USERS)、ORPHAN(5，孤儿当根)
    assert [node["title"] for node in tree] == ["仪表盘", "权限管理", "孤儿菜单"]
    dash, directory, orphan = tree
    assert dash["children"] == []
    # 根 sentinel：parent_id 零值 UUID → parentId null（参照 MeController:273 四后端实测，
    # REQ-2026-006 批5 live 实裁；契约 requiredMode=REQUIRED 为滞后声明）
    assert dash["parentId"] is None
    assert [c["title"] for c in directory["children"]] == ["用户列表"]
    users = directory["children"][0]
    assert users["parentId"] == str(MENU_DIR)
    assert users["path"] == "/users" and users["perms"] == "sys:user:list"
    # 孤儿（parent 不在授权集合）也当 root；非零 parent 原样回显（契约 parentId 必填 UUID）
    assert orphan["parentId"] == str(MENU_ORPHAN_PARENT)
    # query clientId 签名收但 body 恒全量（MeController 镜像）——点名第二应用也是同一份
    scoped = client.get("/api/v1/me/menus", headers=headers, params={"clientId": SECOND_CLIENT_ID})
    assert scoped.status_code == 200, scoped.text
    assert scoped.json() == body


@pytest.mark.fn("M04.F04.I08")
def test_me_menus_empty_for_member_without_grants(client: TestClient) -> None:
    headers = _bearer(client, username="carol", password="carolpass")  # carol@T2，ROLE2 无授权
    resp = client.get("/api/v1/me/menus", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {}


@pytest.mark.fn("M04.F04.I08")
def test_me_menus_requires_bearer(client: TestClient) -> None:
    resp = client.get("/api/v1/me/menus")
    assert resp.status_code == 401, resp.text
