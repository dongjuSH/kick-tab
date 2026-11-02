from datetime import UTC, date, datetime, timedelta, timezone

# Korea has no daylight saving time, so a fixed offset needs no tz database.
KST = timezone(timedelta(hours=9), "KST")


def kst_today(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(KST).date()


def kst_date(moment: datetime) -> date:
    """Calendar date in KST: a 04:00 KST kickoff belongs to that day (SCH-002)."""
    return moment.astimezone(KST).date()
