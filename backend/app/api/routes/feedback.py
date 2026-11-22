import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.api.auth import MaybeMember, member_id_from_cookie
from app.api.deps import RateLimit, SharedCounter
from app.api.errors import ApiError
from app.core.rate_limit import Limit, RateLimiter
from app.db.session import get_db
from app.notifications.discord import FeedbackNotice, notify_feedback
from app.schemas.common import DataResponse
from app.schemas.feedback import FeedbackCreate, FeedbackReceipt
from app.services.feedback import DuplicateFeedbackError, create_feedback

logger = logging.getLogger(__name__)

DAY = 24 * 60 * 60
# P-10: the service-wide ceiling against forged client IPs (C-08, user decision 2026-10-31)
# stays — one counter for members and guests together (Codex N3); per sender, guests
# (key = client IP) are stricter than members (key = user id): guests 2 per minute and 5 per
# day, members 3 per minute and 20 per day (chat 02, the values proposed in guide §10.1).
feedback_global_limit = SharedCounter("feedback", RateLimiter([Limit(20, 60), Limit(300, DAY)]))
feedback_rate_limit = RateLimit(
    "feedback",
    [Limit(2, 60), Limit(5, DAY)],
    shared_global=feedback_global_limit,
)
feedback_member_limit = RateLimit(
    "feedback-member",
    [Limit(3, 60), Limit(20, DAY)],
    key_func=lambda request: str(member_id_from_cookie(request)),
    shared_global=feedback_global_limit,
)


class FeedbackLimitedRoute(APIRoute):
    """Applies the member or guest limit before the body is parsed, so malformed JSON
    counts too (P-10). The cookie decides; an invalid or expired one counts as a guest."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def limited(request: Request) -> Response:
            if member_id_from_cookie(request) is None:
                feedback_rate_limit(request)
            else:
                feedback_member_limit(request)
            return await handler(request)

        return limited


router = APIRouter(prefix="/feedback", tags=["feedback"], route_class=FeedbackLimitedRoute)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    member: MaybeMember,
) -> DataResponse[FeedbackReceipt]:
    if payload.website:
        # Honeypot filled: generic refusal that doesn't explain the trap.
        logger.info("Feedback rejected: honeypot filled")
        raise ApiError(400, "VALIDATION_ERROR", "요청을 처리할 수 없습니다.")
    try:
        # A member's feedback is linked to the account (FEED-003); a guest's stays anonymous.
        feedback = create_feedback(db, payload, user_id=member.id if member else None)
    except DuplicateFeedbackError:
        raise ApiError(
            409, "FEEDBACK_DUPLICATE", "같은 내용의 의견이 이미 접수되었습니다."
        ) from None
    # Discord alert after the response; a failure never affects the stored row.
    background_tasks.add_task(notify_feedback, FeedbackNotice.from_model(feedback))
    return DataResponse(data=FeedbackReceipt(id=feedback.id, created_at=feedback.created_at))
