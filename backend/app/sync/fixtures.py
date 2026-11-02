"""Schedule and live sync for the current season (guide §6.5, OPS-001·003, LIVE-003·004).

- fixtures (every 30 min): one /fixtures request per available competition for today-1 ..
  today+15 (KST), 14 requests per run. A failed competition keeps its stored rows and is
  marked failed so the screen can tell "no matches" from "not collected" (CMP-004).
- fixtures_live (every 60 s, only while a match is live or about to start): one
  /fixtures?live=<our leagues> request, plus /fixtures?ids= for tracked matches missing
  from the live answer (finished or delayed), 20 ids per request. Idle minutes make no
  request and leave no sync_runs row.
"""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import Competition, CompetitionSeason
from app.providers.api_football import ApiFootballError
from app.services.fixtures import (
    collection_window,
    live_targets,
    needs_live_sync,
    upsert_fixtures,
)
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
    description="Current-season schedule, today-1 .. today+15 KST (1 request per competition)",
    schedule={"trigger": "interval", "minutes": 30},
)
def sync_fixtures(ctx: JobContext) -> None:
    session = ctx.session
    season = int(ctx.params.get("season", settings.current_season))
    competitions = _available_competitions(session, season)
    if not competitions:
        raise JobPartialFailure("No available competitions: run the reference job first")

    start, end = collection_window()
    # The provider filters by UTC date; a KST day starts at 15:00 UTC the day before.
    params = {
        "season": season,
        "from": (start - timedelta(days=1)).isoformat(),
        "to": end.isoformat(),
        "timezone": "UTC",
    }
    client = ctx.api_football()
    failed: list[int] = []
    for index, row in enumerate(competitions):
        now = datetime.now(UTC)
        try:
            result = client.get("/fixtures", {**params, "league": row.competition_id})
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
        saved = upsert_fixtures(session, result.response or [], now)
        row.fixtures_synced_at = now
        session.commit()
        logger.info("fixtures %s: %d saved", row.competition_id, saved)
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
    season = settings.current_season
    league_ids = [r.competition_id for r in _available_competitions(session, season)]
    now = datetime.now(UTC)
    tracked = set(live_targets(session, now))

    client = ctx.api_football()
    result = client.get(
        "/fixtures", {"live": "-".join(map(str, league_ids)), "timezone": "UTC"}
    )
    items = result.response or []
    upsert_fixtures(session, items, now)
    session.commit()

    # Tracked matches absent from the live answer may have finished or not started yet:
    # read them by id instead of assuming a result (LIVE-003).
    seen = {(item.get("fixture") or {}).get("id") for item in items}
    missing = sorted(tracked - seen)
    for i in range(0, len(missing), IDS_PER_REQUEST):
        chunk = missing[i : i + IDS_PER_REQUEST]
        result = client.get("/fixtures", {"ids": "-".join(map(str, chunk)), "timezone": "UTC"})
        upsert_fixtures(session, result.response or [], datetime.now(UTC))
        session.commit()
