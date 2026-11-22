"""Member review writing (chat 02, REV-002·003·004). Writing a new review is
`POST /fixtures/{id}/reviews` (matches router); these routes act on one existing review."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.api.auth import Member
from app.db.session import get_db
from app.schemas.match_detail import ReviewReactionWrite, ReviewResponse, ReviewWrite
from app.services import reviews

router = APIRouter(prefix="/reviews", tags=["reviews"])
Db = Annotated[Session, Depends(get_db)]
ReviewId = Annotated[int, Path(gt=0, le=9_223_372_036_854_775_807)]


@router.patch("/{review_id}")
def edit_review(review_id: ReviewId, payload: ReviewWrite, user: Member, db: Db) -> ReviewResponse:
    """Own review only (403 otherwise), while the match is open for reviews (409)."""
    return ReviewResponse(data=reviews.edit_review(db, user.id, review_id, payload.body))


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: ReviewId, user: Member, db: Db) -> None:
    reviews.delete_review(db, user.id, review_id)


@router.put("/{review_id}/reaction")
def react(
    review_id: ReviewId, payload: ReviewReactionWrite, user: Member, db: Db
) -> ReviewResponse:
    """Like (1) or dislike (-1); a second press of the other value switches it. Not on
    one's own review (403)."""
    return ReviewResponse(data=reviews.set_reaction(db, user.id, review_id, payload.value))


@router.delete("/{review_id}/reaction")
def clear_reaction(review_id: ReviewId, user: Member, db: Db) -> ReviewResponse:
    return ReviewResponse(data=reviews.set_reaction(db, user.id, review_id, None))
