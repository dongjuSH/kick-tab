"""Chat 03 behaviour against the dev database (opt-in, always rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_schedule_db.py
Needs the reference job to have loaded competitions and five-league teams.
"""

import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.kst import kst_today
from app.models.fixture import Fixture
from app.models.match_detail import FixtureDetail, FixtureEvent
from app.models.reference import CompetitionSeason
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.services.fixtures import (
    fixtures_on,
    needs_live_sync,
    next_for_teams,
    overlaps,
    schedule_period,
    upsert_fixtures,
)
from app.services.match_detail import detail_fetch_due, ensure_records, store_fixture_records
from app.services.reference import managed_seasons
from app.services.team_search import search_teams
from app.sync import fixtures as fixture_jobs
from app.sync.fixtures import sync_fixtures
from app.sync.registry import JobContext, JobPartialFailure

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

CITY, ARSENAL, MADRID = 50, 42, 541
BASE_ID = 990_000_000


@pytest.fixture
def session():
    from app.db.session import get_engine

    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            yield Session(bind=connection, join_transaction_mode="create_savepoint")
        finally:
            transaction.rollback()


def item(fid, kickoff, short, home=CITY, away=ARSENAL, goals=(None, None), elapsed=None,
         penalty=(None, None), league=39):
    return {
        "fixture": {
            "id": BASE_ID + fid,
            "timestamp": int(kickoff.timestamp()),
            "status": {"short": short, "long": short, "elapsed": elapsed},
            "venue": {"name": "Test", "city": "Test"},
        },
        "league": {"id": league, "season": 2026, "round": "R1"},
        "teams": {
            "home": {"id": home, "name": "H", "logo": None},
            "away": {"id": away, "name": "A", "logo": None},
        },
        "goals": {"home": goals[0], "away": goals[1]},
        "score": {"penalty": {"home": penalty[0], "away": penalty[1]}},
    }


def test_schedule_by_kst_date_status_and_postponement(session):
    now = datetime.now(UTC)
    # 2026-11-xx 19:30 UTC = next day 04:30 KST: grouped under the KST date.
    day = kst_today() + timedelta(days=20)
    kickoff = datetime(day.year, day.month, day.day, 19, 30, tzinfo=UTC) - timedelta(days=1)
    upsert_fixtures(
        session,
        [
            item(1, kickoff, "NS"),
            item(2, kickoff + timedelta(minutes=5), "Canc", goals=(0, 0)),
            item(3, kickoff + timedelta(minutes=10), "PEN", goals=(1, 1), penalty=(4, 2)),
            item(4, kickoff + timedelta(minutes=15), "PST"),
        ],
        now,
    )
    session.flush()
    rows, updated = fixtures_on(session, day)
    mine = {m.id - BASE_ID: m for m in rows if m.id > BASE_ID}
    assert mine[1].status == "scheduled" and mine[1].kickoff_date_kst == day
    assert mine[2].status == "cancelled" and mine[2].score.home is None  # no 0:0
    assert (mine[3].finish_type, mine[3].score.penalty_home, mine[3].score.penalty_away) == (
        "pen", 4, 2,
    )
    assert mine[4].status == "postponed" and mine[4].time_confirmed is False
    assert mine[1].home.name_ko == "맨체스터 시티" and mine[1].home.detail_available is True
    assert updated == now

    # Rescheduled: same id, new date, shown once on the new date only (LIVE-002).
    upsert_fixtures(session, [item(4, kickoff + timedelta(days=2), "NS")], now)
    session.flush()
    old_day = {m.id for m in fixtures_on(session, day)[0]}
    new_day = {m.id for m in fixtures_on(session, day + timedelta(days=2))[0]}
    assert BASE_ID + 4 not in old_day and BASE_ID + 4 in new_day


