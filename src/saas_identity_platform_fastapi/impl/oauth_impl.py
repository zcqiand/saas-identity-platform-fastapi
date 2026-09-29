"""M04.F03 OAuth authorize + token + refresh（springboot OauthController 镜像，REQ-2026-002）。

语义锚点（对照 springboot OauthController.java，2026-09-12/09-15 live 4-way 收敛口径）：
- authorize：Bearer sub + tenant_id claim 必需（无 → 401）；redirect csv 白名单
  精确相等或前缀 + '?' 边界（子路径不算）；code 一次性、5 分钟过期
- token 按 grantType 路由：authorization_code 一次性消费 + 过期 + redirectUri 一致；
  refresh_token rotate（未知/已撤销 → 400）；clientId/userId/tenantId 三件回显
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from saas_identity_platform_fastapi.apis.oauth_api_base import BaseOauthApi
from saas_identity_platform_fastapi.entities import (
    OauthAccessToken,
    OauthClient,
    OauthCode,
    OauthRefreshToken,
)
from saas_identity_platform_fastapi.impl.context import RequestContext, get_context
from saas_identity_platform_fastapi.impl.errors import BadRequestError, InvalidCredentialsError
from saas_identity_platform_fastapi.impl.security import (
    JwtIssuer,
    TokenIssuer,
    as_utc,
    now_utc,
    require_bearer,
    uuid_or_none,
)
from saas_identity_platform_fastapi.models.authorize_code_request import AuthorizeCodeRequest
from saas_identity_platform_fastapi.models.o_auth_authorize200_response import (
    OAuthAuthorize200Response,
)
from saas_identity_platform_fastapi.models.token_request import TokenRequest
from saas_identity_platform_fastapi.models.token_response import TokenResponse

CODE_TTL_MINUTES = 5
_INT32_MAX = 2_147_483_647


def _redirect_allowed(whitelist_csv: str, requested: str) -> bool:
    """csv 白名单：精确相等，或条目是请求前缀且边界在 '?'（RFC 6749 §3.1.2）。"""
    for entry in whitelist_csv.split(","):
        candidate = entry.strip()
        if not candidate:
            continue
        if requested == candidate:
            return True
        boundary = len(candidate)
        if (
            requested.startswith(candidate)
            and len(requested) > boundary
            and requested[boundary] == "?"
        ):
            return True
    return False


def _scope_or_none(scope: str | None) -> str | None:
    """msw oracle 的 scope 是 space-separated（RFC 6749 §3.3）；DB 列是 csv。"""
    if scope is None:
        return None
    return scope.replace(",", " ").strip() or None


def _token_response(
    jwt_issuer: JwtIssuer,
    access_token: str,
    refresh_token: str,
    scope: str | None,
    user_id: uuid.UUID,
    client_id: str,
    tenant_id: uuid.UUID,
) -> TokenResponse:
    return TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        tokenType="Bearer",
        expiresIn=min(jwt_issuer.ttl_seconds, _INT32_MAX),
        scope=scope,
        userId=str(user_id),
        clientId=client_id,
        tenantId=tenant_id,
    )


class OauthApiImpl(BaseOauthApi):
    async def o_auth_authorize(
        self, authorize_code_request: AuthorizeCodeRequest
    ) -> OAuthAuthorize200Response:
        ctx = get_context()
        session = ctx.session
        client = (
            session.query(OauthClient)
            .filter_by(client_id=authorize_code_request.client_id)
            .one_or_none()
        )
        if client is None:
            raise BadRequestError("unknown client_id")
        # 认证前置（四家共同语义）：无 / 坏 Bearer → 401，先于白名单校验
        claims = require_bearer(ctx, ctx.request.app.state.jwt)
        user_id = uuid_or_none(claims.get("sub"))
        tenant_id = uuid_or_none(claims.get("tenant_id"))
        if user_id is None:
            raise InvalidCredentialsError("Bearer sub required for authorize")
        if tenant_id is None:
            raise InvalidCredentialsError("JWT tenant_id claim required for authorize")
        if not _redirect_allowed(client.redirect_uris or "", authorize_code_request.redirect_uri):
            raise BadRequestError(
                f"INVALID_REDIRECT_URI: {authorize_code_request.redirect_uri} "
                "not in oauth_client.redirect_uris"
            )
        now = now_utc()
        code = "ac_" + str(uuid.uuid4())
        session.add(
            OauthCode(
                id=uuid.uuid4(),
                code=code,
                client_id=client.client_id,
                user_id=user_id,
                tenant_id=tenant_id,
                redirect_uri=authorize_code_request.redirect_uri,
                scope=authorize_code_request.scope,
                expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
                created_at=now,
            )
        )
        session.commit()
        return OAuthAuthorize200Response(code=code, state=authorize_code_request.state)

    async def o_auth_token(self, token_request: TokenRequest) -> TokenResponse:
        ctx = get_context()
        jwt_issuer: JwtIssuer = ctx.request.app.state.jwt
        client = (
            ctx.session.query(OauthClient)
            .filter_by(client_id=token_request.client_id)
            .one_or_none()
        )
        if client is None:
            raise BadRequestError("INVALID_CLIENT: unknown client_id")
        if token_request.grant_type == "authorization_code":
            return self._exchange_authorization_code(ctx, jwt_issuer, client, token_request)
        if token_request.grant_type == "refresh_token":
            return self._rotate_refresh_token(ctx, jwt_issuer, client, token_request)
        raise BadRequestError(f"UNSUPPORTED_GRANT_TYPE: {token_request.grant_type}")

    def _exchange_authorization_code(
        self,
        ctx: RequestContext,
        jwt_issuer: JwtIssuer,
        client: OauthClient,
        token_request: TokenRequest,
    ) -> TokenResponse:
        session = ctx.session
        if not token_request.code:
            raise BadRequestError("INVALID_REQUEST: code required for grantType=authorization_code")
        if not token_request.redirect_uri:
            raise BadRequestError(
                "INVALID_REQUEST: redirectUri required for grantType=authorization_code"
            )
        row = (
            session.query(OauthCode)
            .filter_by(code=token_request.code, client_id=client.client_id)
            .one_or_none()
        )
        if row is None:
            raise BadRequestError("INVALID_GRANT: code 不存在或已被使用")
        if row.expires_at is not None and as_utc(row.expires_at) < now_utc():
            session.delete(row)
            session.commit()
            raise BadRequestError("INVALID_GRANT: expired code")
        if token_request.redirect_uri != row.redirect_uri:
            session.delete(row)
            session.commit()
            raise BadRequestError("INVALID_GRANT: redirectUri mismatch")
        user_id: uuid.UUID = row.user_id
        tenant_id: uuid.UUID = row.tenant_id
        scope: str | None = row.scope
        # 一次性消费：删 code 行，防重放
        session.delete(row)
        session.commit()
        refresh_token = TokenIssuer(session).persist_token_pair(
            user_id, tenant_id, client.client_id, scope
        )
        return _token_response(
            jwt_issuer,
            jwt_issuer.issue_access_token(user_id, tenant_id),
            refresh_token,
            _scope_or_none(scope),
            user_id,
            client.client_id,
            tenant_id,
        )

    def _rotate_refresh_token(
        self,
        ctx: RequestContext,
        jwt_issuer: JwtIssuer,
        client: OauthClient,
        token_request: TokenRequest,
    ) -> TokenResponse:
        session = ctx.session
        if not token_request.refresh_token:
            raise BadRequestError(
                "INVALID_REQUEST: refreshToken required for grantType=refresh_token"
            )
        rt = (
            session.query(OauthRefreshToken)
            .filter_by(refresh_token=token_request.refresh_token)
            .one_or_none()
        )
        if rt is None:
            raise BadRequestError("INVALID_GRANT: refreshToken 不存在或已被使用")
        if rt.revoked:
            raise BadRequestError("INVALID_GRANT: revoked refresh_token")
        if rt.user_id is None or rt.tenant_id is None:
            raise BadRequestError("INVALID_GRANT: refreshToken 缺少 user/tenant 绑定")
        user_id: uuid.UUID = rt.user_id
        tenant_id: uuid.UUID = rt.tenant_id
        # rotate：旧 rt 标 revoked
        rt.revoked = True
        session.commit()
        # 新 refresh 行的 client_id 以旧 rt 行绑定的值为准，不信任请求体（springboot 参照）
        client_id: str = rt.client_id if rt.client_id else client.client_id
        access_row = session.get(OauthAccessToken, rt.access_token_id)
        scope: str | None = access_row.scope if access_row is not None else None
        new_refresh = TokenIssuer(session).persist_token_pair(user_id, tenant_id, client_id, scope)
        return _token_response(
            jwt_issuer,
            jwt_issuer.issue_access_token(user_id, tenant_id),
            new_refresh,
            _scope_or_none(scope),
            user_id,
            client_id,
            tenant_id,
        )
