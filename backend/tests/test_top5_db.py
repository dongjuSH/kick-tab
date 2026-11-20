"""Chat 04 against the dev database (opt-in, always rolled back): the weekly TOP 5 attempt
flow (one automatic attempt, delay notice held until 00:20 + alert, manual recovery, timeout)
and the public review order.

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_top5_db.py
External calls are mocked: API-Football answers empty lists, the model is a stub.
"""

import json
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fixture import Fixture
from app.models.reference import CompetitionSeason
from app.models.review import Review, ReviewReaction
from app.models.top_matches import Top5Attempt, Top5Publication, Top5Week
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.providers.gemini import LlmError
from app.services import top5_selection
from app.services.reviews import list_reviews
from app.services.top5_selection import LlmPick, LlmSelection, ModelFailed, run_attempt
from app.services.top_matches import get_current_top_matches

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

BASE_ID = 991_000_000
# Monday 2027-06-07 00:00:30 KST: a week without real fixtures.
NOW = datetime(2027, 6, 6, 15, 0, 30, tzinfo=UTC)
TEAMS = [(50, 42), (541, 529), (157, 165)]


@pytest.fixture
def connection():
    from app.db.session import get_engine

    with get_engine().connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()


@pytest.fixture
def factory(connection, monkeypatch):
    monkeypatch.setattr(top5_selection, "EVIDENCE_WORKERS", 1)  # one connection, in turn

    def make() -> Session:
        return Session(bind=connection, join_transaction_mode="create_savepoint")

    with make() as session:
        session.execute(
            update(CompetitionSeason)
            .where(CompetitionSeason.availability == "available")
            .values(fixtures_synced_at=NOW, fixtures_failed_at=None)
        )
        for index, (home, away) in enumerate(TEAMS):
            kickoff = NOW + timedelta(days=2, hours=index)
            session.add(
                Fixture(
                    id=BASE_ID + index, competition_id=39, season=2026, round="Regular Season - 38",
                    kickoff_at=kickoff, kickoff_date_kst=kickoff.date(), status="scheduled",
                    status_short_raw="NS", home_team_id=home, away_team_id=away, synced_at=NOW,
                )
            )
        session.commit()
    return make


def empty_client() -> ApiFootballClient:
    def handler(request):
        return httpx.Response(200, json={"errors": [], "results": 0, "response": []})

    return ApiFootballClient(
        SecretStr("test-key"), transport=httpx.MockTransport(handler),
        limiter=MinuteRateLimiter(1000), budget=DailyBudget(1000),
    )


def good_model(prompt: str, timeout: float):
    candidates = json.loads(prompt.rsplit("\n", 1)[1])
    picks = [
        LlmPick(fixture_id=c["fixtureId"], rank=i + 1, reason="상위권 맞대결")
        for i, c in enumerate(candidates[:5])
    ]
    answer = LlmSelection(picks=picks)
    return answer, answer.model_dump(mode="json")


def failing_model(prompt: str, timeout: float):
    raise LlmError("Gemini API error 503 UNAVAILABLE")


def model_failing(prompt: str, timeout: float):
    raise ModelFailed("gemini-3.8-flash: Gemini API error 503 → Gemini API error 503")


def run(trigger, factory, model, alerts=None, **kwargs):
    started = time.monotonic()
    return run_attempt(
        trigger, session_factory=factory, client_factory=empty_client, generate=model,
        alert=lambda notice: alerts is None or alerts.append(notice) or True, now=NOW, **kwargs,
        clock=lambda: NOW + timedelta(seconds=time.monotonic() - started),
    )


def week(factory):
    with factory() as session:
        return session.get(Top5Week, NOW.date() + timedelta(days=1))


def public(factory):
    with factory() as session:
        data, _ = get_current_top_matches(session, NOW)
        return data


def test_automatic_attempt_publishes_and_never_runs_again(factory):
    outcome = run("scheduled", factory, good_model)
    assert outcome.status == "published" and outcome.kind == "list"
    shown = public(factory)
    assert shown.view == "list" and shown.version is not None
    assert [i.match.id for i in shown.items] == [BASE_ID, BASE_ID + 1, BASE_ID + 2]
    assert shown.items[0].selected_kickoff_at == shown.items[0].match.kickoff_at
    # A published week is never selected again, by any trigger.
    for trigger in ("scheduled", "manual"):
        assert run(trigger, factory, good_model).status == "skipped"


