"""组合根 —— 手写（生成器 main.py 的手写替代，禁改生成区）。

create_app(config, engine) 工厂装配：生成 router + 每请求上下文中间件 + 家族错误契约 handler。
模块级 ``app``（uvicorn 入口 ``saas_identity_platform_fastapi.app:app``）经 PEP 562 惰性构建：
首次访问才读 env fail-fast —— import 期不读 env，CI 装配冒烟与 pytest 收集不需要真实环境。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import State

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
from saas_identity_platform_fastapi.impl.config import AppConfig, normalize_database_url
from saas_identity_platform_fastapi.impl.context import (
    RequestContext,
    reset_context,
    set_context,
)
from saas_identity_platform_fastapi.impl.errors import ApiError, LockedAccountError
from saas_identity_platform_fastapi.impl.security import JwtIssuer

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


def create_app(config: AppConfig, engine: Engine | None = None) -> FastAPI:
    """装配完整应用。测试注入内存 engine（仓铁律 mock-friendly）；生产从 config.database_url 建。"""
    db_engine = (
        engine
        if engine is not None
        else create_engine(normalize_database_url(config.database_url), pool_pre_ping=True)
    )
    app = FastAPI(title="SaaS 多租户多应用身份平台", version="0.1.0")
    app.state.config = config
    app.state.engine = db_engine
    app.state.session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    app.state.jwt = JwtIssuer(config)

    @app.middleware("http")
    async def _request_context(
        request: Request[State], call_next: Callable[[Request[State]], Awaitable[Response]]
    ) -> Response:
        session = request.app.state.session_factory()
        token = set_context(
            RequestContext(request=request, session=session, config=request.app.state.config)
        )
        try:
            response = await call_next(request)
        finally:
            reset_context(token)
            session.close()
        # 生成区路由对 logout 只声明了 204 responses 没声明 status_code，FastAPI 回 200 null；
        # 家族契约是 204 空体（springboot ResponseEntity.noContent 参照）—— 组合根收口，不动生成区。
        if (
            request.method == "POST"
            and request.url.path == "/api/v1/auth/logout"
            and response.status_code == 200
        ):
            return Response(status_code=204)
        return response

    # starlette 位置传参调 handler（_exception_handler.py:59），下划线前缀参数安全
    @app.exception_handler(ApiError)
    async def _handle_api_error(_request: Request[State], exc: ApiError) -> JSONResponse:
        # 家族 ErrorResponse 形状 {code,message}（springboot GlobalExceptionHandler 镜像）
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.exception_handler(LockedAccountError)
    async def _handle_locked(_request: Request[State], _exc: LockedAccountError) -> Response:
        # 423 空响应体（springboot AuthController body(null) 参照）
        return Response(status_code=423)

    for router in _ROUTERS:
        app.include_router(router)
    return app


_APP: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """PEP 562：``app`` 惰性构建（读 env fail-fast 在首次访问，不在 import）。"""
    if name == "app":
        global _APP
        if _APP is None:
            _APP = create_app(AppConfig.from_env())
        return _APP
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
