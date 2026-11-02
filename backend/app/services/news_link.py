"""Original-article check when a reader opens a news card (NEWS-004).

One HEAD request, then GET headers only (body never read) whenever HEAD fails, because
several press sites answer HEAD with 404 for live articles; at most 3 redirects, public
hosts only. Only 404/410 count as "not reachable"; timeouts and other failures are
"unknown", because one failed attempt never proves the article was deleted.
"""

import ipaddress
import logging
import socket
from typing import Literal
from urllib.parse import urljoin, urlsplit

import httpx

logger = logging.getLogger(__name__)
LinkStatus = Literal["reachable", "gone", "unknown"]
MAX_REDIRECTS = 3
REDIRECTS = frozenset({301, 302, 303, 307, 308})


def is_public_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    return bool(infos) and all(ipaddress.ip_address(info[4][0]).is_global for info in infos)


def check_link(url: str, *, transport: httpx.BaseTransport | None = None) -> LinkStatus:
    headers = {"User-Agent": "KickTab link check (+news original link)"}
    with httpx.Client(timeout=5.0, follow_redirects=False, transport=transport) as client:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if transport is None and not is_public_url(current):
                return "unknown"
            try:
                response = client.head(current, headers=headers)
                if response.status_code >= 400:
                    with client.stream("GET", current, headers=headers) as streamed:
                        response = streamed  # headers only; the body is never read
            except httpx.HTTPError as exc:
                logger.info("news link check failed: %s", type(exc).__name__)
                return "unknown"
            if response.status_code in REDIRECTS and response.headers.get("location"):
                current = urljoin(current, response.headers["location"])
                continue
            if response.status_code in (404, 410):
                return "gone"
            return "reachable" if response.status_code < 400 else "unknown"
    return "unknown"