def repair_at(factory, at, alerts):
    return top5_selection.reconcile_attempts(
        session_factory=factory, clock=lambda: at,
        alert=lambda notice: alerts.append(notice) or True,
    )


WINDOW_END = datetime(2027, 6, 6, 15, 20, tzinfo=UTC)  # Monday 2027-06-07 00:20 KST


def test_early_failure_keeps_last_week_until_0020_then_delays_and_alerts_once(factory):
    # One automatic attempt per week. A failure before 00:20 KST is only recorded: users
    # keep last week's result ('준비 중'); the delay notice and one alert follow at 00:20.
    alerts = []
    first = run("scheduled", factory, failing_model, alerts)
    assert first.status == "failed" and "503" in first.message and first.alert_sent is None
    assert alerts == []
    state = week(factory)
    assert state.status == "delayed" and state.needs_manual and state.auto_attempts == 1
    assert state.next_retry_at == WINDOW_END  # when the delay notice goes public
    assert public(factory).version is None  # nothing new published for this week yet
    # No second automatic attempt.
    assert run("scheduled", factory, good_model).status == "skipped"
    assert repair_at(factory, WINDOW_END - timedelta(seconds=1), alerts) == 0  # 00:19:59
    assert repair_at(factory, WINDOW_END, alerts) == 1  # 00:20:00
    assert repair_at(factory, WINDOW_END + timedelta(minutes=1), alerts) == 0  # only once
    delayed = public(factory)
    assert delayed.view == "delayed" and delayed.version is not None
    assert len(alerts) == 1 and alerts[0].attempts == 1 and "503" in alerts[0].error
    assert week(factory).next_retry_at is None
    # A failed manual recovery keeps the delay notice (same version) and sends no alert.
    assert run("manual", factory, failing_model, alerts).status == "failed"
    assert len(alerts) == 1 and public(factory).version == delayed.version
    assert repair_at(factory, WINDOW_END + timedelta(minutes=2), alerts) == 0
    recovered = run("manual", factory, good_model, alerts)
    assert recovered.status == "published"
    after = public(factory)
    assert after.view == "list" and after.version > delayed.version


def test_manual_recovery_before_0020_cancels_the_held_delay(factory):
    alerts = []
    run("scheduled", factory, model_failing, alerts)
    assert run("manual", factory, good_model, alerts).status == "published"
    assert repair_at(factory, WINDOW_END + timedelta(minutes=1), alerts) == 0
    assert alerts == [] and public(factory).view == "list"


def test_failure_after_0020_shows_the_delay_at_once(factory):
    # A failure recorded after 00:20 shows the delay notice at once (the held time passed).
    alerts = []
    late = WINDOW_END + timedelta(minutes=5)
    outcome = run_attempt(
        "manual", session_factory=factory, client_factory=empty_client,
        generate=failing_model, alert=lambda notice: alerts.append(notice) or True,
        now=late, clock=lambda: late,
    )
    assert outcome.status == "failed"
    assert week(factory).next_retry_at is None
    with factory() as session:
        data, _ = get_current_top_matches(session, late)
    assert data.view == "delayed" and data.version is not None


def test_automatic_attempt_is_cut_at_the_window_end(factory):
    # 00:19:50 KST: only 10 s are left before 00:20, minus the 10 s margin -> skipped.
    late = NOW + timedelta(minutes=19, seconds=20)
    outcome = run_attempt(
        "scheduled", session_factory=factory, client_factory=empty_client,
        generate=good_model, alert=lambda notice: True, now=late, clock=lambda: late,
    )
    assert outcome.status == "skipped" and "window passed" in outcome.message
    # At 00:00:30 the attempt gets until 00:19:50 KST, not the 1200 s setting.
    with factory() as session:
        attempt, *_ = top5_selection._start(
            session, NOW.date() + timedelta(days=1), "scheduled", NOW,
            (top5_selection.window_end(NOW.date() + timedelta(days=1)) - NOW).total_seconds()
            - 10,
        )
        assert attempt.deadline_at == datetime(2027, 6, 6, 15, 19, 50, tzinfo=UTC)
        session.rollback()


