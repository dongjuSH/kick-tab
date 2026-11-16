"""In-process scheduler: all jobs or a single news-only worker (one instance)."""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select

from app.config import settings
from app.sync import jobs  # noqa: F401  (registers feature jobs)
from app.sync.registry import JOBS
from app.sync.runner import run_job

logger = logging.getLogger(__name__)

# Startup catch-up: after downtime, collection jobs whose last successful run is older than
# one period run right away instead of waiting a full interval (2026-11-16: five days of
# stale schedule and expired news after the backend was off). Short polling jobs need no
# catch-up, and TOP 5 jobs keep their fixed Monday slots: a missed slot is published as a
# delay and recovered manually (TOP 5 policy), never re-run automatically here.
CATCH_UP_MIN_PERIOD = timedelta(minutes=10)
CATCH_UP_STAGGER = timedelta(seconds=15)


def _catch_up_eligible(job_id: str, trigger: object) -> bool:
    if job_id.startswith("top5"):
        return False
    return not (isinstance(trigger, IntervalTrigger) and trigger.interval < CATCH_UP_MIN_PERIOD)


def _is_overdue(trigger: object, last_success: datetime | None, now: datetime) -> bool:
    """True when at least one scheduled time has passed since the last successful run."""
    if last_success is None:
        return True
    if isinstance(trigger, IntervalTrigger):
        return last_success + trigger.interval <= now
    following = trigger.get_next_fire_time(None, last_success + timedelta(seconds=1))
    return following is not None and following <= now


def catch_up_overdue(
    scheduler: BaseScheduler, last_success: Mapping[str, datetime], now: datetime
) -> list[str]:
    """Move overdue jobs' next run to now (staggered). Returns the job ids moved."""
    moved = []
    for job in scheduler.get_jobs():
        if not _catch_up_eligible(job.id, job.trigger):
            continue
        if _is_overdue(job.trigger, last_success.get(job.id), now):
            job.modify(next_run_time=now + CATCH_UP_STAGGER * len(moved))
            moved.append(job.id)
    return moved


def last_successful_runs() -> dict[str, datetime]:
    from app.db.session import get_sessionmaker
    from app.models.sync_run import SyncRun

    with get_sessionmaker()() as session:
        rows = session.execute(
            select(SyncRun.job, func.max(SyncRun.started_at))
            .where(SyncRun.status == "succeeded")
            .group_by(SyncRun.job)
        ).all()
    return {job: started for job, started in rows}


def build_scheduler(*, news_only: bool = False) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    for spec in JOBS.values():
        if spec.schedule is None or (news_only and spec.name != "news"):
            continue
        scheduler.add_job(
            run_job,
            args=[spec.name],
            id=spec.name,
            # Never queue overlapping or missed runs; the advisory lock guards other hosts.
            max_instances=1,
            coalesce=True,
            replace_existing=True,
            **dict(spec.schedule),
        )
    return scheduler


def start_scheduler() -> BackgroundScheduler | None:
    if not (settings.scheduler_enabled or settings.news_scheduler_enabled):
        return None
    scheduler = build_scheduler(news_only=not settings.scheduler_enabled)
    scheduler.start()
    logger.info("Sync scheduler started with %d job(s)", len(scheduler.get_jobs()))
    try:
        moved = catch_up_overdue(scheduler, last_successful_runs(), datetime.now(UTC))
    except Exception as exc:  # noqa: BLE001 - startup must not fail on the catch-up query
        logger.warning("Startup catch-up skipped: %s", type(exc).__name__)
    else:
        if moved:
            logger.info("Startup catch-up: running overdue job(s) now: %s", ", ".join(moved))
    return scheduler
