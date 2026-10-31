"""API-Football client skeleton (chat 01). Chat 03 adds endpoint-specific helpers.

Safety rules (guide §6.5):
- The key is read from SecretStr only when building a request and never logged or raised.
- A shared per-minute limiter (<= 250/min) and a daily budget (default 7,000) are checked
  before every network attempt; every attempt, including retries, counts.
- HTTP 200 with a non-empty `errors` body is a failure (COM-004), never an empty result.
- Network errors and 5xx are retried at most twice with exponential backoff, then stop.
  401/403/429 and quota errors stop further calls for this client; no polling, no loops.
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import SecretStr

from app.config import settings

logger = logging.getLogger(__name__)

QUOTA_HEADERS = (
    "x-ratelimit-requests-limit",
    "x-ratelimit-requests-remaining",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
)
_STOP_WORDS = ("rate limit", "ratelimit", "request limit", "too many", "quota", "suspended")


class ApiFootballError(Exception):
    """Base error. Messages never include the API key or raw response bodies."""


class ApiFootballConfigError(ApiFootballError):
    pass


class ApiFootballBudgetExceeded(ApiFootballError):
    pass


class ApiFootballStopped(ApiFootballError):
    """Auth/quota failure earlier in this run; further calls are refused."""


class ApiFootballResponseError(ApiFootballError):
    """HTTP 200 (or 4xx) with an `errors` body. Must not be stored as empty data."""

    def __init__(self, message: str, *, status_code: int, error_keys: list[str]) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_keys = error_keys


class ApiFootballUnavailable(ApiFootballError):
    """Network error or 5xx after the retry limit."""


@dataclass(frozen=True)
class ApiFootballResult:
    endpoint: str
    params: Mapping[str, Any]
    status_code: int
    response: Any
    results: int | None
    paging: Mapping[str, Any]
    quota: Mapping[str, str]


class MinuteRateLimiter:
    """Blocks until a request slot is free within a rolling 60-second window."""

    def __init__(
        self,
        max_per_minute: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_per_minute < 1:
            raise ValueError("max_per_minute must be positive")
        self.max_per_minute = max_per_minute
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            while True:
                now = self._clock()
                while self._sent and self._sent[0] <= now - 60:
                    self._sent.popleft()
                if len(self._sent) < self.max_per_minute:
                    self._sent.append(now)
                    return
                self._sleep(self._sent[0] + 60 - now)


@dataclass
class DailyBudget:
    """Requests used per UTC day (API-Football resets its daily quota at 00:00 UTC)."""

    limit: int
    today: Callable[[], date] = field(default=lambda: datetime.now(UTC).date())
    _day: date | None = field(default=None, init=False)
    _used: int = field(default=0, init=False)

    def _roll(self) -> None:
        day = self.today()
        if day != self._day:
            self._day, self._used = day, 0

    @property
    def used(self) -> int:
        self._roll()
        return self._used

    def consume(self) -> None:
        self._roll()
        if self._used >= self.limit:
            raise ApiFootballBudgetExceeded(
                f"API-Football daily budget reached ({self.limit}); new collection stopped"
            )
        self._used += 1

    def sync_from_remaining(self, plan_limit: int, remaining: int) -> None:
        """Align with the provider's counter (other processes may share the key)."""
        self._roll()
        self._used = max(self._used, plan_limit - remaining)


# One limiter and one budget per process so every job shares the same protection.
_shared_limiter: MinuteRateLimiter | None = None
_shared_budget: DailyBudget | None = None
_shared_lock = threading.Lock()


def shared_protection() -> tuple[MinuteRateLimiter, DailyBudget]:
    global _shared_limiter, _shared_budget
    with _shared_lock:
        if _shared_limiter is None:
            _shared_limiter = MinuteRateLimiter(settings.api_football_per_minute)
        if _shared_budget is None:
            _shared_budget = DailyBudget(settings.api_football_daily_budget)
        return _shared_limiter, _shared_budget


