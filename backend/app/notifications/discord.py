"""New-feedback alerts to a Discord channel webhook.

The database stays the source of truth (FEED-003): a failed or disabled notification never
affects the stored feedback. The webhook URL contains a token, so it is read from
SecretStr only when sending and never logged.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from app.config import settings
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)

DISCORD_HOSTS = frozenset(
    {"discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"}
)
TYPE_LABELS = {"bug": "버그", "suggestion": "제안", "other": "기타"}
EMBED_COLOR = 0x2563EB  # action/primary
WEBHOOK_PATH = "/api/webhooks/"


class _RedactWebhookUrls(logging.Filter):
    """httpx logs every request URL at INFO; a webhook URL carries its token."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and any(WEBHOOK_PATH in str(a) for a in record.args):
            record.args = tuple(
                "[discord webhook]" if WEBHOOK_PATH in str(a) else a for a in record.args
            )
        return True


_httpx_logger = logging.getLogger("httpx")
if not any(isinstance(f, _RedactWebhookUrls) for f in _httpx_logger.filters):
    _httpx_logger.addFilter(_RedactWebhookUrls())


@dataclass(frozen=True)
class FeedbackNotice:
    """Detached copy of a stored feedback row (safe to use after the session closes)."""

    id: int
    type: str | None
    body: str
    page_path: str | None
    created_at: datetime
    user_id: uuid.UUID | None

    @classmethod
    def from_model(cls, feedback: Feedback) -> "FeedbackNotice":
        return cls(
            id=feedback.id,
            type=feedback.type,
            body=feedback.body,
            page_path=feedback.page_path,
            created_at=feedback.created_at,
            user_id=feedback.user_id,
        )


def is_discord_webhook(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and parts.hostname in DISCORD_HOSTS
        and parts.path.startswith(WEBHOOK_PATH)
    )


def build_payload(notice: FeedbackNotice) -> dict[str, Any]:
    label = TYPE_LABELS.get(notice.type or "", "유형 없음")
    return {
        "username": "KickTab 의견",
        # User text must never ping @everyone, roles or members.
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": f"새 의견 · {label}",
                "description": notice.body,
                "color": EMBED_COLOR,
                "fields": [
                    {"name": "페이지", "value": notice.page_path or "—", "inline": True},
                    {"name": "접수 번호", "value": f"#{notice.id}", "inline": True},
                    {
                        "name": "작성자",
                        "value": "회원" if notice.user_id else "비회원",
                        "inline": True,
                    },
                ],
                "timestamp": notice.created_at.isoformat(),
            }
        ],
    }


def notify_feedback(
    notice: FeedbackNotice,
    *,
    webhook_url: SecretStr | None = None,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Send one alert. Returns True on success; never raises (runs as a background task)."""
    url = webhook_url if webhook_url is not None else settings.feedback_discord_webhook_url
    raw = url.get_secret_value()
    if not raw:
        return False
    if not is_discord_webhook(raw):
        logger.warning("Feedback notification skipped: webhook URL is not a Discord webhook")
        return False
    try:
        with httpx.Client(timeout=5.0, transport=transport, follow_redirects=False) as client:
            response = client.post(raw, json=build_payload(notice))
    except httpx.HTTPError as exc:
        logger.warning("Feedback notification failed: %s", type(exc).__name__)
        return False
    if response.status_code >= 400:
        # No retry: the row is already stored and visible in the database.
        logger.warning("Feedback notification failed: HTTP %s", response.status_code)
        return False
    return True
