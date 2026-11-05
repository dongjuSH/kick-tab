"""Past results API (chat 05, HIST-001~003). Served from stored fixtures only (OPS-001)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.routes.schedule import require_supported_season
from app.config import settings
from app.db.session import get_db
from app.models.reference import Team
from app.schemas.schedule import ResultsMeta, ResultsPage, ResultsResponse
from app.seed.competitions import COMPETITION_IDS
from app.services.reference import team_detail_lookup, team_ref
from app.services.results import PAGE_SIZE, finished_results, season_coverage, season_item

router = APIRouter(tags=["results"])
Db = Annotated[Session, Depends(get_db)]

NOT_COLLECTED = "지난 경기를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
TEAM_NOT_FOUND = "팀을 찾을 수 없습니다. 팀 검색으로 다시 선택해 주세요."


def _competition_ids(raw: str | None) -> list[int]:
    """Supported competition ids. One without data in the chosen season is accepted (a
    season change keeps the competitions, HIST-002) and simply has no results."""
    if not raw:
        return []
    try:
        ids = list(dict.fromkeys(int(part) for part in raw.split(",") if part.strip()))
    except ValueError:
        ids = []
    if not ids or any(cid not in COMPETITION_IDS for cid in ids):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "지원하지 않는 대회가 포함되어 있습니다. 대회를 다시 선택해 주세요.",
            details={"fields": {"competitions": "대회 ID를 확인해 주세요."}},
        )
    return ids


@router.get("/results")
def read_results(
    db: Db,
    season: Annotated[int | None, Query(ge=1, description="API season; default current")] = None,
    competitions: Annotated[
        str | None, Query(max_length=200, description="Comma-separated competition ids")
    ] = None,
    team: Annotated[int | None, Query(gt=0, description="Team id")] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> ResultsResponse:
    """HIST-001·002: every finished match of the season (normal results and rulings),
    newest first, combined with competition and team conditions, 10 per page.

    An unsupported season is 404 (never replaced). When no competition in scope was ever
    loaded the answer is 503, so "not collected" is not shown as "no results"; a failed
    refresh of a loaded competition keeps its stored results and lists it in
    `failedCompetitionIds` (CMP-004)."""
    season = season or settings.current_season
    require_supported_season(db, season)
    coverage = season_coverage(db, season)
    competition_ids = _competition_ids(competitions)

    selected = None
    if team is not None:
        found = db.get(Team, team)
        if found is None:
            raise ApiError(404, "NOT_FOUND", TEAM_NOT_FOUND)
        selected = team_ref(found, team_detail_lookup(db))

    # Only competitions with provider data in the season can be "not collected yet".
    scope = [cid for cid in competition_ids or coverage.available_ids
             if cid in coverage.available_ids]
    if scope and not coverage.loaded_any(scope):
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NOT_COLLECTED)
    matches, total, updated_at = finished_results(
        db, season, competition_ids=competition_ids, team_id=team, page=page
    )
    return ResultsResponse(
        data=ResultsPage(season=season_item(season), team=selected, matches=matches),
        meta=ResultsMeta(
            page=page,
            size=PAGE_SIZE,
            total=total,
            updated_at=updated_at,
            failed_competition_ids=[cid for cid in coverage.failed_ids if cid in scope],
        ),
    )