class ApiFootballClient:
    def __init__(
        self,
        api_key: SecretStr | None = None,
        *,
        base_url: str | None = None,
        limiter: MinuteRateLimiter | None = None,
        budget: DailyBudget | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.api_football_key
        shared_limiter, shared_budget = (None, None)
        if limiter is None or budget is None:
            shared_limiter, shared_budget = shared_protection()
        self.limiter = limiter or shared_limiter
        self.budget = budget or shared_budget
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._http = httpx.Client(
            base_url=base_url or settings.api_football_base_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            follow_redirects=False,
        )
        self.request_count = 0  # network attempts in this client's lifetime (sync_runs)
        self.last_quota: dict[str, str] = {}
        self._stop_reason: str | None = None

    def __enter__(self) -> "ApiFootballClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def get(self, endpoint: str, params: Mapping[str, Any] | None = None) -> ApiFootballResult:
        params = dict(params or {})
        key = self._api_key.get_secret_value()
        if not key:
            raise ApiFootballConfigError("API_FOOTBALL_KEY is not configured")
        attempt = 0
        while True:
            if self._stop_reason:
                raise ApiFootballStopped(self._stop_reason)
            self.budget.consume()
            self.limiter.acquire()
            self.request_count += 1
            try:
                response = self._http.get(
                    endpoint, params=params, headers={"x-apisports-key": key}
                )
            except httpx.HTTPError as exc:
                logger.warning("API-Football %s network error: %s", endpoint, type(exc).__name__)
                if attempt >= self.max_retries:
                    raise ApiFootballUnavailable(
                        f"API-Football {endpoint} unreachable after {attempt + 1} attempts"
                    ) from None
                self._backoff(attempt)
                attempt += 1
                continue

            self._record_quota(response)
            logger.info("API-Football %s -> HTTP %s", endpoint, response.status_code)
            if response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise ApiFootballUnavailable(
                        f"API-Football {endpoint} returned HTTP {response.status_code}"
                    )
                self._backoff(attempt)
                attempt += 1
                continue
            return self._parse(endpoint, params, response, key)

    def _parse(
        self, endpoint: str, params: dict[str, Any], response: httpx.Response, key: str
    ) -> ApiFootballResult:
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise ApiFootballResponseError(
                f"API-Football {endpoint} returned a non-JSON body",
                status_code=response.status_code,
                error_keys=["decode"],
            )
        errors = body.get("errors")
        status = response.status_code
        if status in (401, 403, 429) or (errors not in (None, [], {})):
            error_keys = _error_keys(errors)
            text = str(errors).replace(key, "[REDACTED]").lower()
            if status in (401, 403, 429) or any(word in text for word in _STOP_WORDS):
                self._stop_reason = (
                    f"API-Football stopped after HTTP {status} ({', '.join(error_keys) or 'auth'})"
                )
            raise ApiFootballResponseError(
                f"API-Football {endpoint} returned errors: {', '.join(error_keys) or status}",
                status_code=status,
                error_keys=error_keys,
            )
        if status >= 400:
            raise ApiFootballResponseError(
                f"API-Football {endpoint} returned HTTP {status}",
                status_code=status,
                error_keys=[],
            )
        if self.last_quota.get("x-ratelimit-requests-remaining") == "0":
            self._stop_reason = "API-Football daily quota header reached 0"
        return ApiFootballResult(
            endpoint=endpoint,
            params=params,
            status_code=status,
            response=body.get("response"),
            results=body.get("results"),
            paging=body.get("paging") or {},
            quota=dict(self.last_quota),
        )

    def _record_quota(self, response: httpx.Response) -> None:
        quota = {name: response.headers[name] for name in QUOTA_HEADERS if name in response.headers}
        if not quota:
            return
        self.last_quota = quota
        try:
            self.budget.sync_from_remaining(
                int(quota["x-ratelimit-requests-limit"]),
                int(quota["x-ratelimit-requests-remaining"]),
            )
        except (KeyError, ValueError):
            pass

    def _backoff(self, attempt: int) -> None:
        self._sleep(self.backoff_seconds * (2**attempt))


def _error_keys(errors: Any) -> list[str]:
    # Keep only keys/short labels; provider messages may echo request details.
    if isinstance(errors, dict):
        return sorted(str(name) for name in errors)
    if isinstance(errors, list):
        return [f"error[{index}]" for index, _ in enumerate(errors)]
    return ["errors"] if errors else []
