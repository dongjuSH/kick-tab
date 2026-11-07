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
    missing_nationalities,
    never_stored,
    parse_profile_nationality,
    parse_squad,
    parse_statistics,
    parse_transfers,
    pick_coach,
    played_league,
    save_coach,
    save_nationality,
    save_squad,
    save_statistics,
    save_transfers,
    transfer_seasons,
    unsynced_leagues,
)
from app.sync.reference import FATAL
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)

# (team, seasons, kind, label): one request; every season it writes is marked on failure.
Unit = tuple[int, tuple[int, ...], str, str]
Store = Callable[[Session, datetime], None]


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
    ctx: JobContext, units: list[Unit], fetch: Callable[[ApiFootballClient, Unit], Store]
) -> tuple[list[str], bool]:
    """Fetch, parse and store each unit in its own transaction. Returns failed labels and
    whether a fatal provider stop ended the run."""
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
        for team, seasons, kind, label in units[index:] if fatal else [unit]:
            for season in seasons:
                mark_failure(session, team, season, kind, now, reason)
            failed.append(label)
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
