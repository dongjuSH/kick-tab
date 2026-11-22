"""The signed-in member's own data (chat 02; the my page screens are chat 09).

Every route takes the member from the session cookie, never from the request, so a member
can only read or change their own account, favourite teams and reviews (COM-002).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.api.auth import Member, clear_session_cookies, member_schema, set_session_cookies
from app.api.deps import RateLimit
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.schemas.auth import (
    FavoriteAdd,
    MemberFavoritesResponse,
    MemberResponse,
    PasswordChangeRequest,
)
from app.schemas.match_detail import MyReviewsResponse
from app.services import accounts, member_favorites
from app.services.accounts import utcnow
from app.services.reviews import my_reviews

router = APIRouter(prefix="/me", tags=["me"])
Db = Annotated[Session, Depends(get_db)]
TeamId = Annotated[int, Path(gt=0, le=2_147_483_647)]

# Each attempt checks the current password: keep guessing slow.
password_limit = RateLimit("me-password", [Limit(10, 10 * 60)])


@router.patch("/password", dependencies=[Depends(password_limit)])
def change_password(
    payload: PasswordChangeRequest, user: Member, db: Db, response: Response
) -> MemberResponse:
    """MY-004: email accounts only. Errors, one code per field state (09 dialog):
    PASSWORD_CURRENT_MISMATCH (currentPassword), PASSWORD_RULE (newPassword),
    PASSWORD_CONFIRM_MISMATCH (newPasswordConfirm), all 422 with `details.fields`.
    Other sessions end; this browser receives new cookies."""
    tokens = accounts.change_password(
        db,
        user,
        payload.current_password,
        payload.new_password,
        payload.new_password_confirm,
        utcnow(),
    )
    set_session_cookies(response, tokens)
    return MemberResponse(data=member_schema(user))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def withdraw(user: Member, db: Db, response: Response) -> None:
    """P-03 withdrawal (MY-004 rule 3): no extra password step; the valid session is the
    proof. Deletes the account, favourite teams, reviews and reactions (they leave every
    count), keeps feedback without the link, ends every session and clears the cookies."""
    accounts.delete_account(db, user)
    clear_session_cookies(response)


@router.get("/favorites")
def read_favorites(user: Member, db: Db) -> MemberFavoritesResponse:
    return MemberFavoritesResponse(data=member_favorites.list_favorites(db, user.id))


@router.post("/favorites")
def add_favorite(payload: FavoriteAdd, user: Member, db: Db) -> MemberFavoritesResponse:
    """FAV-002: 409 FAVORITE_LIMIT for an 11th team; an existing team changes nothing."""
    return MemberFavoritesResponse(data=member_favorites.add_favorite(db, user.id, payload.team_id))


@router.delete("/favorites/{team_id}")
def remove_favorite(team_id: TeamId, user: Member, db: Db) -> MemberFavoritesResponse:
    return MemberFavoritesResponse(data=member_favorites.remove_favorite(db, user.id, team_id))


@router.get("/reviews")
def read_my_reviews(user: Member, db: Db) -> MyReviewsResponse:
    """The member's reviews, newest first: match, body, counts, `createdAt`, and `editedAt`
    only for reviews changed after writing (my page shows '수정 YYYY.MM.DD')."""
    return MyReviewsResponse(data=my_reviews(db, user.id))
