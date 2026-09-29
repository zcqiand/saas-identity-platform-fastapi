"""家族错误契约：ErrorResponse {code,message} + 423 锁定空体。

异常 → HTTP 映射镜像 springboot GlobalExceptionHandler：
资源不存在 404 / 凭据错误 401 INVALID_CREDENTIALS / 参数非法 400 / 越权 403。
"""

from __future__ import annotations

from datetime import datetime


class ApiError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCredentialsError(ApiError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class BadRequestError(ApiError):
    status_code = 400
    code = "BAD_REQUEST"


class ForbiddenError(ApiError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class NotImplementedYetError(ApiError):
    """骨架 500 兜底的家族形状版：未到批次端点（REQ-2026-001 总纲分批）。"""

    status_code = 500
    code = "NOT_IMPLEMENTED"


class LockedAccountError(Exception):
    """423 空响应体（springboot AuthController body(null) 参照，契约响应模型未启用）。"""

    def __init__(self, locked_until: datetime) -> None:
        super().__init__(f"account locked until {locked_until.isoformat()}")
        self.locked_until = locked_until