def test_favorite_schedule_live_first_and_no_duplicate(session):
    now = datetime.now(UTC)
    upsert_fixtures(
        session,
        [
            item(11, now + timedelta(days=30), "NS", home=CITY, away=ARSENAL),
            item(12, now + timedelta(days=31), "NS", home=ARSENAL, away=MADRID),
            item(13, now - timedelta(minutes=40), "2H", home=MADRID, away=CITY, goals=(1, 0),
                 elapsed=63, league=2),
        ],
        now,
    )
    session.flush()
    # Only our synthetic fixtures are guaranteed; ignore real upcoming matches.
    teams, matches, _ = next_for_teams(session, [CITY, ARSENAL, MADRID], now)
    assert [t.id for t in teams] == [CITY, ARSENAL, MADRID]
    ids = [m.id for m in matches]
    assert len(ids) == len(set(ids))
    assert matches[0].status == "live" and matches[0].elapsed == 63


def test_team_search_aliases(session):
    names = [t.name_ko for t in search_teams(session, "맨시티")]
    assert names[0] == "맨체스터 시티"
    assert search_teams(session, "Man City")[0].id == CITY
    ambiguous = {t.name_ko for t in search_teams(session, "레알")}
    assert {"레알 마드리드", "레알 베티스", "레알 소시에다드"} <= ambiguous
    assert search_teams(session, "존재하지않는팀이름") == []


