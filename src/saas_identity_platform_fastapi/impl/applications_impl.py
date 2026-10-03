"""M00.F05 租户应用订阅（springboot TenantApplicationsController 镜像，REQ-2026-003）。

语义锚点（对照 springboot TenantApplicationsController.java）：
- TenantGuard 同成员面：路径 tenantId ≠ JWT tenant_id claim → 403 FORBIDDEN
- list 分页（无排序）；page 0-based 默认 0/20
- subscribe：先查 oauth_client 存在（未知 clientId → 404）；写 status=1/createdAt=now；
  请求 expireTime 不落库 → 恒 null（springboot 参照）；重复订阅 → 400 constraint violation
- PATCH：status 必填 + expireTime 可选（寻不到行 → 404）
- DELETE：幂等（不存在也 204；不删除 oauth_client 本体；组合根把 200 null 收口 204）
"""

# ruff: noqa: N803 —— Base*Api 缝方法形参名镜像生成契约（tenantId/clientId camelCase），不可改名

from __future__ import annotations

import uuid

from saas_identity_platform_fastapi.apis.tenant_applications_api_base import (
    BaseTenantApplicationsApi,
)
from saas_identity_platform_fastapi.entities import OauthClient, TenantApplication
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import commit_or_bad_request, page_window
from saas_identity_platform_fastapi.impl.errors import BadRequestError, NotFoundError
from saas_identity_platform_fastapi.impl.security import as_utc, now_utc, verify_path_tenant
from saas_identity_platform_fastapi.models.subscribe_tenant_application_request import (
    SubscribeTenantApplicationRequest,
)
from saas_identity_platform_fastapi.models.tenant_application import (
    TenantApplication as TenantApplicationDto,
)
from saas_identity_platform_fastapi.models.tenant_applications_list_tenant_applications200_response import (  # noqa: E501
    TenantApplicationsListTenantApplications200Response,
)
from saas_identity_platform_fastapi.models.update_tenant_application_request import (
    UpdateTenantApplicationRequest,
)


def _app_dto(row: TenantApplication) -> TenantApplicationDto:
    return TenantApplicationDto(
        id=row.id,
        tenantId=row.tenant_id,
        clientId=row.client_id,
        status=row.status,
        expireTime=as_utc(row.expire_time) if row.expire_time is not None else None,
        createdAt=as_utc(row.created_at),
    )


class TenantApplicationsApiImpl(BaseTenantApplicationsApi):
    async def tenant_applications_list_tenant_applications(
        self,
        tenantId: str,
        page: int | None,
        page_size: int | None,  # noqa: N803
    ) -> TenantApplicationsListTenantApplications200Response:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        query = session.query(TenantApplication).filter_by(tenant_id=tenant_id)
        total = query.count()
        p, ps = page_window(page, page_size)
        rows = query.offset(p * ps).limit(ps).all()
        return TenantApplicationsListTenantApplications200Response(
            items=[_app_dto(row) for row in rows], page=p, pageSize=ps, total=total
        )

    async def tenant_applications_subscribe_tenant_application(
        self,
        tenantId: str,
        subscribe_tenant_application_request: SubscribeTenantApplicationRequest,  # noqa: N803,E501
    ) -> TenantApplicationDto:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        req = subscribe_tenant_application_request
        # 先查 oauth_client 存在：未知 clientId → 404（不是 FK 400，springboot 参照）
        known = session.query(OauthClient).filter_by(client_id=req.client_id).one_or_none()
        if known is None:
            raise NotFoundError(f"unknown clientId: {req.client_id}")
        # 2026-10-03 修复（CT 断言同批）：dup 预检——此前盲插撞 unique →
        # commit_or_bad_request 把驱动诊断整段上 wire（裸 DB 泄漏）。
        dup = (
            session.query(TenantApplication)
            .filter_by(tenant_id=tenant_id, client_id=req.client_id)
            .one_or_none()
        )
        if dup is not None:
            raise BadRequestError(
                f"subscription already exists: tenant={tenantId} client={req.client_id}"
            )
        row = TenantApplication(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=req.client_id,
            status=1,
            # 2026-10-03 修复（镜像追平 springboot 01704a2）：契约 expireTime? 语义，
            # 参照已落库，此前硬编码 None 是对旧 springboot 行为的镜像，已陈旧。
            expire_time=req.expire_time,
            created_at=now_utc(),
        )
        session.add(row)
        # 兜底（预检后仍撞并发 unique 等）：驱动诊断不再直上 wire 的语义由预检保证，
        # commit_or_bad_request 保留给真 FK/并发面。
        commit_or_bad_request(session, "tenant_application subscribe")
        return _app_dto(row)

    async def tenant_applications_update_tenant_application(
        self,
        tenantId: str,  # noqa: N803
        clientId: str,  # noqa: N803
        update_tenant_application_request: UpdateTenantApplicationRequest,
    ) -> TenantApplicationDto:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        row = (
            session.query(TenantApplication)
            .filter_by(tenant_id=tenant_id, client_id=clientId)
            .one_or_none()
        )
        if row is None:
            raise NotFoundError(f"application not subscribed: {clientId}")
        row.status = update_tenant_application_request.status
        if update_tenant_application_request.expire_time is not None:
            row.expire_time = update_tenant_application_request.expire_time
        session.commit()
        return _app_dto(row)

    async def tenant_applications_remove_tenant_application(
        self,
        tenantId: str,
        clientId: str,  # noqa: N803
    ) -> None:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        row = (
            ctx.session.query(TenantApplication)
            .filter_by(tenant_id=tenant_id, client_id=clientId)
            .one_or_none()
        )
        if row is not None:
            ctx.session.delete(row)
            ctx.session.commit()
        return None
