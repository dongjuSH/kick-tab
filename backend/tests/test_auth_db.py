"""Chat 02 flows against the dev database (opt-in: KICKTAB_DB_TESTS=1).

Every request runs inside one outer transaction that is rolled back at the end, except the
concurrency test, which needs separate connections: it commits a throwaway account and
deletes it again (the deletion cascades to everything it created).
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

WEB = {"X-KickTab-Client": "web"}
PASSWORD = "abcd1234"
ALL_AGREED = {"termsOfService": True, "privacyCollection": True, "age14OrOlder": True}


class RecordingSender:
    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    def send_code(self, to, purpose, code):
        self.sent.append((to, purpose, code))

    def last(self, to):
        return next(code for addr, _, code in reversed(self.sent) if addr == to)


class Clock:
    def __init__(self):
        self.now = datetime.now(UTC)

    def __call__(self):
        return self.now


@pytest.fixture
def env(monkeypatch):
    from app.api.routes import auth as auth_routes
    from app.api.routes import feedback as feedback_routes
    from app.api.routes import me as me_routes
    from app.config import settings
    from app.db.session import get_db, get_engine
    from app.main import app
    from app.services.mailer import get_email_sender

    monkeypatch.setattr(settings, "auth_jwt_secret", SecretStr("db-test-secret-" + "y" * 64))
    for limit in (
        auth_routes.code_send_limit,
        auth_routes.code_verify_limit,
        auth_routes.login_limit,
        auth_routes.account_limit,
        auth_routes.code_email_limiter,
        auth_routes.login_email_limiter,
        me_routes.password_limit,
        feedback_routes.feedback_rate_limit,
        feedback_routes.feedback_member_limit,
    ):
        limit.reset()
    clock = Clock()
    monkeypatch.setattr(auth_routes, "utcnow", clock)
    monkeypatch.setattr(me_routes, "utcnow", clock)
    sender = RecordingSender()
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_email_sender] = lambda: sender
    try:
        yield app, session, sender, clock
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_email_sender, None)
        session.close()
        transaction.rollback()
        connection.close()


def new_client(app):
    return TestClient(app, raise_server_exceptions=True)


def email():
    return f"kt-test-{uuid.uuid4().hex[:12]}@example.com"


def nickname():
    return "테스트" + uuid.uuid4().hex[:6]


def code_token(client, sender, address, purpose="signup"):
    sent = client.post(
        "/api/v1/auth/email-codes", json={"email": address, "purpose": purpose}, headers=WEB
    )
    assert sent.status_code == 200, sent.text
    verified = client.post(
        "/api/v1/auth/email-codes/verify",
        json={"email": address, "purpose": purpose, "code": sender.last(address)},
        headers=WEB,
    )
    assert verified.status_code == 200, verified.text
    return verified.json()["data"]["verificationToken"]


def signup(client, sender, address=None, name=None, agreements=ALL_AGREED):
    address = address or email()
    token = code_token(client, sender, address)
    return (
        client.post(
            "/api/v1/auth/signup",
            json={
                "email": address,
                "verificationToken": token,
                "nickname": name or nickname(),
                "password": PASSWORD,
                "passwordConfirm": PASSWORD,
                "agreements": agreements,
            },
            headers=WEB,
        ),
        address,
        token,
    )


def users_with(session, address):
    from app.models.user import User

    return session.scalar(select(func.count()).select_from(User).where(User.email == address))


# --- signup and codes -----------------------------------------------------------------


def test_signup_creates_account_session_and_agreements(env):
    from app.models.user import TermsAgreement, User

    app, session, sender, _ = env
    client = new_client(app)
    response, address, _ = signup(client, sender)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["loginMethod"] == "email"
    cookies = response.headers.get_list("set-cookie")
    assert any(
        c.startswith("kt_access=") and "HttpOnly" in c and "SameSite=lax" in c for c in cookies
    )
    assert any(c.startswith("kt_refresh=") and "Path=/api/v1/auth" in c for c in cookies)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["data"]["email"] == address
    user = session.scalar(select(User).where(User.email == address))
    assert user.password_hash.startswith("$argon2id$")
    rows = session.scalars(select(TermsAgreement).where(TermsAgreement.user_id == user.id)).all()
    assert {(r.item_id, r.item_version, r.confirmed) for r in rows} == {
        ("terms_of_service", "draft", True),
        ("privacy_collection", "draft", True),
        ("age_14_or_older", "draft", True),
    }
    assert all(r.agreed_at is not None for r in rows)


@pytest.mark.parametrize(
    "agreements",
    [
        {},
        {"privacyCollection": True, "age14OrOlder": True},
        {"termsOfService": True, "age14OrOlder": True},
        {"termsOfService": True, "privacyCollection": True},
        {"termsOfService": False, "privacyCollection": True, "age14OrOlder": True},
        {"termsOfService": True, "privacyCollection": True, "age14OrOlder": False},
    ],
)
def test_signup_refuses_missing_or_false_confirmations(env, agreements):
    app, session, sender, _ = env
    client = new_client(app)
    response, address, _ = signup(client, sender, agreements=agreements)
    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    expected = {f"agreements.{k}" for k in ALL_AGREED if agreements.get(k) is not True}
    assert expected <= set(fields)
    assert users_with(session, address) == 0


def test_signup_refuses_string_true_for_a_confirmation(env):
    app, session, sender, _ = env
    client = new_client(app)
    response, address, _ = signup(client, sender, agreements={**ALL_AGREED, "age14OrOlder": "true"})
    assert response.status_code == 422
    assert users_with(session, address) == 0


def test_signup_without_verification_creates_nothing(env):
    app, session, _, _ = env
    client = new_client(app)
    address = email()
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": address,
            "verificationToken": "forged",
            "nickname": nickname(),
            "password": PASSWORD,
            "passwordConfirm": PASSWORD,
            "agreements": ALL_AGREED,
        },
        headers=WEB,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"
    assert users_with(session, address) == 0


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"nickname": "가"}, "nickname"),
        ({"nickname": "bad name"}, "nickname"),
        ({"password": "abcdefgh", "passwordConfirm": "abcdefgh"}, "password"),
        ({"passwordConfirm": "abcd12345"}, "passwordConfirm"),
    ],
)
def test_signup_input_rules_match_the_screen(env, change, field):
    app, session, sender, _ = env
    client = new_client(app)
    address = email()
    token = code_token(client, sender, address)
    body = {
        "email": address,
        "verificationToken": token,
        "nickname": nickname(),
        "password": PASSWORD,
        "passwordConfirm": PASSWORD,
        "agreements": ALL_AGREED,
    }
    response = client.post("/api/v1/auth/signup", json={**body, **change}, headers=WEB)
    assert response.status_code == 422
    assert field in response.json()["error"]["details"]["fields"]
    assert users_with(session, address) == 0


def test_taken_email_is_refused_at_code_request_and_nickname_is_unique(env):
    app, _, sender, _ = env
    client = new_client(app)
    name = nickname()
    first, address, _ = signup(client, sender, name=name)
    assert first.status_code == 201
    again = new_client(app).post(
        "/api/v1/auth/email-codes",
        json={"email": address.upper(), "purpose": "signup"},
        headers=WEB,
    )
    assert again.status_code == 409 and again.json()["error"]["code"] == "EMAIL_TAKEN"
    second, _, _ = signup(new_client(app), sender, name=name.upper())
    assert second.status_code == 409 and second.json()["error"]["code"] == "NICKNAME_TAKEN"


def test_resend_waits_one_minute_and_invalidates_previous_code(env):
    app, _, sender, clock = env
    client = new_client(app)
    address = email()
    body = {"email": address, "purpose": "signup"}
    assert client.post("/api/v1/auth/email-codes", json=body, headers=WEB).status_code == 200
    first = sender.last(address)
    early = client.post("/api/v1/auth/email-codes", json=body, headers=WEB)
    assert early.status_code == 429 and int(early.headers["Retry-After"]) >= 1
    clock.now += timedelta(seconds=61)
    assert client.post("/api/v1/auth/email-codes", json=body, headers=WEB).status_code == 200
    second = sender.last(address)
    verify = {"email": address, "purpose": "signup"}
    if first != second:
        old = client.post(
            "/api/v1/auth/email-codes/verify", json={**verify, "code": first}, headers=WEB
        )
        assert old.status_code == 422 and old.json()["error"]["code"] == "VERIFICATION_INVALID"
    ok = client.post(
        "/api/v1/auth/email-codes/verify", json={**verify, "code": second}, headers=WEB
    )
    assert ok.status_code == 200


def test_code_expires_after_ten_minutes(env):
    app, _, sender, clock = env
    client = new_client(app)
    address = email()
    client.post(
        "/api/v1/auth/email-codes", json={"email": address, "purpose": "signup"}, headers=WEB
    )
    clock.now += timedelta(minutes=10, seconds=1)
    response = client.post(
        "/api/v1/auth/email-codes/verify",
        json={"email": address, "purpose": "signup", "code": sender.last(address)},
        headers=WEB,
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "VERIFICATION_EXPIRED"


def test_five_wrong_codes_lock_the_code(env):
    app, _, sender, _ = env
    client = new_client(app)
    address = email()
    client.post(
        "/api/v1/auth/email-codes", json={"email": address, "purpose": "signup"}, headers=WEB
    )
    right = sender.last(address)
    wrong = "000000" if right != "000000" else "111111"
    body = {"email": address, "purpose": "signup"}
    codes = [
        client.post(
            "/api/v1/auth/email-codes/verify", json={**body, "code": wrong}, headers=WEB
        ).json()["error"]["code"]
        for _ in range(5)
    ]
    assert codes == ["VERIFICATION_INVALID"] * 4 + ["VERIFICATION_LOCKED"]
    locked = client.post(
        "/api/v1/auth/email-codes/verify", json={**body, "code": right}, headers=WEB
    )
    assert locked.json()["error"]["code"] == "VERIFICATION_LOCKED"


# --- sessions -------------------------------------------------------------------------


def test_login_refresh_rotation_and_reuse_detection(env):
    app, _, sender, clock = env
    client = new_client(app)
    _, address, _ = signup(client, sender)
    client.cookies.clear()
    bad = client.post(
        "/api/v1/auth/login", json={"email": address, "password": "wrong1234"}, headers=WEB
    )
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "INVALID_CREDENTIALS"
    ok = client.post(
        "/api/v1/auth/login", json={"email": address, "password": PASSWORD}, headers=WEB
    )
    assert ok.status_code == 200
    first_refresh = client.cookies.get("kt_refresh")

    clock.now += timedelta(minutes=20)  # access token past 15 minutes
    rotated = client.post("/api/v1/auth/refresh", headers=WEB)
    assert rotated.status_code == 200
    second_refresh = client.cookies.get("kt_refresh")
    assert second_refresh and second_refresh != first_refresh

    # The old token comes back after the grace window: the whole family is revoked.
    clock.now += timedelta(seconds=30)
    thief = new_client(app)
    thief.cookies.set("kt_refresh", first_refresh, path="/api/v1/auth")
    stolen = thief.post("/api/v1/auth/refresh", headers=WEB)
    assert stolen.status_code == 401
    victim = client.post("/api/v1/auth/refresh", headers=WEB)
    assert victim.status_code == 401


def test_concurrent_refresh_within_grace_keeps_the_session(env):
    app, _, sender, clock = env
    client = new_client(app)
    signup(client, sender)
    old = client.cookies.get("kt_refresh")
    assert client.post("/api/v1/auth/refresh", headers=WEB).status_code == 200
    other_tab = new_client(app)
    other_tab.cookies.set("kt_refresh", old, path="/api/v1/auth")
    late = other_tab.post("/api/v1/auth/refresh", headers=WEB)
    assert late.status_code == 200 and "set-cookie" not in late.headers
    assert client.post("/api/v1/auth/refresh", headers=WEB).status_code == 200


def test_logout_revokes_refresh_and_clears_cookies(env):
    app, _, sender, _ = env
    client = new_client(app)
    signup(client, sender)
    refresh = client.cookies.get("kt_refresh")
    out = client.post("/api/v1/auth/logout", headers=WEB)
    assert out.status_code == 204
    assert client.get("/api/v1/auth/me").json()["data"] is None
    replay = new_client(app)
    replay.cookies.set("kt_refresh", refresh, path="/api/v1/auth")
    assert replay.post("/api/v1/auth/refresh", headers=WEB).status_code == 401


def test_password_reset_then_login_with_new_password(env):
    app, _, sender, clock = env
    client = new_client(app)
    _, address, _ = signup(client, sender)
    old_session = client.cookies.get("kt_refresh")
    clock.now += timedelta(minutes=2)
    guest = new_client(app)
    token = code_token(guest, sender, address, purpose="password_reset")
    reset = guest.post(
        "/api/v1/auth/password-reset",
        json={
            "email": address,
            "verificationToken": token,
            "newPassword": "newpass99",
            "newPasswordConfirm": "newpass99",
        },
        headers=WEB,
    )
    assert reset.status_code == 200
    # Every session of the account ended.
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTH_EXPIRED"
    replay = new_client(app)
    replay.cookies.set("kt_refresh", old_session, path="/api/v1/auth")
    assert replay.post("/api/v1/auth/refresh", headers=WEB).status_code == 401
    assert (
        guest.post(
            "/api/v1/auth/login", json={"email": address, "password": PASSWORD}, headers=WEB
        ).status_code
        == 401
    )
    assert (
        guest.post(
            "/api/v1/auth/login", json={"email": address, "password": "newpass99"}, headers=WEB
        ).status_code
        == 200
    )


def test_password_reset_needs_an_existing_email_account(env):
    app, _, _, _ = env
    response = new_client(app).post(
        "/api/v1/auth/email-codes",
        json={"email": email(), "purpose": "password_reset"},
        headers=WEB,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("body", "code", "field"),
    [
        (
            {
                "currentPassword": "wrong999",
                "newPassword": "newpass99",
                "newPasswordConfirm": "newpass99",
            },
            "PASSWORD_CURRENT_MISMATCH",
            "currentPassword",
        ),
        (
            {"currentPassword": PASSWORD, "newPassword": "short1", "newPasswordConfirm": "short1"},
            "PASSWORD_RULE",
            "newPassword",
        ),
        (
            {
                "currentPassword": PASSWORD,
                "newPassword": "newpass99",
                "newPasswordConfirm": "newpass98",
            },
            "PASSWORD_CONFIRM_MISMATCH",
            "newPasswordConfirm",
        ),
    ],
)
def test_password_change_error_codes(env, body, code, field):
    app, _, sender, _ = env
    client = new_client(app)
    signup(client, sender)
    response = client.patch("/api/v1/me/password", json=body, headers=WEB)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == code and list(error["details"]["fields"]) == [field]


def test_password_change_keeps_this_session_and_ends_others(env):
    app, _, sender, _ = env
    client = new_client(app)
    _, address, _ = signup(client, sender)
    other = new_client(app)
    other.post("/api/v1/auth/login", json={"email": address, "password": PASSWORD}, headers=WEB)
    changed = client.patch(
        "/api/v1/me/password",
        json={
            "currentPassword": PASSWORD,
            "newPassword": "newpass99",
            "newPasswordConfirm": "newpass99",
        },
        headers=WEB,
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401
    assert other.post("/api/v1/auth/refresh", headers=WEB).status_code == 401


# --- favourites -----------------------------------------------------------------------


def detail_teams(session, count):
    from app.models.reference import Team
    from app.services.reference import team_detail_lookup

    lookup = team_detail_lookup(session)
    ids = [t for t in session.scalars(select(Team.id).order_by(Team.id)) if lookup(t) is True]
    if len(ids) < count:
        pytest.skip("not enough team-detail teams collected")
    return ids[:count]


def test_member_favorites_limit_and_ownership(env):
    app, session, sender, _ = env
    teams = detail_teams(session, 11)
    a = new_client(app)
    signup(a, sender)
    for team in teams[:10]:
        assert a.post("/api/v1/me/favorites", json={"teamId": team}, headers=WEB).status_code == 200
    again = a.post("/api/v1/me/favorites", json={"teamId": teams[0]}, headers=WEB)
    assert again.status_code == 200 and len(again.json()["data"]["teams"]) == 10
    eleventh = a.post("/api/v1/me/favorites", json={"teamId": teams[10]}, headers=WEB)
    assert eleventh.status_code == 409 and eleventh.json()["error"]["code"] == "FAVORITE_LIMIT"
    assert eleventh.json()["error"]["message"] == "관심 팀은 최대 10팀까지 등록할 수 있습니다."
    listed = a.get("/api/v1/me/favorites").json()["data"]
    assert [t["id"] for t in listed["teams"]] == teams[:10] and listed["max"] == 10
    # Remove one, the 11th fits; re-adding the removed one is refused again.
    a.delete(f"/api/v1/me/favorites/{teams[3]}", headers=WEB)
    assert (
        a.post("/api/v1/me/favorites", json={"teamId": teams[10]}, headers=WEB).status_code == 200
    )
    assert a.post("/api/v1/me/favorites", json={"teamId": teams[3]}, headers=WEB).status_code == 409
    # Another member's request never touches A's list.
    b = new_client(app)
    signup(b, sender)
    assert b.get("/api/v1/me/favorites").json()["data"]["teams"] == []
    b.delete(f"/api/v1/me/favorites/{teams[0]}", headers=WEB)
    assert len(a.get("/api/v1/me/favorites").json()["data"]["teams"]) == 10


def test_concurrent_adds_never_pass_ten():
    from app.db.session import get_sessionmaker
    from app.models.user import MemberFavorite, User
    from app.services import member_favorites
    from app.services.auth_security import hash_password

    make = get_sessionmaker()
    with make() as session:
        teams = detail_teams(session, 15)
        user = User(
            email=email(),
            nickname=nickname(),
            password_hash=hash_password(PASSWORD),
            login_method="email",
        )
        session.add(user)
        session.commit()
        user_id = user.id

    def add(team_id):
        with make() as db:
            try:
                member_favorites.add_favorite(db, user_id, team_id)
                return "added"
            except Exception as exc:  # noqa: BLE001
                return getattr(exc, "code", type(exc).__name__)

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(add, teams))
        assert results.count("added") == 10 and results.count("FAVORITE_LIMIT") == 5
        with make() as session:
            count = session.scalar(
                select(func.count())
                .select_from(MemberFavorite)
                .where(MemberFavorite.user_id == user_id)
            )
            assert count == 10
    finally:
        with make() as session:
            session.delete(session.get(User, user_id))
            session.commit()


def test_schedule_api_accepts_ten_teams(env):
    app, session, _, _ = env
    teams = detail_teams(session, 10)
    response = new_client(app).get(
        "/api/v1/fixtures/next", params={"teams": ",".join(map(str, teams))}
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]["teams"]) == 10


# --- reviews, feedback, withdrawal ----------------------------------------------------


def open_fixture(session):
    from app.models.fixture import Fixture

    fixture = session.scalar(
        select(Fixture)
        .where(Fixture.status == "finished", Fixture.finish_type == "normal")
        .limit(1)
    )
    if fixture is None:
        pytest.skip("no finished match collected")
    return fixture.id


def test_reviews_write_edit_react_and_ownership(env):
    app, session, sender, _ = env
    fixture_id = open_fixture(session)
    a, b = new_client(app), new_client(app)
    signup(a, sender)
    signup(b, sender)
    blank = a.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": " 　\n"}, headers=WEB)
    assert blank.status_code == 422
    too_long = a.post(
        f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "가" * 301}, headers=WEB
    )
    assert too_long.status_code == 422
    created = a.post(
        f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "좋은 경기"}, headers=WEB
    )
    assert created.status_code == 201
    review = created.json()["data"]
    assert review["mine"] is True and review["authorNickname"]
    dup = a.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "또"}, headers=WEB)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "REVIEW_EXISTS"
    rid = review["id"]
    assert (
        b.patch(f"/api/v1/reviews/{rid}", json={"body": "남의 글"}, headers=WEB).status_code == 403
    )
    assert b.delete(f"/api/v1/reviews/{rid}", headers=WEB).status_code == 403
    assert (
        a.put(f"/api/v1/reviews/{rid}/reaction", json={"value": 1}, headers=WEB).status_code == 403
    )
    liked = b.put(f"/api/v1/reviews/{rid}/reaction", json={"value": 1}, headers=WEB).json()["data"]
    assert liked["likes"] == 1 and liked["myReaction"] == 1
    switched = b.put(f"/api/v1/reviews/{rid}/reaction", json={"value": -1}, headers=WEB).json()[
        "data"
    ]
    assert switched["likes"] == 0 and switched["dislikes"] == 1
    edited = a.patch(f"/api/v1/reviews/{rid}", json={"body": "수정한 평가"}, headers=WEB)
    assert edited.status_code == 200 and edited.json()["data"]["body"] == "수정한 평가"
    mine = a.get("/api/v1/me/reviews").json()["data"]
    assert [m["id"] for m in mine] == [rid]
    assert mine[0]["match"]["id"] == fixture_id and mine[0]["editedAt"] is not None
    listed = b.get(f"/api/v1/fixtures/{fixture_id}/reviews").json()["data"]
    item = next(i for i in listed["items"] if i["id"] == rid)
    assert item["mine"] is False and item["myReaction"] == -1
    # MY-003 (09): once the match is closed the edit is refused with 409 CONFLICT (my page
    # shows '수정할 수 없는 경기'), and the own review can still be deleted. Rolled back.
    from app.models.fixture import Fixture

    fixture = session.get(Fixture, fixture_id)
    fixture.status = "postponed"
    session.flush()
    closed = a.patch(f"/api/v1/reviews/{rid}", json={"body": "닫힌 뒤 수정"}, headers=WEB)
    assert closed.status_code == 409 and closed.json()["error"]["code"] == "CONFLICT"
    after = a.get("/api/v1/me/reviews")
    assert after.status_code == 200, after.text
    assert after.json()["data"][0]["body"] == "수정한 평가"
    assert a.delete(f"/api/v1/reviews/{rid}", headers=WEB).status_code == 204
    fixture.status = "finished"  # the public list is only served for an open match
    session.flush()
    assert all(
        i["id"] != rid
        for i in b.get(f"/api/v1/fixtures/{fixture_id}/reviews").json()["data"]["items"]
    )


def test_member_feedback_is_linked(env, monkeypatch):
    from app.api.routes import feedback as feedback_routes
    from app.models.feedback import Feedback

    monkeypatch.setattr(feedback_routes, "notify_feedback", lambda notice: None)
    app, session, sender, _ = env
    client = new_client(app)
    response, address, _ = signup(client, sender)
    member_id = response.json()["data"]["id"]
    sent = client.post(
        "/api/v1/feedback", json={"body": f"회원 의견 {uuid.uuid4()}", "type": "other"}, headers=WEB
    )
    assert sent.status_code == 201
    row = session.get(Feedback, sent.json()["data"]["id"])
    assert str(row.user_id) == member_id


def test_withdrawal_deletes_member_data_and_unlinks_feedback(env, monkeypatch):
    from app.api.routes import feedback as feedback_routes
    from app.models.feedback import Feedback
    from app.models.review import Review, ReviewReaction
    from app.models.user import MemberFavorite, RefreshToken, TermsAgreement, User

    monkeypatch.setattr(feedback_routes, "notify_feedback", lambda notice: None)
    app, session, sender, _ = env
    fixture_id = open_fixture(session)
    team = detail_teams(session, 1)[0]
    a, b = new_client(app), new_client(app)
    response, address, _ = signup(a, sender)
    user_id = uuid.UUID(response.json()["data"]["id"])
    signup(b, sender)
    a.post("/api/v1/me/favorites", json={"teamId": team}, headers=WEB)
    rid = a.post(
        f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "탈퇴 전 평가"}, headers=WEB
    ).json()["data"]["id"]
    b_rid = b.post(
        f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "남는 평가"}, headers=WEB
    ).json()["data"]["id"]
    a.put(f"/api/v1/reviews/{b_rid}/reaction", json={"value": 1}, headers=WEB)
    fid = a.post(
        "/api/v1/feedback", json={"body": f"탈퇴 의견 {uuid.uuid4()}", "type": "bug"}, headers=WEB
    ).json()["data"]["id"]

    gone = a.delete("/api/v1/me", headers=WEB)
    assert gone.status_code == 204
    session.expire_all()
    assert session.get(User, user_id) is None
    for model in (MemberFavorite, RefreshToken, TermsAgreement, Review, ReviewReaction):
        assert (
            session.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))
            == 0
        )
    assert session.get(Review, rid) is None
    assert session.get(Feedback, fid).user_id is None
    counts = b.get(f"/api/v1/fixtures/{fixture_id}/reviews").json()["data"]
    assert all(i["id"] != rid for i in counts["items"])
    assert next(i for i in counts["items"] if i["id"] == b_rid)["likes"] == 0
    assert a.get("/api/v1/auth/me").json()["data"] is None
    # The same address signs up again as a new account.
    again, _, _ = signup(new_client(app), sender, address=address)
    assert again.status_code == 201 and again.json()["data"]["id"] != str(user_id)


def test_resend_wait_holds_right_after_a_password_reset(env):
    """Codex 1차: a finished reset must not reopen an immediate second mail."""
    app, _, sender, _ = env
    client = new_client(app)
    _, address, _ = signup(client, sender)
    guest = new_client(app)
    token = code_token(guest, sender, address, purpose="password_reset")
    reset = guest.post(
        "/api/v1/auth/password-reset",
        json={"email": address, "verificationToken": token,
              "newPassword": "newpass99", "newPasswordConfirm": "newpass99"},
        headers=WEB,
    )
    assert reset.status_code == 200
    sent = len(sender.sent)
    again = guest.post("/api/v1/auth/email-codes",
                       json={"email": address, "purpose": "password_reset"}, headers=WEB)
    assert again.status_code == 429 and len(sender.sent) == sent
    # The spent token cannot be used twice.
    replay = guest.post(
        "/api/v1/auth/password-reset",
        json={"email": address, "verificationToken": token,
              "newPassword": "other999", "newPasswordConfirm": "other999"},
        headers=WEB,
    )
    assert replay.status_code == 422


def test_overlapping_password_changes_run_one_after_the_other():
    """Codex N2: two requests that read the account before either saved. The second must
    see the first's password and version (committed sessions, cleaned up afterwards)."""
    from app.api.errors import ApiError
    from app.db.session import get_sessionmaker
    from app.models.user import User
    from app.services import accounts
    from app.services.auth_security import hash_password, verify_password

    make = get_sessionmaker()
    with make() as session:
        user = User(email=email(), nickname=nickname(), password_hash=hash_password(PASSWORD),
                    login_method="email")
        session.add(user)
        session.commit()
        user_id = user.id
    first, second = make(), make()
    try:
        stale_a, stale_b = first.get(User, user_id), second.get(User, user_id)
        now = datetime.now(UTC)
        accounts.change_password(first, stale_a, PASSWORD, "newpass11", "newpass11", now)
        with pytest.raises(ApiError) as refused:
            accounts.change_password(second, stale_b, PASSWORD, "newpass22", "newpass22", now)
        assert refused.value.code == "PASSWORD_CURRENT_MISMATCH"
        second.rollback()
        accounts.change_password(second, stale_b, "newpass11", "newpass33", "newpass33", now)
        with make() as check:
            saved = check.get(User, user_id)
            assert saved.token_version == 2
            assert verify_password(saved.password_hash, "newpass33")
    finally:
        first.close()
        second.close()
        with make() as session:
            session.delete(session.get(User, user_id))
            session.commit()


