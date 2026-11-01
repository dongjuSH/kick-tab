import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import RateLimit
from app.api.errors import ApiError
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.notifications.discord import FeedbackNotice, notify_feedback
from app.schemas.common import DataResponse
from app.schemas.feedback import FeedbackCreate, FeedbackReceipt
from app.services.feedback import DuplicateFeedbackError, create_feedback

logger = logging.getLogger(__name__)

# P-10, decided by the user (2026-10-31): 3 per minute and 20 per day per client IP, plus
# a service-wide ceiling of 20 per minute and 300 per day against forged client IPs (C-08).
# Still open: chat 02 splits members (key = user id) and guests — see guide §10.1 P-10.
feedback_rate_limit = RateLimit(
    "feedback",
    [Limit(3, 60), Limit(20, 24 * 60 * 60)],
    global_limits=[Limit(20, 60), Limit(300, 24 * 60 * 60)],
)

# The limit runs in the route class (before body parsing) so malformed JSON counts too.
router = APIRouter(
    prefix="/feedback", tags=["feedback"], route_class=feedback_rate_limit.route_class()
)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> DataResponse[FeedbackReceipt]:
    if payload.website:
        # Honeypot filled: generic refusal that doesn't explain the trap.
        logger.info("Feedback rejected: honeypot filled")
        raise ApiError(400, "VALIDATION_ERROR", "요청을 처리할 수 없습니다.")
    try:
        # Chat 01 stores every submission anonymously; chat 02 attaches the member id.
        feedback = create_feedback(db, payload, user_id=None)
    except DuplicateFeedbackError:
        raise ApiError(
            409, "FEEDBACK_DUPLICATE", "같은 내용의 의견이 이미 접수되었습니다."
        ) from None
    # Discord alert after the response; a failure never affects the stored row.
    background_tasks.add_task(notify_feedback, FeedbackNotice.from_model(feedback))
    return DataResponse(data=FeedbackReceipt(id=feedback.id, created_at=feedback.created_at))
