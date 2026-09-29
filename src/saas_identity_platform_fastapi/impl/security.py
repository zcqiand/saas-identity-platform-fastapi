"""JWT 签发/校验 + 密码校验 + Bearer 提取 + token 对落库。

镜像 springboot JwtIssuer / TokenIssuer（REQ-2026-002 批1，语义逐条对照）：
- HS256，JWT_SIGNING_KEY ≥32 字节；claims iss/aud/sub/tenant_id/jti + iat/nbf/exp
- 密码列家族 dev 约定 ``plain:{password}`` 占位直比；bcrypt 哈希为回退分支
- refresh token ``rt_<uuid>``，token 对（oauth_access_token + oauth_refresh_token）落库
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.entities import OauthAccessToken, OauthClient, OauthRefreshToken
from saas_identity_platform_fastapi.impl.config import AppConfig
from saas_identity_platform_fastapi.impl.context import RequestContext
from saas_identity_platform_fastapi.impl.errors import (
    BadRequestError,
    ForbiddenError,
    InvalidCredentialsError,
)

# springboot TokenIssuer 参照：access 行 +1h / refresh 行 +30d，固定家族口径
_ACCESS_TTL = timedelta(hours=1)
_REFRESH_TTL = timedelta(days=30)


def as_utc(value: datetime) -> datetime:
    """DB 读回时间统一 UTC：sqlite 往返丢 tzinfo（naive 视为 UTC），timestamptz 为 aware。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_or_none(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def password_matches(password: str, stored: str) -> bool:
    if stored.startswith("plain:"):
        return stored == "plain:" + password
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except ValueError:
        # 库里不是合法 bcrypt 哈希（脏数据）——同错密码语义，不泄露存储形态
        return False


class JwtIssuer:
    def __init__(self, config: AppConfig) -> None:
        if len(config.jwt_signing_key.encode()) < 32:
            raise RuntimeError("JWT_SIGNING_KEY must be >=32 bytes for HS256")
        self._key = config.jwt_signing_key
        self._issuer = config.jwt_issuer
        self._audience = config.jwt_audience
        self._ttl = config.jwt_ttl_seconds

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def issue_access_token(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, ttl_seconds: int | None = None
    ) -> str:
        now = now_utc()
        ttl = self._ttl if ttl_seconds is None else ttl_seconds
        epoch = int(now.timestamp())
        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "jti": str(uuid.uuid4()),
            "iat": epoch,
            "nbf": epoch,
            "exp": epoch + ttl,
        }
        return str(jwt.encode(payload, self._key, algorithm="HS256"))

    def decode(self, token: str) -> dict[str, object]:
        try:
            claims: dict[str, object] = jwt.decode(
                token,
                key=self._key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except jwt.PyJWTError as exc:
            raise InvalidCredentialsError(f"invalid bearer token: {exc}") from exc
        return claims


def require_bearer(ctx: RequestContext, issuer: JwtIssuer) -> dict[str, object]:
    """取当前 Bearer 身份（springboot bearerJwtOrNull 的 fail-fast 版：无/坏 → 401）。"""
    header = ctx.request.headers.get("Authorization")
    if header is None or not header.startswith("Bearer "):
        raise InvalidCredentialsError("Bearer token required")
    return issuer.decode(header[len("Bearer ") :].strip())


def verify_path_tenant(ctx: RequestContext, tenant_id: str) -> uuid.UUID:
    """springboot TenantGuard 镜像：路径 tenantId 必须 = JWT tenant_id claim，不等 → 403。

    坏 UUID 不接（mirror springboot UUID.parse：ValueError 直接 500）。
    """
    claims = require_bearer(ctx, ctx.request.app.state.jwt)
    path_tenant = uuid.UUID(tenant_id)
    raw = claims.get("tenant_id")
    if raw != str(path_tenant):
        raise ForbiddenError(f"tenant mismatch: path={path_tenant} jwt={raw}")
    return path_tenant


class TokenIssuer:
    """登录与授权码交换共用的 token 对落库（springboot TokenIssuer 镜像，防两处漂移）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_token_pair(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, client_id: str, scope: str | None
    ) -> str:
        # client_id 是 FK → oauth_client.client_id；写前校验，未知 → 400（springboot 参照）
        known = self._session.query(OauthClient).filter_by(client_id=client_id).one_or_none()
        if known is None:
            raise BadRequestError(f"unknown clientId: {client_id}")
        now = now_utc()
        # id 显式赋值：sqlite 测试无 uuid_generate_v4() server_default（PG 下显式值同样合法）
        access = OauthAccessToken(
            id=uuid.uuid4(),
            token_id=f"at_{uuid.uuid4()}",
            # 真签在 JWT（JwtIssuer 持有）；库列 NOT NULL 存占位（springboot "n/a" 同款）
            access_token="n/a",
            client_id=client_id,
            token_type="Bearer",
            scope=scope,
            expires_at=now + _ACCESS_TTL,
            revoked=False,
            created_at=now,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        self._session.add(access)
        self._session.flush()  # access.id 回填 FK
        refresh_value = "rt_" + str(uuid.uuid4())
        self._session.add(
            OauthRefreshToken(
                id=uuid.uuid4(),
                refresh_token=refresh_value,
                access_token_id=access.id,
                client_id=client_id,
                expires_at=now + _REFRESH_TTL,
                revoked=False,
                created_at=now,
                user_id=user_id,
                tenant_id=tenant_id,
            )
        )
        self._session.commit()
        return refresh_value
