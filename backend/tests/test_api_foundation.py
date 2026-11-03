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
from app.services.top_matches import current_kst_week

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
    session.scalar.return_value = None  # no duplicate within 24 hours
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


def test_top_matches_shows_the_delay_notice_when_nothing_was_ever_published(client):
    session = MagicMock()
    session.scalar.return_value = None  # no publication at all
    app.dependency_overrides[get_db] = lambda: session
    try:
        response = client.get("/api/v1/top-matches/current")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200
    week = current_kst_week()
    period = {"start": week.start.isoformat(), "end": week.end.isoformat()}
    assert response.json() == {
        "data": {
            "version": None,
            "view": "delayed",
            "week": period,
            "currentWeek": period,
            "selectedAt": None,
            "items": [],
        },
        "meta": {"updatedAt": None},
    }


@pytest.mark.parametrize(
    ("now", "start", "end"),
    [
        # Sunday 23:59 KST still belongs to the week that started on Monday.
        (datetime(2026, 11, 1, 14, 59, tzinfo=UTC), "2026-10-26", "2026-11-01"),
        # Monday 00:00 KST (Sunday 15:00 UTC) starts the next week.
        (datetime(2026, 11, 1, 15, 0, tzinfo=UTC), "2026-11-02", "2026-11-08"),
    ],
)
def test_current_kst_week_switches_at_monday_midnight_kst(now, start, end):
    week = current_kst_week(now)
    assert (week.start.isoformat(), week.end.isoformat()) == (start, end)


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
    session.scalar.return_value = None  # no duplicate within 24 hours
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
    item = set(components["TopMatchItem"]["properties"])
    assert item == {"rank", "reason", "selectedKickoffAt", "match"}
    assert set(components["TopMatches"]["properties"]) == {
        "version", "view", "week", "currentWeek", "selectedAt", "items",
    }
    assert components["TopMatches"]["properties"]["view"]["enum"] == ["list", "none", "delayed"]
    feedback_responses = schema["paths"]["/api/v1/feedback"]["post"]["responses"]
    assert "ErrorResponse" in str(feedback_responses["4XX"])


def test_honeypot_filled_is_refused_without_saving(client, stored, monkeypatch):
    from app.api.routes import feedback as route

    notified = []
    monkeypatch.setattr(route, "notify_feedback", notified.append)
    payload = {**HELLO, "website": "http://spam.example"}
    response = client.post("/api/v1/feedback", json=payload, headers=WEB)
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "요청을 처리할 수 없습니다."
    assert "website" not in response.text
    assert stored == [] and notified == []


def test_empty_honeypot_is_accepted(client, stored):
    response = client.post("/api/v1/feedback", json={**HELLO, "website": ""}, headers=WEB)
    assert response.status_code == 201


def test_duplicate_body_within_24_hours_is_refused(client, stored):
    db = app.dependency_overrides[get_db]()
    db.scalar.return_value = 99  # an earlier row with the same body hash exists
    response = client.post("/api/v1/feedback", json=HELLO, headers=WEB)
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "FEEDBACK_DUPLICATE",
        "message": "같은 내용의 의견이 이미 접수되었습니다.",
        "details": {},
    }
    assert stored == []


def test_body_hash_ignores_case_and_whitespace():
    from app.services.feedback import body_hash

    assert body_hash("팀 검색이\n  안 돼요 OK") == body_hash("  팀 검색이 안 돼요 ok ")
    assert body_hash("팀 검색이 안 돼요") != body_hash("팀 검색이 안 돼요!")
    assert len(body_hash("x")) == 64


@pytest.mark.parametrize(
    ("content", "content_type"),
    [("{", "application/json"), ('{"body": "", "type": "bug"}', "application/json")],
)
def test_malformed_or_invalid_bodies_count_toward_the_limit(client, stored, content, content_type):
    """P-10: format errors count too, including JSON that fails to parse."""
    headers = {**WEB, "Content-Type": content_type}
    codes = [
        client.post("/api/v1/feedback", content=content, headers=headers).status_code
        for _ in range(4)
    ]
    assert codes == [422, 422, 422, 429]
    assert stored == []


def test_duplicate_check_runs_under_a_body_hash_lock():
    """Lock first, then check, then insert — so concurrent equal bodies are serialised."""
    from unittest.mock import MagicMock

    from app.schemas.feedback import FeedbackCreate
    from app.services.feedback import body_hash, create_feedback, duplicate_lock_key

    session = MagicMock()
    session.scalar.return_value = None
    create_feedback(session, FeedbackCreate(body="같은 의견", type="bug"))
    calls = [call[0] for call in session.mock_calls if call[0] in ("execute", "scalar", "add")]
    assert calls[:3] == ["execute", "scalar", "add"]
    lock_sql, lock_params = session.execute.call_args.args
    assert "pg_advisory_xact_lock" in str(lock_sql)
    assert lock_params == {"key": duplicate_lock_key(body_hash("같은 의견"))}
