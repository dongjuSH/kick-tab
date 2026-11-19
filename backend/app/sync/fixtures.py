"""Schedule and live sync for the current season (guide §6.5, OPS-001·003, LIVE-003·004).

- fixtures (every 30 min): the common match-day period's calendar span (SCH-002·003, from the
  stored schedule), one /fixtures request per competition season that can play in it - a
  period may cross seasons, and one-off cups outside it cost nothing. A failed competition
  keeps its stored rows and is marked failed so the screen can tell "no matches" from "not
  collected" (CMP-004).
- fixtures_live (every 60 s, only while a match is live or about to start): one
  /fixtures?live=<our leagues> request, plus /fixtures?ids= for tracked matches missing
  from the live answer (finished or delayed), 20 ids per request. Idle minutes make no
  request and leave no sync_runs row. The live answer's events and the full detail blocks
  of the id answers are stored as they come (chat 04), without extra requests.
- fixture_details (every 5 min, only when needed): `/fixtures?ids=` for recently finished
  matches whose final record is still missing (20 ids per request) - the "once at the
  finish" collection of match records (guide §6.5).
- fixtures_season (chat 05, daily for the current season, manual for past ones): the whole
  season list, one /fixtures?league=&season= request per available competition (14).
"""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import Competition, CompetitionSeason
from app.providers.api_football import ApiFootballError
from app.services.fixtures import (
    live_targets,
    needs_live_sync,
    overlaps,
    schedule_period,
    stored_seasons,
    upsert_fixtures,
)
from app.services.match_detail import (
    final_record_targets,
    mark_record_failures,
    needs_final_records,
    store_fixture_records,
)
from app.services.reference import managed_seasons
from app.sync.reference import FATAL
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)
IDS_PER_REQUEST = 20


def _available_competitions(session: Session, season: int) -> list[CompetitionSeason]:
    return list(
        session.scalars(
            select(CompetitionSeason)
            .join(Competition, Competition.id == CompetitionSeason.competition_id)
            .where(
                CompetitionSeason.season == season,
                CompetitionSeason.availability == "available",
                Competition.active,
            )
            .order_by(Competition.sort_order)
        )
    )


@register_job(
    "fixtures",
    description="Schedule of the common match-day period (1 request per competition season)",
    schedule={"trigger": "interval", "minutes": 30},
)
def sync_fixtures(ctx: JobContext) -> None:
    session = ctx.session
    start, end = schedule_period(session).bounds()
    stored = stored_seasons(session, start, end)
    competitions = [
        row
        for season in managed_seasons()
        for row in _available_competitions(session, season)
        if overlaps(row, start, end, stored)
    ]
    if not competitions:
        raise JobPartialFailure("No available competitions: run the reference job first")

    # The provider filters by UTC date; a KST day starts at 15:00 UTC the day before.
    params = {
        "from": (start - timedelta(days=1)).isoformat(),
        "to": end.isoformat(),
        "timezone": "UTC",
    }
    client = ctx.api_football()
    failed: list[int] = []
    for index, row in enumerate(competitions):
        now = datetime.now(UTC)
        try:
            result = client.get(
                "/fixtures", {**params, "league": row.competition_id, "season": row.season}
            )
        except ApiFootballError as exc:
            logger.warning("fixtures %s failed: %s", row.competition_id, type(exc).__name__)
            pending = competitions[index:] if isinstance(exc, FATAL) else [row]
            for item in pending:
                item.fixtures_failed_at = now
                failed.append(item.competition_id)
            session.commit()
            if isinstance(exc, FATAL):
                break
            continue
        items = result.response or []
        saved = upsert_fixtures(session, items, now)
        if saved < len(items):
            # Some fixtures could not be stored (chat 05): a failed run for this competition.
            # The saved rows stay; the last success and its window are left as they were.
            row.fixtures_failed_at = now
            failed.append(row.competition_id)
        else:
            row.fixtures_synced_at = now
            row.fixtures_window_start = start
            row.fixtures_window_end = end
        session.commit()
        logger.info("fixtures %s: %d of %d saved", row.competition_id, saved, len(items))
    if failed:
        raise JobPartialFailure(f"Failed competitions: {', '.join(map(str, failed))}")


