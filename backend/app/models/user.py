"""Members and their account data (chat 02, guide §6.2·§6.3).

Deleting a user (P-03 withdrawal) cascades to identities, refresh tokens, agreements,
favourite teams, reviews and reactions; feedback keeps the row and only loses the link
(`feedback.user_id` ON DELETE SET NULL, migration 0019).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# P-12: the three required confirmations on the signup screen.
AGREEMENT_ITEMS = ("terms_of_service", "privacy_collection", "age_14_or_older")
MEMBER_FAVORITES_MAX = 10


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "login_method IN ('email', 'kakao', 'google')", name="login_method_allowed"
        ),
        # Email accounts always have a password hash (social accounts may not).
        CheckConstraint(
            "login_method <> 'email' OR password_hash IS NOT NULL", name="email_has_password"
        ),
        # Stored lower-cased; one account per address.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("uq_users_nickname_lower", text("lower(nickname)"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    login_method: Mapped[str] = mapped_column(Text, nullable=False)
    # Bumped when every session must end (password reset/change): access tokens carry it.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Terms 제9조: until this moment the member cannot write or edit reviews (set by the
    # operator with `python -m app.moderation`). NULL or past = no restriction.
    review_restricted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuthIdentity(Base):
    """Social sign-in link (later work, P-02). Never linked automatically by email."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        CheckConstraint("provider IN ('kakao', 'google')", name="provider_allowed"),
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identities_provider_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmailVerification(Base):
    """One live code per email and purpose. A resend overwrites the row, so the previous
    code stops working. A confirmed code yields a one-time token (hash only)."""

    __tablename__ = "email_verifications"
    __table_args__ = (
        CheckConstraint("purpose IN ('signup', 'password_reset')", name="purpose_allowed"),
        CheckConstraint("failed_attempts >= 0", name="failed_attempts_positive"),
        UniqueConstraint("email", "purpose", name="uq_email_verifications_email_purpose"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RefreshToken(Base):
    """Refresh token (hash only). Rotated on every use; a used one coming back means the
    family leaked, so the whole family is revoked (guide §6.2)."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_family", "family_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set when rotated (replaced) or revoked; such a token is never accepted again.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TermsAgreement(Base):
    """P-12: which item, which document version, confirmed or not, and when."""

    __tablename__ = "terms_agreements"
    __table_args__ = (
        CheckConstraint(
            "item_id IN ('terms_of_service', 'privacy_collection', 'age_14_or_older')",
            name="item_allowed",
        ),
        UniqueConstraint("user_id", "item_id", "item_version", name="uq_terms_agreements_item"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    item_version: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    agreed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MemberFavorite(Base):
    """A member's favourite team (FAV-001~003): at most 10 per member, checked in the
    service under a per-member lock (the count is not a table constraint)."""

    __tablename__ = "member_favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
