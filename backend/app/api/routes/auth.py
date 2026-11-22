"""Auth APIs (chat 02, AUTH-001~004, guide §6.2): email codes, signup, login, refresh,
logout, password reset and the current member."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import (
    REFRESH_COOKIE,
    MaybeMember,
    clear_session_cookies,
    member_schema,
    set_session_cookies,
)
from app.api.deps import RateLimit
from app.api.errors import ApiError, error_response
from app.core.rate_limit import Limit, RateLimiter, retry_after_header
from app.db.session import get_db
from app.schemas.auth import (
    EmailCodeRequest,
    EmailCodeSent,
    EmailCodeVerified,
    EmailCodeVerify,
    LoginRequest,
    MemberResponse,
    PasswordResetRequest,
    SessionResponse,
    SignupRequest,
)
from app.schemas.common import DataResponse
from app.services import accounts
from app.services import auth_security as sec
from app.services.accounts import RESEND_WAIT, RefreshRejected, SignupInput, utcnow
from app.services.mailer import EmailSender, get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])
Db = Annotated[Session, Depends(get_db)]
Sender = Annotated[EmailSender, Depends(get_email_sender)]

# Sending mail costs Gmail quota (about 500/day): per client IP and service-wide limits,
# plus a per-address limit below. The 1-minute resend wait is stored per address.
code_send_limit = RateLimit(
    "auth-code-send",
    [Limit(5, 10 * 60), Limit(20, 24 * 60 * 60)],
    global_limits=[Limit(60, 60 * 60), Limit(400, 24 * 60 * 60)],
)
code_email_limiter = RateLimiter([Limit(10, 24 * 60 * 60)])
code_verify_limit = RateLimit("auth-code-verify", [Limit(30, 10 * 60)])
login_limit = RateLimit("auth-login", [Limit(20, 10 * 60)], global_limits=[Limit(600, 10 * 60)])
login_email_limiter = RateLimiter([Limit(10, 10 * 60)])
account_limit = RateLimit("auth-account", [Limit(10, 10 * 60)])

TOO_MANY = "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."


def _hit(limiter: RateLimiter, key: str) -> None:
    wait = limiter.hit(key)
    if wait is not None:
        raise ApiError(
            429, "RATE_LIMITED", TOO_MANY, headers={"Retry-After": retry_after_header(wait)}
        )


@router.post("/email-codes", dependencies=[Depends(code_send_limit)])
def send_email_code(
    payload: EmailCodeRequest, db: Db, sender: Sender
) -> DataResponse[EmailCodeSent]:
    """AUTH-001: send a 6-digit code (10 minutes; resend after 1 minute replaces it)."""
    if not sec.email_error(payload.email):
        _hit(code_email_limiter, f"{payload.purpose}:{sec.normalize_email(payload.email)}")
    now = utcnow()
    expires_at = accounts.request_code(db, payload.email, payload.purpose, sender, now)
    return DataResponse(data=EmailCodeSent(expires_at=expires_at, resend_at=now + RESEND_WAIT))


@router.post("/email-codes/verify", dependencies=[Depends(code_verify_limit)])
def verify_email_code(payload: EmailCodeVerify, db: Db) -> DataResponse[EmailCodeVerified]:
    token, expires_at = accounts.verify_code(
        db, payload.email, payload.purpose, payload.code.strip(), utcnow()
    )
    return DataResponse(data=EmailCodeVerified(verification_token=token, expires_at=expires_at))


@router.post("/signup", status_code=status.HTTP_201_CREATED, dependencies=[Depends(account_limit)])
def signup(payload: SignupRequest, db: Db, response: Response) -> MemberResponse:
    """Account + session in one step. The screen still confirms GET /auth/me before
    showing the member state (account created ≠ session established)."""
    agreements = payload.agreements
    user, tokens = accounts.signup(
        db,
        SignupInput(
            email=payload.email,
            verification_token=payload.verification_token,
            nickname=payload.nickname,
            password=payload.password,
            password_confirm=payload.password_confirm,
            terms_of_service=agreements.terms_of_service,
            privacy_collection=agreements.privacy_collection,
            age_14_or_older=agreements.age_14_or_older,
        ),
        utcnow(),
    )
    set_session_cookies(response, tokens)
    return MemberResponse(data=member_schema(user))


@router.post("/login", dependencies=[Depends(login_limit)])
def login(payload: LoginRequest, db: Db, response: Response) -> MemberResponse:
    _hit(login_email_limiter, sec.normalize_email(payload.email))
    user, tokens = accounts.login(db, payload.email, payload.password, utcnow())
    set_session_cookies(response, tokens)
    return MemberResponse(data=member_schema(user))


@router.post("/refresh", response_model=MemberResponse)
def refresh(request: Request, db: Db, response: Response) -> MemberResponse | JSONResponse:
    """Rotate the refresh token and issue a new access token. Failure clears both cookies,
    so the client continues as a guest (AUTH-003)."""
    token = request.cookies.get(REFRESH_COOKIE)
    try:
        if not token:
            raise RefreshRejected
        user, tokens = accounts.refresh_session(db, token, utcnow())
    except RefreshRejected:
        rejected = error_response(
            401, "AUTH_REQUIRED", "로그인 세션이 만료되었습니다. 다시 로그인해 주세요."
        )
        clear_session_cookies(rejected)
        return rejected
    if tokens is not None:
        set_session_cookies(response, tokens)
    return MemberResponse(data=member_schema(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Db, response: Response) -> None:
    accounts.end_session(db, request.cookies.get(REFRESH_COOKIE), utcnow())
    clear_session_cookies(response)


@router.post("/password-reset", dependencies=[Depends(account_limit)])
def password_reset(payload: PasswordResetRequest, db: Db) -> DataResponse[dict[str, bool]]:
    accounts.reset_password(
        db,
        payload.email,
        payload.verification_token,
        payload.new_password,
        payload.new_password_confirm,
        utcnow(),
    )
    return DataResponse(data={"reset": True})


@router.get("/me")
def read_me(user: MaybeMember) -> SessionResponse:
    """AUTH-003 session check: `data` is the member, or null for a guest (200, so a normal
    guest visit logs no failed request). 401 AUTH_EXPIRED = refresh first."""
    return SessionResponse(data=member_schema(user) if user else None)