def test_fixtures_job_keeps_data_and_marks_failed_competition(session, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("league") == "39":
            return httpx.Response(200, json={"errors": {"requests": "fail"}, "response": []})
        return httpx.Response(200, json={"errors": [], "response": [], "results": 0})

    def fake_client(self, **_):
        client = ApiFootballClient(
            SecretStr("test"),
            transport=httpx.MockTransport(handler),
            limiter=MinuteRateLimiter(1000),
            budget=DailyBudget(1000),
        )
        self._clients.append(client)
        return client

    monkeypatch.setattr(JobContext, "api_football", fake_client)
    before = session.execute(text("SELECT count(*) FROM fixtures WHERE competition_id = 39"))
    count_before = before.scalar()
    ctx = JobContext(session=session, params={})
    with pytest.raises(JobPartialFailure) as caught:
        sync_fixtures(ctx)
    assert "39" in str(caught.value)
    epl = session.scalar(
        select(CompetitionSeason).where(
            CompetitionSeason.competition_id == 39, CompetitionSeason.season == 2026
        )
    )
    assert epl.fixtures_failed_at is not None
    after = session.execute(text("SELECT count(*) FROM fixtures WHERE competition_id = 39"))
    assert after.scalar() == count_before  # a failure never deletes stored matches
    assert ctx.api_requests == len(period_rows(session))


def period_rows(session):
    """One schedule request per managed competition season that can play in the period."""
    start, end = schedule_period(session).bounds()
    return [
        row for season in managed_seasons()
        for row in session.scalars(
            select(CompetitionSeason).where(
                CompetitionSeason.season == season, CompetitionSeason.availability == "available"
            )
        )
        if overlaps(row, start, end)
    ]


@pytest.fixture
def record_answers(session):
    now = datetime.now(UTC)
    kickoff = now - timedelta(hours=1)
    stored = item(101, kickoff, "2H")
    stored.update(
        events=[{"type": "Goal", "time": {"elapsed": 44}}],
        statistics=[{"team": {"id": CITY}}],
        lineups=[],
        players=[],
    )
    store_fixture_records(session, [stored], now - timedelta(minutes=15))
    upsert_fixtures(session, [item(101, kickoff, "FT")], now)
    broken = item(101, kickoff, "FT", away=CITY)
    broken.update(events=[], statistics=[], lineups=[], players=[])
    good = item(102, kickoff, "FT", goals=(2, 1))
    good.update(events=[{"type": "Goal", "time": {"elapsed": 55}}],
                statistics=[], lineups=[], players=[])
    return now, stored, broken, good


def _records_client(respond):
    return ApiFootballClient(
        SecretStr("test"),
        transport=httpx.MockTransport(respond),
        limiter=MinuteRateLimiter(1000),
        budget=DailyBudget(1000),
    )


def _event_minutes(session, fixture_id):
    return list(session.scalars(
        select(FixtureEvent.elapsed)
        .where(FixtureEvent.fixture_id == fixture_id)
        .order_by(FixtureEvent.seq)
    ))


@pytest.mark.parametrize("recovers", [True, False])
def test_live_sync_rechecks_rejected_fixture_by_id(session, monkeypatch, record_answers, recovers):
    _, stored, broken, good = record_answers
    bad_id, good_id = BASE_ID + 101, BASE_ID + 102
    calls = []

    def respond(request):
        assert request.url.path == "/fixtures"
        by_id = request.url.params.get("ids")
        calls.append(by_id)
        if by_id is None:
            # An invalid later copy of the good fixture must not wipe its valid detail either.
            bad_copy = {**good, "teams": broken["teams"], "events": []}
            response = [broken, good, bad_copy]
        else:
            response = [{**stored, "fixture": {
                **stored["fixture"], "status": {"short": "FT"},
            }}] if recovers else [broken]
        return httpx.Response(200, json={"errors": [], "response": response})

    monkeypatch.setattr(fixture_jobs, "live_targets", lambda *_: [bad_id, good_id])
    with _records_client(respond) as client:
        monkeypatch.setattr(JobContext, "api_football", lambda *args: client)
        ctx = JobContext(session=session, params={})
        if recovers:
            fixture_jobs.sync_live(ctx)
        else:
            with pytest.raises(JobPartialFailure, match=str(bad_id)):
                fixture_jobs.sync_live(ctx)

    assert calls == [None, str(bad_id)]
    assert _event_minutes(session, bad_id) == [44]
    assert _event_minutes(session, good_id) == [55]
    assert session.get(Fixture, bad_id).away_team_id == ARSENAL
    assert session.get(FixtureDetail, bad_id).fetched_status == ("finished" if recovers else "live")


@pytest.mark.parametrize("source", ["final_job", "on_demand"])
def test_rejected_fixture_keeps_records_and_remains_retryable(
    session, monkeypatch, record_answers, source
):
    now, stored, broken, good = record_answers
    bad_id, good_id = BASE_ID + 101, BASE_ID + 102
    lookup_key = "ids" if source == "final_job" else "id"
    lookup = f"{bad_id}-{good_id}" if source == "final_job" else str(bad_id)

    def respond(request):
        assert request.url.path == "/fixtures"
        assert request.url.params[lookup_key] == lookup
        response = [broken, good] if source == "final_job" else [broken]
        return httpx.Response(200, json={"errors": [], "response": response})

    if source == "final_job":
        monkeypatch.setattr(fixture_jobs, "final_record_targets", lambda *_: [bad_id, good_id])
        with _records_client(respond) as client:
            monkeypatch.setattr(JobContext, "api_football", lambda *args: client)
            with pytest.raises(JobPartialFailure, match=f"Failed fixtures: {bad_id}$"):
                fixture_jobs.sync_final_records(JobContext(session=session, params={}))
        assert _event_minutes(session, good_id) == [55]
        assert session.get(FixtureDetail, good_id).fetched_status == "finished"
    else:
        ensure_records(session, session.get(Fixture, bad_id), now, lambda: _records_client(respond))

    row = session.get(FixtureDetail, bad_id)
    assert row.statistics == stored["statistics"]
    assert row.fetched_status == "live"
    assert row.fetched_at == now - timedelta(minutes=15)
    assert row.last_failed_at is not None
    assert _event_minutes(session, bad_id) == [44]
    assert detail_fetch_due(session.get(Fixture, bad_id), row, now + timedelta(minutes=11))


def _at(day, hour=12, minute=0):  # 12:00 UTC = 21:00 KST the same calendar day
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)


def _after_every_stored_match(session, days):
    """A day far enough after every stored match that only test rows shape the period."""
    last = session.scalar(select(func.max(Fixture.kickoff_date_kst))) or kst_today()
    return max(last, kst_today()) + timedelta(days=days)


