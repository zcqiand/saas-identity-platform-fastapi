"""M04.F01.I06 公共应用元数据（springboot ClientsController 镜像，REQ-2026-005）。

语义锚点（对照 springboot ClientsController.java:23-36）：
- **匿名可读**（SecurityConfig :60-61 permitAll 严格匹配 /api/v1/clients/*，不带 Bearer 也行）
- 寻址用 clientId 字符串（登录页应用选择用），非行 UUID
- findByClientId → 404 "client xxx not found"
- 响应 OAuthClientPublicInfo 仅 clientId/clientName/status 三字段
  （绝不含 clientSecret/redirectUris/scopes——契约裁剪）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.clients_api_base import BaseClientsApi
from saas_identity_platform_fastapi.entities import OauthClient
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.errors import NotFoundError
from saas_identity_platform_fastapi.models.o_auth_client_public_info import OAuthClientPublicInfo


def _resolve_client(session: Session, client_id: str) -> OauthClient:
    row = session.query(OauthClient).filter_by(client_id=client_id).one_or_none()
    if row is None:
        raise NotFoundError(f"client {client_id} not found")
    return row


class ClientsApiImpl(BaseClientsApi):
    async def clients_get_client(self, clientId: str) -> OAuthClientPublicInfo:  # noqa: N803
        ctx = get_context()
        row = _resolve_client(ctx.session, clientId)
        return OAuthClientPublicInfo(
            clientId=row.client_id,
            clientName=row.client_name,
            status=row.status,
        )
