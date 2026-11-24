"""Chat 02 rules that need no database: input rules (P-04), tokens, codes, mail, CSRF."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.routes.auth import login_limit
from app.config import settings
from app.main import app
from app.services import auth_security as sec
from app.services import mailer


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "auth_jwt_secret", SecretStr("test-secret-" + "x" * 64))


@pytest.mark.parametrize(
    ("nickname", "ok"),
    [
        ("축구팬", True),
        ("Kick1", True),
        ("가나다라마바사아자차카타", True),  # 12
        ("가", False),  # 1
        ("가나다라마바사아자차카타파", False),  # 13
        ("ㄱㄴ", False),  # incomplete Hangul
        ("kick tab", False),
        ("kick_tab", False),
        ("킥탭!", False),
        ("Kick1" + chr(10), False),  # Codex N5: `$` alone accepts a trailing line break
    ],
)
def test_nickname_rule(nickname, ok):
    assert (sec.nickname_error(nickname) is None) is ok


@pytest.mark.parametrize(
    ("nickname", "blocked"),
    [
        ("관리자", True),
        ("킥탭운영자", True),
        ("Admin", True),
        ("admin7", True),
        ("KickTab공식", True),
        ("씨발", True),
        ("씨8발", True),  # digits do not hide a word
        ("병신123", True),
        ("개새끼", True),
        ("FuckYou", True),
        # No exceptions (user decision 2026-11-24): the message explains why these fail.
        ("badminton", True),
        ("시발점", True),
        ("축구팬", False),
        ("토트넘팬7", False),
        ("Sonny", False),
    ],
)
def test_blocked_nicknames(nickname, blocked):
    """User decision 2026-11-24: impersonation words and direct profanity, contained."""
    assert (sec.nickname_error(nickname) == sec.NICKNAME_BLOCKED) is blocked


def test_blocked_nickname_message_says_why():
    """The field error names the reason (user decision 2026-11-24)."""
    assert sec.NICKNAME_BLOCKED == (
        "운영자 사칭이나 비속어로 볼 수 있는 단어가 포함되어 사용할 수 없는 닉네임입니다."
    )


def test_signup_screen_blocks_the_same_words():
    """The signup screen checks the same list before sending (frontend rules.ts)."""
    rules = (Path(__file__).resolve().parents[2] / "frontend/src/features/auth/rules.ts").read_text(
        encoding="utf-8"
    )
    listed = re.search(r"BLOCKED_NICKNAME_WORDS = \[(.*?)\]", rules, re.S)
    assert listed is not None
    assert tuple(re.findall(r'"([^"]+)"', listed.group(1))) == sec.BLOCKED_NICKNAME_WORDS


@pytest.mark.parametrize(
    ("password", "ok"),
    [
        ("abcd1234", True),
        ("a1" * 32, True),  # 64
        ("abc123", False),  # 6
        ("a1" * 32 + "x", False),  # 65
        ("abcdefgh", False),  # no digit
        ("12345678", False),  # no letter
        ("비밀번호12345", False),  # no Latin letter
    ],
)
def test_password_rule(password, ok):
    assert (sec.password_error(password) is None) is ok


def test_email_rule_and_normalisation():
    assert sec.email_error(" You@Example.com ") is None
    assert sec.normalize_email(" You@Example.com ") == "you@example.com"
    for bad in ["", "you", "you@", "you@example", "a b@example.com"]:
        assert sec.email_error(bad) is not None


def test_password_hash_is_argon2id_and_verifies():
    hashed = sec.hash_password("abcd1234")
    assert hashed.startswith("$argon2id$")
    assert "abcd1234" not in hashed
    assert sec.verify_password(hashed, "abcd1234")
    assert not sec.verify_password(hashed, "abcd12345")
    assert not sec.verify_password(None, "abcd1234")
    assert not sec.verify_password_or_dummy(None, "abcd1234")


def test_access_token_expires_after_15_minutes():
    user_id = uuid.uuid4()
    issued = datetime.now(UTC)
    claims = sec.decode_access_token(sec.encode_access_token(user_id, 3, issued))
    assert claims.user_id == user_id and claims.version == 3
    old = sec.encode_access_token(user_id, 0, issued - timedelta(minutes=16))
    with pytest.raises(sec.AccessTokenExpired):
        sec.decode_access_token(old)
    with pytest.raises(sec.AccessTokenInvalid):
        sec.decode_access_token(old[:-2] + "xx")


def test_tokens_and_codes_are_stored_as_hashes():
    token = sec.new_token()
    assert len(token) >= 43 and sec.token_hash(token) != token
    code = sec.new_code()
    assert len(code) == 6 and code.isdigit()
    stored = sec.code_hash("a@b.co", "signup", code)
    assert code not in stored
    assert sec.codes_match(stored, "a@b.co", "signup", code)
    # The same code for the other purpose or address does not match.
    assert not sec.codes_match(stored, "a@b.co", "password_reset", code)
    assert not sec.codes_match(stored, "c@b.co", "signup", code)


def test_smtp_password_spaces_are_removed(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_username", "sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", SecretStr("abcd efgh ijkl mnop"))
    monkeypatch.setattr(settings, "email_from", "")
    sender = mailer.get_email_sender()
    assert isinstance(sender, mailer.SmtpSender)
    assert sender.password == "abcdefghijklmnop"
    assert sender.port == 587 and sender.sender == "sender@example.com"


def test_without_smtp_nothing_is_sent_or_logged(monkeypatch, caplog):
    """No console sender in any environment (Codex N6): the request fails instead."""
    monkeypatch.setattr(settings, "smtp_host", "")
    sender = mailer.get_email_sender()
    with pytest.raises(mailer.EmailSendError):
        sender.send_code("to@example.com", "signup", "123456")
    assert "123456" not in caplog.text


def test_code_mail_says_code_and_validity():
    message = mailer.code_message("from@example.com", "to@example.com", "signup", "123456")
    assert message["Subject"] == "[KickTab] 회원가입 인증번호"
    body = message.get_content()
    assert "123456" in body and "10분" in body


def test_cookies_are_secure_outside_local(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "local")
    assert settings.secure_cookies is False
    monkeypatch.setattr(settings, "app_env", "production")
    assert settings.secure_cookies is True


@pytest.fixture
def client():
    login_limit.reset()
    # Not used as a context manager: the lifespan (scheduler) must not start in tests.
    yield TestClient(app)
    login_limit.reset()


def test_auth_changes_require_csrf_header_and_allowed_origin(client):
    body = {"email": "a@b.co", "password": "abcd1234"}
    missing = client.post("/api/v1/auth/login", json=body)
    assert missing.status_code == 403 and missing.json()["error"]["details"]["reason"] == "csrf"
    foreign = client.post(
        "/api/v1/auth/login",
        json=body,
        headers={"X-KickTab-Client": "web", "Origin": "https://evil.example"},
    )
    assert foreign.status_code == 403
    assert foreign.json()["error"]["details"]["reason"] == "origin"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/me/favorites"),
        ("post", "/api/v1/me/favorites"),
        ("delete", "/api/v1/me/favorites/50"),
        ("get", "/api/v1/me/reviews"),
        ("patch", "/api/v1/me/password"),
        ("delete", "/api/v1/me"),
        ("post", "/api/v1/fixtures/1/reviews"),
        ("patch", "/api/v1/reviews/1"),
        ("delete", "/api/v1/reviews/1"),
        ("put", "/api/v1/reviews/1/reaction"),
    ],
)
def test_member_routes_refuse_guests(client, method, path):
    kwargs = {"headers": {"X-KickTab-Client": "web"}}
    if method in ("post", "patch", "put"):
        kwargs["json"] = {
            "teamId": 50,
            "body": "좋은 경기",
            "value": 1,
            "currentPassword": "a",
            "newPassword": "b",
            "newPasswordConfirm": "b",
        }
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_session_check_answers_guests_without_an_error(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200 and response.json()["data"] is None


def test_expired_access_cookie_asks_for_refresh(client):
    old = sec.encode_access_token(uuid.uuid4(), 0, datetime.now(UTC) - timedelta(hours=1))
    client.cookies.set("kt_access", old)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401 and response.json()["error"]["code"] == "AUTH_EXPIRED"


def test_refresh_without_cookie_clears_cookies(client):
    response = client.post("/api/v1/auth/refresh", headers={"X-KickTab-Client": "web"})
    assert response.status_code == 401
    cookies = response.headers.get_list("set-cookie")
    assert any(c.startswith("kt_access=") for c in cookies)
    assert any(c.startswith("kt_refresh=") and "Path=/api/v1/auth" in c for c in cookies)


def test_feedback_service_ceiling_is_shared_by_members_and_guests():
    """Codex N3: guests and members count against one 20-per-minute service counter."""
    from starlette.requests import Request

    from app.api.routes import feedback as routes

    routes.feedback_rate_limit.reset()
    routes.feedback_member_limit.reset()

    def request(ip: str, cookie: str = "") -> Request:
        headers = [(b"cookie", cookie.encode())] if cookie else []
        return Request({"type": "http", "method": "POST", "path": "/", "headers": headers,
                        "client": (ip, 1)})

    allowed = 0
    for i in range(10):
        routes.feedback_rate_limit(request(f"10.0.0.{i}"))
        allowed += 1
    for _ in range(10):
        token = sec.encode_access_token(uuid.uuid4(), 0)
        routes.feedback_member_limit(request("10.0.1.1", f"kt_access={token}"))
        allowed += 1
    from app.api.errors import ApiError

    with pytest.raises(ApiError) as refused:
        routes.feedback_member_limit(
            request("10.0.1.2", f"kt_access={sec.encode_access_token(uuid.uuid4(), 0)}")
        )
    assert allowed == 20 and refused.value.status_code == 429
    with pytest.raises(ApiError):
        routes.feedback_rate_limit(request("10.0.2.1"))
    routes.feedback_rate_limit.reset()
    routes.feedback_member_limit.reset()


def test_member_and_guest_feedback_limits_share_one_lock():
    """Codex R2: the shared counter is checked and recorded under one lock for both."""
    from app.api.routes import feedback as routes

    assert routes.feedback_rate_limit._lock is routes.feedback_member_limit._lock
    assert routes.feedback_rate_limit.global_limiter is routes.feedback_member_limit.global_limiter


def test_close_account_command_needs_confirm(capsys):
    from app.moderation import main

    assert main(["close-account", "someone@example.com"]) == 2
    assert "--confirm" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["restrict", "someone@example.com", "--days", "3"])
