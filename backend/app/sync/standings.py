"""Standings and player data of the five leagues (chat 06, guide §6.5).

- standings (hourly check): one /standings?league=&season= per due league. Current season:
  hourly on a matchday (the league plays that KST day or kicked off in the last 4 hours),
  otherwise once a day. The hourly precheck reads only the DB, so idle hours leave no
  sync_runs row. Past seasons are kept: collected only when never stored or with force=1.
- player_rankings (daily 14:00 KST): the four provider top lists per league
  (/players/topscorers, topassists, topyellowcards, topredcards) = 20 requests a season.
- player_stats (daily 14:20 KST): every /players?league=&season=&page= page of each league
  (about 25-45 pages a league) into player_season_stats; saves are aggregated from it.

Params: season=2025, league=61 (one league, to split a long run), force=1 (ignore the
schedule). Every unit (league × kind) is stored only when its answer is complete; a failed
unit keeps its stored rows, records `league_syncs.failed_at` and the run ends as a partial
failure naming the failed units after the others are saved (CMP-004).
"""

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.providers.api_football import ApiFootballClient, ApiFootballError
from app.seed.competitions import LEAGUE_IDS
from app.services.reference import managed_seasons
from app.services.standings import (
    TOP_LISTS,
    IncompleteData,
    due_leagues,
    mark_failure,
    parse_player_pages,
    parse_standings,
    parse_top_list,
    save_player_stats,
    save_ranking,
    save_standings,
)
from app.sync.reference import FATAL
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)


def _season(params: Mapping[str, Any]) -> int:
    season = int(params.get("season", settings.current_season))
    if season not in managed_seasons():
        raise JobPartialFailure(f"Season {season} is not managed")
    return season


def _targets(session: Session, params: Mapping[str, Any], kind: str, *, hourly: bool) -> list[int]:
    season = _season(params)
    if params.get("league") is not None:
        league = int(params["league"])
        if league not in LEAGUE_IDS:
            raise JobPartialFailure(f"League {league} has no standings")
        leagues = [league]
    else:
        leagues = list(LEAGUE_IDS)
    if str(params.get("force", "")).lower() in ("1", "true", "yes"):
        return leagues
    due = set(due_leagues(session, season, kind, datetime.now(UTC), matchday_hourly=hourly))
    return [league for league in leagues if league in due]


def _collect(
    ctx: JobContext,
    kind_units: list[tuple[int, str]],
    fetch: Callable[[ApiFootballClient, int, str], Callable[[Session, datetime], None]],
) -> None:
    """Run (league, kind) units in order: fetch + parse, then save in one transaction.
    A unit failure is recorded and the next unit goes on; a fatal provider stop (auth,
    quota, budget) marks every remaining unit failed and ends the run."""
    session = ctx.session
    season = _season(ctx.params)
    client = ctx.api_football()
    failed: list[str] = []
    for index, (league, kind) in enumerate(kind_units):
        try:
            store = fetch(client, league, kind)
            now = datetime.now(UTC)
            store(session, now)
            session.commit()
            logger.info("%s %s/%s stored", kind, league, season)
            continue
        except ApiFootballError as exc:
            reason = type(exc).__name__
            fatal = isinstance(exc, FATAL)
        except IncompleteData as exc:
            reason, fatal = f"IncompleteData: {exc}", False
        except SQLAlchemyError as exc:
            reason, fatal = type(exc).__name__, False
        session.rollback()
        now = datetime.now(UTC)
        pending = kind_units[index:] if fatal else [(league, kind)]
        for p_league, p_kind in pending:
            mark_failure(session, p_league, season, p_kind, now, reason)
            failed.append(f"{p_kind}:{p_league}")
        session.commit()
        logger.warning("%s %s/%s failed: %s", kind, league, season, reason)
        if fatal:
            break
    if failed:
        raise JobPartialFailure(f"Failed ({season}): {', '.join(failed)}")


def _standings_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    try:
        return bool(_targets(session, params, "standings", hourly=True))
    except (JobPartialFailure, ValueError):
        return True  # a bad season/league parameter is recorded by the run itself


@register_job(
    "standings",
    description="League tables of the five leagues (1 request per due league)",
    # Checked hourly; the precheck lets only matchday-hourly / daily-due leagues through.
    schedule={"trigger": "cron", "minute": 10},
    precheck=_standings_precheck,
)
def sync_standings(ctx: JobContext) -> None:
    season = _season(ctx.params)
    leagues = _targets(ctx.session, ctx.params, "standings", hourly=True)

    def fetch(client: ApiFootballClient, league: int, _: str):
        result = client.get("/standings", {"league": league, "season": season})
        parsed = parse_standings(result.response, league, season)
        return lambda session, now: save_standings(session, league, season, parsed, now)

    _collect(ctx, [(league, "standings") for league in leagues], fetch)


@register_job(
    "player_rankings",
    description="Provider top lists: goals, assists, yellow, red (4 requests per league)",
    schedule={"trigger": "cron", "hour": 5, "minute": 0},  # 14:00 KST
)
def sync_player_rankings(ctx: JobContext) -> None:
    season = _season(ctx.params)
    units = [
        (league, kind)
        for kind in TOP_LISTS
        for league in _targets(ctx.session, ctx.params, kind, hourly=False)
    ]
    units.sort(key=lambda unit: LEAGUE_IDS.index(unit[0]))

    def fetch(client: ApiFootballClient, league: int, kind: str):
        result = client.get(TOP_LISTS[kind][0], {"league": league, "season": season})
        parsed = parse_top_list(result.response, kind, league, season)
        return lambda session, now: save_ranking(session, league, season, kind, parsed, now)

    _collect(ctx, units, fetch)


@register_job(
    "player_stats",
    description="Every player season line of the five leagues (all /players pages)",
    schedule={"trigger": "cron", "hour": 5, "minute": 20},  # 14:20 KST
)
def sync_player_stats(ctx: JobContext) -> None:
    season = _season(ctx.params)
    leagues = _targets(ctx.session, ctx.params, "player_stats", hourly=False)

    def fetch(client: ApiFootballClient, league: int, _: str):
        params = {"league": league, "season": season}
        first = client.get("/players", {**params, "page": 1})
        pages = [{"response": first.response, "paging": first.paging}]
        total = int((first.paging or {}).get("total") or 0)
        for page in range(2, total + 1):
            result = client.get("/players", {**params, "page": page})
            pages.append({"response": result.response, "paging": result.paging})
        parsed = parse_player_pages(pages, league, season)
        logger.info(
            "player_stats %s/%s: %d pages, %d lines", league, season, total, len(parsed.lines)
        )
        return lambda session, now: save_player_stats(session, league, season, parsed, now)

    _collect(ctx, [(league, "player_stats") for league in leagues], fetch)
