"""NAVER API HUB news search client (chat 03, OPS-004).

- Keys are read from SecretStr only when building the request; never logged or raised.
- Gateway errors ({"error": {...}}), search errors ({"errorCode": ...}), non-2xx and
  non-JSON bodies are failures, never an empty result. 401/403/429 stop further calls.
- No retries and no polling: the 30-minute job is the only caller (daily limit 25,000).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.config import settings

logger = logging.getLogger(__name__)
SEARCH_PATH = "/search/v1/news"
STOP_STATUSES = frozenset({401, 403, 429})


class NaverNewsError(Exception):
    """Messages carry the HTTP status / error code only."""


class NaverNewsConfigError(NaverNewsError):
    pass


class NaverNewsStopped(NaverNewsError):
    pass


@dataclass(frozen=True)
class NaverNewsItem:
    title: str
    description: str
    originallink: str
    link: str
    pub_date: str


class NaverNewsClient:
    def __init__(
        self,
        client_id: SecretStr | None = None,
        client_secret: SecretStr | None = None,
        *,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        min_interval_seconds: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._id = client_id if client_id is not None else settings.naver_client_id
        self._secret = client_secret if client_secret is not None else settings.naver_client_secret
        self._http = httpx.Client(
            base_url=base_url or settings.naver_news_base_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            follow_redirects=False,
        )
        self._interval = min_interval_seconds
        self._sleep = sleep
        self._last: float | None = None
        self.request_count = 0
        self._stop_reason: str | None = None

    def __enter__(self) -> "NaverNewsClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def search(self, query: str, *, display: int = 100) -> list[NaverNewsItem]:
        """Newest first (sort=date). The provider caps display at 100."""
        client_id, secret = self._id.get_secret_value(), self._secret.get_secret_value()
        if not client_id or not secret:
            raise NaverNewsConfigError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET are not configured")
        if self._stop_reason:
            raise NaverNewsStopped(self._stop_reason)
        if self._last is not None:
            wait = self._interval - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
        self.request_count += 1
        self._last = time.monotonic()
        try:
            response = self._http.get(
                SEARCH_PATH,
                params={
                    "query": query, "display": display, "start": 1, "sort": "date", "format": "json"
                },
                headers={"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": secret},
            )
        except httpx.HTTPError as exc:
            raise NaverNewsError(f"NAVER news unreachable ({type(exc).__name__})") from None
        logger.info("NAVER news search -> HTTP %s", response.status_code)
        return self._parse(response)

    def _parse(self, response: httpx.Response) -> list[NaverNewsItem]:
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None
        if status in STOP_STATUSES:
            self._stop_reason = f"NAVER news stopped after HTTP {status}"
            raise NaverNewsStopped(self._stop_reason)
        if not isinstance(body, dict):
            raise NaverNewsError(f"NAVER news returned a non-JSON body (HTTP {status})")
        gateway = body.get("error") if isinstance(body.get("error"), dict) else {}
        code = body.get("errorCode") or gateway.get("errorCode")
        if not 200 <= status < 300 or code or gateway:
            # Only short codes are kept; free-form messages could echo request details.
            safe_code = str(code or "http-error")[:20]
            raise NaverNewsError(f"NAVER news error HTTP {status} ({safe_code})")
        items = body.get("items")
        if not isinstance(items, list):
            raise NaverNewsError("NAVER news response has no items array")
        return [_item(row) for row in items if isinstance(row, dict)]


def _item(row: dict[str, Any]) -> NaverNewsItem:
    return NaverNewsItem(
        title=str(row.get("title") or ""),
        description=str(row.get("description") or ""),
        originallink=str(row.get("originallink") or ""),
        link=str(row.get("link") or ""),
        pub_date=str(row.get("pubDate") or ""),
    )
