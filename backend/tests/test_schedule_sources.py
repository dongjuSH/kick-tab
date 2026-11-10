"""Chat 03 provider/job/route behaviour with mocked transports and sessions (no real HTTP)."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.db.session import get_db
from app.main import app
from app.models.sync_run import SyncRun
from app.providers.naver_news import (
    NaverNewsClient,
    NaverNewsConfigError,
    NaverNewsError,
    NaverNewsStopped,
)
from app.sync.registry import JOBS, register_job
from app.sync.runner import run_job

ID, SECRET = SecretStr("client-id-123"), SecretStr("client-secret-456")


def _client(handler):
    return NaverNewsClient(
        ID, SECRET, transport=httpx.MockTransport(handler), base_url="https://naver.test",
        sleep=lambda _: None,
    )


def test_naver_search_success_and_headers():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        seen["params"] = dict(request.url.params)
        item = {"title": "<b>맨시티</b>", "description": "d", "originallink": "https://a.kr/1",
                "link": "https://n.news.naver.com/1", "pubDate": "Mon, 02 Nov 2026 13:00:00 +0900"}
        return httpx.Response(200, json={"items": [item]})

    with _client(handler) as client:
        items = client.search("프리미어리그")
    assert items[0].originallink == "https://a.kr/1" and client.request_count == 1
    assert seen["x-ncp-apigw-api-key-id"] == "client-id-123"
    assert seen["params"]["sort"] == "date" and seen["params"]["display"] == "100"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"error": {"errorCode": "300", "message": "client-secret-456"}}),
        httpx.Response(200, json={"errorCode": "SE01", "errorMessage": "bad"}),
        httpx.Response(500, json={"items": []}),
        httpx.Response(200, text="<html>oops</html>"),
        httpx.Response(200, json={"total": 0}),
    ],
)
def test_naver_errors_are_failures_not_empty_results(response):
    with _client(lambda _: response) as client, pytest.raises(NaverNewsError) as caught:
        client.search("q")
    assert "client-secret-456" not in str(caught.value)
    assert "client-id-123" not in str(caught.value)


def test_naver_auth_or_quota_errors_stop_further_calls():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"errorCode": "429"})

    with _client(handler) as client:
        with pytest.raises(NaverNewsStopped):
            client.search("a")
        with pytest.raises(NaverNewsStopped):
            client.search("b")
    assert len(calls) == 1


def test_naver_missing_keys_make_no_request():
    client = NaverNewsClient(SecretStr(""), SecretStr(""), transport=httpx.MockTransport(
        lambda _: pytest.fail("no request expected")))
    with pytest.raises(NaverNewsConfigError):
        client.search("a")


def test_precheck_skips_without_a_sync_runs_row():
    store: dict[int, SyncRun] = {}

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def add(self, obj):
            store[len(store) + 1] = obj

        def commit(self):
            pass

    @contextmanager
    def lock(_):
        yield True

    register_job("test-precheck", precheck=lambda _s, params: bool(params.get("go")))(
        lambda ctx: None
    )
    try:
        idle = run_job("test-precheck", session_factory=Session, lock_factory=lock)
        assert idle.status == "skipped" and idle.run_id is None and store == {}
    finally:
        JOBS.pop("test-precheck")


@pytest.fixture
def client():
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_db, None)


def test_fixtures_date_outside_collection_window_is_rejected(client):
    response = client.get("/api/v1/fixtures", params={"date": "2030-01-01"})
    body = response.json()
    assert response.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR"
    assert "date" in body["error"]["details"]["fields"]


@pytest.mark.parametrize("teams", ["", "a,b", "1,2,3,4,5,6", "0", "-1", "50,0"])
def test_favorite_schedule_requires_one_to_five_ids(client, teams):
    response = client.get("/api/v1/fixtures/next", params={"teams": teams})
    assert response.status_code == 422


def test_team_search_requires_a_query(client):
    assert client.get("/api/v1/teams/search", params={"q": ""}).status_code == 422


def test_news_rejects_unknown_badge(client):
    assert client.get("/api/v1/news", params={"badge": "KLeague"}).status_code == 422


def test_openapi_exposes_typed_meta():
    schema = json.loads(TestClient(app).get("/openapi.json").text)["components"]["schemas"]
    assert set(schema["ScheduleMeta"]["properties"]) == {
        "updatedAt", "failedCompetitionIds", "checkedAt", "checkedThrough", "delayed",
    }
    assert set(schema["NewsMeta"]["properties"]) == {
        "nextCursor", "updatedAt", "stale", "total", "noNew",
    }
    assert set(schema["FixtureDateAvailability"]["properties"]) == {
        "date", "competitionIds", "unknownCompetitionIds",
    }
    # Chat 05: past results page meta and the season dropdown.
    assert set(schema["ResultsMeta"]["properties"]) == {
        "page", "size", "total", "updatedAt", "failedCompetitionIds",
    }
    assert set(schema["SeasonItem"]["properties"]) == {"season", "label", "current"}
    assert "seasons" in schema["CompetitionItem"]["properties"]


def _link_transport(head_status, get_status, location=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/moved":
            return httpx.Response(200)
        status = head_status if request.method == "HEAD" else get_status
        headers = {"location": location} if location and status in (301, 302) else {}
        return httpx.Response(status, headers=headers)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    ("head", "get", "expected"),
    [
        (200, 200, "reachable"),
        (404, 200, "reachable"),  # press sites that refuse HEAD with 404
        (404, 404, "gone"),
        (410, 410, "gone"),
        (500, 503, "unknown"),  # one failure never means deleted
        (403, 403, "unknown"),
    ],
)
def test_news_link_check(head, get, expected):
    from app.services.news_link import check_link

    assert check_link("https://press.test/a", transport=_link_transport(head, get)) == expected


def test_news_link_check_follows_redirects():
    from app.services.news_link import check_link

    transport = _link_transport(301, 301, location="https://press.test/moved")
    assert check_link("https://press.test/a", transport=transport) == "reachable"


def test_news_link_rejects_private_hosts():
    from app.services.news_link import is_public_url

    assert not is_public_url("http://127.0.0.1/admin")
    assert not is_public_url("http://localhost:8000/")
    assert not is_public_url("ftp://example.com/")


def test_news_link_unknown_article_is_404(client):
    session = MagicMock()
    session.get.return_value = None
    app.dependency_overrides[get_db] = lambda: session
    response = client.get("/api/v1/news/123/link")
    assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("team", ["0", "abc", ""])
def test_team_schedule_requires_a_team_id(client, team):
    assert client.get("/api/v1/fixtures/team", params={"team": team}).status_code == 422