def test_refresh_waits_for_a_password_change_and_does_not_revive_the_session():
    """Codex R1: change locks the account, then a refresh arrives. Same lock order (account,
    then token) — the refresh waits instead of deadlocking and is refused afterwards."""
    import threading

    from app.db.session import get_sessionmaker
    from app.models.user import User
    from app.services import accounts
    from app.services.auth_security import hash_password

    make = get_sessionmaker()
    now = datetime.now(UTC)
    with make() as session:
        user = User(email=email(), nickname=nickname(), password_hash=hash_password(PASSWORD),
                    login_method="email")
        session.add(user)
        session.flush()
        old = accounts.start_session(session, user, now)
        session.commit()
        user_id = user.id
    outcome: list[str] = []

    def refresh():
        with make() as db:
            try:
                accounts.refresh_session(db, old.refresh, now)
                outcome.append("refreshed")
            except accounts.RefreshRejected:
                outcome.append("rejected")
            except Exception as exc:  # noqa: BLE001
                outcome.append(type(exc).__name__)

    changer = make()
    try:
        stale = changer.get(User, user_id)
        locked = accounts._lock_user(changer, user_id)
        worker = threading.Thread(target=refresh)
        worker.start()
        worker.join(timeout=1.5)
        assert worker.is_alive(), "refresh must wait for the account lock"
        tokens = accounts.change_password(changer, locked or stale, PASSWORD, "newpass44",
                                          "newpass44", now)
        assert tokens.refresh
        worker.join(timeout=10)
        assert outcome == ["rejected"]
    finally:
        changer.close()
        with make() as session:
            session.delete(session.get(User, user_id))
            session.commit()


