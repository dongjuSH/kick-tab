"""Alerts to Discord channel webhooks: new feedback (chat 01) and TOP 5 delays (chat 04).

The database stays the source of truth (FEED-003, TOP 5 policy): a failed or disabled
notification never affects stored data and is never retried. Webhook URLs contain a token,
so they are read from SecretStr only when sending and never logged.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from app.config import settings
from app.core.kst import KST
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


def _post(
    url: SecretStr, payload: dict[str, Any], label: str, transport: httpx.BaseTransport | None
) -> bool:
    """One POST to a Discord webhook. Returns True on success; never raises or retries."""
    raw = url.get_secret_value()
    if not raw:
        return False
    if not is_discord_webhook(raw):
        logger.warning("%s notification skipped: webhook URL is not a Discord webhook", label)
        return False
    try:
        with httpx.Client(timeout=5.0, transport=transport, follow_redirects=False) as client:
            response = client.post(raw, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("%s notification failed: %s", label, type(exc).__name__)
        return False
    if response.status_code >= 400:
        # No retry: the source data is already stored and visible in the database.
        logger.warning("%s notification failed: HTTP %s", label, response.status_code)
        return False
    return True


def notify_feedback(
    notice: FeedbackNotice,
    *,
    webhook_url: SecretStr | None = None,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Send one alert. Returns True on success; never raises (runs as a background task)."""
    url = webhook_url if webhook_url is not None else settings.feedback_discord_webhook_url
    return _post(url, build_payload(notice), "Feedback", transport)


TOP5_ALERT_COLOR = 0xB45309  # status/warning
TOP5_RECOVERY_COMMAND = "uv run python -m app.sync top5"


@dataclass(frozen=True)
class Top5DelayNotice:
    week_start: date
    attempts: int
    error: str
    failed_at: datetime
    # "delay": second automatic failure, delay notice shown (sent once per week).
    # "models_failed": main and fallback model both failed in one attempt; next_retry_at is
    # the remaining automatic slot, if any.
    kind: Literal["delay", "models_failed"] = "delay"
    next_retry_at: datetime | None = None


def build_top5_payload(notice: Top5DelayNotice) -> dict[str, Any]:
    end = date.fromordinal(notice.week_start.toordinal() + 6)
    if notice.kind == "models_failed":
        return _top5_models_failed_payload(notice, end)
    return {
        "username": "KickTab TOP 5",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "TOP 5 업데이트 지연 · 수동 복구 필요",
                "description": (
                    "자동 선정이 모두 실패해 사용자에게 업데이트 지연 안내를 표시하고 있습니다. "
                    "원인을 확인한 뒤 백엔드 폴더에서 관리 명령으로 다시 실행해 주세요."
                ),
                "color": TOP5_ALERT_COLOR,
                "fields": [
                    {
                        "name": "대상 주(KST)",
                        "value": f"{notice.week_start.isoformat()} ~ {end.isoformat()}",
                        "inline": True,
                    },
                    {"name": "자동 시도", "value": f"{notice.attempts}회 실패", "inline": True},
                    {"name": "마지막 원인", "value": notice.error[:300] or "—", "inline": False},
                    {"name": "복구 명령", "value": f"`{TOP5_RECOVERY_COMMAND}`", "inline": False},
                ],
                "timestamp": notice.failed_at.isoformat(),
            }
        ],
    }


def _top5_models_failed_payload(notice: Top5DelayNotice, end: date) -> dict[str, Any]:
    if notice.next_retry_at is not None:
        next_step = f"{notice.next_retry_at.astimezone(KST):%m/%d %H:%M} KST 자동 재시도 예정"
    else:
        next_step = f"자동 재시도 없음 · `{TOP5_RECOVERY_COMMAND}`로 수동 복구"
    return {
        "username": "KickTab TOP 5",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "TOP 5 AI 호출 실패 · 주 모델과 하위 모델 모두 실패",
                "description": (
                    "이번 시도에서 주 모델 오류 후 하위 모델로 다시 호출했지만 실패했습니다. "
                    "공개 결과는 정책대로 유지됩니다."
                ),
                "color": TOP5_ALERT_COLOR,
                "fields": [
                    {
                        "name": "대상 주(KST)",
                        "value": f"{notice.week_start.isoformat()} ~ {end.isoformat()}",
                        "inline": True,
                    },
                    {"name": "자동 시도", "value": f"{notice.attempts}회", "inline": True},
                    {"name": "원인", "value": notice.error[:300] or "—", "inline": False},
                    {"name": "다음 단계", "value": next_step, "inline": False},
                ],
                "timestamp": notice.failed_at.isoformat(),
            }
        ],
    }


def notify_top5_delay(
    notice: Top5DelayNotice,
    *,
    webhook_url: SecretStr | None = None,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Operator alert: second automatic failure, or main and fallback model both failing in
    one attempt. A failed alert is only logged and never adds a selection attempt."""
    url = webhook_url if webhook_url is not None else settings.top5_alert_discord_webhook_url
    return _post(url, build_top5_payload(notice), "TOP 5 delay", transport)
