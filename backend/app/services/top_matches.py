from datetime import datetime, timedelta

from app.core.kst import kst_today
from app.schemas.top_matches import TopMatches, TopMatchesWeek


def current_kst_week(now: datetime | None = None) -> TopMatchesWeek:
    """KST Monday–Sunday containing `now` (default: the current time)."""
    today = kst_today(now)
    start = today - timedelta(days=today.weekday())
    return TopMatchesWeek(start=start, end=start + timedelta(days=6))


def get_current_top_matches() -> TopMatches:
    """This week's AI-selected TOP 5 (guide §6.4).

    Chat 04 adds `weekly_top_matches` and the Monday 00:00 KST selection. Until then no
    selection exists, so the current week is reported as `pending` with no items; the
    previous week is never shown as this week's list.
    """
    return TopMatches(week=current_kst_week(), state="pending", selected_at=None, items=[])