def _committed_member(make, password=PASSWORD):
    from app.models.user import User
    from app.services.auth_security import hash_password

    with make() as session:
        user = User(email=email(), nickname=nickname(), password_hash=hash_password(password),
                    login_method="email")
        session.add(user)
        session.commit()
        return user.id, user.email


def _drop_member(make, user_id):
    from app.models.user import User

    with make() as session:
        user = session.get(User, user_id)
        if user is not None:
            session.delete(user)
            session.commit()


@pytest.mark.parametrize("first", ["refresh", "logout"])
def test_logout_and_refresh_never_leave_the_browser_session_alive(monkeypatch, first):
    """R5: either execution order revokes the whole family, including a just-rotated token.

    Like the other concurrency tests, connections need a committed throwaway account;
    the finally block removes that account and every token it created.
    """
    import threading

    from app.db.session import get_sessionmaker
    from app.models.user import RefreshToken
    from app.services import accounts
    from app.services.auth_security import token_hash

    make = get_sessionmaker()
    user_id, address = _committed_member(make)
    held = threading.Event()
    release = threading.Event()
    first_worker = None
    second_worker = None
    outcomes = {}
    issued = []
    original_start = accounts.start_session
    original_lock = accounts._lock_user
    now = datetime.now(UTC)

    def pause():
        held.set()
        assert release.wait(timeout=10), "the test must release the first operation"

    def start(db, user, instant, family=None):
        if first == "refresh" and threading.current_thread() is first_worker:
            pause()  # Both the account and original token are locked here.
        return original_start(db, user, instant, family)

    def lock(db, owner):
        user = original_lock(db, owner)
        if first == "logout" and threading.current_thread() is first_worker:
            pause()
        return user

    def run(operation, token):
        try:
            with make() as db:
                if operation == "logout":
                    accounts.end_session(db, token, now)
                    outcomes[operation] = "ended"
                else:
                    _, fresh = accounts.refresh_session(db, token, now)
                    issued.append(fresh)
                    outcomes[operation] = "rotated"
        except accounts.RefreshRejected:
            outcomes[operation] = "rejected"
        except Exception as exc:  # noqa: BLE001 - report worker failures to the main test
            outcomes[operation] = type(exc).__name__

    try:
        with make() as db:
            _, old = accounts.login(db, address, PASSWORD, now)
            _, other_browser = accounts.login(db, address, PASSWORD, now)
            family = db.scalar(
                select(RefreshToken.family_id).where(
                    RefreshToken.token_hash == token_hash(old.refresh)
                )
            )
        monkeypatch.setattr(accounts, "start_session", start)
        monkeypatch.setattr(accounts, "_lock_user", lock)
        second = "logout" if first == "refresh" else "refresh"
        first_worker = threading.Thread(target=run, args=(first, old.refresh))
        second_worker = threading.Thread(target=run, args=(second, old.refresh))
        first_worker.start()
        assert held.wait(timeout=5), "the first operation must take its account lock"
        second_worker.start()
        second_worker.join(timeout=1.5)
        assert second_worker.is_alive(), "the second operation must wait for the account lock"
        release.set()
        first_worker.join(timeout=10)
        second_worker.join(timeout=10)
        assert not first_worker.is_alive() and not second_worker.is_alive()
        assert outcomes == {
            "logout": "ended",
            "refresh": "rotated" if first == "refresh" else "rejected",
        }
        with make() as db:
            live = db.scalar(
                select(func.count()).select_from(RefreshToken).where(
                    RefreshToken.family_id == family, RefreshToken.revoked_at.is_(None)
                )
            )
            assert live == 0
            for token in [old, *issued]:
                with pytest.raises(accounts.RefreshRejected):
                    accounts.refresh_session(db, token.refresh, now)
            # Signing out one browser must not terminate a different browser's family.
            _, renewed = accounts.refresh_session(db, other_browser.refresh, now)
            assert renewed is not None
    finally:
        release.set()
        for worker in (first_worker, second_worker):
            if worker is not None and worker.ident is not None:
                worker.join(timeout=15)
        _drop_member(make, user_id)


