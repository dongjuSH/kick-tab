"""Shared FastAPI dependencies: CSRF header check and per-client request limits."""

from collections.abc import Callable, Sequence

from fastapi import Request

from app.api.errors import ApiError
from app.config import settings
from app.core.rate_limit import Limit, RateLimiter, client_ip, retry_after_header

CSRF_HEADER = "X-KickTab-Client"
CSRF_HEADER_VALUE = "web"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def require_csrf(request: Request) -> None:
    """Changing requests must carry X-KickTab-Client: web and an allowed Origin (§6.2).

    A missing Origin is accepted (non-browser clients); the custom header already forces a
    CORS preflight for cross-site browser requests.
    """
    if request.method not in UNSAFE_METHODS:
        return
    if request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE:
        raise ApiError(403, "FORBIDDEN", "허용되지 않은 요청입니다.", details={"reason": "csrf"})
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins:
        raise ApiError(403, "FORBIDDEN", "허용되지 않은 요청입니다.", details={"reason": "origin"})


class RateLimit:
    """Dependency factory. Key = scope + client IP; replace `key_func` to key by user, etc.

    `global_limits` cap the whole scope regardless of client. They are the safety net for a
    forged X-Forwarded-For (guide §10.2 C-08): rotating fake IPs still hits this ceiling.
    """

    def __init__(
        self,
        scope: str,
        limits: Sequence[Limit],
        key_func: Callable[[Request], str] | None = None,
        global_limits: Sequence[Limit] = (),
    ) -> None:
        self.scope = scope
        self.limiter = RateLimiter(limits)
        self.global_limiter = RateLimiter(global_limits) if global_limits else None
        self.key_func = key_func or (lambda request: client_ip(request, settings.trusted_proxies))

    def reset(self) -> None:
        self.limiter.reset()
        if self.global_limiter:
            self.global_limiter.reset()

    def __call__(self, request: Request) -> None:
        # Per-client first, so requests a client is already refused don't use global slots.
        retry_after = self.limiter.hit(f"{self.scope}:{self.key_func(request)}")
        if retry_after is None and self.global_limiter:
            retry_after = self.global_limiter.hit(self.scope)
        if retry_after is not None:
            raise ApiError(
                429,
                "RATE_LIMITED",
                "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                headers={"Retry-After": retry_after_header(retry_after)},
            )
