"""In-memory request limiter for a single backend instance (guide §8, 01 details).

Swap `RateLimiter` for a shared store (e.g. PostgreSQL or Redis) if the backend ever runs
more than one instance; callers only depend on `hit()`.
"""

import ipaddress
import math
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from starlette.requests import Request


@dataclass(frozen=True)
class Limit:
    max_requests: int
    window_seconds: int


class RateLimiter:
    """Sliding-window limiter keyed by an arbitrary string."""

    def __init__(self, limits: Sequence[Limit], clock: Callable[[], float] = time.monotonic):
        self._limits = tuple(limits)
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._longest = max(limit.window_seconds for limit in self._limits)

    def hit(self, key: str) -> float | None:
        """Record a request. Returns None if allowed, else seconds until a retry can pass."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self._longest:
                hits.popleft()
            retry_after: float | None = None
            for limit in self._limits:
                in_window = [t for t in hits if t > now - limit.window_seconds]
                if len(in_window) >= limit.max_requests:
                    wait = in_window[-limit.max_requests] + limit.window_seconds - now
                    retry_after = max(retry_after or 0.0, wait)
            if retry_after is not None:
                return retry_after
            hits.append(now)
            self._prune(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, now: float) -> None:
        # Drop idle keys occasionally so memory does not grow with every client seen.
        if len(self._hits) < 10_000:
            return
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - self._longest]:
            del self._hits[key]


def retry_after_header(seconds: float) -> str:
    return str(max(1, math.ceil(seconds)))


def client_ip(request: Request, trusted_proxies: Sequence[str]) -> str:
    """Client IP. X-Forwarded-For is used only when the direct peer is a trusted proxy.

    The chain is read right to left, skipping trusted proxies, so a spoofed left-most
    value sent by the browser is ignored.
    """
    peer = request.client.host if request.client else "unknown"
    trusted = set(trusted_proxies)
    if peer not in trusted:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    for candidate in reversed(chain):
        if not _is_ip(candidate):
            break
        if candidate not in trusted:
            return candidate
    return peer


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True