@pytest.mark.parametrize("change", ["change", "reset"])
def test_login_with_the_old_password_cannot_outlive_a_password_change(change):
    """Codex R4: a login that overlaps a change/reset never issues a session for the old
    password. The change holds the account lock; the login waits, then checks the new one."""
    import threading

    from app.api.errors import ApiError
    from app.db.session import get_sessionmaker
    from app.models.user import User
    from app.services import accounts
    from app.services.auth_security import hash_password

    make = get_sessionmaker()
    user_id, address = _committed_member(make)
    outcome: list[str] = []

    def login():
        with make() as db:
            try:
                accounts.login(db, address, PASSWORD, datetime.now(UTC))
                outcome.append("issued")
            except ApiError as exc:
                outcome.append(exc.code)

    changer = make()
    try:
        user = accounts._lock_user(changer, user_id)
        worker = threading.Thread(target=login)
        worker.start()
        worker.join(timeout=1.5)
        assert worker.is_alive(), "login must wait for the account lock"
        if change == "change":
            accounts.change_password(changer, user, PASSWORD, "newpass55", "newpass55",
                                     datetime.now(UTC))
        else:  # what reset_password does once the code is confirmed
            user.password_hash = hash_password("newpass55")
            user.token_version += 1
            changer.commit()
        worker.join(timeout=10)
        assert outcome == ["INVALID_CREDENTIALS"]
        with make() as check:
            assert check.get(User, user_id).token_version == 1
    finally:
        changer.close()
        _drop_member(make, user_id)


