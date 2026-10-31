import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate

# The same body (after normalisation) is accepted once per 24 hours across all senders.
DUPLICATE_WINDOW = timedelta(hours=24)


class DuplicateFeedbackError(Exception):
    """Same body already received within DUPLICATE_WINDOW."""


def normalize_body(body: str) -> str:
    """Whitespace collapsed and case-folded, so trivial edits don't bypass the check."""
    return " ".join(body.split()).casefold()


def body_hash(body: str) -> str:
    return hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()


def is_duplicate(session: Session, digest: str) -> bool:
    found = session.scalar(
        select(Feedback.id)
        .where(Feedback.body_hash == digest, Feedback.created_at >= func.now() - DUPLICATE_WINDOW)
        .limit(1)
    )
    return found is not None


def create_feedback(
    session: Session, payload: FeedbackCreate, *, user_id: uuid.UUID | None = None
) -> Feedback:
    """Store one feedback row. Chat 01 always passes user_id=None (anonymous).

    Chat 02 passes the authenticated user's id; anonymous feedback is never linked to an
    account afterwards (FEED-003). Raises DuplicateFeedbackError for a repeat body.
    """
    digest = body_hash(payload.body)
    if is_duplicate(session, digest):
        raise DuplicateFeedbackError
    feedback = Feedback(
        user_id=user_id,
        type=payload.type,
        body=payload.body,
        page_path=payload.page_path,
        body_hash=digest,
    )
    session.add(feedback)
    # Only committed rows count as received feedback (FEED-003).
    session.commit()
    session.refresh(feedback)
    return feedback


def count_feedback(session: Session) -> int:
    """Number of successfully stored feedback rows (basic aggregate for operations)."""
    return session.scalar(select(func.count()).select_from(Feedback)) or 0
