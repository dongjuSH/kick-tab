"""Public side of the AI weekly TOP 5 (TOP-003, guide §6.4).

What users see is decided only by published rows (`top5_publications`), never by the job
state of the week being prepared:
- a publication for the current KST week -> that result (list, none or the delay notice);
- otherwise last week's published list/none, with its real week and selection time, while
  the new week is being selected and retried (00:00 / 00:05 KST);
- otherwise (nothing usable was ever published) the delay notice for the current week.
Visits and refreshes only read; they never start a selection.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.kst import kst_today
from app.models.top_matches import Top5Publication, WeeklyTopMatch
from app.schemas.top_matches import (
    TopMatches,
    TopMatchesVersion,
    TopMatchesWeek,
    TopMatchItem,
)
from app.services.fixtures import summaries_by_ids


def week_of(start: date) -> TopMatchesWeek:
    return TopMatchesWeek(start=start, end=start + timedelta(days=6))


def current_kst_week(now: datetime | None = None) -> TopMatchesWeek:
    """KST Monday–Sunday containing `now` (default: the current time)."""
    today = kst_today(now)
    return week_of(today - timedelta(days=today.weekday()))


def latest_publication(session: Session, week_start: date) -> Top5Publication | None:
    return session.scalar(
        select(Top5Publication)
        .where(Top5Publication.week_start == week_start)
        .order_by(Top5Publication.version.desc())
        .limit(1)
    )


def shown_publication(session: Session, current: date) -> Top5Publication | None:
    """The publication users see in the week starting `current` (None = delay notice)."""
    current_result = latest_publication(session, current)
    if current_result is not None:
        return current_result
    previous = latest_publication(session, current - timedelta(days=7))
    return previous if previous is not None and previous.kind != "delayed" else None


def current_version(session: Session, now: datetime) -> TopMatchesVersion:
    week = current_kst_week(now)
    shown = shown_publication(session, week.start)
    return TopMatchesVersion(
        version=shown.version if shown else None, current_week_start=week.start
    )


def get_current_top_matches(session: Session, now: datetime) -> tuple[TopMatches, datetime | None]:
    current = current_kst_week(now)
    shown = shown_publication(session, current.start)
    if shown is None or shown.kind == "delayed":
        return (
            TopMatches(
                version=shown.version if shown else None,
                view="delayed",
                week=current,
                current_week=current,
                selected_at=None,
                items=[],
            ),
            None,
        )
    rows = (
        list(
            session.scalars(
                select(WeeklyTopMatch)
                .where(WeeklyTopMatch.week_start == shown.week_start)
                .order_by(WeeklyTopMatch.rank)
            )
        )
        if shown.kind == "list"
        else []
    )
    summaries, updated_at = summaries_by_ids(session, [r.fixture_id for r in rows])
    items = [
        TopMatchItem(
            rank=r.rank,
            reason=r.reason,
            selected_kickoff_at=r.selected_kickoff_at,
            match=summaries[r.fixture_id],
        )
        for r in rows
        if r.fixture_id in summaries
    ]
    return (
        TopMatches(
            version=shown.version,
            view="list" if shown.kind == "list" else "none",
            week=week_of(shown.week_start),
            current_week=current,
            selected_at=shown.selected_at,
            items=items,
        ),
        updated_at,
    )
