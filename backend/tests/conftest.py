import httpx
import pytest
from pydantic import SecretStr

from app.config import settings


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    """Tests must never reach external APIs (chat 01: 0 real API-Football calls)."""

    def refuse(self, request):
        raise AssertionError(f"Real HTTP request attempted: {request.url.host}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)


@pytest.fixture(autouse=True)
def no_feedback_webhook(monkeypatch):
    """Ignore a webhook configured in the local .env; tests pass one explicitly."""
    monkeypatch.setattr(settings, "feedback_discord_webhook_url", SecretStr(""))
