"""Chat 03 behaviour against the dev database (opt-in, always rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_schedule_db.py
Needs the reference job to have loaded competitions and five-league teams.
"""

import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.kst import kst_today
from app.models.reference import CompetitionSeason
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.services.fixtures import fixtures_on, next_for_teams, upsert_fixtures
from app.services.team_search import search_teams
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
    assert ctx.api_requests == 14


def test_team_schedule_covers_the_same_three_weeks_as_date_view(session):
    from app.services.fixtures import team_schedule, team_schedule_window

    now = datetime.now(UTC)
    start, end = team_schedule_window()
    assert (end - start).days == 20

    def at(day, hour=12):  # 12:00 UTC = 21:00 KST the same calendar day
        return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)

    upsert_fixtures(
        session,
        [
            item(21, at(start - timedelta(days=1)), "FT", goals=(1, 0)),
            item(22, at(start), "NS"),  # today−3: in
            item(23, at(end), "NS", league=2),  # today+17: in
            item(24, at(end + timedelta(days=1)), "NS"),
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
    day = kst_today() + timedelta(days=20)
    covered = day + timedelta(days=1)
    row = session.get(CompetitionSeason, (39, 2026))
    row.fixtures_window_start = row.fixtures_window_end = covered
    row.fixtures_synced_at = now
    row.fixtures_failed_at = None
    kickoff = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
    upsert_fixtures(session, [item(31, kickoff, "NS")], now)
    session.flush()
    first, second = fixture_availability(session, day, covered)
    assert 39 in first[1] and 39 in first[2]  # a stored game cannot prove full coverage
    assert 39 not in second[1] and 39 not in second[2]  # confirmed empty


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
