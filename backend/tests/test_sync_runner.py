from contextlib import contextmanager

import pytest

from app.config import Settings
from app.models.sync_run import SyncRun
from app.providers.api_football import ApiFootballUnavailable
from app.sync import __main__ as cli
from app.sync import scheduler
from app.sync.registry import JOBS, register_job
from app.sync.runner import advisory_lock_key, run_job


class FakeSession:
    """Minimal stand-in for a SQLAlchemy session storing SyncRun rows in a dict."""

    def __init__(self, store: dict[int, SyncRun]):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def add(self, obj):
        if isinstance(obj, SyncRun):
            obj.id = obj.id or len(self.store) + 1
            self.store[obj.id] = obj

    def commit(self):
        pass

    def get(self, _model, key):
        return self.store.get(key)


@pytest.fixture
def store():
    return {}


@pytest.fixture
def factories(store):
    def session_factory():
        return FakeSession(store)

    def lock_factory(acquired=True):
        @contextmanager
        def lock(_job):
            yield acquired

        return lock

    return session_factory, lock_factory


@pytest.fixture
def temp_job():
    names: list[str] = []

    def add(name, func, **kwargs):
        register_job(name, **kwargs)(func)
        names.append(name)

    yield add
    for name in names:
        JOBS.pop(name, None)


def test_successful_run_is_recorded(store, factories, temp_job):
    session_factory, lock_factory = factories

    def job(ctx):
        assert ctx.params == {"season": "2026", "date": "today"}
        ctx.other_api_requests += 4

    temp_job("test-ok", job, default_params={"season": "2025", "date": "today"})
    outcome = run_job(
        "test-ok", {"season": "2026"}, session_factory=session_factory, lock_factory=lock_factory()
    )
    assert outcome.status == "succeeded"
    run = store[outcome.run_id]
    assert (run.job, run.status, run.api_requests, run.error_summary) == (
        "test-ok", "succeeded", 4, None,
    )
    assert run.params == {"season": "2026", "date": "today"}
    assert run.finished_at is not None


def test_failed_run_keeps_request_count_and_safe_summary(store, factories, temp_job):
    session_factory, lock_factory = factories

    def job(ctx):
        ctx.other_api_requests += 2
        raise ApiFootballUnavailable("API-Football /fixtures returned HTTP 503")

    temp_job("test-fail", job)
    outcome = run_job("test-fail", session_factory=session_factory, lock_factory=lock_factory())
    assert outcome.status == "failed"
    run = store[outcome.run_id]
    assert run.status == "failed"
    assert run.api_requests == 2
    assert run.error_summary == "ApiFootballUnavailable: API-Football /fixtures returned HTTP 503"


def test_unexpected_errors_store_only_the_type(store, factories, temp_job):
    session_factory, lock_factory = factories

    def job(_ctx):
        raise RuntimeError("postgresql://user:secret@host/db")

    temp_job("test-crash", job)
    outcome = run_job("test-crash", session_factory=session_factory, lock_factory=lock_factory())
    assert store[outcome.run_id].error_summary == "RuntimeError"


def test_overlapping_run_is_skipped_without_running_the_job(store, factories, temp_job):
    session_factory, lock_factory = factories
    calls = []
    temp_job("test-lock", calls.append)
    outcome = run_job(
        "test-lock", session_factory=session_factory, lock_factory=lock_factory(False)
    )
    assert outcome.status == "skipped"
    assert calls == []
    assert store[outcome.run_id].status == "skipped"


def test_unknown_job_is_rejected():
    with pytest.raises(KeyError):
        run_job("does-not-exist")


def test_advisory_lock_key_is_stable_signed_64_bit():
    key = advisory_lock_key("fixtures")
    assert key == advisory_lock_key("fixtures")
    assert key != advisory_lock_key("standings")
    assert -(2**63) <= key < 2**63


def test_cli_lists_jobs_and_rejects_unknown(capsys, temp_job):
    temp_job("test-listed", lambda ctx: None, description="for the CLI test")
    assert cli.main(["--list"]) == 0
    assert "test-listed\tfor the CLI test" in capsys.readouterr().out
    assert cli.main(["nope"]) == 2


def test_cli_maps_outcome_to_exit_code(monkeypatch, temp_job):
    temp_job("test-cli", lambda ctx: None)
    monkeypatch.setattr(
        cli, "run_job", lambda name, params: type("O", (), {
            "job": name, "status": "skipped", "run_id": 1, "api_requests": 0,
            "error_summary": "locked",
        })()
    )
    assert cli.main(["test-cli", "season=2026"]) == 3


def test_scheduler_starts_only_when_enabled(monkeypatch, temp_job):
    temp_job("test-scheduled", lambda ctx: None, schedule={"trigger": "interval", "minutes": 30})
    temp_job("test-manual", lambda ctx: None)
    monkeypatch.setattr(
        scheduler, "settings", Settings(scheduler_enabled=False, news_scheduler_enabled=False)
    )
    assert scheduler.start_scheduler() is None

    built = scheduler.build_scheduler()
    ids = [job.id for job in built.get_jobs()]
    assert "test-scheduled" in ids and "test-manual" not in ids
    # Chat 03 jobs: manual-only alias reload stays out of the schedule.
    assert {"reference", "fixtures", "fixtures_live", "news"} <= set(ids)
    assert "team_aliases" not in ids
    job = built.get_job("test-scheduled")
    assert job.max_instances == 1
    assert job.coalesce is True

    news = scheduler.build_scheduler(news_only=True).get_jobs()
    assert [(job.id, str(job.trigger)) for job in news] == [("news", "cron[minute='0']")]


def test_startup_catch_up_moves_only_overdue_collection_jobs(temp_job):
    from datetime import UTC, datetime, timedelta

    from apscheduler.schedulers.background import BackgroundScheduler

    now = datetime(2026, 11, 16, 2, 30, tzinfo=UTC)  # Mon 11:30 KST
    built = BackgroundScheduler(timezone="UTC")
    for job_id, trigger in {
        "stale-interval": {"trigger": "interval", "minutes": 30},
        "fresh-interval": {"trigger": "interval", "minutes": 30},
        "stale-cron": {"trigger": "cron", "minute": 0},
        "fresh-cron": {"trigger": "cron", "minute": 0},
        "never-ran": {"trigger": "cron", "hour": 19, "minute": 0},
        "short-poll": {"trigger": "interval", "seconds": 60},
        "top5_weekly": {"trigger": "cron", "day_of_week": "mon", "hour": 15, "minute": 0},
    }.items():
        built.add_job(lambda: None, id=job_id, **trigger)
    last = {
        "stale-interval": now - timedelta(days=5),
        "fresh-interval": now - timedelta(minutes=10),
        "stale-cron": now - timedelta(hours=2),
        "fresh-cron": now - timedelta(minutes=20),  # 02:10 UTC, next is 03:00
        "short-poll": now - timedelta(days=5),
        "top5_weekly": now - timedelta(days=7),
    }
    moved = scheduler.catch_up_overdue(built, last, now)
    assert moved == ["stale-interval", "stale-cron", "never-ran"]
    times = [built.get_job(job_id).next_run_time for job_id in moved]
    assert times == [now, now + scheduler.CATCH_UP_STAGGER, now + 2 * scheduler.CATCH_UP_STAGGER]
    # Not moved: fresh jobs, short polls and the fixed TOP 5 slots (see the list above).
