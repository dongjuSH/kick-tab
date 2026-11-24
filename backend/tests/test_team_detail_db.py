"""Team detail against the dev database (chat 08, opt-in, always rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_team_detail_db.py
Needs the reference, team_details and transfers jobs to have run once.
"""

import json
import os
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.match_detail import TeamForm
from app.models.news import NewsArticle, NewsArticleTeam
from app.models.reference import Competition, CompetitionSeason, Team
from app.models.team_detail import SquadMember, TeamSync, Transfer
from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.services import team_detail as detail
from app.services.reference import team_detail_lookup, upsert_teams
from app.services.standings import IncompleteData
from app.sync.registry import JobContext, JobPartialFailure

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

CITY, WOLVES, LAZIO, IPSWICH = 50, 39, 487, 57


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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_direct_url_uses_the_allow_set(session):
    assert detail.detail_access(session, CITY).league.id == 39
    with pytest.raises(detail.DetailUnavailable):
        detail.detail_access(session, WOLVES)  # relegated in 2025-26: known, not offered
    with pytest.raises(detail.TeamNotFound):
        detail.detail_access(session, 999_999_999)
    # The league's team list not confirmed: membership unknown, never "relegated".
    session.execute(
        update(CompetitionSeason)
        .where(CompetitionSeason.competition_id == 39, CompetitionSeason.season == 2026)
        .values(teams_synced_at=None)
    )
    with pytest.raises(detail.MembershipUnknown):
        detail.detail_access(session, CITY)
    with pytest.raises(detail.MembershipUnknown):
        detail.detail_access(session, WOLVES)
    # Codex 1차 지적 2: every link decides the same — unknown, not "available".
    lookup = team_detail_lookup(session)
    assert lookup(CITY) is None and lookup(WOLVES) is None
    assert lookup(LAZIO) is True  # another league's confirmed member is unaffected


def test_search_and_standings_links_follow_the_unconfirmed_league(session, client):
    session.execute(
        update(CompetitionSeason)
        .where(CompetitionSeason.competition_id == 39, CompetitionSeason.season == 2026)
        .values(teams_synced_at=None)
    )
    found = client.get("/api/v1/teams/search?q=Manchester City").json()["data"]
    assert next(t for t in found if t["id"] == CITY)["detailAvailable"] is None
    rows = client.get("/api/v1/standings?league=39").json()["data"]["groups"][0]["rows"]
    assert next(r for r in rows if r["team"]["id"] == CITY)["team"]["detailAvailable"] is None
    assert client.get(f"/api/v1/teams/{CITY}").status_code == 503


def test_area_endpoints_answer_codes(client):
    assert client.get(f"/api/v1/teams/{WOLVES}/squad").json()["error"]["code"] == (
        "TEAM_DETAIL_UNAVAILABLE"
    )
    assert client.get("/api/v1/teams/999999999/transfers").status_code == 404
    assert client.get(f"/api/v1/teams/{CITY}/season-stats?season=2024").status_code == 404
    assert client.get("/api/v1/teams/3000000000").status_code == 422


def test_squad_rows_are_one_per_player_with_this_teams_line(session, client):
    data = client.get(f"/api/v1/teams/{CITY}/squad").json()["data"]
    players = data["players"]
    ids = [p["player"]["id"] for p in players]
    assert len(ids) == len(set(ids))
    # TEAM-002 rules 1·7 (2026-11-20): the season's competition master — cups and super cups
    # included, friendlies (667) and competitions not held that season never.
    record = detail.record_competitions(session, 2026)
    assert {45, 48, 528, 2}.issubset(record) and 15 not in record and 667 not in record
    for player in players:
        lines = player["competitions"]
        assert {line["competition"]["id"] for line in lines} <= record
        for line in lines:
            assert line["rating"] is None or float(line["rating"]) > 0  # "0" is not a rating
        totals = player["totals"]
        if totals is not None:  # the totals are the sum of the lines shown under them
            for key in ("appearances", "goals", "assists"):
                assert totals[key] == sum(line[key] for line in lines)


def _form_row(n, league, name, home, away, goals, winner):
    """A normalised official result as `head_to_head` stores it (newest first in the list)."""
    kickoff = datetime.now(UTC) - timedelta(hours=n)
    return {
        "fixtureId": 990_000 + n, "kickoffAt": kickoff.isoformat(), "leagueId": league,
        "leagueName": name, "round": "R", "homeId": home, "homeName": f"T{home}", "awayId": away,
        "awayName": f"T{away}", "goalsHome": goals[0], "goalsAway": goals[1],
        "penaltyHome": None, "penaltyAway": None, "homeWinner": winner == "home",
        "awayWinner": winner == "away", "status": "FT",
    }


