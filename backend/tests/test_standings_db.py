"""Chat 06 standings and player rankings against the dev database (opt-in, rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_standings_db.py
Needs `reference`, `fixtures_season`, `standings`, `player_rankings` and `player_stats` for
2025 and 2026 (guide §6.5).
"""

import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models.fixture import Fixture
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
    assert rows[83]["team"]["detailAvailable"] is False  # relegated: no current team detail
    assert rows[85]["team"]["detailAvailable"] is True  # PSG is a current league team
    # Zones are drawn on screen by position; the API says whether the season is over.
    assert ligue1["data"]["complete"] is True
    assert "zone" not in rows[83] and "description" not in rows[83] and "form" not in rows[83]
    current = client.get("/api/v1/standings", params={"league": 61, "season": 2026}).json()
    assert current["data"]["complete"] is False


def test_cups_and_unsupported_seasons_are_refused(client):
    assert client.get("/api/v1/standings", params={"league": 45}).status_code == 404
    assert client.get("/api/v1/standings", params={"league": 2}).status_code == 200  # UEFA
    cup_players = client.get("/api/v1/player-rankings", params={"league": 45, "type": "goals"})
    assert cup_players.status_code == 404  # player rankings: five leagues and UEFA only
    assert client.get("/api/v1/standings", params={"league": 39, "season": 2019}).status_code == 404
    bad_type = client.get("/api/v1/player-rankings", params={"league": 39, "type": "fouls"})
    assert bad_type.status_code == 422


def test_summary_has_the_leagues_and_uefa_with_six_rows(client):
    """LEAG-001 (06 개선 2026-11-20): five leagues, then the UEFA league phases."""
    body = client.get("/api/v1/standings/summary").json()["data"]
    assert body["season"]["current"] is True
    ids = [item["league"]["id"] for item in body["leagues"]]
    assert ids == [39, 140, 135, 78, 61, 2, 3, 848]
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



def test_recent_matches_are_the_last_five_finished_oldest_first(client, session):
    body = client.get("/api/v1/standings", params={"league": 39, "season": 2025}).json()["data"]
    for row in body["groups"][0]["rows"]:
        recent = row["recent"]
        assert len(recent) == 5  # 38 matches played
        assert [m["kickoffAt"] for m in recent] == sorted(m["kickoffAt"] for m in recent)
        team = row["team"]["id"]
        last = session.scalars(
            select(Fixture.id).where(
                Fixture.competition_id == 39, Fixture.season == 2025,
                Fixture.status == "finished",
                (Fixture.home_team_id == team) | (Fixture.away_team_id == team),
            ).order_by(Fixture.kickoff_at.desc()).limit(5)
        ).all()
        assert [m["fixtureId"] for m in recent] == list(reversed(last))
        for m in recent:
            side = "home" if m["home"]["id"] == team else "away"
            mine, theirs = (m["goalsHome"], m["goalsAway"]) if side == "home" else (
                m["goalsAway"], m["goalsHome"])
            assert m["result"] == ("W" if mine > theirs else "L" if mine < theirs else "D")


def test_uefa_league_phase_table_uses_league_phase_matches_only(client, session):
    for league in (2, 3, 848):
        body = client.get("/api/v1/standings", params={"league": league, "season": 2025}).json()
        rows = body["data"]["groups"][0]["rows"]
        assert len(rows) == 36 and [r["rank"] for r in rows] == list(range(1, 37))
        assert body["data"]["complete"] is True
        phase = set(session.scalars(select(Fixture.id).where(
            Fixture.competition_id == league, Fixture.season == 2025,
            Fixture.round.startswith("League Stage"),
        )))
        assert all(m["fixtureId"] in phase for r in rows for m in r["recent"])
    current = client.get("/api/v1/standings", params={"league": 2, "season": 2026}).json()
    assert current["data"]["complete"] is False


def test_uefa_first_load_takes_only_a_36_team_table(session, monkeypatch):
    """Codex 2차 지적 1: with nothing stored and no league-phase fixtures to compare with, a
    10-team UEFA table was saved as a success. The 36-team rule stands on its own."""
    full = _table_answer(session, 2, 2026)
    assert len(full) == 36
    session.execute(Standing.__table__.delete().where(
        Standing.competition_id == 2, Standing.season == 2026))
    # No league-phase fixture either (the per-team match rule has nothing to check).
    session.execute(Fixture.__table__.update().where(
        Fixture.competition_id == 2, Fixture.season == 2026,
        Fixture.round.startswith("League Stage")).values(round="Qualifying"))
    session.commit()  # a savepoint: the job's rollback on failure must not undo the setup
    params = {"season": "2026", "league": "2", "force": "1"}

    def answer(rows):
        def handler(request):
            return httpx.Response(200, json={"errors": [], "response": [
                {"league": {"id": 2, "season": 2026, "standings": [rows]}}]})
        return handler

    monkeypatch.setattr(JobContext, "api_football", _fake_client(answer(full[:10])))
    with pytest.raises(JobPartialFailure) as caught:
        sync_standings(JobContext(session=session, params=params))
    assert "standings:2" in str(caught.value)
    assert _count(session, Standing, 2, 2026) == 0

    monkeypatch.setattr(JobContext, "api_football", _fake_client(answer(full)))
    sync_standings(JobContext(session=session, params=params))
    assert _count(session, Standing, 2, 2026) == 36