def test_week_without_candidates_publishes_none_without_model(factory):
    with factory() as session:
        session.execute(text(f"DELETE FROM fixtures WHERE id >= {BASE_ID} AND id < {BASE_ID + 10}"))
        session.commit()

    def never(prompt, timeout):
        raise AssertionError("no model request without candidates")

    outcome = run("scheduled", factory, never)
    assert outcome.status == "published" and outcome.kind == "none"
    assert public(factory).view == "none"


def test_stale_schedule_is_a_failure_not_an_empty_week(factory):
    with factory() as session:
        session.execute(
            update(CompetitionSeason).values(fixtures_synced_at=NOW - timedelta(hours=3))
        )
        session.commit()
    outcome = run("scheduled", factory, good_model)
    assert outcome.status == "failed" and "not refreshed" in outcome.message


def test_timed_out_attempt_cannot_publish(factory, monkeypatch):
    def slow(*args, **kwargs):
        time.sleep(0.3)
        return top5_selection.Selection([], {}, 0, {})

    monkeypatch.setattr(top5_selection, "select_week", slow)
    outcome = run("scheduled", factory, good_model, timeout_seconds=0.1)
    assert outcome.status == "failed" and "Timed out" in outcome.message
    with factory() as session:
        attempt = session.get(Top5Attempt, outcome.attempt_id)
        assert attempt.outcome == "timeout"
    time.sleep(0.4)  # the abandoned thread finishes; it has no way to publish
    assert public(factory).version is None  # no late list (and no delay before 00:20)


def interrupted(factory, trigger, attempts):
    week_start = NOW.date() + timedelta(days=1)
    with factory() as session:
        row = Top5Attempt(
            week_start=week_start, trigger=trigger, started_at=NOW,
            deadline_at=NOW + timedelta(seconds=20), outcome="running",
            prompt_version=top5_selection.PROMPT_VERSION,
        )
        session.add(row)
        session.flush()
        session.add(Top5Week(
            week_start=week_start, status="running", auto_attempts=attempts,
            current_attempt_id=row.id,
        ))
        session.commit()
        return row.id


def test_interrupted_automatic_attempt_is_reconciled_then_delayed_at_0020(factory):
    old_id = interrupted(factory, "scheduled", 1)
    alerts = []
    assert repair_at(factory, NOW + timedelta(minutes=1), alerts) == 1  # recorded only
    assert repair_at(factory, NOW + timedelta(minutes=2), alerts) == 0
    with factory() as session:
        assert session.get(Top5Attempt, old_id).outcome == "timeout"
    assert week(factory).status == "delayed" and alerts == []
    assert public(factory).version is None
    assert repair_at(factory, WINDOW_END, alerts) == 1
    assert public(factory).view == "delayed" and len(alerts) == 1
    assert run("scheduled", factory, good_model).status == "skipped"
    assert run("manual", factory, good_model).status == "published"


def test_week_without_any_automatic_attempt_is_delayed_from_0021(factory):
    # The 00:00 attempt never ran (service down): from 00:21 KST (window end + one-minute
    # grace) the reconciler publishes the delay notice and alerts once.
    alerts = []
    assert week(factory) is None
    assert repair_at(factory, WINDOW_END + timedelta(seconds=59), alerts) == 0  # 00:20:59
    assert week(factory) is None and alerts == []
    assert repair_at(factory, WINDOW_END + timedelta(minutes=1), alerts) == 1  # 00:21:00
    assert repair_at(factory, WINDOW_END + timedelta(minutes=2), alerts) == 0
    delayed = public(factory)
    assert delayed.view == "delayed" and len(alerts) == 1
    assert "00:00-00:20" in alerts[0].error
    assert week(factory).status == "delayed" and week(factory).needs_manual
    assert week(factory).auto_attempts == 0
    assert run("manual", factory, good_model).status == "published"
    replaced = public(factory)
    assert replaced.view == "list" and replaced.version > delayed.version
    assert [item.rank for item in replaced.items] == [1, 2, 3]


def test_missed_week_found_before_the_week_ends_is_not_delayed_after_it(factory):
    # Found missing late on Sunday, decided after Monday 00:00 KST: that week is over, so
    # it gets no delay notice and no alert (and the new week is not touched either).
    sunday = NOW + timedelta(days=6, hours=23, minutes=59)
    times = iter([sunday, sunday, NOW + timedelta(days=7)])

    def clock():
        return next(times, NOW + timedelta(days=7))

    assert top5_selection.reconcile_attempts(
        session_factory=factory, clock=clock,
        alert=lambda notice: pytest.fail("no alert for a week that already ended"),
    ) == 0
    weeks = [NOW.date() + timedelta(days=1), NOW.date() + timedelta(days=8)]
    with factory() as session:
        assert session.query(Top5Publication).filter(
            Top5Publication.week_start.in_(weeks)
        ).count() == 0
    assert week(factory) is None


