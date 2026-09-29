"""M01.F01 whoami（springboot MeController 镜像，REQ-2026-002）。

menus / tenants / switch-tenant 归总纲后续批（REQ-2026-001 T-2/T-3/T-4），
本批保持未实现语义（500 NOT_IMPLEMENTED，家族错误形状）。
"""

from __future__ import annotations

from saas_identity_platform_fastapi.apis.me_api_base import BaseMeApi
from saas_identity_platform_fastapi.entities import SysUser, TenantMember
from saas_identity_platform_fastapi.impl.assemble import to_membership
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.errors import (
    InvalidCredentialsError,
    NotImplementedYetError,
)
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

    # 生成 router 以位置传参调用 Base 缝（apis/me_api.py），下划线前缀参数安全
    async def me_get_my_menus(self, _client_id: str | None) -> dict[str, list[EffectiveMenuNode]]:
        raise NotImplementedYetError("me/menus 归批3（REQ-2026-001 T-3）")

    async def me_list_my_tenants(self, _client_id: str | None) -> list[TenantMembership]:
        raise NotImplementedYetError("me/tenants 归批2（REQ-2026-001 T-2）")

    async def me_switch_tenant(
        self, _tenant_id: str, _client_id: str | None
    ) -> SwitchTenantResponse:
        raise NotImplementedYetError("switch-tenant 归批4（REQ-2026-001 T-4）")
