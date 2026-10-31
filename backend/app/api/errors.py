"""Error envelope and exception handlers (guide §6.4)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raise from routes/services to return { "error": { code, message, details } }."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers


# Default Korean messages; safe to show on screen as-is.
_STATUS_DEFAULTS: dict[int, tuple[str, str]] = {
    400: ("VALIDATION_ERROR", "요청 형식을 확인해 주세요."),
    401: ("AUTH_REQUIRED", "로그인이 필요합니다."),
    403: ("FORBIDDEN", "요청을 처리할 권한이 없습니다."),
    404: ("NOT_FOUND", "요청한 정보를 찾을 수 없습니다."),
    405: ("METHOD_NOT_ALLOWED", "지원하지 않는 요청 방식입니다."),
    409: ("CONFLICT", "이미 처리된 요청과 충돌합니다."),
    429: ("RATE_LIMITED", "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."),
    503: ("UPSTREAM_UNAVAILABLE", "데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."),
}
INTERNAL_ERROR_MESSAGE = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
VALIDATION_MESSAGE = "입력값을 확인해 주세요."


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers=headers)


def _field_path(loc: tuple[Any, ...]) -> str:
    # ("body", "body") -> "body", ("query", "page") -> "page"
    parts = [str(part) for part in loc if part not in ("body", "query", "path", "header")]
    return ".".join(parts) or (str(loc[-1]) if loc else "")


def _field_reason(error: dict[str, Any]) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "missing":
        return "필수 항목입니다."
    if kind in ("string_too_long", "too_long"):
        return f"최대 {ctx.get('max_length', '')}자까지 입력할 수 있습니다."
    if kind in ("string_too_short", "too_short"):
        return "내용을 입력해 주세요."
    if kind in ("literal_error", "enum"):
        return "허용되지 않은 값입니다."
    if kind == "value_error":
        # Custom validators raise ValueError with a Korean message.
        return str(ctx.get("error", "")) or "값을 확인해 주세요."
    return "형식이 올바르지 않습니다."


async def _api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def _validation_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields: dict[str, str] = {}
    for error in exc.errors():
        fields.setdefault(_field_path(tuple(error.get("loc", ()))), _field_reason(error))
    # Never echo the submitted input back.
    return error_response(422, "VALIDATION_ERROR", VALIDATION_MESSAGE, {"fields": fields})


async def _http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    fallback = ("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)
    code, message = _STATUS_DEFAULTS.get(exc.status_code, fallback)
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    # Log the type only: messages from drivers/providers can contain SQL or secrets.
    logger.error("Unhandled error: %s", type(exc).__name__)
    return error_response(500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
