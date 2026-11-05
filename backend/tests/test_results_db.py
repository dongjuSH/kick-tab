"""Chat 05 past results against the dev database (opt-in, always rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_results_db.py
Needs the reference job and both seasons' `fixtures_season` loads.
"""

import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.fixture import Fixture
from app.models.reference import CompetitionSeason
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.services.fixtures import upsert_fixtures
from app.services.results import finished_results, season_coverage, supported_seasons
from app.services.team_search import search_teams
from app.sync.fixtures import sync_season_fixtures
from app.sync.reference import _save_season
from app.sync.registry import JobContext, JobPartialFailure

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

CITY, ARSENAL, WEST_HAM = 50, 42, 48
BASE_ID = 991_000_000


@pytest.fixture
def session():
    from app.db.session import get_engine

    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            yield Session(bind=connection, join_transaction_mode="create_savepoint")
        finally:
            transaction.rollback()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def item(fid, kickoff, short, goals=(1, 0), penalty=(None, None), league=39, season=2025,
         home=CITY, away=ARSENAL):
    return {
        "fixture": {
            "id": BASE_ID + fid,
            "timestamp": int(kickoff.timestamp()),
            "status": {"short": short, "long": short, "elapsed": None},
            "venue": {"name": "Test", "city": "Test"},
        },
        "league": {"id": league, "season": season, "round": "R1"},
        "teams": {
            "home": {"id": home, "name": "H", "logo": None},
            "away": {"id": away, "name": "A", "logo": None},
        },
        "goals": {"home": goals[0], "away": goals[1]},
        "score": {"penalty": {"home": penalty[0], "away": penalty[1]}},
    }


def test_seasons_are_both_offered_newest_first(session):
    seasons = supported_seasons(session)
    assert [(s.season, s.label, s.current) for s in seasons][:2] == [
        (2026, "2026-27", True), (2025, "2025-26", False),
    ]


def test_only_finished_matches_newest_first_with_rulings_kept(session):
    # A late-June 2026 date after every real 2025-26 match, so these are the newest rows.
    base = datetime(2026, 6, 28, 12, tzinfo=UTC)
    upsert_fixtures(
        session,
        [
            item(1, base, "FT"),
            item(2, base + timedelta(hours=1), "AWD", goals=(0, 0)),
            item(3, base + timedelta(hours=2), "PEN", goals=(1, 1), penalty=(4, 2)),
            item(4, base + timedelta(hours=3), "NS", goals=(None, None)),
            item(5, base + timedelta(hours=4), "PST", goals=(None, None)),
            item(6, base + timedelta(hours=5), "CANC", goals=(None, None)),
            item(7, base + timedelta(hours=6), "ABD", goals=(0, 1)),
            item(8, base + timedelta(hours=7), "1H", goals=(0, 0)),
        ],
        datetime.now(UTC),
    )
    session.flush()
    matches, total, _ = finished_results(session, 2025, team_id=CITY, competition_ids=[39])
    mine = [m for m in matches if m.id > BASE_ID]
    assert [m.id - BASE_ID for m in mine] == [3, 2, 1]  # newest first, finished only
    assert mine[1].finish_type == "awarded" and mine[1].score.home == 0  # never a plain draw
    assert (mine[0].score.penalty_home, mine[0].score.penalty_away) == (4, 2)
    assert total >= 3


def test_seasons_never_mix_and_pages_split(session):
    base = datetime(2026, 6, 28, 12, tzinfo=UTC)
    upsert_fixtures(session, [item(11, base, "FT", season=2026)], datetime.now(UTC))
    session.flush()
    old, _, _ = finished_results(session, 2025, team_id=CITY, competition_ids=[39])
    assert BASE_ID + 11 not in {m.id for m in old}

    first, total, _ = finished_results(session, 2025, page=1)
    second, _, _ = finished_results(session, 2025, page=2)
    last_page = (total + 9) // 10
    last, _, _ = finished_results(session, 2025, page=last_page)
    beyond, _, _ = finished_results(session, 2025, page=last_page + 1)
    assert len(first) == 10 and not {m.id for m in first} & {m.id for m in second}
    assert 1 <= len(last) <= 10 and beyond == []
    assert first[0].kickoff_at >= second[0].kickoff_at


