"""M01.F01 whoami + M01.F03 我的租户/切换 + M04.F04.I08 有效菜单（springboot MeController 镜像）。

menus 归批3（REQ-2026-001 T-3）、tenants 与 switch-tenant 归批4（REQ-2026-005），
本文件三组均已实现；生成缝内已无未实现端点。
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import select

from saas_identity_platform_fastapi.apis.me_api_base import BaseMeApi
from saas_identity_platform_fastapi.entities import (
    SysMenu,
    SysUser,
    Tenant,
    TenantMember,
    t_sys_role_menu,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.assemble import to_membership
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import uuid_or_bad_request
from saas_identity_platform_fastapi.impl.errors import InvalidCredentialsError, NotFoundError
from saas_identity_platform_fastapi.impl.menus_impl import menu_type_from_db
from saas_identity_platform_fastapi.impl.security import now_utc, require_bearer, uuid_or_none
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
        - 根 sentinel（parent_id 零值 UUID）→ parentId null（参照 :273-276 四后端实测口径；
          契约 requiredMode=REQUIRED 是滞后声明，live 比对 normalize 全等为准，REQ-2026-006）；
          孤儿（parent 非零且不在授权集合）parentId 原样回显仍当 root（:291-298 镜像）
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
        # core Table 列经 .scalars().all() 泛型退化为 Sequence[Never]（sqlalchemy 2.1
        # + mypy strict）——列类型实为 UUID，cast 显式声明（CI mypy 1.20.2 修复批）
        role_ids = cast(
            "list[uuid.UUID]",
            session.execute(
                select(t_tenant_member_role.c.role_id).where(
                    t_tenant_member_role.c.member_id.in_(member_ids)
                )
            )
            .scalars()
            .all(),
        )
        if not role_ids:
            return {}
        menu_ids = cast(
            "list[uuid.UUID]",
            session.execute(
                select(t_sys_role_menu.c.menu_id).where(t_sys_role_menu.c.role_id.in_(role_ids))
            )
            .scalars()
            .all(),
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
            zero_uuid = UUID(int=0)

            def _node(row: SysMenu) -> EffectiveMenuNode:
                # 契约 parent_id 声明必填 UUID，参照实测序列化 null——构造器会拒 None，
                # 走 model_construct 绕开校验层（生成区禁改，响应序列化 parent_id: null）
                return EffectiveMenuNode.model_construct(
                    id=row.id,
                    client_id=row.client_id,
                    parent_id=None if row.parent_id == zero_uuid else row.parent_id,
                    title=row.title,
                    type=menu_type_from_db(row.type),
                    path=row.path,
                    component=row.component,
                    perms=row.perms,
                    icon=row.icon,
                    sort_order=row.sort_order,
                    children=[],
                )

            nodes = {row.id: _node(row) for row in rows}
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
        """M01.F03.I01：当前用户全部租户成员关系（springboot membershipsOf :146-148 镜像）。

        - 排序 created_at ASC + id ASC（TenantMemberRepository :30-31，固定序防首个漂移）
        - 不过滤 status（四值全回）；query clientId 收但忽略（契约残留，参照同样忽略）
        - roleIds 经 to_membership 全量 join、跨租户原样吐出（与 whoami 同一装配器）
        """
        ctx = get_context()
        session = ctx.session
        claims = require_bearer(ctx, ctx.request.app.state.jwt)
        user_id = uuid_or_none(claims.get("sub"))
        if user_id is None:
            return []
        members = (
            session.query(TenantMember)
            .filter_by(user_id=user_id)
            .order_by(TenantMember.created_at, TenantMember.id)
            .all()
        )
        return [to_membership(session, m) for m in members]

    async def me_switch_tenant(
        self, _tenant_id: str, _client_id: str | None
    ) -> SwitchTenantResponse:
        """M01.F03.I02：切换当前租户（springboot MeController :111-143 镜像）。

        校验链：无 sub → 401；坏 UUID → 400；租户不存在 → 404；成员资格门槛 =
        **非 disabled**（status 非 0 且非 NULL，S5 口径：invited/suspended 可切），
        不满足 → 404 "is not an active member"（不是 403）。签发新 access（tenant_id
        claim=目标租户，旧 token 不失效）；refresh 纯构造**不落库**（参照
        generateRefreshToken，rotate 语义归 /auth/refresh）；无 DB 写天然幂等。
        响应镜像参照四字段：accessToken/refreshToken/expiresAt（now+TTL）/tenantId。
        """
        ctx = get_context()
        session = ctx.session
        claims = require_bearer(ctx, ctx.request.app.state.jwt)
        user_id = uuid_or_none(claims.get("sub"))
        if user_id is None:
            raise InvalidCredentialsError("Bearer sub required for tenant switch")
        tenant_id = uuid_or_bad_request(_tenant_id)
        if session.get(Tenant, tenant_id) is None:
            raise NotFoundError(f"tenant {tenant_id}")
        members = session.query(TenantMember).filter_by(user_id=user_id).all()
        if not any(
            m.tenant_id == tenant_id and m.status is not None and m.status != 0 for m in members
        ):
            raise NotFoundError(f"user {user_id} is not an active member of tenant {tenant_id}")
        issuer = ctx.request.app.state.jwt
        # refresh 纯构造不落库，格式镜像 springboot generateRefreshToken（:146-152）
        refresh = f"saas-rt-{user_id}-{int(now_utc().timestamp() * 1000)}-{uuid.uuid4()}"
        return SwitchTenantResponse(
            accessToken=issuer.issue_access_token(user_id, tenant_id),
            refreshToken=refresh,
            expiresAt=now_utc() + timedelta(seconds=issuer.ttl_seconds),  # 参照 :139
            tenantId=tenant_id,
        )
