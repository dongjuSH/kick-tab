"""AI weekly TOP 5 jobs (chat 04, docs/TOP5_POLICY 2026-11-02 revision).

- top5_weekly: Monday 00:00 KST, first automatic attempt (skipped if the week has started).
- top5_retry:  Monday 00:05 KST, fixed retry slot; runs only after a failed (or missed)
  00:00 attempt. A second failure publishes the delay notice and alerts the operator.
- top5:        manual recovery for the current week (`uv run python -m app.sync top5`),
  refused once the week is published.
API-Football requests (standings, form, head-to-head) are counted in sync_runs; the one
Gemini request per attempt is recorded on the attempt row.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.sync.registry import JobContext, JobPartialFailure, register_job

KST_CRON = {"trigger": "cron", "day_of_week": "mon", "timezone": "Asia/Seoul", "hour": 0}
# A missed fire is still run up to a minute late (APScheduler's default grace is 1 s).
GRACE = {"misfire_grace_time": 60}


def _run(ctx: JobContext, trigger: str) -> None:
    from app.db.session import get_sessionmaker
    from app.services.top5_selection import run_attempt

    outcome = run_attempt(
        trigger,  # type: ignore[arg-type]
        session_factory=get_sessionmaker(),
        client_factory=ctx.api_football,
    )
    alert = {True: ", alert sent", False: ", alert NOT delivered", None: ""}[outcome.alert_sent]
    summary = (
        f"week {outcome.week_start}: {outcome.status}"
        + (f" ({outcome.kind})" if outcome.kind else "")
        + (f" attempt {outcome.attempt_id}" if outcome.attempt_id else "")
        + (f" - {outcome.message}" if outcome.message else "")
        + alert
    )
    print(f"TOP 5 {summary}")
    if outcome.status == "failed":
        raise JobPartialFailure(summary)


def _first_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    from app.services.top5_selection import first_attempt_due

    return first_attempt_due(session, datetime.now(UTC))


def _retry_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    from app.services.top5_selection import retry_due

    return retry_due(session, datetime.now(UTC))


@register_job(
    "top5_weekly",
    description="AI TOP 5: first attempt, Monday 00:00 KST",
    schedule={**KST_CRON, "minute": 0, **GRACE},
    precheck=_first_precheck,
)
def top5_weekly(ctx: JobContext) -> None:
    _run(ctx, "scheduled")


@register_job(
    "top5_retry",
    description="AI TOP 5: single retry, Monday 00:05 KST (only after a failed first attempt)",
    schedule={**KST_CRON, "minute": 5, **GRACE},
    precheck=_retry_precheck,
)
def top5_retry(ctx: JobContext) -> None:
    _run(ctx, "retry")


@register_job("top5", description="AI TOP 5: manual recovery of the current week")
def top5_manual(ctx: JobContext) -> None:
    _run(ctx, "manual")


def _recovery_precheck(session: Session, params: Mapping[str, Any]) -> bool:
    from app.services.top5_selection import recovery_due

    return recovery_due(session, datetime.now(UTC))


@register_job(
    "top5_reconcile",
    description="Repair expired TOP 5 attempts without selecting again",
    schedule={"trigger": "interval", "seconds": 60},
    precheck=_recovery_precheck,
)
def top5_reconcile(ctx: JobContext) -> None:
    from app.db.session import get_sessionmaker
    from app.services.top5_selection import reconcile_attempts

    reconcile_attempts(session_factory=get_sessionmaker())