@register_job(
    "fixtures_season",
    description="Whole-season fixture list of one season (1 request per competition)",
    # 13:00 KST daily for the current season: no European match is live then, and finished
    # matches missed while the 21-day sync was down are filled in. Past seasons: manual
    # (`python -m app.sync fixtures_season season=2025`).
    schedule={"trigger": "cron", "hour": 4, "minute": 0},
)
def sync_season_fixtures(ctx: JobContext) -> None:
    """HIST-001·003: every fixture of each available competition in one season.

    Rows are upserted by fixture id, so a re-run never duplicates and a new season never
    removes an older one. A failed competition keeps its stored rows and records
    `season_fixtures_failed_at` (CMP-004). Match records are not bulk-loaded: the detail
    page fetches them once when first opened (chat 04)."""
    session = ctx.session
    season = int(ctx.params.get("season", settings.current_season))
    if season not in managed_seasons():
        raise JobPartialFailure(f"Season {season} is not managed")
    competitions = _available_competitions(session, season)
    # `league=528,556` (manual): only those competitions (new ones, without reloading all).
    only = {int(x) for x in str(ctx.params.get("league", "")).split(",") if x.strip()}
    if only:
        competitions = [row for row in competitions if row.competition_id in only]
    if not competitions:
        raise JobPartialFailure(f"No available competitions in {season}: run reference first")

    client = ctx.api_football()
    failed: list[int] = []
    for index, row in enumerate(competitions):
        now = datetime.now(UTC)
        try:
            result = client.get(
                "/fixtures",
                {"league": row.competition_id, "season": season, "timezone": "UTC"},
            )
        except ApiFootballError as exc:
            logger.warning("season fixtures %s failed: %s", row.competition_id, type(exc).__name__)
            pending = competitions[index:] if isinstance(exc, FATAL) else [row]
            for item in pending:
                item.season_fixtures_failed_at = now
                failed.append(item.competition_id)
            session.commit()
            if isinstance(exc, FATAL):
                break
            continue
        items = result.response or []
        try:
            saved = upsert_fixtures(session, items, now)
        except SQLAlchemyError as exc:
            # This competition's batch is undone; stored rows stay and the next one goes on.
            session.rollback()
            logger.warning(
                "season fixtures %s not saved: %s", row.competition_id, type(exc).__name__
            )
            row.season_fixtures_failed_at = now
            failed.append(row.competition_id)
            session.commit()
            continue
        if saved < len(items):
            # Part of the answer could not be stored: keep what was saved, but this run is a
            # failure - the last complete load (if any) keeps its time.
            row.season_fixtures_failed_at = now
            failed.append(row.competition_id)
        else:
            row.season_fixtures_synced_at = now
        session.commit()
        logger.info(
            "season fixtures %s/%s: %d of %d saved", row.competition_id, season, saved, len(items)
        )
    if failed:
        raise JobPartialFailure(f"Failed competitions: {', '.join(map(str, failed))}")


def _live_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    return bool(params.get("force")) or needs_live_sync(session, datetime.now(UTC))


@register_job(
    "fixtures_live",
    description="Live scores while a supported match is live or about to start",
    schedule={"trigger": "interval", "seconds": 60},
    precheck=_live_precheck,
)
def sync_live(ctx: JobContext) -> None:
    session = ctx.session
    # Competition ids only (any managed season): a tournament held in an earlier season's
    # calendar - e.g. a club world cup or super cup - is followed as well.
    league_ids = sorted({
        row.competition_id
        for season in managed_seasons()
        for row in _available_competitions(session, season)
    })
    now = datetime.now(UTC)
    tracked = set(live_targets(session, now))

    client = ctx.api_football()
    result = client.get(
        "/fixtures", {"live": "-".join(map(str, league_ids)), "timezone": "UTC"}
    )
    seen = store_fixture_records(session, result.response or [], now)
    session.commit()

    # Recheck tracked fixtures the live response did not update (LIVE-003).
    missing = sorted(tracked - seen)
    failed: list[int] = []
    for i in range(0, len(missing), IDS_PER_REQUEST):
        chunk = missing[i : i + IDS_PER_REQUEST]
        result = client.get("/fixtures", {"ids": "-".join(map(str, chunk)), "timezone": "UTC"})
        seen = store_fixture_records(session, result.response or [], datetime.now(UTC))
        failed.extend(sorted(set(chunk) - seen))
        session.commit()
    if failed:
        raise JobPartialFailure(f"Failed live fixtures: {', '.join(map(str, failed))}")


def _final_records_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    return needs_final_records(session, datetime.now(UTC))


@register_job(
    "fixture_details",
    description="Final records of recently finished matches (1 request per 20 matches)",
    schedule={"trigger": "interval", "minutes": 5},
    precheck=_final_records_precheck,
)
def sync_final_records(ctx: JobContext) -> None:
    session = ctx.session
    targets = final_record_targets(session, datetime.now(UTC))
    client = ctx.api_football()
    failed: list[int] = []
    for i in range(0, len(targets), IDS_PER_REQUEST):
        chunk = targets[i : i + IDS_PER_REQUEST]
        now = datetime.now(UTC)
        try:
            result = client.get("/fixtures", {"ids": "-".join(map(str, chunk)), "timezone": "UTC"})
        except ApiFootballError as exc:
            logger.warning("fixture_details failed: %s", type(exc).__name__)
            mark_record_failures(session, chunk, now)
            session.commit()
            failed += chunk
            if isinstance(exc, FATAL):
                break
            continue
        seen = store_fixture_records(session, result.response or [], now)
        missing = sorted(set(chunk) - seen)
        mark_record_failures(session, missing, now)
        failed.extend(missing)
        session.commit()
    if failed:
        raise JobPartialFailure(f"Failed fixtures: {', '.join(map(str, failed))}")