def test_withdrawal_waits_for_a_reset_instead_of_deadlocking():
    """Codex 3차 참고: reset locks the account then updates the code row; withdrawal now
    takes the same order (account, then code rows)."""
    import threading

    from sqlalchemy import update

    from app.db.session import get_sessionmaker
    from app.models.user import EmailVerification, User
    from app.services import accounts

    make = get_sessionmaker()
    user_id, address = _committed_member(make)
    now = datetime.now(UTC)
    with make() as session:
        session.add(EmailVerification(email=address, purpose="password_reset", code_hash="x",
                                      expires_at=now, last_sent_at=now))
        session.commit()
    outcome: list[str] = []

    def withdraw():
        with make() as db:
            try:
                accounts.delete_account(db, db.get(User, user_id))
                outcome.append("deleted")
            except Exception as exc:  # noqa: BLE001
                outcome.append(type(exc).__name__)

    resetter = make()
    try:
        accounts._lock_user(resetter, user_id)
        worker = threading.Thread(target=withdraw)
        worker.start()
        worker.join(timeout=1.5)
        assert worker.is_alive(), "withdrawal must wait for the account lock"
        resetter.execute(
            update(EmailVerification)
            .where(EmailVerification.email == address)
            .values(token_hash=None)
        )
        resetter.commit()
        worker.join(timeout=10)
        assert outcome == ["deleted"]
    finally:
        resetter.close()
        _drop_member(make, user_id)


