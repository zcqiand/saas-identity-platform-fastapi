"""组合根 —— 手写（生成器 main.py 的手写替代，禁改生成区）。

职责只有装配：把 shared 契约生成的 router 挂上 FastAPI 实例。
业务实现在 impl/；鉴权依赖注入等横切面也在此接线。
"""

from fastapi import FastAPI

from saas_identity_platform_fastapi.apis.admin_clients_api import (
    router as admin_clients_api_router,
)
from saas_identity_platform_fastapi.apis.admin_tenants_api import (
    router as admin_tenants_api_router,
)
from saas_identity_platform_fastapi.apis.auth_api import router as auth_api_router
from saas_identity_platform_fastapi.apis.client_menus_api import (
    router as client_menus_api_router,
)
from saas_identity_platform_fastapi.apis.clients_api import router as clients_api_router
from saas_identity_platform_fastapi.apis.me_api import router as me_api_router
from saas_identity_platform_fastapi.apis.oauth_api import router as oauth_api_router
from saas_identity_platform_fastapi.apis.tenant_applications_api import (
    router as tenant_applications_api_router,
)
from saas_identity_platform_fastapi.apis.tenant_members_api import (
    router as tenant_members_api_router,
)
from saas_identity_platform_fastapi.apis.tenant_role_menus_api import (
    router as tenant_role_menus_api_router,
)
from saas_identity_platform_fastapi.apis.tenant_roles_api import (
    router as tenant_roles_api_router,
)

app = FastAPI(
    title="SaaS 多租户多应用身份平台",
    version="0.1.0",
)

_ROUTERS = (
    admin_clients_api_router,
    admin_tenants_api_router,
    auth_api_router,
    client_menus_api_router,
    clients_api_router,
    me_api_router,
    oauth_api_router,
    tenant_applications_api_router,
    tenant_members_api_router,
    tenant_role_menus_api_router,
    tenant_roles_api_router,
)

for _router in _ROUTERS:
    app.include_router(_router)
