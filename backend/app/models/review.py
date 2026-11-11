"""Member match reviews and reactions (REV-001~004).

A review is text only: the body is required (not blank) and at most 300 characters. There
is no star rating or member average (04 개선, migration 0015). One review per member+match.

Chat 04 creates the tables and the public read side. `users` does not exist yet (chat 02),
so `user_id` has no foreign key here; chat 02 adds `REFERENCES users(id) ON DELETE CASCADE`
on both tables (P-03: a withdrawn member's reviews and reactions are deleted and leave the
aggregates).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REVIEW_BODY_MAX = 300
# A body must contain a character outside this class: exactly the characters Python's
# str.isspace() treats as whitespace (tabs, line breaks, NBSP U+00A0, ideographic space
# U+3000, ...), so a body passes the DB check iff `body.strip()` is not empty (02 validates
# the same way). PostgreSQL ARE escapes; tests/test_review_window.py keeps it in sync.
REVIEW_BODY_SPACE_CLASS = (
    r"\t\n\v\f\r\u001c-\u001f \u0085   -     　"
)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "fixture_id", name="uq_reviews_user_fixture"),
        CheckConstraint(f"char_length(body) <= {REVIEW_BODY_MAX}", name="body_length"),
        CheckConstraint(f"body ~ '[^{REVIEW_BODY_SPACE_CLASS}]'", name="body_not_blank"),
        Index("ix_reviews_fixture_created", "fixture_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewReaction(Base):
    __tablename__ = "review_reactions"
    __table_args__ = (CheckConstraint("value IN (-1, 1)", name="value_allowed"),)

    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
