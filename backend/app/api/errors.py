"""Error envelope and exception handlers (guide §6.4)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


class UnhandledErrorMiddleware:
    """Turns any uncaught exception into the 500 envelope and does not re-raise it.

    A Starlette `Exception` handler sends its response and then re-raises, so the server
    (Uvicorn) logs the full traceback including the message, which may hold SQL, input or
    secrets. Catching here keeps every log line to the exception type. Errors after the
    response started (e.g. background tasks) are logged the same way and swallowed.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracked_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception as exc:  # noqa: BLE001 - last line of defence
            logger.error("Unhandled error: %s", type(exc).__name__)
            if not started:
                response = error_response(500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)
                await response(scope, receive, send)


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers and the unhandled-error middleware.

    Call before adding other middleware (e.g. CORS) so those stay outermost.
    """
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_middleware(UnhandledErrorMiddleware)
