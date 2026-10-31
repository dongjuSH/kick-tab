from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import RateLimit
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.schemas.common import DataResponse
from app.schemas.feedback import FeedbackCreate, FeedbackReceipt
from app.services.feedback import create_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

# P-10 proposal (not yet decided): 3 per minute and 20 per day per client IP.
feedback_rate_limit = RateLimit("feedback", [Limit(3, 60), Limit(20, 24 * 60 * 60)])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(feedback_rate_limit)],
)
def submit_feedback(
    payload: FeedbackCreate, db: Annotated[Session, Depends(get_db)]
) -> DataResponse[FeedbackReceipt]:
    # Chat 01 stores every submission anonymously; chat 02 attaches the member id.
    feedback = create_feedback(db, payload, user_id=None)
    return DataResponse(data=FeedbackReceipt(id=feedback.id, created_at=feedback.created_at))
