"""Shared FastAPI dependencies: CSRF header check and per-client request limits."""

import threading
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

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
    """Per-client limits plus optional scope-wide limits (key = scope + client IP).

    Replace `key_func` to key by user etc. `global_limits` cap the whole scope regardless
    of client: the safety net for a forged X-Forwarded-For (guide §10.2 C-08). A request is
    counted only when both pass, so rejected requests never create client state.

    Use `route_class()` on the router so the limit runs before the body is parsed: a
    malformed JSON body then still counts (P-10). Calling the instance directly also works
    (e.g. as a dependency) for routes without a body.
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
        self._lock = threading.Lock()

    def reset(self) -> None:
        self.limiter.reset()
        if self.global_limiter:
            self.global_limiter.reset()

    def __call__(self, request: Request) -> None:
        key = f"{self.scope}:{self.key_func(request)}"
        with self._lock:
            waits = [self.limiter.check(key)]
            if self.global_limiter:
                waits.append(self.global_limiter.check(self.scope))
            blocked = [wait for wait in waits if wait is not None]
            if not blocked:
                self.limiter.record(key)
                if self.global_limiter:
                    self.global_limiter.record(self.scope)
                return
        raise ApiError(
            429,
            "RATE_LIMITED",
            "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": retry_after_header(max(blocked))},
        )

    def route_class(self) -> type[APIRoute]:
        """APIRoute subclass that applies this limit before request parsing."""
        limit = self

        class RateLimitedRoute(APIRoute):
            def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
                handler = super().get_route_handler()

                async def limited(request: Request) -> Response:
                    limit(request)
                    return await handler(request)

                return limited

        return RateLimitedRoute