def test_reconciliation_respects_active_week_lock(factory):
    interrupted(factory, "scheduled", 1)
    with factory() as session:
        engine = session.get_bind().engine
    with top5_selection.week_lock(engine, NOW.date() + timedelta(days=1)) as acquired:
        assert acquired
        assert top5_selection.reconcile_attempts(
            session_factory=factory, clock=lambda: NOW + timedelta(minutes=6),
            alert=lambda notice: pytest.fail("no alert while another owner is active"),
        ) == 0
    assert week(factory).status == "running"


def test_old_week_recovery_does_not_add_public_version(factory):
    interrupted(factory, "scheduled", 1)
    now = NOW + timedelta(days=7)
    assert top5_selection.reconcile_attempts(
        session_factory=factory, clock=lambda: now,
        alert=lambda notice: pytest.fail("no old-week alert"),
    ) == 1
    with factory() as session:
        assert session.query(Top5Publication).filter_by(
            week_start=NOW.date() + timedelta(days=1),
        ).count() == 0
    assert not week(factory).needs_manual


def test_evidence_transaction_timeouts_survive_reopened_transaction(factory):
    with top5_selection._bounded_session(factory, lambda: NOW) as session:
        for _ in range(2):
            assert session.scalar(text("SHOW lock_timeout")) == "5s"
            assert session.scalar(text("SHOW statement_timeout")) == "5s"
            session.commit()


def test_interrupted_manual_recovery_keeps_the_held_delay(factory):
    alerts = []
    run("scheduled", factory, failing_model, alerts)
    with factory() as session:
        top5_selection._start(session, NOW.date() + timedelta(days=1), "manual", NOW, 20)
        session.commit()
    assert repair_at(factory, NOW + timedelta(minutes=1), alerts) == 1
    state = week(factory)
    assert state.status == "delayed" and state.auto_attempts == 1
    assert state.next_retry_at == WINDOW_END and alerts == []  # still held until 00:20
    assert repair_at(factory, WINDOW_END, alerts) == 1 and len(alerts) == 1
    assert run("manual", factory, good_model).status == "published"


def test_reviews_popular_and_latest_order_with_count(connection):
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        kickoff = NOW - timedelta(days=1)
        session.add(
            Fixture(
                id=BASE_ID + 50, competition_id=39, season=2026, kickoff_at=kickoff,
                kickoff_date_kst=kickoff.date(), status="finished", finish_type="normal",
                status_short_raw="FT", home_team_id=50, away_team_id=42, synced_at=NOW,
            )
        )
        session.flush()

        def review(label, minutes_ago, likes, dislikes):
            row = Review(
                user_id=uuid.uuid4(), fixture_id=BASE_ID + 50, body=f"r{label}",
                created_at=NOW - timedelta(minutes=minutes_ago),
                updated_at=NOW - timedelta(minutes=minutes_ago),
            )
            session.add(row)
            session.flush()
            for value, count in ((1, likes), (-1, dislikes)):
                for _ in range(count):
                    session.add(ReviewReaction(review_id=row.id, user_id=uuid.uuid4(), value=value))
            return row.id

        newest_few = review(5, 1, likes=2, dislikes=0)  # 2 reactions: not ranked by ratio
        ratio_high = review(4, 30, likes=3, dislikes=0)
        ratio_mid = review(2, 20, likes=4, dislikes=2)
        ratio_tie_more_likes = review(3, 40, likes=6, dislikes=0)
        session.flush()

        popular = list_reviews(session, BASE_ID + 50, "popular")
        assert [i.id for i in popular.items] == [
            ratio_tie_more_likes, ratio_high, ratio_mid, newest_few,
        ]
        latest = list_reviews(session, BASE_ID + 50, "latest")
        assert [i.id for i in latest.items] == [newest_few, ratio_mid, ratio_high,
                                                 ratio_tie_more_likes]
        # Text reviews only: the summary is the valid count, no average (REV-004).
        assert popular.summary.model_dump() == {"count": 4}
        assert "rating" not in popular.items[0].model_dump()
        assert list_reviews(session, BASE_ID + 51, "popular").summary.count == 0

        # The body is required and never blank, whatever the whitespace (migration 0015):
        # the DB agrees with Python's str.strip(), which chat 02 uses to validate.
        for body in (None, "   ", "\t\n", " ", "　 ", " \r\n"):
            with pytest.raises(IntegrityError), session.begin_nested():
                session.add(Review(user_id=uuid.uuid4(), fixture_id=BASE_ID + 50, body=body))
                session.flush()
        with session.begin_nested():
            session.add(Review(user_id=uuid.uuid4(), fixture_id=BASE_ID + 50, body=" 골!\n"))
            session.flush()


