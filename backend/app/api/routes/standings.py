"""League standings, UEFA league phases and knockouts, player rankings (chat 06,
LEAG-001·002·004). Served from stored data only (OPS-001); no request reaches the provider."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.routes.schedule import require_supported_season
from app.config import settings
from app.db.session import get_db
from app.models.reference import Competition, CompetitionSeason, Team
from app.models.standings import Standing
from app.schemas.standings import (
    KnockoutLeg,
    KnockoutRound,
    KnockoutsResponse,
    KnockoutStage,
    KnockoutTeamSlot,
    KnockoutTie,
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
    TableRow,
    TeamName,
)
from app.schemas.standings import RecentMatch as RecentMatchItem
from app.seed.competitions import LEAGUE_IDS, UEFA_IDS
from app.services.fixtures import _score
from app.services.knockouts import Slot, Tie, build_stage
from app.services.match_status import map_status
from app.services.reference import DetailLookup, competition_ref, team_detail_lookup, team_ref
from app.services.results import season_coverage, season_item
from app.services.standings import (
    STANDINGS_IDS,
    RankedPlayer,
    RecentMatch,
    StandingGroupData,
    league_available,
    league_competitions,
    player_photo,
    read_saves,
    read_standings,
    read_top_list,
    recent_matches,
    sync_state,
    table_complete,
)

router = APIRouter(tags=["standings"])
Db = Annotated[Session, Depends(get_db)]

NOT_A_LEAGUE = "순위를 제공하지 않는 대회입니다. 5대 리그나 UEFA 대회 중에서 선택해 주세요."
NOT_UEFA = "토너먼트 대진은 UEFA 대회만 제공합니다."
NO_PLAYER_RANKINGS = "선수 순위는 5대 리그만 제공합니다."
FIXTURES_NOT_COLLECTED = "대진을 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
NO_SEASON_DATA = "선택한 시즌에는 이 리그의 순위 데이터가 없습니다."
STANDINGS_NOT_COLLECTED = "리그 순위를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
RANKING_NOT_COLLECTED = "선수 순위를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
SUMMARY_ROWS = 6


def _league(
    db: Session, league: int, season: int, scope: tuple[int, ...] = STANDINGS_IDS,
    message: str = NOT_A_LEAGUE,
) -> Competition:
    """Domestic cups have no table (CMP-002); the UEFA competitions have their league phase.
    An unsupported season is refused, never replaced (CMP-003)."""
    competition = db.get(Competition, league) if league in scope else None
    if competition is None:
        raise ApiError(404, "NOT_FOUND", message)
    require_supported_season(db, season)
    if not league_available(db, league, season):
        raise ApiError(404, "NOT_FOUND", NO_SEASON_DATA)
    return competition


def _row(s: Standing, team: Team, lookup: DetailLookup) -> StandingRow:
    return StandingRow(
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
    )


def _name(team: Team) -> TeamName:
    return TeamName(id=team.id, name_ko=team.name_ko, name_en=team.name_en)


def _recent(match: RecentMatch) -> RecentMatchItem:
    f = match.fixture
    return RecentMatchItem(
        fixture_id=f.id,
        kickoff_at=f.kickoff_at,
        kickoff_date_kst=f.kickoff_date_kst,
        home=_name(match.home),
        away=_name(match.away),
        goals_home=f.goals_home,
        goals_away=f.goals_away,
        result=match.result,
    )


def _groups(
    groups: list[StandingGroupData], lookup: DetailLookup, recent: dict[int, list[RecentMatch]]
) -> list[StandingGroup]:
    return [
        StandingGroup(
            name=group.name,
            rows=[
                TableRow(
                    **_row(s, team, lookup).model_dump(),
                    recent=[_recent(m) for m in recent.get(team.id, [])],
                )
                for s, team in group.rows
            ],
        )
        for group in groups
    ]


@router.get("/standings")
def read_league_standings(
    db: Db,
    league: Annotated[
        int, Query(gt=0, description="Five leagues, or UEFA 2·3·848 (league phase table)")
    ],
    season: Annotated[int | None, Query(ge=1, description="API season; default current")] = None,
) -> StandingsResponse:
    """LEAG-002: the whole table of one league season or UEFA league phase as the provider
    gave it (groups and order kept), each row with its last 5 finished matches of that table
    from stored fixtures (UEFA: league-phase matches only).

    Never collected → 503 (not shown as "no table"); a later failed refresh keeps the stored
    table with `refreshFailed`. Team links follow the current-season allow set. Zones are
    drawn by position on screen; `complete` tells current positions from final results."""
    season = season or settings.current_season
    competition = _league(db, league, season)
    state = sync_state(db, league, season, "standings")
    if not state.collected:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", STANDINGS_NOT_COLLECTED)
    groups = _groups(
        read_standings(db, league, season),
        team_detail_lookup(db),
        recent_matches(db, league, season),
    )
    return StandingsResponse(
        data=LeagueStandings(
            league=competition_ref(competition),
            season=season_item(season),
            groups=groups,
            complete=table_complete(db, league, season),
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
        rows = [_row(s, team, lookup) for s, team in stored[0].rows] if stored else []
        leagues.append(
            StandingsSummaryLeague(
                league=competition_ref(competition),
                status="available" if state.collected else "not_collected",
                refresh_failed=state.refresh_failed,
                updated_at=state.synced_at,
                rows=rows[:SUMMARY_ROWS],
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
    competition = _league(db, league, season, LEAGUE_IDS, NO_PLAYER_RANKINGS)
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


def _slot(slot: Slot, lookup: DetailLookup) -> KnockoutTeamSlot:
    feeder = slot.winner_of
    return KnockoutTeamSlot(
        team=team_ref(slot.team, lookup) if slot.team is not None else None,
        winner_of=(
            [team_ref(s.team, lookup) for s in (feeder.home, feeder.away) if s.team is not None]
            if feeder is not None
            else None
        ),
    )


def _tie(tie: Tie, lookup: DetailLookup) -> KnockoutTie:
    return KnockoutTie(
        state=tie.state,
        home=_slot(tie.home, lookup),
        away=_slot(tie.away, lookup),
        legs=[
            KnockoutLeg(
                fixture_id=leg.fixture.id,
                leg=number + 1 if len(tie.legs) == tie.legs_needed else None,
                kickoff_at=leg.fixture.kickoff_at,
                time_confirmed=map_status(leg.fixture.status_short_raw).time_confirmed,
                status=leg.fixture.status,
                finish_type=leg.fixture.finish_type,
                home=team_ref(leg.home, lookup),
                away=team_ref(leg.away, lookup),
                score=_score(leg.fixture),
            )
            for number, leg in enumerate(tie.legs)
        ],
        legs_needed=tie.legs_needed,
        aggregate_home=tie.aggregate_home,
        aggregate_away=tie.aggregate_away,
        penalty_home=tie.penalty_home,
        penalty_away=tie.penalty_away,
        winner=team_ref(tie.winner, lookup) if tie.winner is not None else None,
    )


@router.get("/knockouts")
def read_knockouts(
    db: Db,
    league: Annotated[int, Query(gt=0, description="UEFA competition id (2, 3, 848)")],
    stage: Annotated[KnockoutStage, Query(description="Knockout stage")],
    season: Annotated[int | None, Query(ge=1, description="API season; default current")] = None,
) -> KnockoutsResponse:
    """LEAG-002 rule 7: the ties of one UEFA knockout stage built from stored fixtures — legs,
    aggregate, shoot-out and winner; "A–B전 승자" only for a path stored matches fix; the rest
    "예정 · 대진 미정". The season list never loaded → 503; a later failed refresh keeps the
    stored ties with `refreshFailed`."""
    season = season or settings.current_season
    competition = _league(db, league, season, UEFA_IDS, NOT_UEFA)
    coverage = season_coverage(db, season)
    if league in coverage.never_loaded_ids:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", FIXTURES_NOT_COLLECTED)
    state = db.get(CompetitionSeason, (league, season))
    lookup = team_detail_lookup(db)
    return KnockoutsResponse(
        data=KnockoutRound(
            league=competition_ref(competition),
            season=season_item(season),
            stage=stage,
            ties=[_tie(tie, lookup) for tie in build_stage(db, league, season, stage)],
        ),
        meta=StandingsMeta(
            updated_at=state.season_fixtures_synced_at if state else None,
            refresh_failed=league in coverage.failed_ids,
        ),
    )
