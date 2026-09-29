"""M01.F04 密码登录 + 失败锁定 + 登出（springboot AuthController 镜像，REQ-2026-002）。

语义锚点（对照 springboot AuthController.java）：
- 未知用户与错密码同语义 401 INVALID_CREDENTIALS（不泄露用户存在性）
- 连续 5 次错 → 锁 15 分钟；锁定窗口内即使密码正确也 423 空体
- tenantId = 首个 active membership（status=1）且租户 active
- availableTenants = active membership ∩ tenant_application(clientId) 订阅（空集不过滤）
"""

from __future__ import annotations

from datetime import timedelta

from saas_identity_platform_fastapi.apis.auth_api_base import BaseAuthApi
from saas_identity_platform_fastapi.entities import (
    SysUser,
    Tenant,
    TenantApplication,
    TenantMember,
)
from saas_identity_platform_fastapi.impl.assemble import to_membership, user_status_from_db
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.errors import (
    ForbiddenError,
    InvalidCredentialsError,
    LockedAccountError,
)
from saas_identity_platform_fastapi.impl.security import (
    TokenIssuer,
    as_utc,
    now_utc,
    password_matches,
)
from saas_identity_platform_fastapi.models.login_request import LoginRequest
from saas_identity_platform_fastapi.models.login_response import LoginResponse
from saas_identity_platform_fastapi.models.sys_user import SysUser as SysUserDto

LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15
# springboot 登录响应字面 3600（JWT exp 本身走 JWT_TTL_SECONDS），家族口径
LOGIN_EXPIRES_IN = 3600


class AuthApiImpl(BaseAuthApi):
    async def sessions_login(self, login_request: LoginRequest) -> LoginResponse:
        ctx = get_context()
        session = ctx.session
        user = session.query(SysUser).filter_by(username=login_request.username).one_or_none()
        if user is None:
            raise InvalidCredentialsError("invalid credentials")

        # M01.F04.I02 —— 锁定窗口检查
        locked_until = user.locked_until
        if locked_until is not None and as_utc(locked_until) > now_utc():
            raise LockedAccountError(as_utc(locked_until))

        if not password_matches(login_request.password, user.password):
            attempts = (user.failed_attempts or 0) + 1
            user.failed_attempts = attempts
            if attempts >= LOCKOUT_THRESHOLD:
                user.locked_until = now_utc() + timedelta(minutes=LOCKOUT_MINUTES)
            session.commit()
            raise InvalidCredentialsError("invalid credentials")

        # 成功：重置失败计数
        user.failed_attempts = 0
        user.locked_until = None
        session.commit()

        members = (
            session.query(TenantMember)
            .filter_by(user_id=user.id)
            .order_by(TenantMember.created_at, TenantMember.id)
            .all()
        )
        active = [m for m in members if m.status == 1]
        if not active:
            raise ForbiddenError("user has no active tenant membership")
        tenant_id = active[0].tenant_id
        tenant = session.get(Tenant, tenant_id)
        if tenant is None or tenant.status != 1:
            raise ForbiddenError(f"tenant unavailable: {tenant_id}")

        access_token = ctx.request.app.state.jwt.issue_access_token(user.id, tenant_id)
        refresh_token = TokenIssuer(session).persist_token_pair(
            user.id, tenant_id, login_request.client_id, None
        )

        # clientId 无订阅 → 退化为不过滤（空集 filter 会吞掉全部 membership，家族 S3 修复口径）
        subscribed = {
            row.tenant_id
            for row in session.query(TenantApplication)
            .filter_by(client_id=login_request.client_id)
            .all()
        }
        available = [
            to_membership(session, m) for m in active if not subscribed or m.tenant_id in subscribed
        ]
        return LoginResponse(
            user=SysUserDto(
                id=user.id,
                username=user.username,
                email=user.email,
                status=user_status_from_db(user.status),
                createdAt=as_utc(user.created_at),
                updatedAt=as_utc(user.updated_at),
            ),
            availableTenants=available,
            userId=user.id,
            currentTenantId=tenant_id,
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="Bearer",
            expiresIn=LOGIN_EXPIRES_IN,
            clientId=login_request.client_id,
        )

    async def sessions_logout(self) -> None:
        return None
