import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate


def create_feedback(
    session: Session, payload: FeedbackCreate, *, user_id: uuid.UUID | None = None
) -> Feedback:
    """Store one feedback row. Chat 01 always passes user_id=None (anonymous).

    Chat 02 passes the authenticated user's id; anonymous feedback is never linked to an
    account afterwards (FEED-003).
    """
    feedback = Feedback(
        user_id=user_id,
        type=payload.type,
        body=payload.body,
        page_path=payload.page_path,
    )
    session.add(feedback)
    # Only committed rows count as received feedback (FEED-003).
    session.commit()
    session.refresh(feedback)
    return feedback


def count_feedback(session: Session) -> int:
    """Number of successfully stored feedback rows (basic aggregate for operations)."""
    return session.scalar(select(func.count()).select_from(Feedback)) or 0