def test_review_restriction_blocks_writing_until_lifted(env):
    """Terms 제9조: a restricted member cannot write or edit reviews, can still delete their
    own, and sees the end moment on /auth/me; lifting restores writing."""
    from app.services import moderation

    app, session, sender, _ = env
    fixture_id = open_fixture(session)
    client = new_client(app)
    _, address, _ = signup(client, sender)
    written = client.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "제한 전 평가"},
                          headers=WEB)
    review_id = written.json()["data"]["id"]

    with pytest.raises(moderation.ModerationError):
        moderation.restrict_reviews(session, address, 3, datetime.now(UTC))
    until = moderation.restrict_reviews(session, address, 7, datetime.now(UTC))
    me = client.get("/api/v1/auth/me").json()["data"]
    assert me["reviewRestrictedUntil"] is not None
    assert abs(datetime.fromisoformat(me["reviewRestrictedUntil"]) - until) < timedelta(seconds=1)
    edit = client.patch(f"/api/v1/reviews/{review_id}", json={"body": "제한 중 수정"}, headers=WEB)
    assert edit.status_code == 403 and edit.json()["error"]["code"] == "REVIEW_RESTRICTED"
    assert client.delete(f"/api/v1/reviews/{review_id}", headers=WEB).status_code == 204
    new = client.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "제한 중 작성"},
                      headers=WEB)
    assert new.status_code == 403 and new.json()["error"]["code"] == "REVIEW_RESTRICTED"

    moderation.lift_restriction(session, address)
    assert client.get("/api/v1/auth/me").json()["data"]["reviewRestrictedUntil"] is None
    again = client.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "해제 후 작성"},
                        headers=WEB)
    assert again.status_code == 201


def test_operator_removes_a_review_and_closes_an_account(env):
    from app.models.review import Review
    from app.models.user import User
    from app.services import moderation

    app, session, sender, _ = env
    fixture_id = open_fixture(session)
    client = new_client(app)
    _, address, _ = signup(client, sender)
    review_id = client.post(f"/api/v1/fixtures/{fixture_id}/reviews", json={"body": "광고 글"},
                            headers=WEB).json()["data"]["id"]
    removed = moderation.remove_review(session, review_id)
    assert removed.author_email == address and session.get(Review, review_id) is None
    with pytest.raises(moderation.ModerationError):
        moderation.remove_review(session, review_id)
    moderation.close_account(session, address)
    session.expire_all()
    assert session.scalar(select(User).where(User.email == address)) is None
    assert client.get("/api/v1/auth/me").json()["data"] is None
