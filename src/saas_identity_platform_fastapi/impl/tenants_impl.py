"""M00.F01 租户维护 —— 平台 admin 域 CRUD（springboot AdminTenantsController 镜像，REQ-2026-003）。

语义锚点（对照 springboot AdminTenantsController.java）：
- 平台域 dev 简化：只要求有效 JWT（不挂 TenantGuard，springboot anyRequest().authenticated 参照）
- list 无排序；page 0-based 默认 0/20；读路径 status 恒 active（springboot 参照实现即此语义）
- create 返回 200（生成契约无 201）；status 写 1；tenantKey 撞 unique → 400 constraint violation
- PATCH 部分更新（null 字段跳过）；ACTIVE → 1 / 其他 → 0
- DELETE 幂等：不存在也 204（级联靠 DB FK；组合根把 200 null 收口 204）
"""

from __future__ import annotations

import uuid

from saas_identity_platform_fastapi.apis.admin_tenants_api_base import BaseAdminTenantsApi
from saas_identity_platform_fastapi.entities import Tenant
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import commit_or_bad_request, page_window
from saas_identity_platform_fastapi.impl.errors import NotFoundError
from saas_identity_platform_fastapi.impl.security import as_utc, now_utc, require_bearer
from saas_identity_platform_fastapi.models.admin_tenants_list_tenants200_response import (
    AdminTenantsListTenants200Response,
)
from saas_identity_platform_fastapi.models.create_tenant_request import CreateTenantRequest
from saas_identity_platform_fastapi.models.tenant import Tenant as TenantDto
from saas_identity_platform_fastapi.models.tenant_status import TenantStatus
from saas_identity_platform_fastapi.models.update_tenant_request import UpdateTenantRequest


def _tenant_dto(row: Tenant) -> TenantDto:
    # 读路径 status 恒 active（springboot 参照实现 96 行起即此语义：DTO 只认枚举不分档）
    return TenantDto(
        id=row.id,
        tenantKey=row.tenant_key,
        name=row.name,
        status=TenantStatus("active"),
        createdAt=as_utc(row.created_at),
        updatedAt=as_utc(row.updated_at),
    )


class AdminTenantsApiImpl(BaseAdminTenantsApi):
    async def admin_tenants_list_tenants(
        self, page: int | None, page_size: int | None
    ) -> AdminTenantsListTenants200Response:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        p, ps = page_window(page, page_size)
        session = ctx.session
        query = session.query(Tenant)
        total = query.count()
        rows = query.offset(p * ps).limit(ps).all()
        return AdminTenantsListTenants200Response(
            items=[_tenant_dto(row) for row in rows], page=p, pageSize=ps, total=total
        )

    async def admin_tenants_create_tenant(
        self, create_tenant_request: CreateTenantRequest
    ) -> TenantDto:
        ctx = get_context()
        session = ctx.session
        now = now_utc()
        row = Tenant(
            id=uuid.uuid4(),
            tenant_key=create_tenant_request.tenant_key,
            name=create_tenant_request.name,
            status=1,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        commit_or_bad_request(session, "tenant create")
        return _tenant_dto(row)

    async def admin_tenants_get_tenant(self, id: str) -> TenantDto:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        row = ctx.session.get(Tenant, uuid.UUID(id))
        if row is None:
            raise NotFoundError(f"tenant not found: {id}")
        return _tenant_dto(row)

    async def admin_tenants_delete_tenant(self, id: str) -> None:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        row = ctx.session.get(Tenant, uuid.UUID(id))
        if row is not None:
            ctx.session.delete(row)
            ctx.session.commit()
        return None

    async def admin_tenants_update_tenant(
        self, id: str, update_tenant_request: UpdateTenantRequest
    ) -> TenantDto:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        session = ctx.session
        row = session.get(Tenant, uuid.UUID(id))
        if row is None:
            raise NotFoundError(f"tenant not found: {id}")
        if update_tenant_request.name is not None:
            row.name = update_tenant_request.name
        if update_tenant_request.status is not None:
            # ACTIVE → 1 / 其他 → 0（springboot 参照；status 值域 = smallint 字典）
            row.status = 1 if update_tenant_request.status == TenantStatus.ACTIVE else 0
        row.updated_at = now_utc()
        session.commit()
        return _tenant_dto(row)
