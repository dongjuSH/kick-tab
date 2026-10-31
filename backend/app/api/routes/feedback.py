from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import RateLimit
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.notifications.discord import FeedbackNotice, notify_feedback
from app.schemas.common import DataResponse
from app.schemas.feedback import FeedbackCreate, FeedbackReceipt
from app.services.feedback import create_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

# P-10 proposal (not yet decided): 3 per minute and 20 per day per client IP, plus a
# service-wide ceiling of 20 per minute and 300 per day against forged client IPs (C-08).
feedback_rate_limit = RateLimit(
    "feedback",
    [Limit(3, 60), Limit(20, 24 * 60 * 60)],
    global_limits=[Limit(20, 60), Limit(300, 24 * 60 * 60)],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(feedback_rate_limit)],
)
def submit_feedback(
    payload: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> DataResponse[FeedbackReceipt]:
    # Chat 01 stores every submission anonymously; chat 02 attaches the member id.
    feedback = create_feedback(db, payload, user_id=None)
    # Discord alert after the response; a failure never affects the stored row.
    background_tasks.add_task(notify_feedback, FeedbackNotice.from_model(feedback))
    return DataResponse(data=FeedbackReceipt(id=feedback.id, created_at=feedback.created_at))