def test_complete_needs_the_whole_fixture_list(client, session):
    """Codex 2차 지적 2: only finished fixtures stored (later rounds not loaded yet) read as
    a finished season. A season moved out of the table's scope stands for "not stored"."""
    for league, later in ((39, Fixture.round == "Regular Season - 38"),
                          (2, Fixture.round == "League Stage - 8")):
        assert client.get("/api/v1/standings", params={"league": league, "season": 2025}
                          ).json()["data"]["complete"] is True
        session.execute(Fixture.__table__.update().where(
            Fixture.competition_id == league, Fixture.season == 2025, later).values(season=2019))
        session.flush()
        body = client.get("/api/v1/standings", params={"league": league, "season": 2025}).json()
        assert body["data"]["complete"] is False


def _complete(client, league, season=2025):
    return client.get("/api/v1/standings", params={"league": league, "season": season}
                      ).json()["data"]["complete"]


def _copy_fixture(session, fixture_id, new_id, **values):
    """A second row for the same pairing (a cancelled record beside its replayed match)."""
    table = Fixture.__table__
    row = dict(session.execute(select(table).where(table.c.id == fixture_id)).mappings().one())
    session.execute(table.insert().values({**row, "id": new_id, **values}))


def test_complete_counts_pairings_not_rows(client, session):
    """Codex 3차 지적 1: a missing league match was hidden by the two relegation play-off
    rows (2. Bundesliga opponent), a missing UEFA pairing by a cancelled duplicate row."""
    assert _complete(client, 78) is True
    session.execute(Fixture.__table__.update().where(Fixture.id == 1388605).values(season=2019))
    session.flush()
    assert _complete(client, 78) is False

    assert _complete(client, 2) is True
    phase = session.scalars(select(Fixture.id).where(
        Fixture.competition_id == 2, Fixture.season == 2025,
        Fixture.round.startswith("League Stage")).order_by(Fixture.id)).all()
    session.execute(Fixture.__table__.update().where(Fixture.id == phase[0]).values(season=2019))
    _copy_fixture(session, phase[1], 990_000_001, status="cancelled")
    session.flush()
    assert _complete(client, 2) is False
    # The duplicate row alone (nothing missing) does not turn a finished phase open.
    session.execute(Fixture.__table__.update().where(Fixture.id == phase[0]).values(season=2025))
    session.flush()
    assert _complete(client, 2) is True


def test_a_team_against_itself_is_no_pairing(client, session):
    """Codex 4차 지적: fixture 1378969 (40 v 35) saved as 40 v 40 kept EPL 2025 complete.
    Saving skips such an answer (the stored match stays) and the completion check ignores
    such a row if one is stored anyway."""
    from app.services.fixtures import upsert_fixtures

    stored = session.get(Fixture, 1378969)
    assert (stored.home_team_id, stored.away_team_id) == (40, 35)
    broken = {
        "fixture": {"id": 1378969, "timestamp": int(stored.kickoff_at.timestamp()),
                    "status": {"short": "FT", "long": "Match Finished", "elapsed": 90}},
        "league": {"id": 39, "season": 2025, "round": stored.round},
        "teams": {"home": {"id": 40, "name": "Liverpool"}, "away": {"id": 40, "name": "Liverpool"}},
        "goals": {"home": 1, "away": 0},
        "score": {},
    }
    assert upsert_fixtures(session, [broken], datetime.now(UTC)) == 0
    session.expire_all()
    stored = session.get(Fixture, 1378969)
    assert (stored.home_team_id, stored.away_team_id) == (40, 35)
    assert _complete(client, 39) is True

    session.execute(Fixture.__table__.update().where(Fixture.id == 1378969)
                    .values(away_team_id=40))
    session.flush()
    assert _complete(client, 39) is False


