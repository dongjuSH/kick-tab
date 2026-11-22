"""Member accounts: verification codes, signup, sessions, password reset/change and
withdrawal (AUTH-001~004, MY-004, P-03·P-04·P-12, guide §6.2).

Every check that the screen also makes (rules, three confirmations, verified email) is made
again here, so a request that skips the screen creates nothing.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import settings
from app.core.locks import advisory_key
from app.models.user import (
    AGREEMENT_ITEMS,
    EmailVerification,
    RefreshToken,
    TermsAgreement,
    User,
)
from app.services import auth_security as sec
from app.services.mailer import EmailSender, EmailSendError

CODE_TTL = timedelta(minutes=10)
RESEND_WAIT = timedelta(minutes=1)
MAX_CODE_FAILURES = 5
VERIFICATION_TOKEN_TTL = timedelta(minutes=30)
# Two tabs refreshing with the same cookie at once: the later one finds the token just
# rotated. Within this window it is answered without new cookies (the browser already holds
# the new ones) instead of being treated as a stolen token.
ROTATION_GRACE = timedelta(seconds=10)

VERIFY_FIRST = "이메일 인증을 먼저 완료해 주세요."


def _lock(db: Session, name: str) -> None:
    db.execute(select(func.pg_advisory_xact_lock(advisory_key(f"kicktab-auth:{name}"))))


def _validation(fields: dict[str, str], message: str = "입력값을 확인해 주세요.") -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", message, details={"fields": fields})


def _require_email(raw: str) -> str:
    if error := sec.email_error(raw):
        raise _validation({"email": error})
    return sec.normalize_email(raw)


def _user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


# --- verification codes ---------------------------------------------------------------


def request_code(
    db: Session, raw_email: str, purpose: str, sender: EmailSender, now: datetime
) -> datetime:
    """Send a new 6-digit code (AUTH-001 rule 1). A resend replaces the previous code and
    is allowed one minute after the last send. Returns the code's expiry."""
    email = _require_email(raw_email)
    _lock(db, f"code:{purpose}:{email}")
    user = _user_by_email(db, email)
    if purpose == "signup" and user is not None:
        db.rollback()
        raise ApiError(
            409,
            "EMAIL_TAKEN",
            "이미 가입된 이메일입니다. 로그인하거나 비밀번호 찾기를 이용해 주세요.",
            details={"fields": {"email": "이미 가입된 이메일입니다."}},
        )
    if purpose == "password_reset" and (user is None or user.login_method != "email"):
        db.rollback()
        raise ApiError(
            404,
            "NOT_FOUND",
            "이메일로 가입한 계정을 찾을 수 없습니다. 이메일 주소를 확인해 주세요.",
            details={"fields": {"email": "가입된 이메일 계정이 없습니다."}},
        )
    # Row lock: the daily clean-up may delete a 30-day-old row at the same moment; waiting
    # here means the send either updates the row first (the clean-up then keeps it) or finds
    # it gone and creates a new one (Codex N3).
    row = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.email == email, EmailVerification.purpose == purpose)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is not None and now < row.last_sent_at + RESEND_WAIT:
        wait = int((row.last_sent_at + RESEND_WAIT - now).total_seconds()) + 1
        db.rollback()
        raise ApiError(
            429,
            "RATE_LIMITED",
            "인증번호는 1분 뒤에 다시 받을 수 있습니다.",
            details={"retryAfter": wait},
            headers={"Retry-After": str(wait)},
        )
    code = sec.new_code()
    if row is None:
        row = EmailVerification(email=email, purpose=purpose)
        db.add(row)
    row.code_hash = sec.code_hash(email, purpose, code)
    row.expires_at = now + CODE_TTL
    row.failed_attempts = 0
    row.last_sent_at = now
    row.verified_at = None
    row.token_hash = None
    row.token_expires_at = None
    db.flush()
    try:
        sender.send_code(email, purpose, code)
    except EmailSendError:
        # Nothing changes: the previous code (if any) stays as it was.
        db.rollback()
        raise ApiError(
            503,
            "UPSTREAM_UNAVAILABLE",
            "인증 메일을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from None
    db.commit()
    return row.expires_at


def verify_code(
    db: Session, raw_email: str, purpose: str, code: str, now: datetime
) -> tuple[str, datetime]:
    """Check a code. Returns a one-time verification token (30 minutes) for signup or
    password reset. Five wrong codes make the code unusable (a new one must be sent)."""
    email = _require_email(raw_email)
    if not (len(code) == 6 and code.isascii() and code.isdigit()):
        raise _validation({"code": "인증번호 6자리 숫자를 입력해 주세요."})
    _lock(db, f"code:{purpose}:{email}")
    row = db.scalar(
        select(EmailVerification).where(
            EmailVerification.email == email, EmailVerification.purpose == purpose
        )
    )
    if row is None or row.verified_at is not None:
        db.rollback()
        raise ApiError(
            422,
            "VERIFICATION_INVALID",
            "인증번호를 다시 받아 주세요.",
            details={"fields": {"code": "유효한 인증번호가 없습니다."}},
        )
    if row.failed_attempts >= MAX_CODE_FAILURES:
        db.rollback()
        raise _locked()
    if now >= row.expires_at:
        db.rollback()
        raise ApiError(
            410,
            "VERIFICATION_EXPIRED",
            "인증번호가 만료되었습니다. 인증번호를 다시 받아 주세요.",
            details={"fields": {"code": "만료된 인증번호입니다."}},
        )
    if not sec.codes_match(row.code_hash, email, purpose, code):
        row.failed_attempts += 1
        db.commit()
        if row.failed_attempts >= MAX_CODE_FAILURES:
            raise _locked()
        remaining = MAX_CODE_FAILURES - row.failed_attempts
        raise ApiError(
            422,
            "VERIFICATION_INVALID",
            f"인증번호가 일치하지 않습니다. {remaining}회 더 입력할 수 있습니다.",
            details={
                "fields": {"code": "인증번호가 일치하지 않습니다."},
                "remainingAttempts": remaining,
            },
        )
    token = sec.new_token()
    row.verified_at = now
    row.token_hash = sec.token_hash(token)
    row.token_expires_at = now + VERIFICATION_TOKEN_TTL
    db.commit()
    return token, row.token_expires_at


def _locked() -> ApiError:
    return ApiError(
        422,
        "VERIFICATION_LOCKED",
        "인증번호를 5회 잘못 입력해 더 이상 사용할 수 없습니다. 인증번호를 다시 받아 주세요.",
        details={"fields": {"code": "사용할 수 없는 인증번호입니다."}},
    )


def _spend(verification: EmailVerification) -> None:
    """The confirmed code and its token can never be used again. The row (address, purpose,
    last send time) stays, so the 1-minute resend wait also holds right after a signup or a
    reset; withdrawal deletes it."""
    verification.token_hash = None
    verification.token_expires_at = None


def _lock_user(db: Session, user_id: uuid.UUID) -> User | None:
    """The account row, locked until the transaction ends and re-read from the database."""
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _consume_token(
    db: Session, email: str, purpose: str, token: str, now: datetime
) -> EmailVerification:
    row = db.scalar(
        select(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
            EmailVerification.token_hash == sec.token_hash(token),
        )
    )
    if row is None or row.token_expires_at is None or now >= row.token_expires_at:
        db.rollback()
        raise ApiError(
            422,
            "VERIFICATION_INVALID",
            "이메일 인증이 만료되었습니다. 인증번호를 다시 받아 주세요.",
            details={"fields": {"email": VERIFY_FIRST}},
        )
    return row


# --- sessions -------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionTokens:
    access: str
    refresh: str


def start_session(
    db: Session, user: User, now: datetime, family: uuid.UUID | None = None
) -> SessionTokens:
    """Issue an access token and a new refresh token (added to the session, not committed)."""
    refresh = sec.new_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=sec.token_hash(refresh),
            family_id=family or uuid.uuid4(),
            expires_at=now + sec.REFRESH_TOKEN_TTL,
        )
    )
    return SessionTokens(
        access=sec.encode_access_token(user.id, user.token_version, now), refresh=refresh
    )


