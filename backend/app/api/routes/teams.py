"""Team browse (chat 07, LEAG-003). Served from stored reference data only."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.schemas.teams import BrowseTeam, TeamsMeta, TeamsResponse
from app.seed.competitions import LEAGUE_IDS
from app.services.reference import competition_ref, team_detail_lookup, team_ref
from app.services.team_browse import PAGE_SIZE, MembershipUnknown, browse_teams

router = APIRouter(tags=["teams"])
Db = Annotated[Session, Depends(get_db)]

NOT_A_LEAGUE = "팀 탐색을 제공하지 않는 리그입니다. 5대 리그 중에서 선택해 주세요."
MEMBERSHIP_UNKNOWN = "현재 시즌 소속 팀을 확인하지 못했습니다. 잠시 후 다시 확인해 주세요."


@router.get("/teams")
def read_teams(
    db: Db,
    # Any integer that is not a five-league id (0, negative, cup, UEFA) is 404; not an integer
    # is 422 (Codex 1차 지적 4: one contract for every unsupported league).
    league: Annotated[int | None, Query(description="Five-league id; omitted = all")] = None,
    q: Annotated[
        str | None, Query(min_length=1, max_length=40, description="Team name or alias")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
) -> TeamsResponse:
    """LEAG-003: current-season members of the five leagues, 12 per page.

    Unknown membership (a league's team list never collected) is 503, never a short or empty
    list. No match is an empty list with total 0; no other team is offered instead."""
    if league is not None and league not in LEAGUE_IDS:
        raise ApiError(404, "NOT_FOUND", NOT_A_LEAGUE)
    try:
        result = browse_teams(db, league=league, query=q, page=page)
    except MembershipUnknown:
        raise ApiError(503, "MEMBERSHIP_UNKNOWN", MEMBERSHIP_UNKNOWN) from None
    lookup = team_detail_lookup(db)
    return TeamsResponse(
        data=[
            BrowseTeam(team=team_ref(row.team, lookup), league=competition_ref(row.league))
            for row in result.rows
        ],
        meta=TeamsMeta(
            page=page, size=PAGE_SIZE, total=result.total, updated_at=result.updated_at
        ),
    )
