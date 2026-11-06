"""Chat 06 standings and player rankings against the dev database (opt-in, rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_standings_db.py
Needs `reference`, `fixtures_season`, `standings`, `player_rankings` and `player_stats` for
2025 and 2026 (guide §6.5).
"""

import os
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.reference import TeamCompetitionSeason
from app.models.standings import LeagueSync, PlayerRanking, PlayerSeasonStat, Standing
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.sync.registry import JobContext, JobPartialFailure
from app.sync.standings import sync_player_rankings, sync_player_stats, sync_standings

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)


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


def _count(session, model, league, season, **where):
    return session.scalar(
        select(func.count()).select_from(model).where(
            model.competition_id == league,
            model.season == season,
            *(getattr(model, k) == v for k, v in where.items()),
        )
    )


def test_tables_of_both_seasons_are_served_as_given(client):
    for league, teams in ((39, 20), (140, 20), (135, 20), (78, 18), (61, 18)):
        for season in (2025, 2026):
            body = client.get("/api/v1/standings", params={"league": league, "season": season})
            assert body.status_code == 200
            rows = body.json()["data"]["groups"][0]["rows"]
            assert len(rows) == teams
            assert [r["rank"] for r in rows] == list(range(1, teams + 1))
    ligue1 = client.get("/api/v1/standings", params={"league": 61, "season": 2025}).json()
    rows = {r["team"]["id"]: r for r in ligue1["data"]["groups"][0]["rows"]}
    assert rows[83]["played"] == 33  # Nantes: the provider's 33 is kept
    assert rows[83]["zone"] == "relegation" and rows[83]["team"]["detailAvailable"] is False
    assert rows[84]["zone"] == "relegation_playoff"  # Nice, 2025-26
    assert rows[85]["team"]["detailAvailable"] is True  # PSG is a current league team


def test_cups_and_unsupported_seasons_are_refused(client):
    assert client.get("/api/v1/standings", params={"league": 45}).status_code == 404
    assert client.get("/api/v1/standings", params={"league": 2}).status_code == 404
    assert client.get("/api/v1/standings", params={"league": 39, "season": 2019}).status_code == 404
    bad_type = client.get("/api/v1/player-rankings", params={"league": 39, "type": "fouls"})
    assert bad_type.status_code == 422


def test_summary_has_five_leagues_with_six_rows(client):
    body = client.get("/api/v1/standings/summary").json()["data"]
    assert body["season"]["current"] is True
    assert [item["league"]["id"] for item in body["leagues"]] == [39, 140, 135, 78, 61]
    assert all(item["status"] == "available" and len(item["rows"]) == 6 for item in body["leagues"])


def test_top_lists_are_twenty_in_provider_order(client, session):
    for kind in ("goals", "assists", "yellow", "red"):
        body = client.get(
            "/api/v1/player-rankings", params={"league": 39, "season": 2025, "type": kind}
        ).json()["data"]
        stored = session.scalars(
            select(PlayerRanking.player_id).where(
                PlayerRanking.competition_id == 39,
                PlayerRanking.season == 2025,
                PlayerRanking.type == kind,
            ).order_by(PlayerRanking.position)
        ).all()
        assert [i["player"]["id"] for i in body["items"]] == stored and len(stored) == 20
        assert [i["rank"] for i in body["items"]] == list(range(1, 21))
        assert body["excluded"] is None
        if kind != "red":  # second yellows are kept on red rows only, never added
            assert all(i["yellowRed"] is None for i in body["items"])


def test_saves_exclude_missing_players_and_share_ranks(client):
    body = client.get(
        "/api/v1/player-rankings", params={"league": 39, "season": 2025, "type": "saves"}
    ).json()["data"]
    # Same as the 2026-10-30 API validation: 38 ranked, 34 excluded, M. Dúbravka 127 first.
    assert len(body["items"]) == 38 and body["excluded"] == 34
    assert (body["items"][0]["player"]["id"], body["items"][0]["value"]) == (18886, 127)
    second = body["items"][1:3]
    assert [(i["rank"], i["tied"], i["value"]) for i in second] == [(2, True, 109), (2, True, 109)]