def test_past_team_is_searchable_in_its_season_without_team_detail(session):
    found = search_teams(session, "웨스트햄", season=2025)
    assert [t.id for t in found] == [WEST_HAM] and found[0].detail_available is False
    assert {t.id for t in search_teams(session, "West Ham", season=2025)} == {WEST_HAM}
    # An ambiguous alias lists every candidate of that season.
    assert {541, 543, 548} <= {t.id for t in search_teams(session, "레알", season=2025)}


def test_results_api_states(client, session):
    body = client.get("/api/v1/results", params={"season": 2025, "team": WEST_HAM}).json()
    assert body["data"]["team"]["detailAvailable"] is False
    assert body["meta"]["size"] == 10 and body["meta"]["total"] > 0
    assert all(m["status"] == "finished" for m in body["data"]["matches"])

    unsupported = client.get("/api/v1/results", params={"season": 2019})
    assert unsupported.status_code == 404  # never replaced by another season
    assert client.get("/api/v1/teams/search", params={"q": "a", "season": 2019}).status_code == 404
    assert client.get("/api/v1/results", params={"competitions": "1,39"}).status_code == 422
    assert client.get("/api/v1/results", params={"team": 999_999_999}).status_code == 404

    # Whole-season lists never loaded: "not collected", not "no results".
    session.execute(
        CompetitionSeason.__table__.update()
        .where(CompetitionSeason.season == 2025)
        .values(season_fixtures_synced_at=None)
    )
    session.flush()
    assert client.get("/api/v1/results", params={"season": 2025}).status_code == 503


