"""Main schedule APIs (chat 03): competitions, fixtures, favourite teams' schedule, team
search and news. Every response is served from collected data; no request reaches an
external API (OPS-001)."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RateLimit
from app.api.errors import ApiError
from app.config import settings
from app.core.kst import kst_today
from app.core.rate_limit import Limit
from app.db.session import get_db
from app.models.news import NewsArticle
from app.models.reference import Competition, CompetitionSeason, Team
from app.schemas.schedule import (
    CompetitionItem,
    CompetitionSeasonInfo,
    CompetitionsResponse,
    FavoriteSchedule,
    FavoriteScheduleResponse,
    FixtureAvailability,
    FixtureAvailabilityResponse,
    FixtureDateAvailability,
    FixturesResponse,
    NewsBadge,
    NewsLink,
    NewsLinkResponse,
    NewsMeta,
    NewsResponse,
    ScheduleMeta,
    SeasonsResponse,
    TeamSchedule,
    TeamScheduleResponse,
    TeamSearchResponse,
)
from app.services.fixtures import (
    collection_window,
    fixture_availability,
    fixtures_on,
    next_for_teams,
    sync_state,
    team_schedule,
    team_schedule_window,
)
from app.services.news import InvalidCursor, collection_state, list_news
from app.services.news_link import check_link
from app.services.reference import managed_seasons, team_detail_lookup, team_ref
from app.services.results import supported_seasons
from app.services.team_search import search_teams

router = APIRouter(tags=["schedule"])
UNSUPPORTED_SEASON = "지원하지 않는 시즌입니다. 시즌 목록에서 다시 선택해 주세요."
Db = Annotated[Session, Depends(get_db)]
MAX_FAVORITES = 5

NOT_COLLECTED = "경기 일정을 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
# Each check makes one outbound request to a press site: keep it from becoming a proxy.
news_link_limit = RateLimit(
    "news-link", [Limit(30, 60)], global_limits=[Limit(300, 60)]
)
NEWS_NOT_COLLECTED = "뉴스를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."


@router.get("/competitions")
def read_competitions(db: Db) -> CompetitionsResponse:
    competitions = db.scalars(
        select(Competition).where(Competition.active).order_by(Competition.sort_order)
    ).all()
    seasons: dict[int, list[CompetitionSeasonInfo]] = {}
    for row in db.scalars(
        select(CompetitionSeason)
        .where(CompetitionSeason.season.in_(managed_seasons()))
        .order_by(CompetitionSeason.season.desc())
    ):
        seasons.setdefault(row.competition_id, []).append(
            CompetitionSeasonInfo(season=row.season, label=row.label, availability=row.availability)
        )
    current = settings.current_season
    return CompetitionsResponse(
        data=[
            CompetitionItem(
                id=c.id,
                name_ko=c.name_ko,
                short_name=c.short_name,
                group=c.group_key,
                current_season=next(
                    (s for s in seasons.get(c.id, []) if s.season == current), None
                ),
                seasons=seasons.get(c.id, []),
            )
            for c in competitions
        ]
    )


@router.get("/seasons")
def read_seasons(db: Db) -> SeasonsResponse:
    """Season dropdown (HIST-002, CMP-003): newest first, `current` marks the default."""
    return SeasonsResponse(data=supported_seasons(db))


def require_supported_season(db: Session, season: int) -> None:
    """An unsupported season is refused, never swapped for another one (HIST-002)."""
    if season not in {item.season for item in supported_seasons(db)}:
        raise ApiError(404, "NOT_FOUND", UNSUPPORTED_SEASON)


@router.get("/fixtures")
def read_fixtures(
    db: Db,
    day: Annotated[date | None, Query(alias="date", description="KST date (YYYY-MM-DD)")] = None,
) -> FixturesResponse:
    """Matches of every supported competition on one KST calendar date (SCH-002).

    Competition/team filters are applied on screen to this list, so "no matches that day"
    and "no matches for the filter" stay distinguishable."""
    day = day or kst_today()
    start, end = collection_window()
    if not start <= day <= end:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            f"조회할 수 있는 날짜는 {start.isoformat()}부터 {end.isoformat()}까지입니다.",
            details={"fields": {"date": "조회 가능한 날짜 범위를 벗어났습니다."}},
        )
    state = sync_state(db, window=(day, day))
    matches, updated_at = fixtures_on(db, day)
    if state.never_synced or (not matches and _all_failed(db, state.failed_competition_ids)):
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NOT_COLLECTED)
    return FixturesResponse(
        data=matches,
        meta=ScheduleMeta(
            updated_at=updated_at, failed_competition_ids=state.failed_competition_ids
        ),
    )


def _all_failed(db: Session, failed_ids: list[int]) -> bool:
    available = db.scalar(
        select(CompetitionSeason.competition_id)
        .where(
            CompetitionSeason.season == settings.current_season,
            CompetitionSeason.availability == "available",
            CompetitionSeason.competition_id.not_in(failed_ids),
        )
        .limit(1)
    )
    return available is None


@router.get("/fixtures/availability")
def read_fixture_availability(db: Db) -> FixtureAvailabilityResponse:
    start, end = collection_window()
    return FixtureAvailabilityResponse(data=FixtureAvailability(
        start=start,
        end=end,
        dates=[
            FixtureDateAvailability(date=day, competition_ids=ids, unknown_competition_ids=unknown)
            for day, ids, unknown in fixture_availability(db, start, end)
        ],
    ))


@router.get("/fixtures/next")
def read_favorite_schedule(
    db: Db,
    teams: Annotated[str, Query(description="Comma-separated team ids, at most 5")],
) -> FavoriteScheduleResponse:
    """FAV-004: the live or nearest upcoming match of each favourite team."""
    try:
        team_ids = list(dict.fromkeys(int(t) for t in teams.split(",") if t.strip()))
    except ValueError:
        team_ids = []
    if not team_ids or len(team_ids) > MAX_FAVORITES or min(team_ids) <= 0:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "관심 팀은 1~5개의 팀 ID로 조회합니다.",
            details={"fields": {"teams": "팀 ID를 확인해 주세요."}},
        )
    state = sync_state(db)
    if state.never_synced:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NOT_COLLECTED)
    known, matches, updated_at = next_for_teams(db, team_ids, datetime.now(UTC))
    lookup = team_detail_lookup(db)
    return FavoriteScheduleResponse(
        data=FavoriteSchedule(teams=[team_ref(t, lookup) for t in known], matches=matches),
        meta=ScheduleMeta(
            updated_at=updated_at, failed_competition_ids=state.failed_competition_ids
        ),
    )


@router.get("/fixtures/team")
def read_team_schedule(
    db: Db, team: Annotated[int, Query(gt=0, description="Team id")]
) -> TeamScheduleResponse:
    """Team view: the team's stored matches today-3 .. today+17 KST.
    Competition filters are applied on screen; `failedCompetitionIds` tells which
    competitions may be incomplete, so "no matches" is never claimed for them."""
    start, end = team_schedule_window()
    state = sync_state(db, window=(start, end))
    if state.never_synced:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NOT_COLLECTED)
    found, matches, updated_at = team_schedule(db, team, start, end)
    if found is None:
        raise ApiError(404, "NOT_FOUND", "팀을 찾을 수 없습니다. 팀 검색으로 다시 선택해 주세요.")
    return TeamScheduleResponse(
        data=TeamSchedule(
            team=team_ref(found, team_detail_lookup(db)), start=start, end=end, matches=matches
        ),
        meta=ScheduleMeta(
            updated_at=updated_at, failed_competition_ids=state.failed_competition_ids
        ),
    )


@router.get("/teams/search")
def read_team_search(
    db: Db,
    q: Annotated[str, Query(min_length=1, max_length=40)],
    season: Annotated[
        int | None,
        Query(ge=1, description="Search that season's teams (past results); default current"),
    ] = None,
) -> TeamSearchResponse:
    if season is not None:
        require_supported_season(db, season)
    return TeamSearchResponse(data=search_teams(db, q, season=season))


@router.get("/news")
def read_news(
    db: Db,
    badge: NewsBadge | None = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    size: Annotated[int, Query(ge=1, le=24)] = 6,
    team: Annotated[
        int | None,
        Query(gt=0, le=2_147_483_647, description="Team news (chat 08): linked articles"),
    ] = None,
) -> NewsResponse:
    """NEWS-001·002: classified Korean articles, newest first; `nextCursor` loads more.
    With `team` (TEAM-004, NEWS-003): the team's linked articles; `badge` still narrows."""
    now = datetime.now(UTC)
    if team is not None and db.get(Team, team) is None:
        raise ApiError(404, "NOT_FOUND", "팀을 찾을 수 없습니다. 팀 탐색에서 다시 선택해 주세요.")
    state = collection_state(db, now)
    never = state.updated_at is None
    if (state.empty_store and (never or state.stale)) or (team is not None and never):
        # Nothing stored and the collection never worked / just failed: not "no news".
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", NEWS_NOT_COLLECTED)
    try:
        items, next_cursor, total = list_news(
            db, now, badge=badge, size=size, cursor=cursor, team=team
        )
    except InvalidCursor:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "더 보기 위치가 올바르지 않습니다. 처음부터 다시 불러와 주세요.",
            details={"fields": {"cursor": "형식이 올바르지 않습니다."}},
        ) from None
    return NewsResponse(
        data=items,
        meta=NewsMeta(
            next_cursor=next_cursor, total=total, updated_at=state.updated_at,
            stale=state.stale, no_new=state.no_new,
        ),
    )


@router.get("/news/{article_id}/link", dependencies=[Depends(news_link_limit)])
def read_news_link(db: Db, article_id: int) -> NewsLinkResponse:
    """NEWS-004: the stored original link and whether it answers right now."""
    article = db.get(NewsArticle, article_id)
    if article is None or article.expires_at <= datetime.now(UTC):
        raise ApiError(404, "NOT_FOUND", "기사를 찾을 수 없습니다. 목록을 새로 불러와 주세요.")
    return NewsLinkResponse(data=NewsLink(url=article.url, status=check_link(article.url)))
