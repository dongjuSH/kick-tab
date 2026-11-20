"""Team detail collection (chat 08, guide §6.5).

- team_details (daily 15:00 KST, after the 14:20 player lines): per current five-league team
  /coachs, /players/squads and /teams/statistics of the current season (3 requests), the past
  season's statistics once when the team played that league then, and /players/profiles once
  per squad player whose nationality is missing. 96 teams = 288 requests a day.
- transfers (daily 00:00 KST): /transfers?team= per team (96 a day). A season is refreshed until
  the July 1 00:00 run after it ends (it picks up records added up to June 30) and fixed
  afterwards; a season never stored is stored once.
Each unit runs once per KST day (last try on an earlier KST date), so an off-schedule manual
run never makes the next scheduled run skip a day.

Params: team=50 or league=39 (narrow the run), force=1 (ignore the daily schedule).
Every unit is stored only when its answer is usable; a failed unit keeps its stored rows,
records team_syncs.failed_at and the run ends as a partial failure naming the failed units
after the others are saved (CMP-004). A fatal provider stop (auth, quota, budget) marks the
remaining units failed and ends the run.
"""

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.kst import kst_today
from app.providers.api_football import ApiFootballClient, ApiFootballError
from app.seed.competitions import LEAGUE_IDS
from app.services.reference import managed_seasons
from app.services.standings import IncompleteData
from app.services.team_detail import (
    current_members,
    is_due,
    mark_failure,
    mark_player_season_failure,
    missing_nationalities,
    never_stored,
    parse_player_season,
    parse_profile_nationality,
    parse_squad,
    parse_statistics,
    parse_team_players,
    parse_transfers,
    pending_checks,
    pick_coach,
    played_league,
    record_competitions,
    save_coach,
    save_nationality,
    save_player_season,
    save_squad,
    save_statistics,
    save_team_player_stats,
    save_transfers,
    transfer_seasons,
    unsynced_leagues,
)
from app.sync.reference import FATAL
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)

# (team, seasons, kind, label): one request; every season it writes is marked on failure.
# The prior-club checks use (player, (season,), "player_season", label).
Unit = tuple[int, tuple[int, ...], str, str]
Store = Callable[[Session, datetime], None]
Mark = Callable[[Session, Unit, datetime, str], None]


def _mark_team_unit(session: Session, unit: Unit, now: datetime, reason: str) -> None:
    team, seasons, kind, _ = unit
    for season in seasons:
        mark_failure(session, team, season, kind, now, reason)


def _forced(params: Mapping[str, Any]) -> bool:
    return str(params.get("force", "")).lower() in ("1", "true", "yes")


def _teams(session: Session, params: Mapping[str, Any]) -> dict[int, int]:
    """team -> league of the members this run covers (team= / league= narrow it)."""
    members = current_members(session)
    if params.get("team") is not None:
        team = int(params["team"])
        if team not in members:
            raise JobPartialFailure(f"Team {team} is not a current five-league member")
        return {team: members[team]}
    if params.get("league") is not None:
        league = int(params["league"])
        if league not in LEAGUE_IDS:
            raise JobPartialFailure(f"League {league} is not one of the five leagues")
        return {t: lg for t, lg in members.items() if lg == league}
    return members


def _ordered(teams: Mapping[int, int]) -> list[tuple[int, int]]:
    return sorted(teams.items(), key=lambda item: (LEAGUE_IDS.index(item[1]), item[0]))


def _run_units(
    ctx: JobContext,
    units: list[Unit],
    fetch: Callable[[ApiFootballClient, Unit], Store],
    mark: Mark = _mark_team_unit,
) -> tuple[list[str], bool]:
    """Fetch, parse and store each unit in its own transaction. Returns failed labels and
    whether a fatal provider stop ended the run (every remaining unit is marked failed)."""
    session = ctx.session
    client = ctx.api_football()
    failed: list[str] = []
    for index, unit in enumerate(units):
        try:
            store = fetch(client, unit)
            store(session, datetime.now(UTC))
            session.commit()
            continue
        except ApiFootballError as exc:
            reason, fatal = type(exc).__name__, isinstance(exc, FATAL)
        except IncompleteData as exc:
            reason, fatal = f"IncompleteData: {exc}", False
        except SQLAlchemyError as exc:
            reason, fatal = type(exc).__name__, False
        session.rollback()
        now = datetime.now(UTC)
        for failed_unit in units[index:] if fatal else [unit]:
            mark(session, failed_unit, now, reason)
            failed.append(failed_unit[3])
        session.commit()
        logger.warning("%s failed: %s", unit[3], reason)
        if fatal:
            return failed, True
    return failed, False


def _details_units(session: Session, params: Mapping[str, Any], now: datetime) -> list[Unit]:
    current = settings.current_season
    previous = current - 1
    force = _forced(params)
    units: list[Unit] = []
    for team, league in _ordered(_teams(session, params)):
        for kind in ("coach", "squad", "statistics"):
            if force or is_due(session, team, current, kind, now):
                units.append((team, (current,), kind, f"{kind}:{team}"))
        # The past season is over: stored once, only if the team played this league then.
        if (
            previous in managed_seasons()
            and played_league(session, team, league, previous)
            and never_stored(session, team, previous, "statistics")
            and (force or is_due(session, team, previous, "statistics", now))
        ):
            units.append((team, (previous,), "statistics", f"statistics:{team}:{previous}"))
    return units


