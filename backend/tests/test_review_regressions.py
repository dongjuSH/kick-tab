"""04 cross-review boundaries; no external requests or persistent database writes."""

import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.fixture import Fixture
from app.models.match_detail import FixtureDetail
from app.models.top_matches import Top5Attempt, Top5Publication, Top5Week
from app.providers.api_football import ApiFootballUnavailable
from app.services.head_to_head import ensure_form, ensure_meetings
from app.services.match_detail import read_records
from app.services.top5_selection import Selection, SelectionError, _publish, retry_due
from app.services.top_matches import shown_publication

NOW = datetime(2027, 6, 6, 15, 0, 30, tzinfo=UTC)
WEEK = date(2027, 6, 7)


def test_current_publication_wins_over_higher_previous_week_version():
    current = Top5Publication(version=2, week_start=WEEK, kind="none")
    previous = Top5Publication(version=3, week_start=WEEK - timedelta(days=7), kind="list")
    session = Mock()

    def by_week(query):
        requested = next(iter(query.compile().params.values()))
        return next((p for p in (current, previous) if p.week_start == requested), None)

    session.scalar.side_effect = by_week
    assert shown_publication(session, WEEK) is current


@pytest.mark.parametrize("cross_week", [False, True])
def test_publication_checks_clock_after_lock_waits(cross_week):
    attempt = Top5Attempt(
        id=1, week_start=WEEK, outcome="running", deadline_at=NOW + timedelta(seconds=4)
    )
    week = Top5Week(week_start=WEEK, current_attempt_id=1, status="running")
    session = Mock()
    wall = [NOW]

    def get(model, key, **kwargs):
        # The lock wait crosses either the deadline or a KST week boundary.
        wall[0] = NOW + (timedelta(days=7) if cross_week else timedelta(seconds=5))
        return attempt if model is Top5Attempt else week

    if cross_week:
        attempt.deadline_at = NOW + timedelta(days=8)
    session.get.side_effect = get
    session.scalar.return_value = None
    with pytest.raises(SelectionError):
        _publish(session, 1, Selection([], {}, 0, {}), clock=lambda: wall[0])
    session.add.assert_not_called()


def test_retry_precheck_admits_interrupted_running_attempt():
    session = Mock()
    session.get.return_value = SimpleNamespace(status="running")
    assert retry_due(session, NOW + timedelta(minutes=5))


@pytest.mark.parametrize("operation", ["meetings", "form"])
def test_concurrent_failures_share_cooldown(operation):
    barrier = threading.Barrier(2)
    shared = {"row": None, "calls": 0}
    counter_lock = threading.Lock()

    class Session:
        def __init__(self):
            self.inside = False

        def get(self, *args, **kwargs):
            if not self.inside:
                barrier.wait(timeout=3)
                return None
            return shared["row"]

        def expire_all(self):
            self.inside = True

        def execute(self, *args, **kwargs):
            pass

        def add(self, row):
            shared["row"] = row

        def commit(self):
            pass

        def rollback(self):
            pass

    class Client:
        request_count = 1

        def get(self, *args, **kwargs):
            with counter_lock:
                shared["calls"] += 1
            raise ApiFootballUnavailable("mock")

        def close(self):
            pass

    fixture = Fixture(id=991888001, home_team_id=50, away_team_id=42)

    def request(_):
        if operation == "meetings":
            ensure_meetings(Session(), fixture, NOW, Client)
        else:
            ensure_form(Session(), 50, NOW, Client)

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(request, range(2)))
    assert shared["calls"] == 1


@pytest.mark.parametrize(
    ("status", "kickoff_in", "expected"),
    [
        # A failure is reported where the server reads the provider again.
        ("live", timedelta(minutes=-30), "unavailable"),
        ("finished", timedelta(hours=-3), "unavailable"),
        # Before kickoff nothing is read (MAT-004 rule 4): an old failure (e.g. from before
        # a postponement) is "not yet" instead of a retry that can never succeed.
        ("scheduled", timedelta(minutes=50), "not_yet"),
        ("postponed", timedelta(minutes=50), "not_yet"),
        ("scheduled", timedelta(days=7), "not_yet"),
    ],
)
def test_failed_empty_blocks_are_unavailable_only_while_lookups_run(status, kickoff_in, expected):
    fixture = Fixture(
        id=1, home_team_id=50, away_team_id=42, status=status, kickoff_at=NOW + kickoff_in
    )
    session = Mock()
    session.get.return_value = FixtureDetail(fixture_id=1, last_failed_at=NOW)
    session.scalars.return_value = []
    records, _ = read_records(session, fixture)
    blocks = ("events", "statistics", "lineups", "players")
    assert {getattr(records, name).status for name in blocks} == {expected}


def test_cancelled_evidence_workers_do_not_hold_process_open():
    # A stuck DB/transport stub must not be joined by Python's executor atexit hook.
    code = """
import threading
from datetime import UTC, datetime, timedelta
from sqlalchemy.orm import Session
from app.services.top5_selection import _collect_evidence
started = threading.Event()
cancelled = threading.Event()
def stuck(session):
    started.set()
    threading.Event().wait()
def run():
    try:
        _collect_evidence([stuck], Session, datetime.now(UTC) + timedelta(seconds=60),
                          cancelled, lambda: datetime.now(UTC))
    except Exception:
        pass
owner = threading.Thread(target=run, daemon=True)
owner.start()
assert started.wait(2)
cancelled.set()
owner.join(1)
assert not owner.is_alive()
print('cancelled and returned', flush=True)
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            timeout=10, check=True)
    assert "cancelled and returned" in result.stdout