def test_period_is_three_past_match_days_today_and_seventeen_ahead(session):
    now = datetime.now(UTC)
    today = _after_every_stored_match(session, 60)
    yesterday = today - timedelta(days=1)
    rows = [
        # KST midnight: 14:59 UTC is still yesterday in Korea, 15:00 UTC is already today.
        item(41, _at(yesterday, 14, 59), "FT"),
        item(42, _at(yesterday, 15), "NS"),
        item(43, _at(today - timedelta(days=2)), "FT"),
        item(44, _at(today - timedelta(days=3)), "Canc"),  # a cancelled match is no match day
        item(45, _at(today - timedelta(days=5)), "FT"),
        item(46, _at(today - timedelta(days=9)), "FT"),  # fourth past match day: left out
        item(47, _at(today - timedelta(days=2), 13), "FT"),  # same day twice counts once
    ]
    rows += [item(50 + n, _at(today + timedelta(days=n)), "NS") for n in range(1, 19)]
    upsert_fixtures(session, rows, now)
    session.flush()

    period = schedule_period(session, today)
    ahead = [today + timedelta(days=n) for n in range(1, 18)]  # the 18th day is left out
    assert period.dates == (
        today - timedelta(days=5), today - timedelta(days=2), yesterday, today, *ahead
    )
    assert period.bounds() == (today - timedelta(days=5), today + timedelta(days=17))

    # A day without a match: no "today" entry, and the range still includes today.
    later = today + timedelta(days=40)
    empty = schedule_period(session, later)
    assert later not in empty.dates and len(empty.dates) == 3
    assert empty.end == today + timedelta(days=18) and empty.bounds()[1] == later


def test_team_schedule_covers_the_common_period(session):
    from app.services.fixtures import team_schedule

    now = datetime.now(UTC)
    start, end = schedule_period(session).bounds()
    upsert_fixtures(
        session,
        [
            item(21, _at(start - timedelta(days=1)), "FT", goals=(1, 0)),
            item(22, _at(start), "NS"),  # first day of the period: in
            item(23, _at(end), "NS", league=2),  # last day: in
            item(24, _at(end + timedelta(days=1)), "NS"),
        ],
        now,
    )
    session.flush()
    team, matches, _ = team_schedule(session, CITY, start, end)
    mine = [m.id - BASE_ID for m in matches if m.id > BASE_ID]
    assert team.id == CITY and mine == [22, 23]
    assert all(start <= m.kickoff_date_kst <= end for m in matches)
    assert [m.kickoff_at for m in matches] == sorted(m.kickoff_at for m in matches)


def test_availability_keeps_uncovered_dates_separate_from_stored_games(session):
    from app.services.fixtures import fixture_availability

    now = datetime.now(UTC)
    # A month after every stored match (any competition, any season): no real game is on
    # these days, whatever the collected schedule holds (the whole season is stored since 05).
    day = _after_every_stored_match(session, 30)
    covered = day + timedelta(days=1)
    row = session.get(CompetitionSeason, (39, 2026))
    row.fixtures_window_start = row.fixtures_window_end = covered
    row.fixtures_synced_at = now
    row.fixtures_failed_at = None
    # Outside the 30-minute job's window the whole-season load decides: its last run failed.
    row.season_fixtures_failed_at = now
    row.end_date = covered  # the season still plays then (dates after every stored match)
    kickoff = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
    upsert_fixtures(session, [item(31, kickoff, "NS")], now)
    session.flush()
    first, second = fixture_availability(session, [day, covered])
    assert 39 in first[1] and 39 in first[2]  # a stored game cannot prove full coverage
    assert 39 not in second[1] and 39 not in second[2]  # the job confirmed it empty
    # Once the season load succeeds again, the day outside the job window is confirmed too.
    row.season_fixtures_synced_at = now + timedelta(seconds=1)
    session.flush()
    assert 39 not in fixture_availability(session, [day])[0][2]