def _details_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    try:
        return bool(_details_units(session, params, datetime.now(UTC)))
    except (JobPartialFailure, ValueError):
        return True  # a bad parameter is recorded by the run itself


@register_job(
    "team_details",
    description="Coach, squad and league season statistics per five-league team (3/team/day)",
    schedule={"trigger": "cron", "hour": 6, "minute": 0},  # 15:00 KST
    precheck=_details_precheck,
)
def sync_team_details(ctx: JobContext) -> None:
    session = ctx.session
    failed = [f"members:{league}" for league in unsynced_leagues(session)]
    teams = _teams(session, ctx.params)
    units = _details_units(session, ctx.params, datetime.now(UTC))

    def fetch(client: ApiFootballClient, unit: Unit) -> Store:
        team, (season,), kind, _ = unit
        if kind == "coach":
            answer = client.get("/coachs", {"team": team}).response
            coach = pick_coach(answer, team, kst_today())
            return lambda s, now: save_coach(s, team, coach, now)
        if kind == "squad":
            squad = parse_squad(client.get("/players/squads", {"team": team}).response, team)
            return lambda s, now: save_squad(s, team, squad, now)
        league = teams[team]
        params = {"team": team, "league": league, "season": season}
        payload = parse_statistics(
            client.get("/teams/statistics", params).response, team, league, season
        )
        return lambda s, now: save_statistics(s, team, league, season, payload, now)

    unit_failures, stopped = _run_units(ctx, units, fetch)
    failed += unit_failures
    if not stopped:
        failed += _supplement_nationalities(ctx, list(teams))
    if failed:
        raise JobPartialFailure(f"Failed: {', '.join(failed[:40])}" + (
            f" (+{len(failed) - 40})" if len(failed) > 40 else ""
        ))


def _supplement_nationalities(ctx: JobContext, team_ids: list[int]) -> list[str]:
    """TEAM-002: one /players/profiles lookup per squad player without a nationality. A
    failed lookup is retried on the next run (the player is not marked as checked)."""
    session = ctx.session
    client = ctx.api_football()
    failed: list[str] = []
    for player_id in missing_nationalities(session, team_ids):
        try:
            result = client.get("/players/profiles", {"player": player_id})
            nationality = parse_profile_nationality(result.response, player_id)
        except FATAL as exc:
            failed.append(f"profiles:stopped:{type(exc).__name__}")
            break
        except (ApiFootballError, IncompleteData) as exc:
            failed.append(f"profile:{player_id}:{type(exc).__name__}")
            continue
        save_nationality(session, player_id, nationality, datetime.now(UTC))
        session.commit()
    return failed


def _transfer_units(session: Session, params: Mapping[str, Any], now: datetime) -> list[Unit]:
    force = _forced(params)
    today = kst_today(now)
    units: list[Unit] = []
    for team, _ in _ordered(_teams(session, params)):
        seasons = transfer_seasons(session, team, today)
        if not seasons:
            continue
        due = force or any(is_due(session, team, s, "transfers", now) for s in seasons)
        if due:
            units.append((team, tuple(seasons), "transfers", f"transfers:{team}"))
    return units


def _transfers_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    try:
        return bool(_transfer_units(session, params, datetime.now(UTC)))
    except (JobPartialFailure, ValueError):
        return True


@register_job(
    "transfers",
    description="Transfers per five-league team, classified into season halves (1/team/day)",
    schedule={"trigger": "cron", "hour": 15, "minute": 0},  # 00:00 KST
    precheck=_transfers_precheck,
)
def sync_transfers(ctx: JobContext) -> None:
    session = ctx.session
    failed = [f"members:{league}" for league in unsynced_leagues(session)]
    now = datetime.now(UTC)
    units = _transfer_units(session, ctx.params, now)
    today = kst_today(now)

    def fetch(client: ApiFootballClient, unit: Unit) -> Store:
        team, seasons, _, _ = unit
        rows = parse_transfers(client.get("/transfers", {"team": team}).response, team, today)

        def store(s: Session, at: datetime) -> None:
            for season in seasons:
                save_transfers(s, team, season, [r for r in rows if r["season"] == season], at)

        return store

    unit_failures, _ = _run_units(ctx, units, fetch)
    failed += unit_failures
    if failed:
        raise JobPartialFailure(f"Failed: {', '.join(failed[:40])}" + (
            f" (+{len(failed) - 40})" if len(failed) > 40 else ""
        ))


# Past seasons kept for the squad (last season) and as appearance evidence for the moves of
# the managed seasons (2026-11-20: the season before last too, e.g. 2024 for 2025-26 moves).
PLAYER_PAST_SEASONS = 2