def test_season_job_failure_keeps_rows_and_rerun_never_duplicates(session, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        league = request.url.params.get("league")
        if league == "39":
            return httpx.Response(200, json={"errors": {"requests": "fail"}, "response": []})
        kickoff = datetime(2026, 5, 1, 12, tzinfo=UTC)
        payload = [item(100, kickoff, "FT", league=int(league))] if league == "45" else []
        return httpx.Response(200, json={"errors": [], "response": payload, "results": 0})

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

    def count(league):
        return session.scalar(
            select(func.count()).select_from(Fixture)
            .where(Fixture.season == 2025, Fixture.competition_id == league)
        )

    epl_before, cup_before = count(39), count(45)
    for _ in range(2):
        ctx = JobContext(session=session, params={"season": "2025"})
        with pytest.raises(JobPartialFailure) as caught:
            sync_season_fixtures(ctx)
        assert "39" in str(caught.value) and ctx.api_requests == 14
    assert count(39) == epl_before  # a failure never deletes or overwrites stored matches
    assert count(45) == cup_before + 1  # two runs, one row
    coverage = season_coverage(session, 2025)
    assert 39 in coverage.failed_ids and 45 not in coverage.failed_ids


def test_competition_without_data_in_season_is_empty_not_an_error(client, session):
    # Season change keeps competitions (HIST-002): a kept competition the provider has no
    # data for in that season is answered normally, never 422 or "not collected" (503).
    session.execute(
        CompetitionSeason.__table__.update()
        .where(CompetitionSeason.competition_id == 66, CompetitionSeason.season == 2025)
        .values(availability="no_data")
    )
    session.flush()
    only = client.get("/api/v1/results", params={"season": 2025, "competitions": "66"})
    # Stored rows stay (never deleted); the competition is not reported as "not collected".
    assert only.status_code == 200 and only.json()["meta"]["failedCompetitionIds"] == []
    mixed = client.get("/api/v1/results", params={"season": 2025, "competitions": "66,39"})
    assert mixed.status_code == 200 and mixed.json()["meta"]["total"] > 0
    assert mixed.json()["meta"]["failedCompetitionIds"] == []


def test_loaded_season_never_turns_into_no_data(session):
    # A /leagues answer that leaves out an already loaded season keeps it offered (CMP-004).
    _save_season(session, 39, 2025, {"seasons": []})
    session.flush()
    row = session.scalar(
        select(CompetitionSeason).where(
            CompetitionSeason.competition_id == 39, CompetitionSeason.season == 2025
        )
    )
    session.refresh(row)
    assert row.availability == "available" and row.start_date is not None
    # A season never loaded follows the provider answer as before.
    session.execute(
        CompetitionSeason.__table__.update()
        .where(CompetitionSeason.competition_id == 39, CompetitionSeason.season == 2025)
        .values(season_fixtures_synced_at=None)
    )
    _save_season(session, 39, 2025, {"seasons": []})
    session.flush()
    session.refresh(row)
    assert row.availability == "no_data"


def test_season_job_refuses_unmanaged_seasons(session):
    with pytest.raises(JobPartialFailure):
        sync_season_fixtures(JobContext(session=session, params={"season": "2019"}))


# ---- Codex cross-check follow-ups (2026-11-05) ----------------------------------------

NEW_TEAM = 999_999_901  # not in the DB


def _mark(session, season, values, competition_id=None):
    stmt = CompetitionSeason.__table__.update().where(CompetitionSeason.season == season)
    if competition_id is not None:
        stmt = stmt.where(CompetitionSeason.competition_id == competition_id)
    session.execute(stmt.values(**values))
    session.flush()


def _fake_client(handler):
    def build(self, **_):
        client = ApiFootballClient(
            SecretStr("test"),
            transport=httpx.MockTransport(handler),
            limiter=MinuteRateLimiter(1000),
            budget=DailyBudget(1000),
        )
        self._clients.append(client)
        return client

    return build


def _nameless(fixture):
    fixture["teams"]["home"]["name"] = None
    return fixture


def _state(session, competition_id, season):
    row = session.scalar(
        select(CompetitionSeason).where(
            CompetitionSeason.competition_id == competition_id,
            CompetitionSeason.season == season,
        )
    )
    session.refresh(row)
    return row


def _count(session, season, competition_id):
    return session.scalar(
        select(func.count()).select_from(Fixture).where(
            Fixture.season == season, Fixture.competition_id == competition_id
        )
    )


def test_failed_refresh_keeps_results_but_never_loaded_is_503(client, session):
    stored = session.scalar(
        select(func.count()).select_from(Fixture).where(
            Fixture.season == 2025, Fixture.competition_id == 39, Fixture.status == "finished"
        )
    )
    later = datetime.now(UTC) + timedelta(minutes=1)
    # One loaded competition fails its refresh: stored results stay, flagged as incomplete.
    _mark(session, 2025, {"season_fixtures_failed_at": later}, competition_id=39)
    one = client.get("/api/v1/results", params={"season": 2025, "competitions": "39"})
    assert one.status_code == 200
    assert one.json()["meta"]["total"] == stored
    assert one.json()["meta"]["failedCompetitionIds"] == [39]
    partial = client.get("/api/v1/results", params={"season": 2025}).json()["meta"]
    assert partial["failedCompetitionIds"] == [39] and partial["total"] > stored

    # Every competition's refresh fails: still the stored season, every id flagged.
    _mark(session, 2025, {"season_fixtures_failed_at": later})
    every = client.get("/api/v1/results", params={"season": 2025})
    assert every.status_code == 200 and every.json()["meta"]["total"] == partial["total"]
    assert len(every.json()["meta"]["failedCompetitionIds"]) == 14

    # Never loaded successfully: "not collected" (503) when nothing in scope was loaded.
    _mark(session, 2025, {"season_fixtures_synced_at": None}, competition_id=39)
    first = client.get("/api/v1/results", params={"season": 2025, "competitions": "39"})
    assert first.status_code == 503
    mixed = client.get("/api/v1/results", params={"season": 2025, "competitions": "39,140"})
    assert mixed.status_code == 200 and 39 in mixed.json()["meta"]["failedCompetitionIds"]


def test_new_team_without_a_name_skips_only_its_fixture(session):
    from app.models.reference import Team

    base = datetime(2026, 6, 20, 12, tzinfo=UTC)
    city_name = session.get(Team, CITY).name_en
    nameless_new = _nameless(item(201, base, "FT", home=NEW_TEAM))
    nameless_known = _nameless(item(202, base, "FT"))  # stored team sent without a name
    saved = upsert_fixtures(session, [nameless_new, nameless_known], base)
    session.flush()
    assert saved == 1
    assert session.get(Team, NEW_TEAM) is None  # no invented team row
    assert session.get(Team, CITY).name_en == city_name  # the stored name is kept
    # A valid fixture in the same answer is stored as before.
    assert upsert_fixtures(session, [item(200, base, "FT"), nameless_new], base) == 1
    session.flush()
    stored = set(session.scalars(select(Fixture.id).where(Fixture.id >= BASE_ID + 200)))
    assert stored == {BASE_ID + 200, BASE_ID + 202}


def test_season_job_records_partial_and_save_failures_and_continues(session, monkeypatch):
    import app.sync.fixtures as fixtures_job

    base = datetime(2026, 6, 21, 12, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        league = int(request.url.params.get("league"))
        payload = []
        if league == 39:
            payload = [item(300, base, "FT"), _nameless(item(301, base, "FT", home=NEW_TEAM))]
        elif league == 45:
            payload = [item(310, base, "FT", league=45)]
        elif league == 140:
            payload = [item(320, base, "FT", league=140, home=541, away=529)]
        return httpx.Response(
            200, json={"errors": [], "response": payload, "results": len(payload)}
        )

    real_upsert = fixtures_job.upsert_fixtures

    def flaky_upsert(session_, items, now):
        result = real_upsert(session_, items, now)
        if any((i.get("league") or {}).get("id") == 45 for i in items):
            raise fixtures_job.SQLAlchemyError("simulated save failure")  # after writing
        return result

    monkeypatch.setattr(JobContext, "api_football", _fake_client(handler))
    monkeypatch.setattr(fixtures_job, "upsert_fixtures", flaky_upsert)
    cup_before = _count(session, 2025, 45)

    ctx = JobContext(session=session, params={"season": "2025"})
    with pytest.raises(JobPartialFailure) as caught:
        sync_season_fixtures(ctx)
    assert "39" in str(caught.value) and "45" in str(caught.value)
    assert ctx.api_requests == 14  # every competition was still processed

    epl, cup, liga = (_state(session, cid, 2025) for cid in (39, 45, 140))
    # Partly stored answer: the valid fixture is kept, the list is not reported complete.
    assert epl.season_fixtures_failed_at > epl.season_fixtures_synced_at
    assert session.get(Fixture, BASE_ID + 300) is not None
    assert session.get(Fixture, BASE_ID + 301) is None
    # Save failure: that batch is rolled back, stored rows stay, the failure is recorded.
    assert session.get(Fixture, BASE_ID + 310) is None
    assert _count(session, 2025, 45) == cup_before
    assert cup.season_fixtures_failed_at > cup.season_fixtures_synced_at
    # The competitions after it went on normally.
    assert session.get(Fixture, BASE_ID + 320) is not None
    coverage = season_coverage(session, 2025)
    assert {39, 45} <= set(coverage.failed_ids) and 140 not in coverage.failed_ids
    assert liga.season_fixtures_synced_at is not None


def test_schedule_job_marks_a_partly_stored_competition(session, monkeypatch):
    # Chat 03 path: skipping a nameless new team must not look like a complete schedule.
    from app.sync.fixtures import sync_fixtures

    kickoff = datetime.now(UTC) + timedelta(days=2)

    def handler(request: httpx.Request) -> httpx.Response:
        payload = []
        if request.url.params.get("league") == "39":
            payload = [_nameless(item(401, kickoff, "NS", season=2026, home=NEW_TEAM,
                                      goals=(None, None)))]
        return httpx.Response(
            200, json={"errors": [], "response": payload, "results": len(payload)}
        )

    monkeypatch.setattr(JobContext, "api_football", _fake_client(handler))
    ctx = JobContext(session=session, params={})
    with pytest.raises(JobPartialFailure) as caught:
        sync_fixtures(ctx)
    assert "39" in str(caught.value) and ctx.api_requests == 14
    epl = _state(session, 39, 2026)
    assert epl.fixtures_failed_at > epl.fixtures_synced_at
    assert session.get(Fixture, BASE_ID + 401) is None
