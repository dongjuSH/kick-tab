import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, StrictBool

from app.schemas.common import ApiModel
from app.schemas.match import TeamRef

VerificationPurpose = Literal["signup", "password_reset"]
LoginMethod = Literal["email", "kakao", "google"]

# Generous length caps only stop oversized bodies; the real rules are checked in the
# service so the messages match the screen hints exactly (P-04).
Email = Field(min_length=1, max_length=320)
Secret = Field(min_length=1, max_length=256)


class EmailCodeRequest(ApiModel):
    email: str = Email
    purpose: VerificationPurpose


class EmailCodeSent(ApiModel):
    expires_at: datetime
    # The earliest moment a new code may be requested (resend wait, 1 minute).
    resend_at: datetime


class EmailCodeVerify(ApiModel):
    email: str = Email
    purpose: VerificationPurpose
    code: str = Field(min_length=1, max_length=12)


class EmailCodeVerified(ApiModel):
    verification_token: str
    expires_at: datetime


class Agreements(ApiModel):
    # Missing or false is refused by the server (P-12); only true passes.
    terms_of_service: StrictBool | None = None
    privacy_collection: StrictBool | None = None
    age_14_or_older: StrictBool | None = Field(default=None, alias="age14OrOlder")


class SignupRequest(ApiModel):
    email: str = Email
    verification_token: str = Secret
    nickname: str = Field(min_length=1, max_length=64)
    password: str = Secret
    password_confirm: str = Secret
    agreements: Agreements = Field(default_factory=Agreements)


class LoginRequest(ApiModel):
    email: str = Email
    password: str = Secret


class PasswordResetRequest(ApiModel):
    email: str = Email
    verification_token: str = Secret
    new_password: str = Secret
    new_password_confirm: str = Secret


class PasswordChangeRequest(ApiModel):
    current_password: str = Secret
    new_password: str = Secret
    new_password_confirm: str = Secret


class Member(ApiModel):
    """The signed-in member (AUTH-003, MY-004 display-only fields)."""

    id: uuid.UUID
    email: str
    nickname: str
    login_method: LoginMethod
    created_at: datetime
    # Terms 제9조: reviews cannot be written or edited until then; null = no restriction.
    review_restricted_until: datetime | None = None


class MemberResponse(ApiModel):
    data: Member


class SessionResponse(ApiModel):
    """GET /auth/me: the member, or null when nobody is signed in."""

    data: Member | None


class MemberFavorites(ApiModel):
    """A member's favourite teams in registration order (FAV-001), max 10."""

    teams: list[TeamRef]
    max: int


class MemberFavoritesResponse(ApiModel):
    data: MemberFavorites


class FavoriteAdd(ApiModel):
    team_id: int = Field(gt=0, le=2_147_483_647)