def test_failed_refresh_keeps_rows_and_rerun_never_duplicates(client, session, monkeypatch):
    before = _count(session, Standing, 39, 2025)
    rankings_before = _count(session, PlayerRanking, 39, 2025, type="goals")
    stats_before = _count(session, PlayerSeasonStat, 39, 2025)

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": {"requests": "fail"}, "response": []})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(failing))
    params = {"season": "2025", "league": "39", "force": "1"}
    for job in (sync_standings, sync_player_rankings, sync_player_stats):
        with pytest.raises(JobPartialFailure):
            job(JobContext(session=session, params=params))
    assert _count(session, Standing, 39, 2025) == before
    assert _count(session, PlayerRanking, 39, 2025, type="goals") == rankings_before
    assert _count(session, PlayerSeasonStat, 39, 2025) == stats_before
    state = session.get(LeagueSync, (39, 2025, "standings"))
    assert state.failed_at > state.synced_at
    shown = client.get("/api/v1/standings", params={"league": 39, "season": 2025}).json()
    assert shown["meta"]["refreshFailed"] is True and len(shown["data"]["groups"][0]["rows"]) == 20

    rows = _table_answer(session, 39, 2025)

    def standing(request: httpx.Request) -> httpx.Response:
        payload = [{"league": {"id": 39, "season": 2025, "standings": [rows]}}]
        return httpx.Response(200, json={"errors": [], "response": payload})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(standing))
    for _ in range(2):
        sync_standings(JobContext(session=session, params=params))
    assert _count(session, Standing, 39, 2025) == 20  # replaced as a whole, never duplicated
    state = session.get(LeagueSync, (39, 2025, "standings"))
    assert state.synced_at > state.failed_at > datetime(2026, 1, 1, tzinfo=UTC)


def _table_answer(session, league, season, limit=None):
    """The stored table as a provider answer (ranks and team ids kept)."""
    stored = session.scalars(
        select(Standing).where(Standing.competition_id == league, Standing.season == season)
        .order_by(Standing.rank)
    ).all()[:limit]
    return [
        {"rank": r.rank, "team": {"id": r.team_id, "name": f"T{r.team_id}"}, "points": r.points,
         "group": r.group_name, "all": {"played": r.played}}
        for r in stored
    ]


def _top_answer(count, league=39, season=2025):
    return [
        {"player": {"id": 990_000 + i, "name": f"P{i}"},
         "statistics": [{"team": {"id": 42, "name": "Arsenal"},
                         "league": {"id": league, "season": season},
                         "goals": {"total": 30 - i}}]}
        for i in range(count)
    ]


def _player_page(current, total, count, league=39, season=2025):
    return {
        "errors": [], "paging": {"current": current, "total": total},
        "response": [
            {"player": {"id": 980_000 + current * 100 + i, "name": f"P{i}"},
             "statistics": [{"team": {"id": 42, "name": "Arsenal"},
                             "league": {"id": league, "season": season},
                             "games": {"position": "Goalkeeper", "appearences": 1},
                             "goals": {"saves": 1}, "cards": {}}]}
            for i in range(count)
        ],
    }


def _assert_kept(client, session, kind, before, synced_before, count):
    assert count() == before
    state = session.get(LeagueSync, (39, 2025, kind))
    assert state.synced_at == synced_before and state.failed_at > synced_before
    path, params = ("/api/v1/standings", {}) if kind == "standings" else (
        "/api/v1/player-rankings", {"type": "saves" if kind == "player_stats" else kind})
    body = client.get(path, params={"league": 39, "season": 2025, **params}).json()
    assert body["meta"]["refreshFailed"] is True


def test_cut_answers_never_replace_stored_rows(client, session, monkeypatch):
    """Codex 1차 지적 1: 10 of 20 teams, 10 of 20 scorers and total=2 with an empty second
    page each replaced the stored rows and were recorded as successes."""
    params = {"season": "2025", "league": "39", "force": "1"}
    cases = {
        "standings": (
            sync_standings,
            lambda: _count(session, Standing, 39, 2025),
            lambda req: {"errors": [], "response": [{"league": {
                "id": 39, "season": 2025, "standings": [_table_answer(session, 39, 2025, 10)]}}]},
        ),
        "goals": (
            sync_player_rankings,
            lambda: _count(session, PlayerRanking, 39, 2025, type="goals"),
            lambda req: {"errors": [], "response": _top_answer(10)},
        ),
        "player_stats": (
            sync_player_stats,
            lambda: _count(session, PlayerSeasonStat, 39, 2025),
            lambda req: _player_page(int(req.url.params.get("page")), 2,
                                     20 if req.url.params.get("page") == "1" else 0),
        ),
    }
    for kind, (job, count, answer) in cases.items():
        before = count()
        synced_before = session.get(LeagueSync, (39, 2025, kind)).synced_at
        assert before >= 20

        def handler(request, answer=answer, kind=kind):
            if kind == "goals" and not request.url.path.endswith("topscorers"):
                # The other three lists answer as stored, so only the cut one fails.
                stored = _count(session, PlayerRanking, 39, 2025, type="assists")
                return httpx.Response(200, json={"errors": [], "response": _top_answer(stored)})
            return httpx.Response(200, json=answer(request))

        monkeypatch.setattr(JobContext, "api_football", _fake_client(handler))
        with pytest.raises(JobPartialFailure) as caught:
            job(JobContext(session=session, params=params))
        assert f"{kind}:39" in str(caught.value)
        _assert_kept(client, session, kind, before, synced_before, count)