def test_uefa_table_must_be_one_group_ranked_1_to_36(session, monkeypatch):
    """Codex 3차 지적 2: the 36 teams in two groups ranked 1..18 replaced the stored table."""
    full = _table_answer(session, 2, 2025)
    halves = [[{**row, "rank": i, "group": name} for i, row in enumerate(part, 1)]
              for name, part in (("A", full[:18]), ("B", full[18:]))]
    synced_before = session.get(LeagueSync, (2, 2025, "standings")).synced_at

    def handler(request):
        return httpx.Response(200, json={"errors": [], "response": [
            {"league": {"id": 2, "season": 2025, "standings": halves}}]})

    monkeypatch.setattr(JobContext, "api_football", _fake_client(handler))
    with pytest.raises(JobPartialFailure) as caught:
        sync_standings(JobContext(session=session, params={"season": "2025", "league": "2",
                                                             "force": "1"}))
    assert "standings:2" in str(caught.value)
    stored = session.scalars(select(Standing).where(
        Standing.competition_id == 2, Standing.season == 2025)).all()
    assert len(stored) == 36 and len({r.group_name for r in stored}) == 1
    assert sorted(r.rank for r in stored) == list(range(1, 37))
    assert session.get(LeagueSync, (2, 2025, "standings")).synced_at == synced_before


def test_uefa_saves_exclude_missing_keepers_and_share_ranks(client, session):
    """06 개선 2026-11-20 (LEAG-004): UEFA saves come from every player line of the whole
    competition — a goalkeeper with any missing value is excluded (never counted as 0) and
    equal totals share a rank. The four provider lists keep their order, 20 at most."""
    for league in (2, 3, 848):
        for season in (2025, 2026):
            body = client.get("/api/v1/player-rankings",
                              params={"league": league, "season": season, "type": "saves"}).json()
            items = body["data"]["items"]
            lines = session.execute(select(
                PlayerSeasonStat.player_id, PlayerSeasonStat.saves, PlayerSeasonStat.appearances,
            ).where(
                PlayerSeasonStat.competition_id == league, PlayerSeasonStat.season == season,
                PlayerSeasonStat.position == "Goalkeeper",
            )).all()
            missing = {p for p, saves, _ in lines if saves is None}
            assert body["data"]["excluded"] == len(missing)
            assert not missing & {i["player"]["id"] for i in items}
            values = [i["value"] for i in items]
            assert values == sorted(values, reverse=True)
            for item in items:
                assert item["rank"] == 1 + sum(v > item["value"] for v in values)
                assert item["tied"] == (values.count(item["value"]) > 1)
            for kind in ("goals", "assists", "yellow", "red"):
                listed = client.get("/api/v1/player-rankings",
                                    params={"league": league, "season": season, "type": kind})
                assert listed.status_code == 200 and len(listed.json()["data"]["items"]) <= 20


def test_uefa_player_lists_wait_for_a_uefa_result(session):
    """UEFA player lists (about 90-110 pages a competition) are read again only after a UEFA
    result since the last success; the leagues keep the daily rule."""
    from app.services.standings import due_leagues

    season = settings.current_season
    latest = session.scalar(select(func.max(Fixture.kickoff_at)).where(
        Fixture.competition_id == 2, Fixture.season == season, Fixture.status == "finished"))
    assert latest is not None
    for synced, due in ((latest + timedelta(hours=4), False), (latest + timedelta(hours=2), True)):
        for league in (2, 39):
            row = session.get(LeagueSync, (league, season, "player_stats"))
            row.synced_at, row.failed_at = synced, None
        session.flush()
        now = synced + timedelta(days=1)
        result = due_leagues(session, season, "player_stats", now, matchday_hourly=False,
                             leagues=(39, 2))
        assert (2 in result) is due and 39 in result


def test_a_teamless_refusal_waits_for_the_next_uefa_result(session):
    """A UEFA player unit refused for a teamless goalkeeper / unknown-position line is not
    asked again (60-110 requests) until a UEFA result after that refusal; other failures are
    tried again in the next daily slot."""
    from app.services.standings import due_leagues

    season = settings.current_season
    latest = session.scalar(select(func.max(Fixture.kickoff_at)).where(
        Fixture.competition_id == 2, Fixture.season == season, Fixture.status == "finished"))
    row = session.get(LeagueSync, (2, season, "player_stats"))
    row.synced_at = latest - timedelta(days=2)  # a result since the last success: due
    cases = (
        (latest + timedelta(hours=4), "IncompleteData: players: player 7 without team "
                                      "(position None)", False),
        (latest + timedelta(hours=4), "ApiFootballUnavailable", True),
        (latest + timedelta(hours=2), "IncompleteData: players: player 7 without team "
                                      "(position Goalkeeper)", True),  # result after it
    )
    for failed, reason, due in cases:
        row.failed_at, row.failure = failed, reason
        session.flush()
        result = due_leagues(session, season, "player_stats", failed + timedelta(days=1),
                             matchday_hourly=False, leagues=(2,))
        assert (2 in result) is due, reason


