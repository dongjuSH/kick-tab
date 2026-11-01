import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import func, select, text
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


def duplicate_lock_key(digest: str) -> int:
    """Signed 64-bit advisory lock key for one body hash (namespaced, see app.sync.runner)."""
    key = hashlib.sha256(f"kicktab-feedback:{digest}".encode()).digest()
    return int.from_bytes(key[:8], "big", signed=True)


def lock_body_hash(session: Session, digest: str) -> None:
    """Serialise check-and-insert for one body until the transaction ends.

    Two concurrent submissions of the same body would otherwise both see "no duplicate"
    and both be stored. Released automatically on commit or rollback.
    """
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": duplicate_lock_key(digest)}
    )


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
    lock_body_hash(session, digest)
    if is_duplicate(session, digest):
        session.rollback()  # end the transaction so the lock is released now
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
