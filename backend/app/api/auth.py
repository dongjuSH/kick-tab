"""Auth cookies and the current-member dependencies (guide §6.2).

`kt_access` (JWT, Path=/) and `kt_refresh` (Path=/api/v1/auth) are httpOnly, SameSite=Lax,
and Secure outside local development. Both live 14 days in the browser; the JWT's own
15-minute expiry decides whether the access token is still accepted.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import Member as MemberSchema
from app.services import auth_security as sec
from app.services.accounts import SessionTokens
from app.services.reviews import review_restriction

ACCESS_COOKIE = "kt_access"
REFRESH_COOKIE = "kt_refresh"
REFRESH_PATH = "/api/v1/auth"
COOKIE_MAX_AGE = int(sec.REFRESH_TOKEN_TTL.total_seconds())

AUTH_REQUIRED = "로그인이 필요합니다."
SESSION_EXPIRED = "로그인 세션이 만료되었습니다."
NOT_CONFIGURED = "회원 기능을 잠시 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."


def set_session_cookies(response: Response, tokens: SessionTokens) -> None:
    common = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.secure_cookies,
        "max_age": COOKIE_MAX_AGE,
    }
    response.set_cookie(ACCESS_COOKIE, tokens.access, path="/", **common)
    response.set_cookie(REFRESH_COOKIE, tokens.refresh, path=REFRESH_PATH, **common)


def clear_session_cookies(response: Response) -> None:
    common = {"httponly": True, "samesite": "lax", "secure": settings.secure_cookies}
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, **common)


def member_id_from_cookie(request: Request) -> uuid.UUID | None:
    """The member id of a valid, unexpired access cookie, without a database read (used to
    pick a request limit before the body is parsed). None = treat as a guest."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        return sec.decode_access_token(token).user_id
    except (sec.AuthNotConfigured, sec.AccessTokenExpired, sec.AccessTokenInvalid):
        return None


def _member(request: Request, db: Session, *, required: bool) -> User | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        if required:
            raise ApiError(401, "AUTH_REQUIRED", AUTH_REQUIRED)
        return None
    try:
        claims = sec.decode_access_token(token)
    except sec.AuthNotConfigured:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NOT_CONFIGURED) from None
    except sec.AccessTokenExpired:
        # The client refreshes once and retries (guide §6.2), also on public reads.
        raise ApiError(401, "AUTH_EXPIRED", SESSION_EXPIRED) from None
    except sec.AccessTokenInvalid:
        if required:
            raise ApiError(401, "AUTH_REQUIRED", AUTH_REQUIRED) from None
        return None
    user = db.get(User, claims.user_id)
    if user is None:
        if required:
            raise ApiError(401, "AUTH_REQUIRED", AUTH_REQUIRED)
        return None
    if user.token_version != claims.version:
        # Password changed or reset elsewhere: the refresh token is revoked too.
        raise ApiError(401, "AUTH_EXPIRED", SESSION_EXPIRED)
    return user


def require_member(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    user = _member(request, db, required=True)
    assert user is not None
    return user


def optional_member(request: Request, db: Annotated[Session, Depends(get_db)]) -> User | None:
    return _member(request, db, required=False)


def member_schema(user: User) -> MemberSchema:
    return MemberSchema(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        login_method=user.login_method,  # type: ignore[arg-type]
        created_at=user.created_at,
        review_restricted_until=review_restriction(user, datetime.now(UTC)),
    )


Member = Annotated[User, Depends(require_member)]
MaybeMember = Annotated[User | None, Depends(optional_member)]
