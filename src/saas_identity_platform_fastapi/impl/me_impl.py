"""M01.F01 whoami + M04.F04.I08 当前用户有效菜单（springboot MeController 镜像）。

menus / tenants / switch-tenant 分批：menus 归批3（REQ-2026-001 T-3，本文件已实现）；
tenants 与 switch-tenant 归批4（M01.F03，REQ-2026-001 T-4），保持未实现语义
（500 NOT_IMPLEMENTED，家族错误形状）。
"""

from __future__ import annotations

from sqlalchemy import select

from saas_identity_platform_fastapi.apis.me_api_base import BaseMeApi
from saas_identity_platform_fastapi.entities import (
    SysMenu,
    SysUser,
    TenantMember,
    t_sys_role_menu,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.assemble import to_membership
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.errors import (
    InvalidCredentialsError,
    NotImplementedYetError,
)
from saas_identity_platform_fastapi.impl.menus_impl import menu_type_from_db
from saas_identity_platform_fastapi.impl.security import require_bearer, uuid_or_none
from saas_identity_platform_fastapi.models.current_user import CurrentUser
from saas_identity_platform_fastapi.models.effective_menu_node import EffectiveMenuNode
from saas_identity_platform_fastapi.models.switch_tenant_response import SwitchTenantResponse
from saas_identity_platform_fastapi.models.tenant_membership import TenantMembership


class MeApiImpl(BaseMeApi):
    async def me_whoami(self) -> CurrentUser:
        ctx = get_context()
        session = ctx.session
        claims = require_bearer(ctx, ctx.request.app.state.jwt)
        user_id = uuid_or_none(claims.get("sub"))
        if user_id is None:
            raise InvalidCredentialsError("Bearer sub required for whoami")
        members = (
            session.query(TenantMember)
            .filter_by(user_id=user_id)
            .order_by(TenantMember.created_at, TenantMember.id)
            .all()
        )
        memberships = [to_membership(session, m) for m in members]
        user = session.get(SysUser, user_id)
        # currentTenantId 优先取 JWT tenant_id claim；无 claim 落首个 membership 的 tenant
        claim_tenant = uuid_or_none(claims.get("tenant_id"))
        current_tenant_id = (
            claim_tenant
            if claim_tenant is not None
            else (memberships[0].tenant_id if memberships else None)
        )
        return CurrentUser(
            id=user_id,
            email=user.email if user is not None else None,
            memberships=memberships,
            currentTenantId=current_tenant_id,
        )

    # query clientId 参照实现未用（MeController 签名收但 body 恒全量；生成 router 位置传参）
    async def me_get_my_menus(self, _client_id: str | None) -> dict[str, list[EffectiveMenuNode]]:
        """M04.F04.I08：四跳 join（member→member_role→role_menu→sys_menu）按 clientId 组树。

        springboot MeController.assembleMenus/buildTree（:233-313）镜像：
        - 任何一环为空 → 空 Map；无 sub claim → 空 Map（:183-185 分支镜像）
        - 根判定：parent（零值 UUID 或孤儿——parent 不在授权集合）→ 当 root
        - 只排根层（sortOrder 升序），children 保持装载序（参照 :307-311）
        - 契约 EffectiveMenuNode.parentId 必填 UUID：零值/孤儿 parent 原样回显（不产 null）
        """
        ctx = get_context()
        session = ctx.session
        claims = require_bearer(ctx, ctx.request.app.state.jwt)
        user_id = uuid_or_none(claims.get("sub"))
        if user_id is None:
            return {}
        member_ids = (
            session.execute(select(TenantMember.id).where(TenantMember.user_id == user_id))
            .scalars()
            .all()
        )
        if not member_ids:
            return {}
        role_ids = (
            session.execute(
                select(t_tenant_member_role.c.role_id).where(
                    t_tenant_member_role.c.member_id.in_(member_ids)
                )
            )
            .scalars()
            .all()
        )
        if not role_ids:
            return {}
        menu_ids = (
            session.execute(
                select(t_sys_role_menu.c.menu_id).where(t_sys_role_menu.c.role_id.in_(role_ids))
            )
            .scalars()
            .all()
        )
        if not menu_ids:
            return {}
        menus = session.query(SysMenu).filter(SysMenu.id.in_(set(menu_ids))).all()
        # query clientId 被接收但完全未用于过滤/分组裁剪（MeController.meGetMyMenus 镜像：
        # 签名收 clientId 但 body 恒 assembleMenus(userId)）——恒返回全量分组 Map
        grouped: dict[str, list[SysMenu]] = {}
        for menu in menus:
            grouped.setdefault(menu.client_id, []).append(menu)

        def _build(rows: list[SysMenu]) -> list[EffectiveMenuNode]:
            nodes = {
                row.id: EffectiveMenuNode(
                    id=row.id,
                    clientId=row.client_id,
                    parentId=row.parent_id,
                    title=row.title,
                    type=menu_type_from_db(row.type),
                    path=row.path,
                    component=row.component,
                    perms=row.perms,
                    icon=row.icon,
                    sortOrder=row.sort_order,
                    children=[],
                )
                for row in rows
            }
            roots: list[EffectiveMenuNode] = []
            for row in rows:
                node = nodes[row.id]
                parent = nodes.get(row.parent_id)
                if parent is None or parent is node:
                    roots.append(node)  # 零值/孤儿 parent 不在授权集合 → root
                else:
                    parent.children.append(node)
            roots.sort(key=lambda n: n.sort_order)  # 只排根层（参照 :307-311）
            return roots

        return {client: _build(rows) for client, rows in grouped.items()}

    # 生成 router 以位置传参调用 Base 缝（apis/me_api.py），下划线前缀参数安全
    async def me_list_my_tenants(self, _client_id: str | None) -> list[TenantMembership]:
        raise NotImplementedYetError("me/tenants 归批4（M01.F03，REQ-2026-001 T-4）")

    async def me_switch_tenant(
        self, _tenant_id: str, _client_id: str | None
    ) -> SwitchTenantResponse:
        raise NotImplementedYetError("switch-tenant 归批4（M01.F03，REQ-2026-001 T-4）")