def _failing_provider(monkeypatch):
    from app.api.routes import teams

    def factory():
        return ApiFootballClient(
            SecretStr("test"),
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
            limiter=MinuteRateLimiter(1000),
            budget=DailyBudget(1000),
            max_retries=0,
        )

    monkeypatch.setattr(teams, "ApiFootballClient", factory)


def test_recent_five_are_the_teams_official_matches_oldest_first(session, client):
    """06 개선 2026-11-20 (TEAM-001 rule 3): the head-to-head source — official matches of
    every competition, a super cup (531) and one outside the supported list (provider name)
    included. A fresh list is read without a request (real HTTP is refused in tests)."""
    payload = [
        _form_row(1, 39, "Premier League", CITY, 42, (2, 1), "home"),
        _form_row(30, 9999, "Some Official Cup", 1000, CITY, (0, 0), None),
        _form_row(60, 531, "UEFA Super Cup", CITY, 541, (1, 1), "away"),
        _form_row(90, 2, "UEFA Champions League", 541, CITY, (3, 0), "home"),
        _form_row(120, 45, "FA Cup", CITY, 33, (4, 0), "home"),
        _form_row(150, 39, "Premier League", 40, CITY, (1, 0), "home"),
    ]
    session.merge(TeamForm(team_id=CITY, payload=payload, fetched_at=datetime.now(UTC)))
    session.flush()
    recent = client.get(f"/api/v1/teams/{CITY}").json()["data"]["recent"]
    assert [m["fixtureId"] for m in recent] == [990_120, 990_090, 990_060, 990_030, 990_001]
    names = {c.id: c.name_ko for c in session.scalars(select(Competition))}
    assert [m["competition"] for m in recent] == [
        names[45], names[2], names[531], "Some Official Cup", names[39]
    ]
    # Winner flags decide (a shoot-out win reads as a win); otherwise a draw.
    assert [m["result"] for m in recent] == ["W", "L", "L", "D", "W"]


def test_a_failed_refresh_keeps_the_last_official_list(session, client, monkeypatch):
    payload = [_form_row(1, 39, "Premier League", CITY, 42, (2, 1), "home")]
    stale = datetime.now(UTC) - timedelta(days=8)
    session.merge(TeamForm(team_id=CITY, payload=payload, fetched_at=stale))
    session.flush()
    _failing_provider(monkeypatch)
    recent = client.get(f"/api/v1/teams/{CITY}").json()["data"]["recent"]
    assert [m["fixtureId"] for m in recent] == [990_001]
    row = session.get(TeamForm, CITY)
    assert row.fetched_at == stale and row.last_failed_at is not None


def test_never_read_falls_back_to_stored_matches_oldest_first(session, client, monkeypatch):
    row = session.get(TeamForm, CITY)
    if row is not None:
        session.delete(row)
        session.flush()
    _failing_provider(monkeypatch)
    recent = client.get(f"/api/v1/teams/{CITY}").json()["data"]["recent"]
    assert 0 < len(recent) <= 5
    days = [m["kickoffAt"] for m in recent]
    assert days == sorted(days)
    names = set(session.scalars(select(Competition.name_ko)))
    for match in recent:
        assert CITY in (match["home"]["id"], match["away"]["id"])
        assert match["result"] in ("W", "D", "L")
        assert match["competition"] in names


def test_promoted_team_has_no_last_season_record(client):
    body = client.get(f"/api/v1/teams/{IPSWICH}/season-stats?season=2025").json()["data"]
    assert (body["status"], body["record"]) == ("not_participated", None)
    city = client.get(f"/api/v1/teams/{CITY}/season-stats?season=2025").json()["data"]
    record = city["record"]
    assert city["status"] == "available" and sum(
        record[key]["total"] for key in ("wins", "draws", "loses")
    ) == 38


