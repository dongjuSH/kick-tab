"""API-Football client protections, using a mock transport only (0 real calls)."""

import logging
from datetime import date

import httpx
import pytest
from pydantic import SecretStr

from app.providers.api_football import (
    ApiFootballBudgetExceeded,
    ApiFootballClient,
    ApiFootballConfigError,
    ApiFootballResponseError,
    ApiFootballStopped,
    ApiFootballUnavailable,
    DailyBudget,
    MinuteRateLimiter,
)

KEY = "test-secret-key-123"
OK_BODY = {
    "errors": [],
    "results": 1,
    "paging": {"current": 1, "total": 1},
    "response": [{"id": 1}],
}


class Recorder:
    """httpx.MockTransport handler that replays queued responses and records requests."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(recorder, *, budget=None, limiter=None, sleeps=None, key=KEY):
    return ApiFootballClient(
        SecretStr(key),
        base_url="https://api-football.test",
        limiter=limiter or MinuteRateLimiter(250, sleep=lambda _: None),
        budget=budget or DailyBudget(7000),
        transport=httpx.MockTransport(recorder),
        sleep=(sleeps.append if sleeps is not None else (lambda _: None)),
    )


def test_success_returns_response_and_records_quota():
    recorder = Recorder(
        httpx.Response(
            200,
            json=OK_BODY,
            headers={
                "x-ratelimit-requests-limit": "7500",
                "x-ratelimit-requests-remaining": "7400",
            },
        )
    )
    budget = DailyBudget(7000)
    with make_client(recorder, budget=budget) as client:
        result = client.get("/fixtures", {"date": "2026-11-01"})
    assert result.response == [{"id": 1}]
    assert result.results == 1
    assert client.request_count == 1
    assert result.quota["x-ratelimit-requests-remaining"] == "7400"
    # Budget aligns with the provider's counter (7500 - 7400 = 100 used today).
    assert budget.used == 100
    request = recorder.requests[0]
    assert request.headers["x-apisports-key"] == KEY
    assert KEY not in str(request.url)


def test_http_200_with_errors_is_a_failure_not_empty_data():
    recorder = Recorder(httpx.Response(200, json={"errors": {"date": "bad"}, "response": []}))
    with make_client(recorder) as client, pytest.raises(ApiFootballResponseError) as exc:
        client.get("/fixtures")
    assert exc.value.error_keys == ["date"]
    assert client.request_count == 1  # validation errors are not retried


def test_server_errors_are_retried_at_most_twice_with_backoff():
    sleeps: list[float] = []
    recorder = Recorder(*(httpx.Response(503) for _ in range(5)))
    with make_client(recorder, sleeps=sleeps) as client, pytest.raises(ApiFootballUnavailable):
        client.get("/fixtures")
    assert len(recorder.requests) == 3
    assert client.request_count == 3
    assert sleeps == [1.0, 2.0]


def test_network_error_then_success():
    recorder = Recorder(httpx.ConnectError("boom"), httpx.Response(200, json=OK_BODY))
    with make_client(recorder) as client:
        assert client.get("/fixtures").response == [{"id": 1}]
    assert client.request_count == 2


def test_auth_or_quota_failure_stops_further_calls():
    body = {"errors": {"requests": "You have reached the request limit"}}
    recorder = Recorder(httpx.Response(200, json=body))
    with make_client(recorder) as client:
        with pytest.raises(ApiFootballResponseError):
            client.get("/fixtures")
        with pytest.raises(ApiFootballStopped):
            client.get("/fixtures")
    assert len(recorder.requests) == 1


def test_http_429_stops_without_retry():
    recorder = Recorder(httpx.Response(429, json={"errors": {"rateLimit": "Too many requests"}}))
    with make_client(recorder) as client:
        with pytest.raises(ApiFootballResponseError):
            client.get("/fixtures")
        with pytest.raises(ApiFootballStopped):
            client.get("/standings")
    assert len(recorder.requests) == 1


def test_daily_budget_blocks_before_any_network_call():
    recorder = Recorder(httpx.Response(200, json=OK_BODY), httpx.Response(200, json=OK_BODY))
    budget = DailyBudget(1)
    with make_client(recorder, budget=budget) as client:
        client.get("/fixtures")
        with pytest.raises(ApiFootballBudgetExceeded):
            client.get("/fixtures")
    assert len(recorder.requests) == 1


def test_daily_budget_resets_on_new_utc_day():
    days = iter([date(2026, 10, 31)] * 2 + [date(2026, 11, 1)] * 2)
    budget = DailyBudget(1, today=lambda: next(days))
    budget.consume()
    with pytest.raises(ApiFootballBudgetExceeded):
        budget.consume()
    budget.consume()  # new day
    assert budget.used == 1


def test_minute_limiter_waits_for_the_oldest_request_to_expire():
    now = [0.0]
    waits: list[float] = []

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    limiter = MinuteRateLimiter(2, clock=lambda: now[0], sleep=sleep)
    limiter.acquire()
    now[0] = 10.0
    limiter.acquire()
    now[0] = 20.0
    limiter.acquire()  # must wait until t=60
    assert waits == [40.0]


def test_missing_key_never_sends_a_request():
    recorder = Recorder()
    with make_client(recorder, key="") as client, pytest.raises(ApiFootballConfigError):
        client.get("/fixtures")
    assert recorder.requests == []


def test_key_is_not_exposed_in_errors_or_logs(caplog):
    caplog.set_level(logging.DEBUG)
    recorder = Recorder(
        httpx.ConnectError(f"failed with {KEY}"),
        httpx.ConnectError("again"),
        httpx.ConnectError("again"),
    )
    with make_client(recorder) as client, pytest.raises(ApiFootballUnavailable) as exc:
        client.get("/fixtures")
    assert KEY not in str(exc.value)
    assert exc.value.__cause__ is None
    assert KEY not in caplog.text
    assert KEY not in repr(client.__dict__)


@pytest.mark.parametrize("status", [401, 403, 429])
@pytest.mark.parametrize(
    "response_kwargs",
    [{"text": "<html>Too Many Requests</html>"}, {"json": {"errors": {"token": "bad"}}}],
    ids=["non-json", "json"],
)
def test_auth_and_rate_limit_statuses_stop_even_without_json(status, response_kwargs):
    recorder = Recorder(
        httpx.Response(status, **response_kwargs), httpx.Response(200, json=OK_BODY)
    )
    with make_client(recorder) as client:
        with pytest.raises(ApiFootballResponseError) as exc:
            client.get("/fixtures")
        assert exc.value.status_code == status
        with pytest.raises(ApiFootballStopped):
            client.get("/fixtures")
    assert len(recorder.requests) == 1
    assert client.request_count == 1