def _player_units(session: Session, params: Mapping[str, Any], now: datetime) -> list[Unit]:
    """The current season once a KST day; each past season (over) until stored once.
    `season=` narrows the run to one of those seasons; with `force=1` that season is fetched
    again even when it was stored (e.g. after the competition scope changed)."""
    current = settings.current_season
    seasons = [current - back for back in range(PLAYER_PAST_SEASONS + 1)]
    if params.get("season") is not None:
        asked = int(params["season"])
        if asked not in seasons:
            raise ValueError(f"season must be one of {seasons}")
        seasons = [asked]
    force = _forced(params)
    units: list[Unit] = []
    for team, _ in _ordered(_teams(session, params)):
        for season in seasons:
            wanted = season == current or never_stored(session, team, season, "player_stats")
            if force or (wanted and is_due(session, team, season, "player_stats", now)):
                label = f"player_stats:{team}" + ("" if season == current else f":{season}")
                units.append((team, (season,), "player_stats", label))
    return units


def _players_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    try:
        return bool(_player_units(session, params, datetime.now(UTC)))
    except (JobPartialFailure, ValueError):
        return True


@register_job(
    "team_player_stats",
    description=(
        "Team player records in the supported competitions (all /players?team=&season= pages)"
    ),
    schedule={"trigger": "cron", "hour": 6, "minute": 30},  # 15:30 KST
    precheck=_players_precheck,
)
def sync_team_player_stats(ctx: JobContext) -> None:
    """TEAM-002: every page of /players?team=&season= (about 3 a team), one listing per player,
    this team's lines in the supported competitions held that season (`record_competitions`,
    2026-11-20: domestic cups, super cups and the Club World Cup included)."""
    session = ctx.session
    failed = [f"members:{league}" for league in unsynced_leagues(session)]
    units = _player_units(session, ctx.params, datetime.now(UTC))
    scopes = {season: record_competitions(session, season) for _, (season,), _, _ in units}

    def fetch(client: ApiFootballClient, unit: Unit) -> Store:
        team, (season,), _, _ = unit
        params = {"team": team, "season": season}
        first = client.get("/players", {**params, "page": 1})
        pages = [{"response": first.response, "paging": first.paging}]
        total = int((first.paging or {}).get("total") or 0)
        for page in range(2, total + 1):
            result = client.get("/players", {**params, "page": page})
            pages.append({"response": result.response, "paging": result.paging})
        parsed = parse_team_players(pages, team, season, scopes[season])
        return lambda s, now: save_team_player_stats(s, team, season, parsed, now)

    unit_failures, _ = _run_units(ctx, units, fetch)
    failed += unit_failures
    if failed:
        raise JobPartialFailure(f"Failed: {', '.join(failed[:40])}" + (
            f" (+{len(failed) - 40})" if len(failed) > 40 else ""
        ))


# Prior-club checks per run (TEAM-006 rule 6): the first backlog (thousands of signings) is
# spread over several days inside the daily budget; afterwards only new signings remain.
PLAYER_CHECKS_PER_RUN = 1500


def _check_units(session: Session, params: Mapping[str, Any]) -> list[Unit]:
    limit = int(params.get("limit") or PLAYER_CHECKS_PER_RUN)
    if limit < 1:
        raise ValueError("limit must be positive")
    pending = pending_checks(session, (team for team, _ in _ordered(_teams(session, params))))
    return [
        (player, (season,), "player_season", f"player_season:{player}:{season}")
        for player, season in pending[:limit]
    ]


def _mark_check_unit(session: Session, unit: Unit, now: datetime, reason: str) -> None:
    player, (season,), _, _ = unit
    mark_player_season_failure(session, player, season, now, reason)


def _checks_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    try:
        return bool(_check_units(session, {**params, "limit": 1}))
    except (JobPartialFailure, ValueError):
        return True


@register_job(
    "transfer_player_checks",
    description="First-team appearances of signings at the club they came from (/players?id=)",
    schedule={"trigger": "cron", "hour": 15, "minute": 40},  # 00:40 KST, after transfers
    precheck=_checks_precheck,
)
def sync_transfer_player_checks(ctx: JobContext) -> None:
    """TEAM-006 rule 6 (2026-11-20): for each signing of the managed seasons that still waits
    for evidence (`check_pending`), one /players?id=&season= request for the season of the
    club he came from (`check_season`); the first-team appearances per club are stored
    (`player_club_seasons`) and the player-season is never asked again. A failed request is
    asked again on a later run. At most `limit` (default PLAYER_CHECKS_PER_RUN) a run;
    `team=`/`league=` narrow the signings."""
    session = ctx.session
    units = _check_units(session, ctx.params)

    def fetch(client: ApiFootballClient, unit: Unit) -> Store:
        player, (season,), _, _ = unit
        result = client.get("/players", {"id": player, "season": season})
        total = int((result.paging or {}).get("total") or 1)
        if total > 1:
            raise IncompleteData(f"player season: {total} pages")
        clubs = parse_player_season(result.response, player, season)
        return lambda s, now: save_player_season(s, player, season, clubs, now)

    failed, _ = _run_units(ctx, units, fetch, _mark_check_unit)
    if failed:
        raise JobPartialFailure(f"Failed: {', '.join(failed[:40])}" + (
            f" (+{len(failed) - 40})" if len(failed) > 40 else ""
        ))