def test_first_load_takes_a_short_list_but_not_a_cut_table(session, monkeypatch):
    for model in (Standing, PlayerRanking):
        session.execute(
            model.__table__.delete().where(model.competition_id == 39, model.season == 2025)
        )
    session.flush()
    params = {"season": "2025", "league": "39", "force": "1"}

    # A short top list with nothing stored (season start) is a normal answer.
    def short_list(request):
        return httpx.Response(200, json={"errors": [], "response": _top_answer(5)})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(short_list))
    sync_player_rankings(JobContext(session=session, params=params))
    assert _count(session, PlayerRanking, 39, 2025, type="goals") == 5

    # A first table with 10 of the 20 league teams (each has 38 fixtures) is refused.
    teams = session.scalars(
        select(TeamCompetitionSeason.team_id)
        .where(TeamCompetitionSeason.competition_id == 39, TeamCompetitionSeason.season == 2025)
        .order_by(TeamCompetitionSeason.team_id)
    ).all()[:10]
    ten = [{"rank": i, "team": {"id": t, "name": "T"}, "all": {}} for i, t in enumerate(teams, 1)]

    def cut_table(request):
        return httpx.Response(200, json={"errors": [], "response": [
            {"league": {"id": 39, "season": 2025, "standings": [ten]}}]})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(cut_table))
    with pytest.raises(JobPartialFailure) as caught:
        sync_standings(JobContext(session=session, params=params))
    assert "standings:39" in str(caught.value)
    assert _count(session, Standing, 39, 2025) == 0


def test_empty_answer_never_replaces_a_stored_table(session, monkeypatch):
    before = _count(session, Standing, 61, 2025)

    def empty(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [], "response": []})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(empty))
    with pytest.raises(JobPartialFailure):
        sync_standings(JobContext(session=session, params={"season": "2025", "league": "61",
                                                             "force": "1"}))
    assert _count(session, Standing, 61, 2025) == before


def test_never_collected_is_503_not_an_empty_table(client, session):
    session.execute(
        LeagueSync.__table__.update()
        .where(LeagueSync.competition_id == 78, LeagueSync.season == 2026)
        .values(synced_at=None)
    )
    session.flush()
    assert client.get("/api/v1/standings", params={"league": 78}).status_code == 503
    assert client.get(
        "/api/v1/player-rankings", params={"league": 78, "type": "saves"}
    ).status_code == 503
    summary = client.get("/api/v1/standings/summary").json()["data"]["leagues"]
    bundesliga = next(item for item in summary if item["league"]["id"] == 78)
    assert bundesliga["status"] == "not_collected" and bundesliga["rows"] == []


def test_shifted_pages_never_replace_stored_lines(client, session, monkeypatch):
    """Codex 2차 지적: right page numbers and sizes but repeated players. 35 pages of 20 with
    page 2 repeating 5 players of page 1 would store 695 lines over 693 (no shrink), losing
    the 5 players that were never received; the run must fail and keep the stored lines."""
    before = _count(session, PlayerSeasonStat, 39, 2025)
    synced_before = session.get(LeagueSync, (39, 2025, "player_stats")).synced_at

    def handler(request):
        current = int(request.url.params.get("page"))
        body = _player_page(current, 35, 20)
        if current == 2:
            body["response"][:5] = _player_page(1, 35, 20)["response"][-5:]
        return httpx.Response(200, json=body)

    monkeypatch.setattr(JobContext, "api_football", _fake_client(handler))
    with pytest.raises(JobPartialFailure) as caught:
        sync_player_stats(JobContext(session=session, params={"season": "2025", "league": "39",
                                                               "force": "1"}))
    assert "player_stats:39" in str(caught.value)
    _assert_kept(client, session, "player_stats", before, synced_before,
                 lambda: _count(session, PlayerSeasonStat, 39, 2025))
    assert "repeats player" in session.get(LeagueSync, (39, 2025, "player_stats")).failure
