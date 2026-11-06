"""League standings and player rankings (chat 06, LEAG-001·002·004). Served from stored
data only (OPS-001); no request reaches the provider."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.routes.schedule import require_supported_season
from app.config import settings
from app.db.session import get_db
from app.models.reference import Competition
from app.schemas.standings import (
    LeagueStandings,
    PlayerRankings,
    PlayerRankingsResponse,
    PlayerRankItem,
    PlayerRef,
    RankingType,
    StandingGroup,
    StandingRow,
    StandingsMeta,
    StandingsResponse,
    StandingsSummary,
    StandingsSummaryLeague,
    StandingsSummaryResponse,
)
from app.seed.competitions import LEAGUE_IDS
from app.services.reference import DetailLookup, competition_ref, team_detail_lookup, team_ref
from app.services.results import season_item
from app.services.standings import (
    RankedPlayer,
    StandingGroupData,
    league_available,
    league_competitions,
    player_photo,
    read_saves,
    read_standings,
    read_top_list,
    relegation_zone,
    sync_state,
)

router = APIRouter(tags=["standings"])
Db = Annotated[Session, Depends(get_db)]

NOT_A_LEAGUE = "리그 순위를 제공하지 않는 대회입니다. 5대 리그 중에서 선택해 주세요."
NO_SEASON_DATA = "선택한 시즌에는 이 리그의 순위 데이터가 없습니다."
STANDINGS_NOT_COLLECTED = "리그 순위를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
RANKING_NOT_COLLECTED = "선수 순위를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
SUMMARY_ROWS = 6


def _league(db: Session, league: int, season: int) -> Competition:
    """Cups and UEFA competitions have no league table (CMP-002); an unsupported season is
    refused, never replaced (CMP-003)."""
    competition = db.get(Competition, league) if league in LEAGUE_IDS else None
    if competition is None:
        raise ApiError(404, "NOT_FOUND", NOT_A_LEAGUE)
    require_supported_season(db, season)
    if not league_available(db, league, season):
        raise ApiError(404, "NOT_FOUND", NO_SEASON_DATA)
    return competition


def _rows(groups: list[StandingGroupData], lookup: DetailLookup) -> list[StandingGroup]:
    return [
        StandingGroup(
            name=group.name,
            rows=[
                StandingRow(
                    rank=s.rank,
                    team=team_ref(team, lookup),
                    played=s.played,
                    win=s.win,
                    draw=s.draw,
                    lose=s.lose,
                    goals_for=s.goals_for,
                    goals_against=s.goals_against,
                    goals_diff=s.goals_diff,
                    points=s.points,
                    form=s.form,
                    description=s.description,
                    zone=relegation_zone(s.description),
                )
                for s, team in group.rows
            ],
        )
        for group in groups
    ]


@router.get("/standings")
def read_league_standings(
    db: Db,
    league: Annotated[int, Query(gt=0, description="League id (five leagues only)")],
    season: Annotated[int | None, Query(ge=1, description="API season; default current")] = None,
) -> StandingsResponse:
    """LEAG-002: the whole table of one league season as the provider gave it (groups kept).

    Never collected → 503 (not shown as "no table"); a later failed refresh keeps the stored
    table with `refreshFailed`. Team links follow the current-season allow set."""
    season = season or settings.current_season
    competition = _league(db, league, season)
    state = sync_state(db, league, season, "standings")
    if not state.collected:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", STANDINGS_NOT_COLLECTED)
    groups = _rows(read_standings(db, league, season), team_detail_lookup(db))
    return StandingsResponse(
        data=LeagueStandings(
            league=competition_ref(competition), season=season_item(season), groups=groups
        ),
        meta=StandingsMeta(updated_at=state.synced_at, refresh_failed=state.refresh_failed),
    )


@router.get("/standings/summary")
def read_standings_summary(db: Db) -> StandingsSummaryResponse:
    """LEAG-001: the top rows of each five-league table, current season. One league that was
    never collected does not hide the others."""
    season = settings.current_season
    lookup = team_detail_lookup(db)
    leagues = []
    for competition in league_competitions(db):
        state = sync_state(db, competition.id, season, "standings")
        stored = read_standings(db, competition.id, season) if state.collected else []
        groups = _rows(stored, lookup)
        leagues.append(
            StandingsSummaryLeague(
                league=competition_ref(competition),
                status="available" if state.collected else "not_collected",
                refresh_failed=state.refresh_failed,
                updated_at=state.synced_at,
                rows=groups[0].rows[:SUMMARY_ROWS] if groups else [],
            )
        )
    if leagues and all(item.status == "not_collected" for item in leagues):
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", STANDINGS_NOT_COLLECTED)
    return StandingsSummaryResponse(
        data=StandingsSummary(season=season_item(season), leagues=leagues)
    )


def _item(entry: RankedPlayer, lookup: DetailLookup) -> PlayerRankItem:
    return PlayerRankItem(
        rank=entry.rank,
        tied=entry.tied,
        player=PlayerRef(
            id=entry.player.id, name=entry.player.name, photo_url=player_photo(entry.player)
        ),
        team=team_ref(entry.team, lookup) if entry.team is not None else None,
        value=entry.value,
        yellow_red=entry.yellowred,
    )


@router.get("/player-rankings")
def read_player_rankings(
    db: Db,
    league: Annotated[int, Query(gt=0, description="League id (five leagues only)")],
    type: Annotated[RankingType, Query(description="Ranking type")],  # noqa: A002
    season: Annotated[int | None, Query(ge=1, description="API season; default current")] = None,
) -> PlayerRankingsResponse:
    """LEAG-004: goals / assists / yellow / red are the provider's top lists in its order (not
    a full ranking); red counts direct red cards only. Saves are aggregated from every
    player line: goalkeepers with a missing value are excluded (`excluded`), ties share a
    rank."""
    season = season or settings.current_season
    competition = _league(db, league, season)
    kind = "player_stats" if type == "saves" else type
    state = sync_state(db, league, season, kind)
    if not state.collected:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", RANKING_NOT_COLLECTED)
    lookup = team_detail_lookup(db)
    if type == "saves":
        saves = read_saves(db, league, season)
        entries, excluded = saves.items, saves.excluded
    else:
        entries, excluded = read_top_list(db, league, season, type), None
    return PlayerRankingsResponse(
        data=PlayerRankings(
            type=type,
            league=competition_ref(competition),
            season=season_item(season),
            items=[_item(entry, lookup) for entry in entries],
            excluded=excluded,
        ),
        meta=StandingsMeta(updated_at=state.synced_at, refresh_failed=state.refresh_failed),
    )
