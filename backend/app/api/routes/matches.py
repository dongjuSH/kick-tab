"""Match detail APIs (chat 04, MAT-001~005, REV-004).

Each area has its own endpoint so one failing area never hides the others (MAT-004
"해당 영역만 오류·재시도"). Records and head-to-head are read from the database and fetched
from the provider at most once when missing (guide §6.5 요청 시 보충); concurrent requests
for the same match wait for that single fetch.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.models.fixture import Fixture
from app.models.reference import Competition, Team
from app.providers.api_football import ApiFootballClient
from app.schemas.match_detail import (
    HeadToHeadResponse,
    MatchInfo,
    MatchInfoResponse,
    MatchRecordsResponse,
    ReviewListResponse,
    UpdatedMeta,
)
from app.seed.competitions import season_label
from app.services.fixtures import to_summary
from app.services.head_to_head import ensure_form, ensure_meetings, read_head_to_head
from app.services.match_detail import BEFORE_KICKOFF, ensure_records, read_records
from app.services.reference import team_detail_lookup
from app.services.reviews import ReviewSort, list_reviews, review_open

router = APIRouter(prefix="/fixtures", tags=["matches"])
Db = Annotated[Session, Depends(get_db)]
FixtureId = Annotated[int, Path(gt=0, description="Match (fixture) id")]

NOT_FOUND = "경기를 찾을 수 없습니다. 경기 목록에서 다시 선택해 주세요."


def _fixture(db: Session, fixture_id: int) -> Fixture:
    fixture = db.get(Fixture, fixture_id)
    competition = fixture and db.get(Competition, fixture.competition_id)
    if fixture is None or competition is None or not competition.active:
        # An unknown id is never answered with another match (MAT-001).
        raise ApiError(404, "NOT_FOUND", NOT_FOUND)
    return fixture


@router.get("/{fixture_id}")
def read_match(db: Db, fixture_id: FixtureId) -> MatchInfoResponse:
    fixture = _fixture(db, fixture_id)
    competition = db.get(Competition, fixture.competition_id)
    home, away = db.get(Team, fixture.home_team_id), db.get(Team, fixture.away_team_id)
    summary = to_summary(fixture, competition, home, away, team_detail_lookup(db))
    return MatchInfoResponse(
        data=MatchInfo(
            match=summary,
            round=fixture.round,
            season_label=season_label(fixture.season),
            status_long=fixture.status_long_raw,
            status_code=fixture.status_short_raw,
            reviews_available=review_open(fixture),
            head_to_head_available=fixture.status in BEFORE_KICKOFF,
        ),
        meta=UpdatedMeta(updated_at=fixture.synced_at),
    )


@router.get("/{fixture_id}/detail")
def read_match_records(db: Db, fixture_id: FixtureId) -> MatchRecordsResponse:
    """Timeline, team statistics, lineups and provider player ratings (MAT-002·004)."""
    fixture = _fixture(db, fixture_id)
    ensure_records(db, fixture, datetime.now(UTC), ApiFootballClient)
    records, fetched_at = read_records(db, _fixture(db, fixture_id))
    return MatchRecordsResponse(data=records, meta=UpdatedMeta(updated_at=fetched_at))


@router.get("/{fixture_id}/head-to-head")
def read_match_head_to_head(db: Db, fixture_id: FixtureId) -> HeadToHeadResponse:
    """Last official meetings and both teams' recent form, before kickoff only (MAT-005)."""
    fixture = _fixture(db, fixture_id)
    if fixture.status not in BEFORE_KICKOFF:
        raise ApiError(409, "CONFLICT", "상대 전적은 경기 시작 전에만 제공합니다.")
    now = datetime.now(UTC)
    home_id, away_id = fixture.home_team_id, fixture.away_team_id
    ensure_meetings(db, fixture, now, ApiFootballClient)
    ensure_form(db, home_id, now, ApiFootballClient)
    ensure_form(db, away_id, now, ApiFootballClient)
    data, fetched_at = read_head_to_head(db, _fixture(db, fixture_id))
    return HeadToHeadResponse(data=data, meta=UpdatedMeta(updated_at=fetched_at))


@router.get("/{fixture_id}/reviews")
def read_match_reviews(
    db: Db, fixture_id: FixtureId, sort: Annotated[ReviewSort, Query()] = "popular"
) -> ReviewListResponse:
    """Public text reviews and their count, live or normally finished (REV-001·004)."""
    fixture = _fixture(db, fixture_id)
    if not review_open(fixture):
        raise ApiError(409, "CONFLICT", "이 경기는 경기 평가를 제공하지 않습니다.")
    return ReviewListResponse(data=list_reviews(db, fixture_id, sort))
