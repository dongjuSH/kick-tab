import json
import logging
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.deps import RateLimit
from app.api.errors import ApiError
from app.api.routes import feedback as feedback_route
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.main import app
from app.notifications.discord import (
    FeedbackNotice,
    build_payload,
    is_discord_webhook,
    notify_feedback,
)

WEBHOOK = SecretStr("https://discord.com/api/webhooks/123/secret-token-value")
NOTICE = FeedbackNotice(
    id=7,
    type="bug",
    body="@everyone 팀 검색이 안 돼요",
    page_path="/teams",
    created_at=datetime(2026, 10, 31, 10, 0, tzinfo=UTC),
    user_id=None,
)


def test_payload_disables_mentions_and_carries_feedback_fields():
    payload = build_payload(NOTICE)
    assert payload["allowed_mentions"] == {"parse": []}
    embed = payload["embeds"][0]
    assert embed["title"] == "새 의견 · 버그"
    assert embed["description"] == NOTICE.body
    fields = {field["name"]: field["value"] for field in embed["fields"]}
    assert fields == {"페이지": "/teams", "접수 번호": "#7", "작성자": "비회원"}
    member = build_payload(
        FeedbackNotice(1, None, "x", None, NOTICE.created_at, uuid.uuid4())
    )["embeds"][0]
    assert member["title"] == "새 의견 · 유형 없음"
    assert {f["name"]: f["value"] for f in member["fields"]}["작성자"] == "회원"


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://discord.com/api/webhooks/1/abc", True),
        ("https://discordapp.com/api/webhooks/1/abc", True),
        ("http://discord.com/api/webhooks/1/abc", False),
        ("https://evil.example/api/webhooks/1/abc", False),
        ("https://discord.com/channels/1", False),
    ],
)
def test_only_https_discord_webhooks_are_used(url, ok):
    assert is_discord_webhook(url) is ok


def test_sends_payload_to_webhook():
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(204)

    assert notify_feedback(NOTICE, webhook_url=WEBHOOK, transport=httpx.MockTransport(handler))
    assert str(sent[0].url) == WEBHOOK.get_secret_value()
    assert json.loads(sent[0].content)["embeds"][0]["fields"][1]["value"] == "#7"


def test_disabled_or_invalid_webhook_sends_nothing():
    def handler(request):
        raise AssertionError("must not send")

    transport = httpx.MockTransport(handler)
    assert notify_feedback(NOTICE, webhook_url=SecretStr(""), transport=transport) is False
    evil = SecretStr("https://evil.example/x")
    assert notify_feedback(NOTICE, webhook_url=evil, transport=transport) is False


@pytest.mark.parametrize(
    "outcome", [httpx.Response(429), httpx.Response(500), httpx.ConnectError("down")]
)
def test_failures_never_raise_or_log_the_webhook(outcome, caplog):
    caplog.set_level(logging.DEBUG)

    def handler(request):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    transport = httpx.MockTransport(handler)
    assert notify_feedback(NOTICE, webhook_url=WEBHOOK, transport=transport) is False
    assert "secret-token-value" not in caplog.text


def test_feedback_route_schedules_notification_after_saving(monkeypatch):
    from unittest.mock import MagicMock

    session = MagicMock()
    session.scalar.return_value = None  # no duplicate within 24 hours

    def refresh(obj):
        obj.id = 42
        obj.created_at = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)

    session.refresh.side_effect = refresh
    notified: list[FeedbackNotice] = []
    monkeypatch.setattr(feedback_route, "notify_feedback", notified.append)
    app.dependency_overrides[get_db] = lambda: session
    feedback_route.feedback_rate_limit.reset()
    try:
        response = TestClient(app).post(
            "/api/v1/feedback",
            json={"body": "좋아요", "type": "suggestion", "pagePath": "/"},
            headers={"X-KickTab-Client": "web"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)
        feedback_route.feedback_rate_limit.reset()
    assert response.status_code == 201
    created = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)
    assert notified == [FeedbackNotice(42, "suggestion", "좋아요", "/", created, None)]


def test_global_cap_stops_rotating_client_ips():
    """A forged X-Forwarded-For gives a new per-client bucket each time (C-08)."""
    counter = iter(range(100))
    limit = RateLimit(
        "probe",
        [Limit(3, 60)],
        key_func=lambda request: f"10.0.0.{next(counter)}",
        global_limits=[Limit(2, 60)],
    )
    request = Request({"type": "http", "headers": []})
    limit(request)
    limit(request)
    with pytest.raises(ApiError) as exc:
        limit(request)
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1


def test_global_rejection_does_not_create_client_buckets():
    counter = iter(range(20_000))
    limit = RateLimit(
        "probe",
        [Limit(3, 60)],
        key_func=lambda request: f"10.0.{next(counter)}",
        global_limits=[Limit(1, 60)],
    )
    request = Request({"type": "http", "headers": []})
    limit(request)
    for _ in range(10_050):
        with pytest.raises(ApiError):
            limit(request)
    assert limit.limiter.size == 1
    assert limit.global_limiter is not None and limit.global_limiter.size == 1
