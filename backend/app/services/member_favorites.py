"""Member favourite teams in the DB (FAV-001~003, COM-005): at most 10 per member.

Adds and removals of one member are serialised by a per-member advisory lock, so the count
read inside the transaction is the count that is saved: concurrent requests never pass 10.
The guest list (localStorage, max 5) is separate and never merged with this one.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.locks import advisory_key
from app.models.reference import Team
from app.models.user import MEMBER_FAVORITES_MAX, MemberFavorite
from app.schemas.auth import MemberFavorites
from app.services.reference import team_detail_lookup, team_ref

LIMIT_MESSAGE = f"관심 팀은 최대 {MEMBER_FAVORITES_MAX}개까지 등록할 수 있습니다."


def _lock(db: Session, user_id: uuid.UUID) -> None:
    db.execute(select(func.pg_advisory_xact_lock(advisory_key(f"kicktab-favorites:{user_id}"))))


def list_favorites(db: Session, user_id: uuid.UUID) -> MemberFavorites:
    rows = db.execute(
        select(Team)
        .join(MemberFavorite, MemberFavorite.team_id == Team.id)
        .where(MemberFavorite.user_id == user_id)
        .order_by(MemberFavorite.created_at, MemberFavorite.team_id)
    ).scalars()
    lookup = team_detail_lookup(db)
    return MemberFavorites(teams=[team_ref(t, lookup) for t in rows], max=MEMBER_FAVORITES_MAX)


def add_favorite(db: Session, user_id: uuid.UUID, team_id: int) -> MemberFavorites:
    """Register one team. Already registered = no change. The 11th distinct team is refused
    and the list stays as it was. Only teams with a team detail (current-season five-league
    teams, the same set the screens offer) can be registered."""
    team = db.get(Team, team_id)
    if team is None:
        raise ApiError(404, "NOT_FOUND", "팀을 찾을 수 없습니다.")
    if team_detail_lookup(db)(team_id) is not True:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "현재 시즌 5대 리그 팀만 관심 팀으로 등록할 수 있습니다.",
            details={"fields": {"teamId": "등록할 수 없는 팀입니다."}},
        )
    _lock(db, user_id)
    exists = db.get(MemberFavorite, (user_id, team_id)) is not None
    if not exists:
        count = db.scalar(
            select(func.count())
            .select_from(MemberFavorite)
            .where(MemberFavorite.user_id == user_id)
        )
        if (count or 0) >= MEMBER_FAVORITES_MAX:
            db.rollback()
            raise ApiError(
                409, "FAVORITE_LIMIT", LIMIT_MESSAGE, details={"max": MEMBER_FAVORITES_MAX}
            )
        db.add(MemberFavorite(user_id=user_id, team_id=team_id))
    db.commit()
    return list_favorites(db, user_id)


def remove_favorite(db: Session, user_id: uuid.UUID, team_id: int) -> MemberFavorites:
    """Remove one of this member's teams; a team not in the list changes nothing (FAV-003)."""
    _lock(db, user_id)
    db.execute(
        delete(MemberFavorite).where(
            MemberFavorite.user_id == user_id, MemberFavorite.team_id == team_id
        )
    )
    db.commit()
    return list_favorites(db, user_id)