def test_transfer_halves_and_the_not_started_second_half(client):
    data = client.get(f"/api/v1/teams/{CITY}/transfers").json()["data"]
    first, second = data["halves"]
    assert (first["label"], first["period"]) == ("26-27 전반기", "2026년 6~12월")
    assert (second["label"], second["period"]) == ("26-27 후반기", "2027년 1~5월")
    if date.today() < date(2027, 1, 1):
        assert second["state"] == "not_started" and not second["arrivals"]
    rows = [*first["arrivals"], *first["departures"], *first["otherArrivals"],
            *first["otherDepartures"]]
    for row in rows:
        for move in row["moves"]:
            assert "2026-06-01" <= move["transferDate"] <= "2026-12-31"
    # One row per player and half; D-08-6 still merges repeated entries (Stones: one move).
    names = [r["playerName"] for r in rows]
    assert len(names) == len(set(names))
    stones = next(r for r in rows if r["playerName"] == "J. Stones")
    assert len(stones["moves"]) == 1
    # Akanji: back from loan and sold to Inter — one row, both moves kept, oldest first.
    akanji = next(r for r in rows if r["playerName"] == "M. Akanji")
    assert [(m["direction"], m["type"]) for m in akanji["moves"]] == [
        ("in", "Return from loan"), ("out", "Transfer"),
    ]
    assert akanji in first["departures"]  # listed where he ended up
    shown = {r["playerName"] for r in [*first["arrivals"], *first["departures"]]}
    # Departures not in the squad stay shown (they played here); so does the new signing.
    assert {"M. Akanji", "C. Echeverri", "Rodri", "Bernardo Silva", "E. Anderson"} <= shown
    last = client.get(f"/api/v1/teams/{CITY}/transfers?season=2025").json()["data"]
    assert [h["state"] for h in last["halves"]] == ["open", "open"]
    assert (last["halves"][1]["label"], last["halves"][1]["period"]) == (
        "25-26 후반기", "2026년 1~5월"
    )


def test_a_finished_season_is_fixed_after_the_july_1_run(session):
    # 2025-26 was stored once: the July 1 00:00 run still rewrites it (June 30 records),
    # from July 2 only the current season is written again.
    assert detail.transfer_seasons(session, CITY, date(2026, 7, 1)) == [2025, 2026]
    assert detail.transfer_seasons(session, CITY, date(2026, 7, 2)) == [2026]
    assert detail.transfer_seasons(session, CITY, date(2026, 11, 7)) == [2026]
    session.execute(
        TeamSync.__table__.delete().where(
            TeamSync.team_id == CITY, TeamSync.season == 2025, TeamSync.kind == "transfers"
        )
    )
    assert detail.transfer_seasons(session, CITY, date(2026, 11, 7)) == [2025, 2026]


def _count(session, model, *where):
    return session.scalar(select(func.count()).select_from(model).where(*where))


def test_cut_answers_keep_stored_rows(session):
    """Codex 1차 지적 1: 27 → 1 players, 59 → 1 transfers, a record of fewer matches."""
    now = datetime.now(UTC)
    squad = _count(session, SquadMember, SquadMember.team_id == CITY)
    moves = _count(session, Transfer, Transfer.team_id == CITY, Transfer.season == 2026)
    one = detail.ParsedSquad(
        [{"player_id": 999_000_001, "number": 1, "position": "Goalkeeper"}],
        [{"id": 999_000_001, "name": "Cut", "photo_url": None}],
    )
    with pytest.raises(IncompleteData):
        detail.save_squad(session, CITY, one, now)
    first = session.scalars(
        select(Transfer).where(Transfer.team_id == CITY, Transfer.season == 2026).limit(1)
    ).one()
    row = {c: getattr(first, c) for c in (
        "player_id", "player_name", "transfer_date", "direction", "counterpart_id",
        "counterpart_name", "counterpart_logo", "type_raw", "season", "half",
    )}
    with pytest.raises(IncompleteData):
        detail.save_transfers(session, CITY, 2026, [row], now)
    stored = detail.read_season_stat(session, CITY, 39, 2026)
    # Well-formed but older (0 matches): a season record never shrinks.
    older = json.loads(json.dumps(stored.payload))
    for key in ("played", "wins", "draws", "loses"):
        older["fixtures"][key] = {"home": 0, "away": 0, "total": 0}
    with pytest.raises(IncompleteData):
        detail.save_statistics(session, CITY, 39, 2026, older, now)
    session.rollback()
    assert _count(session, SquadMember, SquadMember.team_id == CITY) == squad
    assert _count(
        session, Transfer, Transfer.team_id == CITY, Transfer.season == 2026
    ) == moves
    synced = session.get(TeamSync, (CITY, 2026, "squad")).synced_at
    assert synced is not None and synced < now  # the success time is not moved either


