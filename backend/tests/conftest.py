import httpx
import pytest


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    """Tests must never reach external APIs (chat 01: 0 real API-Football calls)."""

    def refuse(self, request):
        raise AssertionError(f"Real HTTP request attempted: {request.url.host}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
