"""Runs one registered job: advisory lock -> sync_runs record -> job -> final status.

The runner is independent of how it is triggered (CLI, APScheduler, or a platform cron
chosen at deployment), so the trigger can change without touching job code.
"""

import hashlib
import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.models.sync_run import SyncRun
from app.providers.api_football import ApiFootballError
from app.sync.registry import JOBS, JobContext, JobPartialFailure

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]
LockFactory = Callable[[str], AbstractContextManager[bool]]


@dataclass(frozen=True)
class RunOutcome:
    job: str
    status: str  # succeeded | failed | skipped
    run_id: int | None
    api_requests: int
    error_summary: str | None = None


def advisory_lock_key(job: str) -> int:
    """Stable signed 64-bit key for pg_try_advisory_lock."""
    digest = hashlib.sha256(f"kicktab-sync:{job}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def pg_advisory_lock(engine: Engine) -> LockFactory:
    """Session-level advisory lock held on its own connection for the job's duration."""

    @contextmanager
    def lock(job: str) -> Iterator[bool]:
        key = advisory_lock_key(job)
        with engine.connect() as connection:
            acquired = bool(
                connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar()
            )
            connection.commit()
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                    connection.commit()

    return lock


def _summary(exc: BaseException) -> str:
    # Our own provider errors are written to be safe to store; others keep the type only.
    if isinstance(exc, ApiFootballError | JobPartialFailure):
        return f"{type(exc).__name__}: {str(exc)[:300]}"
    return type(exc).__name__


def run_job(
    name: str,
    params: Mapping[str, Any] | None = None,
    *,
    session_factory: SessionFactory | None = None,
    lock_factory: LockFactory | None = None,
) -> RunOutcome:
    if name not in JOBS:
        raise KeyError(f"Unknown sync job: {name}")
    spec = JOBS[name]
    merged = {**spec.default_params, **(params or {})}

    if session_factory is None or lock_factory is None:
        from app.db.session import get_engine, get_sessionmaker

        session_factory = session_factory or get_sessionmaker()
        lock_factory = lock_factory or pg_advisory_lock(get_engine())

    if spec.precheck is not None:
        with session_factory() as check_session:
            if not spec.precheck(check_session, merged):
                return RunOutcome(name, "skipped", None, 0, "Precheck: nothing to do")

    with lock_factory(name) as acquired:
        with session_factory() as record_session:
            run = SyncRun(job=name, params=merged, status="running" if acquired else "skipped")
            if not acquired:
                run.finished_at = datetime.now(UTC)
                run.error_summary = "Another run of this job holds the lock"
            record_session.add(run)
            record_session.commit()
            run_id = run.id
        if not acquired:
            logger.info("Sync job %s skipped: already running", name)
            return RunOutcome(name, "skipped", run_id, 0, "Another run of this job holds the lock")

        ctx: JobContext | None = None
        status, error = "succeeded", None
        try:
            with session_factory() as job_session:
                ctx = JobContext(session=job_session, params=merged)
                try:
                    spec.func(ctx)
                finally:
                    ctx.close()
        except Exception as exc:  # noqa: BLE001 - every failure is recorded, then reported
            status, error = "failed", _summary(exc)
            logger.warning("Sync job %s failed: %s", name, error)

        api_requests = ctx.api_requests if ctx else 0
        with session_factory() as record_session:
            run = record_session.get(SyncRun, run_id)
            if run is not None:
                run.status = status
                run.finished_at = datetime.now(UTC)
                run.api_requests = api_requests
                run.error_summary = error
                record_session.commit()
        return RunOutcome(name, status, run_id, api_requests, error)
