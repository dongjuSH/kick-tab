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
from app.models.news import NewsArticle, NewsArticleTeam
from app.models.reference import CompetitionSeason, Team
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


def test_squad_rows_are_one_per_player_with_this_teams_line(client):
    data = client.get(f"/api/v1/teams/{CITY}/squad").json()["data"]
    players = data["players"]
    ids = [p["player"]["id"] for p in players]
    assert len(ids) == len(set(ids))
    record = {39, 140, 135, 78, 61, 2, 3, 848}
    for player in players:
        lines = player["competitions"]
        assert {line["competition"]["id"] for line in lines} <= record
        for line in lines:
            assert line["rating"] is None or float(line["rating"]) > 0  # "0" is not a rating
        totals = player["totals"]
        if totals is not None:  # the totals are the sum of the lines shown under them
            for key in ("appearances", "goals", "assists"):
                assert totals[key] == sum(line[key] for line in lines)


def test_recent_matches_come_from_stored_fixtures_oldest_first(client):
    recent = client.get(f"/api/v1/teams/{CITY}").json()["data"]["recent"]
    assert 0 < len(recent) <= 5
    days = [m["kickoffAt"] for m in recent]
    assert days == sorted(days)
    for match in recent:
        assert CITY in (match["home"]["id"], match["away"]["id"])
        assert match["result"] in ("W", "D", "L")


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
    moves = [*first["arrivals"], *first["departures"], *first["otherArrivals"],
             *first["otherDepartures"]]
    for item in moves:
        assert "2026-06-01" <= item["transferDate"] <= "2026-12-31"
    # One entry per move (D-08-6): Stones once, Akanji and Echeverri shown first.
    assert [m["playerName"] for m in moves].count("J. Stones") == 1
    shown = {m["playerName"] for m in [*first["arrivals"], *first["departures"]]}
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
    assert labels == [f"player_stats:{CITY}", f"player_stats:{CITY}:2025"]
    detail.mark_success(session, CITY, 2026, "player_stats", now, 1)
    detail.mark_success(session, CITY, 2025, "player_stats", now, 1)
    assert job._player_units(session, {"team": CITY}, now) == []
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