def _ko(client, league, stage, season=2025):
    return client.get(
        "/api/v1/knockouts", params={"league": league, "season": season, "stage": stage}
    )


def test_knockout_ties_follow_stored_matches(client):
    for league in (2, 3, 848):
        prev_winners: set[int] = set()
        for stage, size in (("playoff", 8), ("r16", 8), ("qf", 4), ("sf", 2), ("final", 1)):
            body = _ko(client, league, stage)
            assert body.status_code == 200
            ties = body.json()["data"]["ties"]
            assert len(ties) == size and {t["state"] for t in ties} == {"finished"}
            teams = {s["team"]["id"] for t in ties for s in (t["home"], t["away"])}
            if stage in ("qf", "sf", "final"):
                assert teams == prev_winners  # every tie is fed by the previous round's winners
            if stage == "r16":
                assert prev_winners <= teams
            prev_winners = {t["winner"]["id"] for t in ties}
            for t in ties:
                assert len(t["legs"]) == t["legsNeeded"] == (1 if stage == "final" else 2)
                assert t["legs"][0]["home"]["id"] == t["home"]["team"]["id"]
    final = _ko(client, 2, "final").json()["data"]["ties"][0]
    # 2025-26 UCL final: 1-1, PSG won the shoot-out 4-3.
    assert (final["aggregateHome"], final["aggregateAway"]) == (1, 1)
    assert (final["penaltyHome"], final["penaltyAway"]) == (4, 3)
    assert final["winner"]["id"] == final["home"]["team"]["id"] == 85


def test_a_missing_final_is_fixed_by_the_semi_finals_only(client, session):
    """No final stored: its places are the semi-final winners, or "A–B전 승자" while a semi
    is open, or "상대 미정" when only one semi-final is stored (Codex-style test data)."""
    final = session.scalars(select(Fixture).where(
        Fixture.competition_id == 2, Fixture.season == 2025, Fixture.round == "Final")).one()
    session.delete(final)
    session.flush()
    tie = _ko(client, 2, "final").json()["data"]["ties"][0]
    assert tie["state"] == "scheduled" and tie["legs"] == []
    assert tie["home"]["team"] is not None and tie["away"]["team"] is not None

    semis = session.scalars(select(Fixture).where(
        Fixture.competition_id == 2, Fixture.season == 2025, Fixture.round == "Semi-finals")
        .order_by(Fixture.kickoff_at)).all()
    semis[-1].status = "scheduled"  # one semi-final second leg not played yet
    session.flush()
    tie = _ko(client, 2, "final").json()["data"]["ties"][0]
    sides = [tie["home"], tie["away"]]
    assert sum(s["team"] is not None for s in sides) == 1
    open_side = next(s for s in sides if s["team"] is None)
    assert len(open_side["winnerOf"]) == 2  # "A–B전 승자"

    open_pair = {semis[-1].home_team_id, semis[-1].away_team_id}
    for fixture in semis:
        if {fixture.home_team_id, fixture.away_team_id} == open_pair:
            session.delete(fixture)
    session.flush()
    tie = _ko(client, 2, "final").json()["data"]["ties"][0]
    assert tie["home"]["team"] is not None
    assert tie["away"] == {"team": None, "winnerOf": None}  # "상대 미정"


def test_a_single_stored_leg_has_no_leg_number(client, session):
    """Codex 2차 지적 3: the only stored match of a tie was labelled 1차전 although it can be
    the second leg. Numbers are given only when every leg is stored."""
    ties = _ko(client, 2, "r16").json()["data"]["ties"]
    assert all([leg["leg"] for leg in t["legs"]] == [1, 2] for t in ties)
    first = ties[0]["legs"][0]["fixtureId"]
    session.delete(session.get(Fixture, first))
    session.flush()
    ties = _ko(client, 2, "r16").json()["data"]["ties"]
    single = [t for t in ties if len(t["legs"]) == 1]
    assert len(single) == 1 and single[0]["legs"][0]["leg"] is None
    assert single[0]["state"] == "scheduled" and single[0]["winner"] is None
    final = _ko(client, 2, "final").json()["data"]["ties"][0]
    assert [leg["leg"] for leg in final["legs"]] == [1]


def test_unannounced_rounds_are_undecided_and_cups_are_refused(client):
    ties = _ko(client, 2, "r16", season=2026).json()["data"]["ties"]
    assert len(ties) == 8 and {t["state"] for t in ties} == {"undecided"}
    assert all(t["legs"] == [] and t["home"]["team"] is None for t in ties)
    assert _ko(client, 39, "final").status_code == 404
    bad_stage = client.get("/api/v1/knockouts", params={"league": 2, "stage": "groups"})
    assert bad_stage.status_code == 422
    assert _ko(client, 2, "final", season=2019).status_code == 404