def test_a_failed_request_marks_every_season_it_would_write(session, monkeypatch):
    """Codex 1차 지적 3: the July 1 run fails → both seasons show the failure, and the past
    season keeps being retried until a final refresh succeeds."""
    from app.sync import team_detail as job

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": {"requests": "fail"}, "response": []})

    def fake_client(self, **_):
        client = ApiFootballClient(
            SecretStr("test"), transport=httpx.MockTransport(handler),
            limiter=MinuteRateLimiter(1000), budget=DailyBudget(1000),
        )
        self._clients.append(client)
        return client

    last_day = date(2026, 7, 1)
    session.execute(
        update(TeamSync)
        .where(TeamSync.team_id == CITY, TeamSync.season == 2025, TeamSync.kind == "transfers")
        .values(synced_at=datetime(2026, 6, 29, 15, tzinfo=UTC))  # 6/30 00:00 KST run
    )
    session.commit()  # releases the savepoint only; the outer transaction is rolled back
    monkeypatch.setattr(JobContext, "api_football", fake_client)
    monkeypatch.setattr(job, "kst_today", lambda now=None: last_day)
    ctx = JobContext(session=session, params={"team": CITY, "force": "1"})
    with pytest.raises(JobPartialFailure):
        job.sync_transfers(ctx)
    assert ctx.api_requests == 1
    for season in (2025, 2026):
        row = session.get(TeamSync, (CITY, season, "transfers"))
        assert row.failed_at is not None and row.failed_at > row.synced_at
    # The final refresh did not succeed: 2025-26 stays writable after July 1 ...
    assert detail.transfer_seasons(session, CITY, date(2026, 7, 2)) == [2025, 2026]
    # ... until a run on or after July 1 stores it.
    session.get(TeamSync, (CITY, 2025, "transfers")).synced_at = datetime(
        2026, 6, 30, 15, 5, tzinfo=UTC
    )  # 7/1 00:05 KST
    assert detail.transfer_seasons(session, CITY, date(2026, 7, 2)) == [2026]


def test_two_same_day_moves_to_unnamed_id_clubs_are_both_stored(session):
    """Codex 3차 N4: the DB key tells the clubs apart by name when there is no id."""
    now = datetime.now(UTC)
    stored = _count(session, Transfer, Transfer.team_id == CITY, Transfer.season == 2026)
    rows = [
        {**row, "transfer_date": date(2026, 8, 31)}
        for row in detail.parse_transfers(
            [{"player": {"id": 999_000_002, "name": "Loanee"}, "transfers": [
                {"date": "2026-08-31", "type": "Loan", "teams": {
                    "in": {"id": None, "name": club}, "out": {"id": CITY, "name": "City"}}}
                for club in ("A", "B")
            ]}], CITY, date(2026, 11, 7),
        )
    ]
    existing = session.scalars(
        select(Transfer).where(Transfer.team_id == CITY, Transfer.season == 2026)
    ).all()
    keep = [{c: getattr(t, c) for c in (
        "player_id", "player_name", "transfer_date", "direction", "counterpart_id",
        "counterpart_name", "counterpart_logo", "type_raw", "season", "half",
    )} for t in existing]
    detail.save_transfers(session, CITY, 2026, [*keep, *rows], now)
    session.flush()
    assert _count(
        session, Transfer, Transfer.team_id == CITY, Transfer.season == 2026
    ) == stored + 2


def test_transfer_identity_uses_the_name_only_when_the_counterpart_id_is_missing(session):
    entry = insert(Transfer).values(
        team_id=CITY,
        player_id=999_000_003,
        player_name="Loanee",
        transfer_date=date(2026, 8, 31),
        direction="out",
        season=2026,
        half=1,
        synced_at=datetime.now(UTC),
    )
    for club_id, name in ((39, "A"), (None, "A"), (None, "B"), (None, None)):
        session.execute(entry.values(counterpart_id=club_id, counterpart_name=name))

    for club_id, name in ((39, "A renamed"), (None, "A"), (None, None)):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.execute(entry.values(counterpart_id=club_id, counterpart_name=name))


