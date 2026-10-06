"""组合根 —— 手写（生成器 main.py 的手写替代，禁改生成区）。

create_app(config, engine) 工厂装配：生成 router + 每请求上下文中间件 + 家族错误契约 handler。
模块级 ``app``（uvicorn 入口 ``saas_identity_platform_fastapi.app:app``）经 PEP 562 惰性构建：
首次访问才读 env fail-fast —— import 期不读 env，CI 装配冒烟与 pytest 收集不需要真实环境。
"""

from __future__ import annotations

import inspect
import types
from collections.abc import Awaitable, Callable
from typing import Union, get_args, get_origin

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.routing import APIRoute
from pydantic import Strict
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


def _strict_base(annotation: object) -> object | None:
    """取 Strict 注记的基型（int/str/…）；非 Annotated-Strict 形状（含 Optional 包裹）返回 None。"""
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        members = [a for a in get_args(annotation) if a is not type(None)]
        return _strict_base(members[0]) if len(members) == 1 else None
    args = get_args(annotation)
    if args and any(isinstance(m, Strict) for m in args[1:]):
        base: object = args[0]
        return base
    return None


def _relax_strict_query_ints(router: APIRouter) -> None:
    """生成契约把分页 query 参数钉成 StrictInt；query 串恒是字符串，FastAPI+pydantic v2
    strict 模式拒收 "0" 这类字面量 → 分页请求必 422（openapi-generator python-fastapi 缺陷）。
    组合根收口：本版 FastAPI include 走 _IncludedRouter 惰性物化，effective dependant 是
    请求期从 route.endpoint 重新分析出来的（改已构建的 dependant 无效），故在 include 前
    给 endpoint 挂改写后的 __signature__——StrictInt → lax int（Query alias/默认值原样保留）；
    body 内 Strict 语义不动；生成文件零改动（只改运行时函数属性）。
    """
    for route in router.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        signature = inspect.signature(endpoint)
        changed = False
        params = []
        for param in signature.parameters.values():
            base = _strict_base(param.annotation)
            if base is None:
                params.append(param)
                continue
            params.append(param.replace(annotation=base))
            changed = True
        if changed:
            endpoint.__signature__ = signature.replace(parameters=params)


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

    # CORS 白名单（lab app.py 镜像 aspnetcore/springboot 同名策略；REQ-2026-002 Phase 2）：
    # 显式 origin（非 *）+ credentials —— 前端直连后端（saas-flutter dev 5108）要求回显
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 家族健康探针（contract-test fnReporter healthcheck 目标；rails health#show 镜像）。
    # 基建端点不入功能树（rails 先例），匿名 200 纯探针、无 body、不泄运行面信息。
    @app.get("/health", include_in_schema=False)
    async def _health() -> Response:
        return Response(status_code=200)

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
        # 生成区路由对若干端点只声明了 204 responses 没声明 status_code，FastAPI 回 200 null；
        # 家族契约是 204 空体（springboot ResponseEntity.noContent 参照）—— 组合根收口，不动生成区。
        # 覆盖：POST /auth/logout（批1）；批2 三个幂等 DELETE（M00.F01.I05 / M00.F02.I05 /
        # M00.F05.I04）——/api/v1/tenants/ 下现存 DELETE 仅成员移除、应用退订（批2，均 204）与
        # 角色/角色菜单授权（批3：roles DELETE 先 resolve 404、role-menus clear 幂等，均 204）；
        # 批3 另有 /api/v1/clients/ 菜单删除（M04.F04.I05 幂等 204）；
        # 批4 增 /api/v1/admin/clients/ 应用删除（M04.F01.I05 先 resolve 404 非幂等，均 204）。
        if response.status_code == 200 and (
            (request.method == "POST" and request.url.path == "/api/v1/auth/logout")
            or (
                request.method == "DELETE" and request.url.path.startswith("/api/v1/admin/tenants/")
            )
            or (
                request.method == "DELETE" and request.url.path.startswith("/api/v1/admin/clients/")
            )
            or (request.method == "DELETE" and request.url.path.startswith("/api/v1/tenants/"))
            or (request.method == "DELETE" and request.url.path.startswith("/api/v1/clients/"))
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

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        _request: Request[State], exc: RequestValidationError
    ) -> JSONResponse:
        # 契约必填/类型不符：fastapi 校验层默认 422 {detail:[…]}，但家族契约面统一
        # springboot @Valid 口径 400 BAD_REQUEST {code,message}（CT live 比对 5.82 收严，
        # REQ-2026-006 批5 实测 4 处红全此根因）。message 取首违字段「field: msg」。
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path"))
        return JSONResponse(
            status_code=400,
            content={"code": "BAD_REQUEST", "message": f"{field}: {first.get('msg', '')}"},
        )

    @app.exception_handler(LockedAccountError)
    async def _handle_locked(_request: Request[State], _exc: LockedAccountError) -> Response:
        # 423 空响应体（springboot AuthController body(null) 参照）
        return Response(status_code=423)

    for router in _ROUTERS:
        _relax_strict_query_ints(router)
        # 家族 DTO 序列化形状：springboot 逐字段 @JsonInclude(NON_NULL) 镜像——
        # null 可选字段不落 JSON（lab 仓同款先挂；2026-10-03 用户裁定向家族对齐）。
        # include 复制路由时读 route 属性固化进 handler 闭包（include_router
        # 本身不收 exclude_none 参数；生成区零改动，挂属性即全局生效）。
        # 唯一例外（2026-10-03 wire 实证）：EffectiveMenuNode.parentId 是 springboot
        # 全家族唯一无 @Nullable、无 NON_NULL 注解、由 MeController 运行时置 null 的
        # 根 sentinel 字段（REQ-2026-006 批5 四后端实测裁决「parentId:null 键在」）——
        # 粗放 exclude_none 会砍掉这条已裁决形状，故 /me/menus 单路由豁免。
        for route in router.routes:
            if isinstance(route, APIRoute):
                if route.path == "/api/v1/me/menus":
                    continue
                route.response_model_exclude_none = True
        app.include_router(router)

    # 基建：根路径默认跳转 Swagger UI（REQ-2026-007 T-1；/health 同类基建端点，
    # 不入契约面不入功能树）。include_in_schema=False 不污染 openapi schema（AC-4）；
    # 307 临时重定向：浏览器匿名 GET 直达 /docs，契约端点零影响（跳转只占根路径）。
    @app.get("/", include_in_schema=False)
    async def _root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/docs", status_code=307)

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
