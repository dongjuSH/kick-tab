"""Team browse (chat 07, LEAG-003) and team detail (chat 08, TEAM-001~006).

Served from stored data only (no provider request). Each detail area has its own endpoint
so one failing area never hides the others.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import settings
from app.core.kst import kst_date, kst_today
from app.db.session import get_db
from app.models.reference import Competition, Team
from app.models.team_detail import TeamCoach, Transfer
from app.providers.api_football import ApiFootballClient
from app.schemas.standings import RecentMatch, TeamName
from app.schemas.team_detail import (
    CoachBlock,
    CoachInfo,
    HomeAway,
    SquadCompetitionLine,
    SquadPlayer,
    SquadPlayerRef,
    SquadTotals,
    StandingBlock,
    TeamFixtures,
    TeamFixturesMeta,
    TeamFixturesResponse,
    TeamOverview,
    TeamOverviewResponse,
    TeamSeasonRecord,
    TeamSeasonStats,
    TeamSeasonStatsResponse,
    TeamSquad,
    TeamSquadResponse,
    TeamStanding,
    TeamSyncMeta,
    TeamTransfers,
    TeamTransfersResponse,
    TransferCounterpart,
    TransferGroup,
    TransferHalf,
    TransferItem,
    VenueBlock,
    VenueInfo,
)
from app.schemas.teams import BrowseTeam, TeamsMeta, TeamsResponse
from app.seed.competitions import LEAGUE_IDS
from app.services import team_detail as detail
from app.services.head_to_head import competition_names, ensure_form, result_for, team_names
from app.services.reference import competition_ref, crest, team_detail_lookup, team_ref
from app.services.results import season_item
from app.services.team_browse import PAGE_SIZE, MembershipUnknown, browse_teams
from app.services.team_detail import flag_url

router = APIRouter(tags=["teams"])
Db = Annotated[Session, Depends(get_db)]
# Team ids are 32-bit provider ids: a larger number is no team (422), never a DB error.
TeamId = Annotated[int, Path(gt=0, le=2_147_483_647, description="Team id")]

NOT_A_LEAGUE = "팀 탐색을 제공하지 않는 리그입니다. 5대 리그 중에서 선택해 주세요."
MEMBERSHIP_UNKNOWN = "현재 시즌 소속 팀을 확인하지 못했습니다. 잠시 후 다시 확인해 주세요."
TEAM_NOT_FOUND = "팀을 찾을 수 없습니다. 팀 탐색에서 다시 선택해 주세요."
DETAIL_UNAVAILABLE = (
    "현재 시즌 5대 리그 소속 팀만 팀 상세를 제공합니다. "
    "지난 경기와 경기 상세는 계속 볼 수 있습니다."
)
SeasonParam = Annotated[
    int | None, Query(description="This or the last season; default this season")
]
UNSUPPORTED_SEASON = "이번 시즌과 지난 시즌만 조회할 수 있습니다."


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
    team: Annotated[
        int | None,
        Query(gt=0, le=2_147_483_647, description="Only this team (a picked search candidate)"),
    ] = None,
) -> TeamsResponse:
    """LEAG-003: current-season members of the five leagues, 12 per page.

    Unknown membership (a league's team list never collected) is 503, never a short or empty
    list. No match is an empty list with total 0; no other team is offered instead. `team`
    keeps only that member (the search's picked candidate; `q` is then not used)."""
    if league is not None and league not in LEAGUE_IDS:
        raise ApiError(404, "NOT_FOUND", NOT_A_LEAGUE)
    try:
        result = browse_teams(db, league=league, query=q, page=page, team_id=team)
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


# ---------------------------------------------------------------- team detail (chat 08)


def _access(db: Session, team_id: int) -> detail.TeamAccess:
    """Direct URLs use the same allow set as every team link (D-15) and team browse."""
    try:
        return detail.detail_access(db, team_id)
    except detail.TeamNotFound:
        raise ApiError(404, "NOT_FOUND", TEAM_NOT_FOUND) from None
    except detail.DetailUnavailable:
        raise ApiError(404, "TEAM_DETAIL_UNAVAILABLE", DETAIL_UNAVAILABLE) from None
    except detail.MembershipUnknown:
        raise ApiError(503, "MEMBERSHIP_UNKNOWN", MEMBERSHIP_UNKNOWN) from None


def _season(season: int | None) -> int:
    """This season and the last one only (TEAM-005·006 이번/지난 시즌); never another."""
    current = settings.current_season
    season = current if season is None else season
    if season not in (current, current - 1):
        raise ApiError(404, "NOT_FOUND", UNSUPPORTED_SEASON)
    return season


def _not_collected(area: str) -> ApiError:
    message = f"{area} 정보를 아직 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
    return ApiError(503, "UPSTREAM_UNAVAILABLE", message)


@router.get("/teams/{team_id}")
def read_team(db: Db, team_id: TeamId) -> TeamOverviewResponse:
    """TEAM-001: identity, league standing, coach, venue and the last five official results.
    The results come from the team's official matches cached for head-to-head (`team_forms`,
    friendlies excluded, 06 개선 2026-11-20): read again from the provider only when a newer
    stored result exists or the list is 7 days old (1 request, 2 when widened; a failure keeps
    the last list and waits 5 minutes). Never read → the stored supported-competition matches.
    A missing part is marked on its own and never hides the rest of the page."""
    access = _access(db, team_id)
    league_id = access.league.id
    team, season = access.team, settings.current_season

    if not detail.standings_collected(db, league_id, season):
        standing = StandingBlock(status="unavailable", data=None)
    else:
        row = detail.read_standing(db, team_id, league_id, season)
        standing = (
            StandingBlock(status="available", data=TeamStanding(rank=row.rank, points=row.points))
            if row else StandingBlock(status="not_provided", data=None)
        )

    coach_row = db.get(TeamCoach, team_id)
    if coach_row is None:
        coach = CoachBlock(status="unavailable", data=None)
    elif coach_row.name is None:
        coach = CoachBlock(status="not_provided", data=None)
    else:
        coach = CoachBlock(
            status="available",
            data=CoachInfo(name=coach_row.name),
        )

    venue = (
        VenueBlock(
            status="available",
            data=VenueInfo(name=team.venue_name, capacity=team.venue_capacity),
        )
        if team.venue_name or team.venue_capacity
        else VenueBlock(status="not_provided", data=None)
    )
    return TeamOverviewResponse(
        data=TeamOverview(
            team=team_ref(team, team_detail_lookup(db)),
            league=competition_ref(access.league),
            season=season_item(season),
            standing=standing,
            coach=coach,
            venue=venue,
            recent=_recent(db, team_id),
        )
    )


def _team_name(team: Team) -> TeamName:
    return TeamName(id=team.id, name_ko=team.name_ko, name_en=team.name_en)


def _recent(db: Session, team_id: int) -> list[RecentMatch]:
    """The last five official results, oldest first (see `read_team`)."""
    ensure_form(db, team_id, datetime.now(UTC), ApiFootballClient)
    form = detail.official_form(db, team_id)
    if form is None:
        return [
            RecentMatch(
                fixture_id=r.fixture.id,
                kickoff_at=r.fixture.kickoff_at,
                kickoff_date_kst=r.fixture.kickoff_date_kst,
                competition=r.competition.name_ko or r.competition.short_name,
                home=_team_name(r.home),
                away=_team_name(r.away),
                goals_home=r.fixture.goals_home,
                goals_away=r.fixture.goals_away,
                result=r.result,
            )
            for r in detail.recent_results(db, team_id)
        ]
    leagues, names = competition_names(db), team_names(db, [form])
    items = []
    for r in form:
        kickoff = datetime.fromisoformat(r["kickoffAt"])
        items.append(
            RecentMatch(
                fixture_id=r["fixtureId"],
                kickoff_at=kickoff,
                kickoff_date_kst=kst_date(kickoff),
                competition=leagues.get(r.get("leagueId")) or r.get("leagueName") or "—",
                home=TeamName(
                    id=r["homeId"], name_ko=names.get(r["homeId"]), name_en=r["homeName"] or "—"
                ),
                away=TeamName(
                    id=r["awayId"], name_ko=names.get(r["awayId"]), name_en=r["awayName"] or "—"
                ),
                goals_home=r["goalsHome"],
                goals_away=r["goalsAway"],
                result=result_for(r, team_id),
            )
        )
    return items


@router.get("/teams/{team_id}/fixtures")
def read_team_fixtures(db: Db, team_id: TeamId) -> TeamFixturesResponse:
    """TEAM-003: up to three upcoming (live first) and the last five results of the current
    season, from the stored season schedule of every supported competition."""
    _access(db, team_id)
    failed = detail.season_fixture_failures(db, team_id)
    upcoming, recent, updated = detail.team_fixtures(db, team_id, datetime.now(UTC))
    if not upcoming and not recent and detail.season_never_loaded(db):
        raise _not_collected("경기")
    return TeamFixturesResponse(
        data=TeamFixtures(upcoming=upcoming, recent=recent),
        meta=TeamFixturesMeta(updated_at=updated, failed_competition_ids=failed),
    )


@router.get("/teams/{team_id}/squad")
def read_team_squad(db: Db, team_id: TeamId) -> TeamSquadResponse:
    """TEAM-002: the current squad, one row per player, with the sum of the player's lines
    for this team this season in the competitions held this season (`record_competitions`,
    2026-11-20: domestic cups, super cups, UEFA and the Club World Cup included) and each line
    on its own. Missing values are null (shown as '—'), never 0; a played competition without
    collected lines makes the totals partial."""
    _access(db, team_id)
    season = settings.current_season
    synced, squad_failed = detail.sync_meta(db, team_id, season, "squad")
    if synced is None:
        raise _not_collected("선수단")
    _, lines_failed = detail.sync_meta(db, team_id, season, "player_stats")
    players = [
        SquadPlayer(
            player=SquadPlayerRef(
                id=row.player.id,
                name=detail.display_text(row.player.name),
                photo_url=crest(row.player.photo_url),
            ),
            number=row.member.number,
            position=row.member.position,
            nationality=row.player.nationality,
            flag_url=crest(flag_url(row.player.nationality)),
            totals=_totals([line for line, _ in row.lines]) if row.lines else None,
            competitions=[
                SquadCompetitionLine(
                    competition=competition_ref(competition),
                    appearances=line.appearances,
                    goals=line.goals,
                    assists=line.assists,
                    rating=line.rating,
                )
                for line, competition in row.lines
            ],
        )
        for row in detail.read_squad(db, team_id)
    ]
    missing = detail.missing_record_competitions(db, team_id)
    names = {c.id: c for c in db.scalars(select(Competition).where(Competition.id.in_(missing)))}
    return TeamSquadResponse(
        data=TeamSquad(
            season=season_item(season),
            players=players,
            missing_competitions=[competition_ref(names[c]) for c in missing if c in names],
        ),
        meta=TeamSyncMeta(updated_at=synced, refresh_failed=squad_failed or lines_failed),
    )


def _totals(lines: list[Any]) -> SquadTotals:
    """Sum per value over the player's competition lines; a missing value in any line makes that
    total unknown (null), never a smaller number."""

    def total(key: str) -> int | None:
        values = [getattr(line, key) for line in lines]
        return None if any(v is None for v in values) else sum(values)

    return SquadTotals(
        appearances=total("appearances"), goals=total("goals"), assists=total("assists")
    )


def _home_away(block: Any) -> HomeAway:
    block = block if isinstance(block, dict) else {}

    def value(key: str) -> int | None:
        item = block.get(key)
        return item if isinstance(item, int) and not isinstance(item, bool) else None

    return HomeAway(home=value("home"), away=value("away"), total=value("total"))


def _record(payload: dict[str, Any]) -> TeamSeasonRecord:
    fixtures = payload.get("fixtures") or {}
    goals = payload.get("goals") or {}
    lineups = [
        item for item in payload.get("lineups") or []
        if isinstance(item, dict) and item.get("formation")
    ]
    # The provider lists formations by use; the most played one is the main formation.
    main = max(lineups, key=lambda item: item.get("played") or 0, default=None)
    return TeamSeasonRecord(
        wins=_home_away(fixtures.get("wins")),
        draws=_home_away(fixtures.get("draws")),
        loses=_home_away(fixtures.get("loses")),
        goals_for=_home_away((goals.get("for") or {}).get("total")),
        goals_against=_home_away((goals.get("against") or {}).get("total")),
        clean_sheets=_home_away(payload.get("clean_sheet")),
        formation=main["formation"] if main else None,
    )


@router.get("/teams/{team_id}/season-stats")
def read_team_season_stats(
    db: Db, team_id: TeamId, season: SeasonParam = None
) -> TeamSeasonStatsResponse:
    """TEAM-005: the team's league record of one season. A season the team did not play in
    this league (promoted team) is `not_participated`; a season without a record is
    `not_provided` — never filled from another season."""
    access = _access(db, team_id)
    season = _season(season)
    league = access.league.id
    standing_row = detail.read_standing(db, team_id, league, season)
    standing = (
        TeamStanding(rank=standing_row.rank, points=standing_row.points) if standing_row else None
    )
    base = {"season": season_item(season), "league": competition_ref(access.league)}
    if season != settings.current_season and not detail.played_league(db, team_id, league, season):
        return TeamSeasonStatsResponse(
            data=TeamSeasonStats(**base, status="not_participated", record=None, standing=None),
            meta=TeamSyncMeta(updated_at=None, refresh_failed=False),
        )
    synced, refresh_failed = detail.sync_meta(db, team_id, season, "statistics")
    if synced is None:
        raise _not_collected("시즌 기록")
    row = detail.read_season_stat(db, team_id, league, season)
    return TeamSeasonStatsResponse(
        data=TeamSeasonStats(
            **base,
            status="available" if row else "not_provided",
            record=_record(row.payload) if row else None,
            standing=standing,
        ),
        meta=TeamSyncMeta(updated_at=synced, refresh_failed=refresh_failed),
    )


HALF_NAMES = {1: ("first", "전반기", "6~12월"), 2: ("second", "후반기", "1~5월")}


@router.get("/teams/{team_id}/transfers")
def read_team_transfers(
    db: Db, team_id: TeamId, season: SeasonParam = None
) -> TeamTransfersResponse:
    """TEAM-006: arrivals and departures of one season in its two halves (by transfer date).
    The provider's repeated entries are merged into one move (`merge_transfers`, D-08-6); a
    player's moves in one half are one row (`group_moves`). Rows with first-team evidence or
    an undecided move are shown first (`judge_move`, TEAM-006 rule 6); rows confirmed without
    appearances are kept in the "other" lists. A half that has not begun is `not_started`."""
    _access(db, team_id)
    season = _season(season)
    synced, refresh_failed = detail.sync_meta(db, team_id, season, "transfers")
    if synced is None:
        raise _not_collected("이적")
    today = kst_today()
    rows = detail.merge_transfers(detail.read_transfers(db, team_id, season))
    evidence = detail.move_evidence(db, team_id, season, rows)
    known = detail.counterpart_names(db, (r.counterpart_id for r in rows))
    short = f"{season % 100:02d}-{(season + 1) % 100:02d}"

    def item(r: Transfer) -> TransferItem:
        club = known.get(r.counterpart_id) if r.counterpart_id else None
        return TransferItem(
            transfer_date=r.transfer_date,
            direction=r.direction,
            counterpart=TransferCounterpart(
                id=r.counterpart_id,
                name=(
                    club.name_ko if club and club.name_ko
                    else detail.display_text(r.counterpart_name)
                ),
            ),
            type=r.type_raw,
        )

    halves = []
    for half in (1, 2):
        start, _ = detail.half_range(season, half)
        key, word, months = HALF_NAMES[half]
        groups: dict[tuple[bool, str], list[TransferGroup]] = {
            (shown, direction): [] for shown in (True, False) for direction in ("in", "out")
        }
        for group in detail.group_moves([r for r in rows if r.half == half], evidence):
            groups[(group.shown, group.direction)].append(
                TransferGroup(
                    player_id=group.player_id,
                    player_name=detail.display_text(group.moves[-1].player_name),
                    moves=[item(m) for m in group.moves],
                )
            )
        halves.append(
            TransferHalf(
                half=key,
                label=f"{short} {word}",
                period=f"{start.year}년 {months}",
                state="not_started" if today < start else "open",
                arrivals=groups[(True, "in")],
                departures=groups[(True, "out")],
                other_arrivals=groups[(False, "in")],
                other_departures=groups[(False, "out")],
            )
        )
    return TeamTransfersResponse(
        data=TeamTransfers(season=season_item(season), halves=halves),
        meta=TeamSyncMeta(updated_at=synced, refresh_failed=refresh_failed),
    )
