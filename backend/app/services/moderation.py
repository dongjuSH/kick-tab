"""Operator moderation (terms 제8조·제9조, 2026-11-22). There is no admin screen: the
operator runs `uv run python -m app.moderation …` (see app/moderation.py).

Steps the terms describe: 1st — the review is deleted and a warning mail is sent; 2nd —
reviews are restricted for 7 days; 3rd — 30 days; then, or for a serious violation — the
account is closed after notice. Mails to the member are sent by the operator from the
contact mailbox; these functions only change the data.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.user import User
from app.services import accounts
from app.services.auth_security import normalize_email

RESTRICTION_DAYS = (7, 30)


class ModerationError(Exception):
    """The target does not exist or the request is not allowed."""


def _member(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        raise ModerationError("No member with this email")
    return user


def restrict_reviews(db: Session, email: str, days: int, now: datetime) -> datetime:
    """Block writing and editing reviews until now + days. Returns the end moment."""
    if days not in RESTRICTION_DAYS:
        raise ModerationError(f"Restriction must be one of {RESTRICTION_DAYS} days")
    user = accounts._lock_user(db, _member(db, email).id)
    assert user is not None
    user.review_restricted_until = now + timedelta(days=days)
    db.commit()
    return user.review_restricted_until


def lift_restriction(db: Session, email: str) -> None:
    user = accounts._lock_user(db, _member(db, email).id)
    assert user is not None
    user.review_restricted_until = None
    db.commit()


@dataclass(frozen=True)
class RemovedReview:
    review_id: int
    fixture_id: int
    author_email: str


def remove_review(db: Session, review_id: int) -> RemovedReview:
    """Delete a review that breaks terms 제7조 (its reactions go with it)."""
    review = db.get(Review, review_id)
    if review is None:
        raise ModerationError("No review with this id")
    author = db.get(User, review.user_id)
    removed = RemovedReview(review.id, review.fixture_id, author.email if author else "")
    db.delete(review)
    db.commit()
    return removed


def close_account(db: Session, email: str) -> None:
    """Terms 제9조 last step: the same deletion as a withdrawal (P-03)."""
    accounts.delete_account(db, _member(db, email))