def test_news_cap_applies_before_badge_filter_and_cursor(session):
    from app.models.news import NewsArticle
    from app.services.news import list_news

    now = datetime.now(UTC)
    session.add_all([
        NewsArticle(
            url_hash=f"{i + BASE_ID:064x}", url=f"https://example.com/news/{i}",
            title=f"News test {i}", source_domain="example.com",
            published_at=now + timedelta(minutes=i), fetched_at=now,
            expires_at=now + timedelta(hours=1), badge="EPL" if i < 4 else "UEFA",
        )
        for i in range(52)
    ])
    session.flush()
    first, cursor, total = list_news(session, now, badge=None, size=24, cursor=None)
    second, cursor, second_total = list_news(session, now, badge=None, size=24, cursor=cursor)
    assert total == second_total == len({a.id for a in first + second}) == 48
    assert cursor is None
    assert list_news(session, now, badge="EPL", size=24, cursor=None) == ([], None, 0)


def test_current_season_state_trusts_the_season_load_for_unjobbed_competitions(session):
    """A competition the 30-minute job never had to ask (no match in the period, e.g. a super
    cup months away) is not "unconfirmed" while its season load is fine (2026-11-19)."""
    from app.services.fixtures import sync_state

    now = datetime.now(UTC)
    row = session.get(CompetitionSeason, (547, 2026))
    if row is None or row.availability != "available":
        pytest.skip("Italian Super Cup 2026 not loaded")
    row.fixtures_synced_at = row.fixtures_failed_at = None
    row.season_fixtures_synced_at, row.season_fixtures_failed_at = now, None
    session.flush()
    assert 547 not in sync_state(session).failed_competition_ids
    row.season_fixtures_failed_at = now + timedelta(seconds=1)  # season load failed
    session.flush()
    assert 547 in sync_state(session).failed_competition_ids
    row.fixtures_synced_at, row.fixtures_failed_at = now, now + timedelta(seconds=2)
    session.flush()
    assert 547 in sync_state(session).failed_competition_ids  # a failed job run still counts


def test_failed_refresh_after_a_success_is_not_never_collected(session):
    """Both refreshes failing after earlier successes keeps the stored matches with the
    failure meta instead of "never collected" (Codex N1, 2026-11-19)."""
    from app.services.fixtures import sync_state

    later = datetime.now(UTC) + timedelta(hours=1)
    rows = list(session.scalars(
        select(CompetitionSeason).where(CompetitionSeason.availability == "available")
    ))
    if not any(r.fixtures_synced_at or r.season_fixtures_synced_at for r in rows):
        pytest.skip("nothing collected yet")
    for row in rows:
        row.fixtures_failed_at = row.season_fixtures_failed_at = later
    session.flush()
    start, end = schedule_period(session).bounds()
    state = sync_state(session, window=(start, end))
    assert not state.never_synced
    assert state.failed_competition_ids


def test_no_match_day_with_every_window_competition_failed_is_unavailable(session):
    """A day without stored matches whose every competition failed is "not collected" (503),
    even when a competition outside that day (e.g. a super cup months away) is fine
    (Codex 2차 N8, 2026-11-19)."""
    from app.api.errors import ApiError
    from app.api.routes.schedule import read_fixtures
    from app.services.fixtures import sync_state

    start, end = schedule_period(session).bounds()
    played = set(session.scalars(
        select(Fixture.kickoff_date_kst).where(Fixture.kickoff_date_kst.between(start, end))
    ))
    empty = next(
        (start + timedelta(days=n) for n in range((end - start).days + 1)
         if start + timedelta(days=n) not in played),
        None,
    )
    if empty is None:
        pytest.skip("every calendar day of the period has a stored match")
    rows = list(session.scalars(
        select(CompetitionSeason).where(CompetitionSeason.availability == "available")
    ))
    if not any(r.fixtures_synced_at or r.season_fixtures_synced_at for r in rows):
        pytest.skip("nothing collected yet")
    later = datetime.now(UTC) + timedelta(hours=1)
    state = sync_state(session, window=(empty, empty))
    relevant = set(state.relevant_competition_ids)
    assert relevant
    for row in rows:
        if row.competition_id in relevant:
            row.fixtures_failed_at = row.season_fixtures_failed_at = later
    session.flush()
    state = sync_state(session, window=(empty, empty))
    assert state.all_failed and not state.never_synced
    with pytest.raises(ApiError) as caught:
        read_fixtures(db=session, day=empty)
    assert caught.value.status_code == 503

    # One competition of that day confirmed again: an empty day with the failure meta.
    back = next(
        (r for r in rows if r.competition_id in relevant and r.season_fixtures_synced_at
         and r.fixtures_synced_at),
        None,
    )
    if back is None:
        return
    back.fixtures_failed_at = back.season_fixtures_failed_at = None
    session.flush()
    assert not sync_state(session, window=(empty, empty)).all_failed
    response = read_fixtures(db=session, day=empty)
    assert response.data == [] and response.meta.failed_competition_ids