def test_a_partial_venue_block_keeps_the_fields_it_leaves_out(session):
    now = datetime.now(UTC)
    upsert_teams(session, [{"id": CITY, "name": "Manchester City",
                            "venue": {"name": "Etihad Stadium"}}], now)
    session.expire_all()
    team = session.get(Team, CITY)
    assert (team.venue_name, team.venue_capacity) == ("Etihad Stadium", 55097)
    upsert_teams(session, [{"id": CITY, "name": "Manchester City",
                            "venue": {"capacity": None}}], now)
    session.expire_all()
    assert session.get(Team, CITY).venue_capacity is None  # given as empty: cleared


def test_empty_answers_never_replace_stored_rows(session):
    now = datetime.now(UTC)
    stored = session.scalar(
        select(func.count()).select_from(Transfer).where(
            Transfer.team_id == CITY, Transfer.season == 2026
        )
    )
    with pytest.raises(IncompleteData):
        detail.save_transfers(session, CITY, 2026, [], now)
    with pytest.raises(IncompleteData):
        detail.save_squad(session, CITY, detail.ParsedSquad([], []), now)
    session.rollback()
    assert session.scalar(
        select(func.count()).select_from(Transfer).where(
            Transfer.team_id == CITY, Transfer.season == 2026
        )
    ) == stored
    assert session.scalar(
        select(func.count()).select_from(SquadMember).where(SquadMember.team_id == CITY)
    )


