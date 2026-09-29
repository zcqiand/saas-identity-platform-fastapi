"""M00.F04 角色菜单授权（springboot TenantRoleMenusController 镜像，REQ-2026-004）。

语义锚点（对照 springboot TenantRoleMenusController.java）：
- TenantGuard 同租户面；但 role **只 findById 不校验租户归属**（:129-132，与 roles 组
  findRoleInTenant 的 404 口径不同——两组口径不一致是参照实现真实现状，逐组镜像）
- GET：RoleMenuGrant{roleId, tenantId, menuIds 字典序 sorted, updatedAt=sys_role.updated_at}
- PUT 全量替换（:76-107）：坏 menuId UUID → 400（parseMenuIds 先于 role 解析）；role
  不存在 → 404；差量删不在新集合的行 + 新增行幂等插入；**touch sys_role.updated_at**
  （:105，聚合 updatedAt 来源）；响应直接从请求集合构造（sorted、不回读 DB）；
  不存在的 menuId 撞 FK → 400；外 client 的 menu 静默接受；空 menuIds = 合法清空
- DELETE：纯 bulk delete **幂等 204**——不 resolve role、不存在也 204、**不 touch updatedAt**
"""

# ruff: noqa: N803, ARG002 —— Base*Api 缝方法形参名镜像生成契约（tenantId/roleId camelCase）
# 不可改名也不可删（生成 router 位置传参）；query clientId 在参照实现中就未参与语义。

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.tenant_role_menus_api_base import BaseTenantRoleMenusApi
from saas_identity_platform_fastapi.entities import SysRole, t_sys_role_menu
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import uuid_or_bad_request
from saas_identity_platform_fastapi.impl.errors import BadRequestError, NotFoundError
from saas_identity_platform_fastapi.impl.security import as_utc, now_utc, verify_path_tenant
from saas_identity_platform_fastapi.models.role_menu_grant import RoleMenuGrant
from saas_identity_platform_fastapi.models.set_sys_role_menus_request import (
    SetSysRoleMenusRequest,
)


def _resolve_role(session: Session, role_id: str) -> SysRole:
    """纯 findById（不校验 tenant 归属，:129-132 镜像）；不存在 → 404。"""
    row = session.get(SysRole, uuid_or_bad_request(role_id))
    if row is None:
        raise NotFoundError(f"role not found: {role_id}")
    return row


def _grant_of(role: SysRole, menu_ids: list[str]) -> RoleMenuGrant:
    return RoleMenuGrant(
        roleId=role.id,
        tenantId=role.tenant_id,
        menuIds=sorted(menu_ids),
        updatedAt=as_utc(role.updated_at),
    )


class TenantRoleMenusApiImpl(BaseTenantRoleMenusApi):
    async def tenant_role_menus_list_sys_role_menus(
        self,
        tenantId: str,
        roleId: str,
        client_id: str | None,  # noqa: N803
    ) -> RoleMenuGrant:
        ctx = get_context()
        verify_path_tenant(ctx, tenantId)
        role = _resolve_role(ctx.session, roleId)
        rows = ctx.session.execute(
            select(t_sys_role_menu.c.menu_id).where(t_sys_role_menu.c.role_id == role.id)
        ).all()
        # query clientId 接收但不过滤（参照 list 端点无 clientId 语义，镜像忽略）
        return _grant_of(role, [str(row[0]) for row in rows])

    async def tenant_role_menus_set_sys_role_menus(
        self,
        tenantId: str,  # noqa: N803
        roleId: str,  # noqa: N803
        set_sys_role_menus_request: SetSysRoleMenusRequest,
        client_id: str | None,  # noqa: N803
    ) -> RoleMenuGrant:
        ctx = get_context()
        verify_path_tenant(ctx, tenantId)
        # parseMenuIds 先于 role 解析：坏 UUID → 400（参照 :76-85 顺序）
        requested: list[str] = []
        for raw in set_sys_role_menus_request.menu_ids:
            menu_id = uuid_or_bad_request(raw)
            if str(menu_id) not in requested:  # LinkedHashSet 去重镜像
                requested.append(str(menu_id))
        session = ctx.session
        role = _resolve_role(session, roleId)
        if requested:
            kept = [uuid.UUID(u) for u in requested]
            # 差量删：只删不在新集合里的行（SysRoleMenuRepository deleteByRoleIdAndMenuIdNotIn）
            session.execute(
                delete(t_sys_role_menu).where(
                    t_sys_role_menu.c.role_id == role.id,
                    t_sys_role_menu.c.menu_id.not_in(kept),
                )
            )
            existing = set(
                session.execute(
                    select(t_sys_role_menu.c.menu_id).where(t_sys_role_menu.c.role_id == role.id)
                )
                .scalars()
                .all()
            )
            new_rows = [
                {"role_id": role.id, "menu_id": menu_id}
                for menu_id in kept
                if menu_id not in existing
            ]
        else:
            # 空集 = 合法清空（deleteAllForRole）
            session.execute(delete(t_sys_role_menu).where(t_sys_role_menu.c.role_id == role.id))
            new_rows = []
        role.updated_at = now_utc()  # touch：聚合 updatedAt 来源（参照 :105）
        # 不存在的 menuId 撞 FK：IntegrityError 在 insert 执行期（非 commit 期）即抛，故
        # insert+commit 同包一个收口；回滚则 touch 一并撤销（同参照事务语义）
        try:
            if new_rows:
                session.execute(t_sys_role_menu.insert(), new_rows)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise BadRequestError(f"constraint violation: role menus set: {exc.orig}") from exc
        # 响应从请求集合构造（sorted、不回读 DB，toGrantFromRequested 镜像）
        return RoleMenuGrant(
            roleId=role.id,
            tenantId=role.tenant_id,
            menuIds=sorted(requested),
            updatedAt=as_utc(role.updated_at),
        )

    async def tenant_role_menus_clear_sys_role_menus(
        self,
        tenantId: str,
        roleId: str,
        client_id: str | None,  # noqa: N803
    ) -> None:
        ctx = get_context()
        verify_path_tenant(ctx, tenantId)
        # 不 resolve role：纯 bulk delete 幂等，不存在也 204，不 touch updatedAt
        ctx.session.execute(
            delete(t_sys_role_menu).where(t_sys_role_menu.c.role_id == uuid_or_bad_request(roleId))
        )
        ctx.session.commit()
        return None