def test_answering_model_is_recorded(factory):
    def answered(prompt: str, timeout: float):
        answer, raw = good_model(prompt, timeout)
        return answer, {"model": "gemini-3.8-flash", **raw}

    outcome = run("scheduled", factory, answered)
    assert outcome.status == "published"
    with factory() as session:
        attempt = session.get(Top5Attempt, outcome.attempt_id)
        assert attempt.model == "gemini-3.8-flash"


def manual_running_through_0020(factory, monkeypatch, alerts, answer):
    """A manual recovery starts at 00:19:00 after the automatic failure; its model request is
    still open when 00:20 comes (the clock jumps there inside the request)."""
    monkeypatch.setattr(top5_selection, "HELD_POLL_SECONDS", 0.02)
    run("scheduled", factory, failing_model, alerts)
    clock = {"now": WINDOW_END - timedelta(minutes=1)}
    seen = {}

    def slow(prompt, timeout):
        clock["now"] = WINDOW_END + timedelta(seconds=5)
        time.sleep(0.4)  # the attempt thread shows the held delay meanwhile
        seen["alerts_during"] = len(alerts)
        return answer(prompt, timeout)

    outcome = run_attempt(
        "manual", session_factory=factory, client_factory=empty_client, generate=slow,
        alert=lambda notice: alerts.append(notice) or True,
        now=clock["now"], clock=lambda: clock["now"],
    )
    return outcome, seen


def kinds(factory):
    with factory() as session:
        rows = session.query(Top5Publication).filter_by(
            week_start=NOW.date() + timedelta(days=1)
        ).order_by(Top5Publication.version).all()
        return [row.kind for row in rows]


def test_running_manual_recovery_still_shows_the_delay_at_0020(factory, monkeypatch):
    # Starting a manual recovery must not cancel the held delay; at 00:20 it goes public
    # with one alert even though the recovery holds the week lock. A later success replaces it.
    alerts = []
    outcome, seen = manual_running_through_0020(factory, monkeypatch, alerts, good_model)
    assert seen["alerts_during"] == 1 and "503" in alerts[0].error
    assert outcome.status == "published" and len(alerts) == 1
    assert kinds(factory) == ["delayed", "list"]
    assert public(factory).view == "list" and week(factory).next_retry_at is None


def test_running_manual_recovery_failing_after_0020_keeps_one_delay(factory, monkeypatch):
    alerts = []
    outcome, seen = manual_running_through_0020(factory, monkeypatch, alerts, model_failing)
    assert seen["alerts_during"] == 1
    assert outcome.status == "failed" and outcome.alert_sent is None and len(alerts) == 1
    assert kinds(factory) == ["delayed"]
    assert week(factory).next_retry_at is None
    assert repair_at(factory, WINDOW_END + timedelta(minutes=1), alerts) == 0


def test_dead_manual_recovery_owner_still_shows_the_delay_at_0020(factory):
    # The process running the manual recovery died before its deadline (lock released):
    # the reconciler shows the held delay at 00:20 without waiting for the deadline.
    alerts = []
    run("scheduled", factory, failing_model, alerts)
    with factory() as session:
        top5_selection._start(
            session, NOW.date() + timedelta(days=1), "manual", WINDOW_END - timedelta(minutes=1),
            1200,
        )
        session.commit()
    assert week(factory).next_retry_at == WINDOW_END  # starting did not cancel the hold
    assert repair_at(factory, WINDOW_END - timedelta(seconds=1), alerts) == 0
    assert repair_at(factory, WINDOW_END, alerts) == 1 and len(alerts) == 1
    assert week(factory).status == "running" and kinds(factory) == ["delayed"]
    assert repair_at(factory, WINDOW_END + timedelta(minutes=1), alerts) == 0
