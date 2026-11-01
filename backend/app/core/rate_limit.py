"""In-memory request limiter for a single backend instance (guide §8, 01 details).

Swap `RateLimiter` for a shared store (e.g. PostgreSQL or Redis) if the backend ever runs
more than one instance; callers only depend on `check()`/`record()`/`hit()`.
"""

import ipaddress
import math
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from starlette.requests import Request

# Upper bound on tracked keys. Beyond it the least recently seen keys are dropped; the
# scope-wide (global) limit still applies to them.
DEFAULT_MAX_KEYS = 10_000


@dataclass(frozen=True)
class Limit:
    max_requests: int
    window_seconds: int


class RateLimiter:
    """Sliding-window limiter keyed by an arbitrary string.

    Keys are kept in least-recently-seen order, so expiring idle keys and enforcing
    `max_keys` only touch the oldest entries (amortised O(1) per request).
    """

    def __init__(
        self,
        limits: Sequence[Limit],
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = DEFAULT_MAX_KEYS,
    ):
        self._limits = tuple(limits)
        self._clock = clock
        self._max_keys = max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()
        self._longest = max(limit.window_seconds for limit in self._limits)
        self._keep = max(limit.max_requests for limit in self._limits)

    @property
    def size(self) -> int:
        return len(self._hits)

    def check(self, key: str) -> float | None:
        """None if a request would be allowed now, else seconds until it would be.

        Never creates state for an unseen key.
        """
        now = self._clock()
        with self._lock:
            return self._check_locked(key, now)

    def record(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._record_locked(key, now)

    def hit(self, key: str) -> float | None:
        """Check and record as one step (one lock). Rejected requests are not counted."""
        now = self._clock()
        with self._lock:
            retry_after = self._check_locked(key, now)
            if retry_after is None:
                self._record_locked(key, now)
            return retry_after

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    # The *_locked helpers assume self._lock is held; they never take it themselves.
    def _check_locked(self, key: str, now: float) -> float | None:
        self._expire(now)
        return self._wait(self._hits.get(key), now)

    def _record_locked(self, key: str, now: float) -> None:
        hits = self._hits.get(key)
        if hits is None:
            hits = self._hits[key] = deque()
        else:
            self._hits.move_to_end(key)
        hits.append(now)
        while len(hits) > self._keep:  # older entries can no longer decide a window
            hits.popleft()
        while len(self._hits) > self._max_keys:
            self._hits.popitem(last=False)

    def _wait(self, hits: deque[float] | None, now: float) -> float | None:
        if not hits:
            return None
        retry_after: float | None = None
        for limit in self._limits:
            in_window = [t for t in hits if t > now - limit.window_seconds]
            if len(in_window) >= limit.max_requests:
                wait = in_window[-limit.max_requests] + limit.window_seconds - now
                retry_after = max(retry_after or 0.0, wait)
        return retry_after

    def _expire(self, now: float) -> None:
        # Oldest-seen keys first: stop at the first key that is still active.
        while self._hits:
            key, hits = next(iter(self._hits.items()))
            if hits and hits[-1] > now - self._longest:
                break
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
