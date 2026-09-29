"""每请求上下文：request + Session + AppConfig 经 contextvar 注入 impl 缝。

生成 router 对 Base 缝方法的调用签名固定（无法走 Depends），故由 app 组合根的
HTTP 中间件按请求建 Session 并压栈 contextvar；impl 实现从这里取货。
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.datastructures import State

from saas_identity_platform_fastapi.impl.config import AppConfig


@dataclass(frozen=True)
class RequestContext:
    request: Request[State]
    session: Session
    config: AppConfig


_CTX: ContextVar[RequestContext | None] = ContextVar("saas_request_ctx", default=None)


def set_context(ctx: RequestContext) -> Token[RequestContext | None]:
    return _CTX.set(ctx)


def reset_context(token: Token[RequestContext | None]) -> None:
    _CTX.reset(token)


def get_context() -> RequestContext:
    ctx = _CTX.get()
    if ctx is None:
        raise RuntimeError("request context missing —— 组合根中间件未装配（REQ-2026-002 T-4）")
    return ctx
