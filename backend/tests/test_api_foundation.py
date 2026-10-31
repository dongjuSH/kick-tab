from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.api.errors import ApiError
from app.api.routes.feedback import feedback_rate_limit
from app.db.session import get_db
from app.main import app
from app.models.feedback import Feedback

WEB = {"X-KickTab-Client": "web"}
HELLO = {"body": "hello", "type": "other"}
HI = {"body": "hi", "type": "other"}

# Test-only routes to exercise the shared exception handlers.
_probe = APIRouter(prefix="/__probe")


@_probe.get("/api-error")
def _raise_api_error():
    raise ApiError(409, "FAVORITE_LIMIT", "관심 팀은 최대 5개까지 등록할 수 있습니다.")


@_probe.get("/crash")
def _crash():
    raise RuntimeError("password=private-test-value SELECT * FROM users")


app.include_router(_probe)


@pytest.fixture
def stored():
    """Fake DB session capturing feedback rows instead of writing to PostgreSQL."""
    rows: list[Feedback] = []
    session = MagicMock()
    session.add.side_effect = rows.append

    def refresh(obj):
        obj.id = len(rows)
        obj.created_at = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)

    session.refresh.side_effect = refresh
    app.dependency_overrides[get_db] = lambda: session
    feedback_rate_limit.reset()
    yield rows
    app.dependency_overrides.pop(get_db, None)
    feedback_rate_limit.reset()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_top_matches_contract_is_empty_until_policy_is_decided(client):
    response = client.get("/api/v1/top-matches/current")
    assert response.status_code == 200
    assert response.json() == {"data": {"period": None, "items": []}, "meta": {"updatedAt": None}}


def test_feedback_is_stored_anonymously_with_trimmed_body(client, stored):
    response = client.post(
        "/api/v1/feedback",
        json={"body": "  팀 검색이 느려요  ", "type": "bug", "pagePath": "/teams?q=x"},
        headers=WEB,
    )
    assert response.status_code == 201
    assert response.json() == {
        "data": {"id": 1, "createdAt": "2026-10-31T10:00:00Z"},
        "meta": {},
    }
    (row,) = stored
    assert row.user_id is None
    assert row.body == "팀 검색이 느려요"
    assert row.type == "bug"
    assert row.page_path == "/teams"


@pytest.mark.parametrize("payload", [{"body": "좋아요"}, {"body": "좋아요", "type": None}])
def test_feedback_type_is_required(client, stored, payload):
    """User decision 2026-10-31: 의견 유형(버그·제안·기타) is required."""
    response = client.post("/api/v1/feedback", json=payload, headers=WEB)
    assert response.status_code == 422
    assert "type" in response.json()["error"]["details"]["fields"]
    assert stored == []


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"body": "   \n  "}, "body"),
        ({"type": "bug"}, "body"),
        ({"body": "가" * 1001, "type": "bug"}, "body"),
        ({"body": "ok", "type": "spam"}, "type"),
        ({"body": "ok", "type": "bug", "pagePath": "https://evil.example"}, "pagePath"),
    ],
)
def test_invalid_feedback_is_rejected_without_saving(client, stored, payload, field):
    response = client.post("/api/v1/feedback", json=payload, headers=WEB)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["details"]["fields"]
    assert stored == []


def test_feedback_accepts_exactly_1000_characters(client, stored):
    payload = {"body": "가" * 1000, "type": "other"}
    response = client.post("/api/v1/feedback", json=payload, headers=WEB)
    assert response.status_code == 201


def test_changing_request_without_csrf_header_is_forbidden(client, stored):
    response = client.post("/api/v1/feedback", json=HELLO)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert stored == []


def test_changing_request_from_unknown_origin_is_forbidden(client, stored):
    response = client.post(
        "/api/v1/feedback",
        json=HELLO,
        headers={**WEB, "Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "origin"}
    assert stored == []


def test_allowed_origin_passes_csrf_check(client, stored):
    response = client.post(
        "/api/v1/feedback",
        json=HELLO,
        headers={**WEB, "Origin": "http://localhost:3000"},
    )
    assert response.status_code == 201


def test_feedback_rate_limit_returns_429_with_retry_after(client, stored):
    for _ in range(3):
        assert client.post("/api/v1/feedback", json=HI, headers=WEB).status_code == 201
    response = client.post("/api/v1/feedback", json=HI, headers=WEB)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) >= 1
    assert len(stored) == 3


def test_failed_save_is_not_counted_and_hides_internal_details(client):
    session = MagicMock()
    session.commit.side_effect = RuntimeError("password=private-test-value")
    app.dependency_overrides[get_db] = lambda: session
    feedback_rate_limit.reset()
    try:
        response = client.post("/api/v1/feedback", json=HELLO, headers=WEB)
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private-test-value" not in response.text


def test_unknown_route_uses_error_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_api_error_and_unhandled_error_envelopes(client):
    response = client.get("/__probe/api-error")
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "FAVORITE_LIMIT",
        "message": "관심 팀은 최대 5개까지 등록할 수 있습니다.",
        "details": {},
    }
    crash = client.get("/__probe/crash")
    assert crash.status_code == 500
    assert crash.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private-test-value" not in crash.text
    assert "SELECT" not in crash.text


def test_openapi_uses_camel_case_and_documents_error_envelope(client):
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]
    assert set(components["MatchSummary"]["properties"]) >= {
        "kickoffAt", "kickoffDateKst", "timeConfirmed", "finishType", "statusReason",
    }
    assert set(components["TeamRef"]["properties"]) == {
        "id", "nameKo", "nameEn", "crestUrl", "detailAvailable",
    }
    assert "pagePath" in components["FeedbackCreate"]["properties"]
    assert {"rank", "match", "averageRating", "ratingCount"} == set(
        components["TopMatchItem"]["properties"]
    )
    feedback_responses = schema["paths"]["/api/v1/feedback"]["post"]["responses"]
    assert "ErrorResponse" in str(feedback_responses["4XX"])
