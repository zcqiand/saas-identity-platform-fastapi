"""M04.F01.I01-I05 + M04.F02.I01 平台应用维护与启停（springboot AdminClientsController 镜像）。

语义锚点（对照 springboot AdminClientsController.java，REQ-2026-005）：
- **仅有效 Bearer JWT**（SecurityConfig :79-86 anyRequest authenticated——无角色门、无
  TenantGuard；prod 恢复方案在参照注释里，本批不启用）
- 寻址用 clientId 字符串非行 UUID；list 分页 0/20 缺省、无排序、无过滤
- create（:44-70）：全字段直拷；**validity 应用层缺省**（null 或 ≤0 → 3600/86400，
  非 DB 列默认 7200/2592000）；autoApprove null→false；status=1；clientId 撞 unique
  → 400 constraint violation；返回 200 非 201
- update（:82-92）：**只应用 clientName/redirectUris/scopes 三字段**（grantTypes/
  validity/autoApprove/status 忽略）；不 touch updatedAt（参照无 @PreUpdate）
- delete（:95-102）：先 resolve → 404 非幂等；级联靠 DB FK ON DELETE CASCADE
  （tenant_application/sys_role/sys_menu/oauth_code/两 token 表）；204
- set-status（:105-113）：status 必填、**无值域校验**（任意 int 直写 smallint）
- 响应镜像 toDto（:115-132）：OAuthClient 含 id/createdAt/updatedAt，**永不含 clientSecret**
"""

# ruff: noqa: N803, ARG002 —— Base*Api 缝方法形参名镜像生成契约（camelCase），不可改名。

from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.admin_clients_api_base import BaseAdminClientsApi
from saas_identity_platform_fastapi.entities import OauthClient
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import commit_or_bad_request, page_window
from saas_identity_platform_fastapi.impl.errors import NotFoundError
from saas_identity_platform_fastapi.impl.security import as_utc, now_utc, require_bearer
from saas_identity_platform_fastapi.models.admin_clients_list_clients200_response import (
    AdminClientsListClients200Response,
)
from saas_identity_platform_fastapi.models.admin_clients_set_client_status_request import (
    AdminClientsSetClientStatusRequest,
)
from saas_identity_platform_fastapi.models.create_o_auth_client_request import (
    CreateOAuthClientRequest,
)
from saas_identity_platform_fastapi.models.o_auth_client import OAuthClient
from saas_identity_platform_fastapi.models.update_o_auth_client_request import (
    UpdateOAuthClientRequest,
)

# 应用层 validity 缺省（springboot :56-63 家族口径，非 DB 列 DEFAULT 7200/2592000）
_ACCESS_VALIDITY_DEFAULT = 3600
_REFRESH_VALIDITY_DEFAULT = 86400


def _resolve_client(session: Session, client_id: str) -> OauthClient:
    row = session.query(OauthClient).filter_by(client_id=client_id).one_or_none()
    if row is None:
        raise NotFoundError(f"client {client_id}")
    return row


def _client_dto(row: OauthClient) -> OAuthClient:
    return OAuthClient(
        id=row.id,
        clientId=row.client_id,
        clientName=row.client_name,
        grantTypes=row.grant_types,
        redirectUris=row.redirect_uris,
        scopes=row.scopes,
        accessTokenValidity=row.access_token_validity,
        refreshTokenValidity=row.refresh_token_validity,
        autoApprove=row.auto_approve,
        status=row.status,
        createdAt=as_utc(row.created_at),
        updatedAt=as_utc(row.updated_at),
    )


class AdminClientsApiImpl(BaseAdminClientsApi):
    async def admin_clients_list_clients(
        self, page: int | None, page_size: int | None
    ) -> AdminClientsListClients200Response:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        p, ps = page_window(page, page_size)
        rows = (
            ctx.session.query(OauthClient)
            .offset(p * ps)  # 无排序（参照 findAll(PageRequest) 无 Sort，落 DB 自然序）
            .limit(ps)
            .all()
        )
        total = ctx.session.query(OauthClient).count()
        return AdminClientsListClients200Response(
            items=[_client_dto(row) for row in rows],
            page=p,
            pageSize=ps,
            total=total,
        )

    async def admin_clients_create_client(
        self, create_o_auth_client_request: CreateOAuthClientRequest
    ) -> OAuthClient:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        req = create_o_auth_client_request
        access_validity = req.access_token_validity
        if access_validity is None or access_validity <= 0:
            access_validity = _ACCESS_VALIDITY_DEFAULT
        refresh_validity = req.refresh_token_validity
        if refresh_validity is None or refresh_validity <= 0:
            refresh_validity = _REFRESH_VALIDITY_DEFAULT
        row = OauthClient(
            id=uuid.uuid4(),
            client_id=req.client_id,
            client_secret=req.client_secret,
            client_name=req.client_name,
            grant_types=req.grant_types,
            redirect_uris=req.redirect_uris,
            scopes=req.scopes,
            access_token_validity=access_validity,
            refresh_token_validity=refresh_validity,
            auto_approve=req.auto_approve if req.auto_approve is not None else False,
            status=1,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        ctx.session.add(row)
        commit_or_bad_request(ctx.session, "admin client create")  # clientId 撞 unique → 400
        return _client_dto(row)

    async def admin_clients_get_client(self, clientId: str) -> OAuthClient:  # noqa: N803
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        return _client_dto(_resolve_client(ctx.session, clientId))

    async def admin_clients_delete_client(self, clientId: str) -> None:  # noqa: N803
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        row = _resolve_client(ctx.session, clientId)
        # 级联在 DB FK ON DELETE CASCADE（参照 deleteById 无应用层级联）。必须走 core
        # delete：ORM session.delete 会先 UPDATE 子行 FK=NULL（不识 DB CASCADE），撞
        # sys_role.client_id NOT NULL（批4 实测）。
        ctx.session.execute(sa_delete(OauthClient).where(OauthClient.id == row.id))
        ctx.session.commit()
        return None

    async def admin_clients_update_client(
        self,
        clientId: str,  # noqa: N803
        update_o_auth_client_request: UpdateOAuthClientRequest,
    ) -> OAuthClient:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        row = _resolve_client(ctx.session, clientId)
        req = update_o_auth_client_request
        # 只应用三字段（参照 :88-90）；grantTypes/validity/autoApprove/status 忽略
        if req.client_name is not None:
            row.client_name = req.client_name
        if req.redirect_uris is not None:
            row.redirect_uris = req.redirect_uris
        if req.scopes is not None:
            row.scopes = req.scopes
        ctx.session.commit()  # 不 touch updatedAt（参照无 @PreUpdate、handler 不 set）
        return _client_dto(row)

    async def admin_clients_set_client_status(
        self,
        clientId: str,  # noqa: N803
        admin_clients_set_client_status_request: AdminClientsSetClientStatusRequest,
    ) -> OAuthClient:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)  # 参照 anyRequest().authenticated()
        row = _resolve_client(ctx.session, clientId)
        # 无值域校验：任意 int 直写 smallint（参照 :111 镜像）
        row.status = admin_clients_set_client_status_request.status
        ctx.session.commit()
        return _client_dto(row)
