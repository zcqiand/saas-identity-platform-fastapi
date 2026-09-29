"""租户面 CRUD 共用缝（REQ-2026-003）：家族分页窗口 + unique 冲突收口。

- 分页家族约定 0-based 默认 0/20（contract-test 分页对齐先例）
- 重复/冲突一律 400 BAD_REQUEST "constraint violation"，全家族无 409
  （springboot GlobalExceptionHandler 参照）
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.impl.errors import BadRequestError

DEFAULT_PAGE = 0
DEFAULT_PAGE_SIZE = 20


def page_window(page: int | None, page_size: int | None) -> tuple[int, int]:
    """家族分页约定：0-based，默认 0/20。"""
    return (
        DEFAULT_PAGE if page is None else page,
        DEFAULT_PAGE_SIZE if page_size is None else page_size,
    )


def commit_or_bad_request(session: Session, action: str) -> None:
    """唯一显式写入点的 IntegrityError 收口：撞 unique → 400（保留底层原因，不吞真 bug 面）。

    只在 create/subscribe 等显式 insert 后调用；捕获过宽会掩盖查询期错误（REQ §6 风险项）。
    """
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise BadRequestError(f"constraint violation: {action}: {exc.orig}") from exc