def _revoke_all(db: Session, user_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


class RefreshRejected(Exception):
    """No usable refresh token: the client becomes a guest."""


def refresh_session(db: Session, token: str, now: datetime) -> tuple[User, SessionTokens | None]:
    """Rotate a refresh token. A rotated token presented again outside the grace window is
    treated as stolen: the whole family is revoked. `None` tokens = concurrent rotation,
    keep the cookies the browser already received.

    Lock order is the account row first, then the token row — the same order as a password
    change or reset (`_lock_user`, then revoking the tokens), so the two never deadlock
    (Codex R1). A refresh that waited for a password change then finds its token revoked
    and is refused: the old session is not revived."""
    found = db.execute(
        select(RefreshToken.id, RefreshToken.user_id).where(
            RefreshToken.token_hash == sec.token_hash(token)
        )
    ).first()
    if not found:
        db.rollback()
        raise RefreshRejected
    token_id, user_id = found
    user = _lock_user(db, user_id)
    row = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.id == token_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or row is None:
        db.rollback()
        raise RefreshRejected
    if row.revoked_at is not None:
        live = db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.family_id == row.family_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        if live and now - row.revoked_at <= ROTATION_GRACE:
            db.rollback()
            return user, None
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise RefreshRejected
    if now >= row.expires_at:
        db.rollback()
        raise RefreshRejected
    row.revoked_at = now
    tokens = start_session(db, user, now, family=row.family_id)
    db.commit()
    return user, tokens


def end_session(db: Session, token: str | None, now: datetime) -> None:
    """Logout: revoke this browser's whole token family under the account lock.

    A refresh must finish before the revocation UPDATE starts, so the UPDATE sees and
    revokes its new token too. Keep the same account -> token lock order as refresh.
    """
    if token:
        found = db.execute(
            select(RefreshToken.user_id, RefreshToken.family_id).where(
                RefreshToken.token_hash == sec.token_hash(token)
            )
        ).first()
        if found is not None and _lock_user(db, found.user_id) is not None:
            db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == found.user_id,
                    RefreshToken.family_id == found.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
    db.commit()


def login(db: Session, raw_email: str, password: str, now: datetime) -> tuple[User, SessionTokens]:
    """The account row is locked and re-read before the password check, and stays locked
    until the session is issued: a password change or reset that lands in between either
    waits for this login or makes it check the new password — a session is never issued
    for an old password (Codex R4)."""
    email = sec.normalize_email(raw_email)
    found = _user_by_email(db, email) if not sec.email_error(raw_email) else None
    user = _lock_user(db, found.id) if found is not None else None
    hashed = user.password_hash if user is not None else None
    if not sec.verify_password_or_dummy(hashed, password):
        db.rollback()
        raise ApiError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")
    assert user is not None
    tokens = start_session(db, user, now)
    db.commit()
    return user, tokens


# --- signup / password ----------------------------------------------------------------


@dataclass(frozen=True)
class SignupInput:
    email: str
    verification_token: str
    nickname: str
    password: str
    password_confirm: str
    # None = missing from the request; only True counts (P-12).
    terms_of_service: bool | None
    privacy_collection: bool | None
    age_14_or_older: bool | None


AGREEMENT_MESSAGES = {
    "terms_of_service": "서비스 이용약관 동의를 확인해 주세요.",
    "privacy_collection": "개인정보 수집·이용 동의를 확인해 주세요.",
    "age_14_or_older": "만 14세 이상인지 확인해 주세요.",
}
AGREEMENT_FIELDS = {
    "terms_of_service": "agreements.termsOfService",
    "privacy_collection": "agreements.privacyCollection",
    "age_14_or_older": "agreements.age14OrOlder",
}


def _password_fields(password: str, confirm: str, field: str, confirm_field: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if error := sec.password_error(password):
        fields[field] = error
    elif password != confirm:
        fields[confirm_field] = sec.CONFIRM_RULE
    return fields


def signup(db: Session, data: SignupInput, now: datetime) -> tuple[User, SessionTokens]:
    """AUTH-001: one verified, valid, fully confirmed request creates one account and a
    session. Anything missing creates nothing."""
    email = _require_email(data.email)
    fields: dict[str, str] = {}
    if error := sec.nickname_error(data.nickname):
        fields["nickname"] = error
    fields |= _password_fields(data.password, data.password_confirm, "password", "passwordConfirm")
    agreements = {
        "terms_of_service": data.terms_of_service,
        "privacy_collection": data.privacy_collection,
        "age_14_or_older": data.age_14_or_older,
    }
    for item, value in agreements.items():
        if value is not True:
            fields[AGREEMENT_FIELDS[item]] = AGREEMENT_MESSAGES[item]
    if fields:
        raise _validation(fields)

    _lock(db, f"signup:{email}")
    verification = _consume_token(db, email, "signup", data.verification_token, now)
    if _user_by_email(db, email) is not None:
        db.rollback()
        raise ApiError(
            409,
            "EMAIL_TAKEN",
            "이미 가입된 이메일입니다.",
            details={"fields": {"email": "이미 가입된 이메일입니다."}},
        )
    if _nickname_taken(db, data.nickname):
        db.rollback()
        raise _nickname_conflict()
    user = User(
        email=email,
        nickname=data.nickname,
        password_hash=sec.hash_password(data.password),
        login_method="email",
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _nickname_conflict() from None
    for item in AGREEMENT_ITEMS:
        db.add(
            TermsAgreement(
                user_id=user.id,
                item_id=item,
                item_version=settings.terms_version,
                confirmed=True,
                agreed_at=now,
            )
        )
    _spend(verification)
    tokens = start_session(db, user, now)
    db.commit()
    return user, tokens


def _nickname_taken(db: Session, nickname: str) -> bool:
    return (
        db.scalar(select(User.id).where(func.lower(User.nickname) == nickname.lower())) is not None
    )


def _nickname_conflict() -> ApiError:
    return ApiError(
        409,
        "NICKNAME_TAKEN",
        "이미 사용 중인 닉네임입니다.",
        details={"fields": {"nickname": "이미 사용 중인 닉네임입니다."}},
    )


def reset_password(
    db: Session, raw_email: str, token: str, password: str, confirm: str, now: datetime
) -> None:
    """Forgot password (AUTH-001 rule 4): verified email → new password. Every session of
    the account ends; the member signs in again with the new password."""
    email = _require_email(raw_email)
    if fields := _password_fields(password, confirm, "newPassword", "newPasswordConfirm"):
        raise _validation(fields)
    _lock(db, f"code:password_reset:{email}")
    verification = _consume_token(db, email, "password_reset", token, now)
    found = _user_by_email(db, email)
    user = _lock_user(db, found.id) if found is not None else None
    if user is None or user.login_method != "email":
        db.rollback()
        raise ApiError(404, "NOT_FOUND", "이메일로 가입한 계정을 찾을 수 없습니다.")
    user.password_hash = sec.hash_password(password)
    user.token_version += 1
    _revoke_all(db, user.id, now)
    _spend(verification)
    db.commit()


# MY-004 password change: one error code per field state (09 dialog states 1:1).
PASSWORD_ERRORS = {
    "PASSWORD_RULE": ("newPassword", sec.PASSWORD_RULE),
    "PASSWORD_CONFIRM_MISMATCH": ("newPasswordConfirm", sec.CONFIRM_RULE),
    "PASSWORD_CURRENT_MISMATCH": ("currentPassword", "현재 비밀번호가 일치하지 않습니다."),
}


def _password_error(code: str) -> ApiError:
    field, message = PASSWORD_ERRORS[code]
    return ApiError(422, code, message, details={"fields": {field: message}})


def change_password(
    db: Session, user: User, current: str, new: str, confirm: str, now: datetime
) -> SessionTokens:
    """Email accounts only. Other sessions end; this browser gets a fresh session.

    The account row is locked and read again first, so two overlapping changes run one after
    the other: the second sees the first's password and version (no stale password accepted,
    no version bump lost)."""
    user = _lock_user(db, user.id) or user
    if user.login_method != "email":
        raise ApiError(403, "FORBIDDEN", "이메일로 가입한 계정만 비밀번호를 변경할 수 있습니다.")
    if sec.password_error(new):
        raise _password_error("PASSWORD_RULE")
    if new != confirm:
        raise _password_error("PASSWORD_CONFIRM_MISMATCH")
    if not sec.verify_password(user.password_hash, current):
        raise _password_error("PASSWORD_CURRENT_MISMATCH")
    user.password_hash = sec.hash_password(new)
    user.token_version += 1
    _revoke_all(db, user.id, now)
    tokens = start_session(db, user, now)
    db.commit()
    return tokens


def delete_account(db: Session, user: User) -> None:
    """P-03 withdrawal: the account and (by cascade) its favourite teams, reviews, reactions,
    agreements, refresh tokens and identities are deleted; feedback only loses the link.
    Pending codes for the address go too, so the same email can sign up as a new account.

    Lock order is the account row first, then the code rows — the same as a password reset
    (Codex 3차 참고), so the two never wait on each other in a cycle."""
    user = _lock_user(db, user.id) or user
    db.execute(delete(EmailVerification).where(EmailVerification.email == user.email))
    db.delete(user)
    db.commit()


def utcnow() -> datetime:
    return datetime.now(UTC)
