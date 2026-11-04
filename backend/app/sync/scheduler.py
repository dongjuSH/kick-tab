"""In-process scheduler: all jobs or a single news-only worker (one instance)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.sync import jobs  # noqa: F401  (registers feature jobs)
from app.sync.registry import JOBS
from app.sync.runner import run_job

logger = logging.getLogger(__name__)


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
    return scheduler