@pytest.mark.parametrize("collected", [True, False])
def test_day_outside_every_season_is_empty_only_after_collection(session, collected):
    """No relevant season is a normal empty day, except before anything was collected (N11)."""
    from app.api.errors import ApiError
    from app.api.routes.schedule import read_fixtures
    from app.services.fixtures import sync_state

    start, end = schedule_period(session).bounds()
    played = set(session.scalars(
        select(Fixture.kickoff_date_kst).where(Fixture.kickoff_date_kst.between(start, end))
    ))
    empty = next(
        (start + timedelta(days=n) for n in range((end - start).days + 1)
         if start + timedelta(days=n) not in played),
        None,
    )
    if empty is None:
        pytest.skip("every calendar day of the period has a stored match")

    rows = list(session.scalars(select(CompetitionSeason)))
    for row in rows:
        row.start_date = start - timedelta(days=30)
        row.end_date = empty - timedelta(days=1)
        row.fixtures_synced_at = row.season_fixtures_synced_at = None
        row.fixtures_failed_at = row.season_fixtures_failed_at = None
    if collected:
        session.get(CompetitionSeason, (39, 2026)).season_fixtures_synced_at = datetime.now(UTC)
    session.flush()

    state = sync_state(session, window=(empty, empty))
    assert state.relevant_competition_ids == () and not state.all_failed
    assert state.never_synced is not collected
    if collected:
        response = read_fixtures(db=session, day=empty)
        assert response.data == [] and response.meta.failed_competition_ids == []
    else:
        with pytest.raises(ApiError) as caught:
            read_fixtures(db=session, day=empty)
        assert caught.value.status_code == 503


def test_live_sync_starts_at_kickoff_and_names_a_break(session):
    # Far ahead of real data: only this test's fixture counts.
    day = kst_today() + timedelta(days=400)
    kickoff = datetime(day.year, day.month, day.day, 3, 7, tzinfo=UTC)
    now = datetime.now(UTC)
    # Real matches live right now would keep the job on: out of scope (rolled back).
    session.execute(text("UPDATE fixtures SET status = 'finished' WHERE status = 'live'"))
    upsert_fixtures(session, [item(31, kickoff, "NS")], now)
    session.flush()
    # Not before kickoff: `/fixtures?live=` lists started matches only (2026-11-22).
    assert not needs_live_sync(session, kickoff - timedelta(minutes=30))
    assert not needs_live_sync(session, kickoff - timedelta(seconds=1))
    assert needs_live_sync(session, kickoff)
    assert needs_live_sync(session, kickoff + timedelta(hours=2, minutes=59))
    assert not needs_live_sync(session, kickoff + timedelta(hours=3, minutes=1))

    def shown(short, elapsed):
        upsert_fixtures(session, [item(31, kickoff, short, goals=(1, 0), elapsed=elapsed)], now)
        session.flush()
        match = next(m for m in fixtures_on(session, kickoff.date())[0] if m.id == BASE_ID + 31)
        return match.status, match.elapsed, match.live_break

    assert shown("1H", 30) == ("live", 30, None)
    assert shown("HT", 45) == ("live", 45, "half_time")
    assert shown("BT", 90) == ("live", 90, "extra_time")
    assert shown("2H", 50) == ("live", 50, None)
    assert shown("FT", 90) == ("finished", None, None)