def test_an_answer_without_repeated_entries_replaces_the_stored_season(session):
    """2026-11-24: the provider sends each move once — fewer rows, no move lost — and the
    season is replaced; the same answer missing most moves is still refused."""
    fields = ("player_id", "player_name", "transfer_date", "direction", "counterpart_id",
              "counterpart_name", "counterpart_logo", "type_raw", "season", "half")
    once = [{c: getattr(m, c) for c in fields}
            for m in detail.merge_transfers(detail.read_transfers(session, CITY, 2026))]
    # Stored as the provider used to send it: every move once more, a day later.
    again = [{**m, "transfer_date": m["transfer_date"] + timedelta(days=1)} for m in once
             if m["counterpart_id"] is not None]
    detail.save_transfers(session, CITY, 2026, [*once, *again], datetime.now(UTC))
    session.flush()
    with pytest.raises(IncompleteData):
        detail.save_transfers(session, CITY, 2026, once[: len(once) // 2], datetime.now(UTC))
    detail.save_transfers(session, CITY, 2026, once, datetime.now(UTC))
    session.flush()
    assert _count(
        session, Transfer, Transfer.team_id == CITY, Transfer.season == 2026
    ) == len(once)


def test_team_news_lists_linked_articles_only(session, client):
    now = datetime.now(UTC)
    mine = NewsArticle(
        url_hash="f" * 64, url="https://example.com/team-only", source_domain="example.com",
        title="Team only", published_at=now + timedelta(minutes=5), fetched_at=now,
        expires_at=now + timedelta(hours=1), badge=None,
    )
    other = NewsArticle(
        url_hash="e" * 64, url="https://example.com/other", source_domain="example.com",
        title="Other team", published_at=now + timedelta(minutes=6), fetched_at=now,
        expires_at=now + timedelta(hours=1), badge="EPL",
    )
    session.add_all([mine, other])
    session.flush()
    session.add_all([
        NewsArticleTeam(article_id=mine.id, team_id=CITY),
        NewsArticleTeam(article_id=other.id, team_id=LAZIO),
    ])
    session.flush()
    first = client.get(f"/api/v1/news?team={CITY}&size=24").json()
    titles = [a["title"] for a in first["data"]]
    assert titles[0] == "Team only" and "Other team" not in titles  # no badge needed
    main = [a["title"] for a in client.get("/api/v1/news?size=24").json()["data"]]
    assert "Team only" not in main  # the main page still needs a badge
    assert client.get("/api/v1/news?team=999999999").status_code == 404


def test_team_news_is_capped_at_24(session, client):
    now = datetime.now(UTC)
    articles = [
        NewsArticle(
            url_hash=f"{i:064x}", url=f"https://example.com/cap-{i}", source_domain="example.com",
            title=f"Cap {i}", published_at=now + timedelta(minutes=10 + i), fetched_at=now,
            expires_at=now + timedelta(hours=1), badge=None,
        )
        for i in range(30)
    ]
    session.add_all(articles)
    session.flush()
    session.add_all([NewsArticleTeam(article_id=a.id, team_id=CITY) for a in articles])
    session.flush()
    body = client.get(f"/api/v1/news?team={CITY}&size=24").json()
    assert len(body["data"]) == 24 and body["data"][0]["title"] == "Cap 29"
    assert body["meta"]["total"] == 24 and body["meta"]["nextCursor"] is None


def test_shifted_player_pages_keep_the_stored_lines(session, monkeypatch):
    """Codex 1차 지적 1: page 2 repeats page 1's last player instead of another one. The job
    fails for the team; the stored lines and the success time stay."""
    from app.models.team_detail import TeamPlayerStat
    from app.sync import team_detail as job

    def listing(pid):
        return {"player": {"id": pid, "name": f"P{pid}"}, "statistics": [{
            "team": {"id": CITY}, "league": {"id": 39, "season": 2026},
            "games": {"appearences": 1, "rating": None}, "goals": {"total": 0, "assists": 0},
        }]}

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        people = range(1, 21) if page == 1 else [20, 21]  # 20 listed again, 22 left out
        return httpx.Response(200, json={
            "errors": [], "paging": {"current": page, "total": 2},
            "response": [listing(990_000_000 + p) for p in people],
        })

    def fake_client(self, **_):
        client = ApiFootballClient(
            SecretStr("test"), transport=httpx.MockTransport(handler),
            limiter=MinuteRateLimiter(1000), budget=DailyBudget(1000),
        )
        self._clients.append(client)
        return client

    where = (TeamPlayerStat.team_id == CITY, TeamPlayerStat.season == 2026)
    stored = _count(session, TeamPlayerStat, *where)
    synced = session.get(TeamSync, (CITY, 2026, "player_stats")).synced_at
    monkeypatch.setattr(JobContext, "api_football", fake_client)
    ctx = JobContext(session=session, params={"team": CITY, "force": "1"})
    with pytest.raises(JobPartialFailure):
        job.sync_team_player_stats(ctx)
    session.expire_all()
    assert _count(session, TeamPlayerStat, *where) == stored
    row = session.get(TeamSync, (CITY, 2026, "player_stats"))
    assert row.synced_at == synced and row.failed_at is not None
    meta = detail.sync_meta(session, CITY, 2026, "player_stats")
    assert meta[1] is True  # shown as "refresh failed" on the squad


def test_folded_rows_are_only_confirmed_non_appearances(session, client):
    """TEAM-006 rule 6: a row goes under '기타 이동' only when every move is `not_played`;
    undecided moves stay shown."""
    for season in (2025, 2026):
        rows = detail.merge_transfers(detail.read_transfers(session, CITY, season))
        evidence = detail.move_evidence(session, CITY, season, rows)
        for group in detail.group_moves(rows, evidence):
            reasons = {detail.judge_move(m, evidence)[1] for m in group.moves}
            assert group.shown == (reasons != {"not_played"})


def test_null_team_lines_follow_user_decision_b(session):
    from app.models.team_detail import TeamPlayerStat

    rows = detail.merge_transfers(detail.read_transfers(session, CITY, 2026))
    rodri = next(r for r in rows if r.player_name == "Rodri" and r.direction == "out")
    session.execute(update(TeamPlayerStat).where(
        TeamPlayerStat.team_id == CITY, TeamPlayerStat.player_id == rodri.player_id,
    ).values(appearances=None, goals=None, assists=None, rating=None))
    assert detail.judge_move(rodri, detail.move_evidence(session, CITY, 2026, rows)) == (
        False, "not_played",
    )
    line = session.scalar(select(TeamPlayerStat).where(
        TeamPlayerStat.team_id == CITY, TeamPlayerStat.player_id == rodri.player_id,
        TeamPlayerStat.season == 2025,
    ))
    line.assists, line.rating = 2, 7.287
    session.flush()
    assert detail.judge_move(rodri, detail.move_evidence(session, CITY, 2026, rows)) == (
        True, "played_here",
    )
    # A past fixed season is read at response time; no collection is necessary.
    assert 325975 in detail.move_evidence(session, 157, 2025, []).played
    session.execute(TeamSync.__table__.delete().where(
        TeamSync.team_id == CITY, TeamSync.kind == "player_stats", TeamSync.season == 2025,
    ))
    assert detail.judge_move(rodri, detail.move_evidence(session, CITY, 2026, rows)) == (
        True, "records_incomplete",
    )


def test_signing_checks_store_first_team_clubs_and_retry_failures(session, monkeypatch):
    """transfer_player_checks: one /players?id=&season= per pending signing; youth lines are
    not first-team; a failed answer is marked and asked again later."""
    from app.models.team_detail import PlayerClubSeason, PlayerSeasonCheck
    from app.sync import team_detail as job

    session.execute(PlayerSeasonCheck.__table__.delete())
    session.execute(PlayerClubSeason.__table__.delete())
    pending = detail.pending_checks(session, [CITY])
    assert pending
    (good_player, good_season), (bad_player, bad_season) = pending[0], pending[1]

    def handler(request: httpx.Request) -> httpx.Response:
        player = int(request.url.params["id"])
        if player == bad_player:
            return httpx.Response(200, json={"errors": [], "paging": {"current": 1, "total": 1},
                                             "response": [{"player": {"id": 1}, "statistics": []}]})
        stats = [
            {"team": {"id": 4242}, "league": {"name": "Eredivisie", "season": good_season},
             "games": {"appearences": 20}},
            {"team": {"id": 4243}, "league": {"name": "Premier League 2", "season": good_season},
             "games": {"appearences": 9}},
        ]
        return httpx.Response(200, json={"errors": [], "paging": {"current": 1, "total": 1},
                                         "response": [{"player": {"id": player},
                                                       "statistics": stats}]})

    def fake_client(self, **_):
        client = ApiFootballClient(
            SecretStr("test"), transport=httpx.MockTransport(handler),
            limiter=MinuteRateLimiter(1000), budget=DailyBudget(1000),
        )
        self._clients.append(client)
        return client

    monkeypatch.setattr(JobContext, "api_football", fake_client)
    ctx = JobContext(session=session, params={"team": CITY, "limit": "2"})
    with pytest.raises(JobPartialFailure):
        job.sync_transfer_player_checks(ctx)
    assert ctx.api_requests == 2
    good = session.get(PlayerSeasonCheck, (good_player, good_season))
    assert good.checked_at is not None
    clubs = {c.team_id: c.appearances for c in session.scalars(
        select(PlayerClubSeason).where(PlayerClubSeason.player_id == good_player)
    )}
    assert clubs == {4242: 20}  # the youth side's Premier League 2 line is not first-team
    bad = session.get(PlayerSeasonCheck, (bad_player, bad_season))
    assert bad.checked_at is None and bad.failed_at is not None
    assert (bad_player, bad_season) in detail.pending_checks(session, [CITY])  # asked again


def test_player_record_units_current_daily_and_past_until_stored(session):
    """team_player_stats: the current season once a KST day; the past season only until it
    has been stored once (then fixed)."""
    from app.sync import team_detail as job

    session.execute(
        TeamSync.__table__.delete().where(
            TeamSync.team_id == CITY, TeamSync.kind == "player_stats"
        )
    )
    now = datetime(2026, 11, 18, 7, tzinfo=UTC)  # 16:00 KST
    labels = [u[3] for u in job._player_units(session, {"team": CITY}, now)]
    # The season before last (2024) is kept once too, as move evidence (2026-11-20).
    assert labels == [
        f"player_stats:{CITY}", f"player_stats:{CITY}:2025", f"player_stats:{CITY}:2024",
    ]
    for season in (2026, 2025, 2024):
        detail.mark_success(session, CITY, season, "player_stats", now, 1)
    assert job._player_units(session, {"team": CITY}, now) == []
    # season= with force=1 fetches a stored past season again (competition scope change).
    forced = job._player_units(session, {"team": CITY, "season": 2025, "force": "1"}, now)
    assert [u[3] for u in forced] == [f"player_stats:{CITY}:2025"]
    with pytest.raises(ValueError):
        job._player_units(session, {"team": CITY, "season": 2023}, now)
    tomorrow = now + timedelta(days=1)
    labels = [u[3] for u in job._player_units(session, {"team": CITY}, tomorrow)]
    assert labels == [f"player_stats:{CITY}"]  # the stored past season is not asked again
    # A failed past season is retried the next day until it succeeds once.
    session.execute(
        TeamSync.__table__.delete().where(
            TeamSync.team_id == CITY, TeamSync.season == 2025, TeamSync.kind == "player_stats"
        )
    )
    detail.mark_failure(session, CITY, 2025, "player_stats", now, "IncompleteData")
    labels = [u[3] for u in job._player_units(session, {"team": CITY}, tomorrow)]
    assert f"player_stats:{CITY}:2025" in labels
