"""Chat 07 team browse against the dev database (opt-in, always rolled back).

Run: KICKTAB_DB_TESTS=1 uv run python -m pytest tests/test_teams_db.py
Needs the reference job of the current season (five-league team lists and aliases).
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models.reference import CompetitionSeason, TeamCompetitionSeason
from app.seed.competitions import LEAGUE_IDS, UEFA_IDS
from app.services.team_browse import PAGE_SIZE

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)

CITY, UNITED, BAYERN, WEST_HAM = 50, 33, 157, 48


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


def members(session, leagues=LEAGUE_IDS) -> set[int]:
    return set(
        session.scalars(
            select(TeamCompetitionSeason.team_id).where(
                TeamCompetitionSeason.season == settings.current_season,
                TeamCompetitionSeason.competition_id.in_(leagues),
            )
        )
    )


def all_pages(client, **query) -> list[dict]:
    items, page = [], 1
    while True:
        body = client.get("/api/v1/teams", params={**query, "page": page}).json()
        if not body["data"]:
            return items
        items += body["data"]
        page += 1


def test_every_current_member_once_in_league_order(client, session):
    expected = members(session)
    first = client.get("/api/v1/teams").json()
    assert first["meta"]["total"] == len(expected)
    assert (first["meta"]["page"], first["meta"]["size"]) == (1, PAGE_SIZE)
    assert first["meta"]["updatedAt"] is not None
    items = all_pages(client)
    ids = [i["team"]["id"] for i in items]
    assert len(ids) == len(set(ids)) and set(ids) == expected
    # Premier League first ... Ligue 1 last; every team links to its detail.
    order = [LEAGUE_IDS.index(i["league"]["id"]) for i in items]
    assert order == sorted(order)
    assert all(i["team"]["detailAvailable"] is True for i in items)
    last = -(-len(expected) // PAGE_SIZE)
    tail = client.get("/api/v1/teams", params={"page": last}).json()
    assert len(tail["data"]) == len(expected) - (last - 1) * PAGE_SIZE
    past = client.get("/api/v1/teams", params={"page": last + 1}).json()
    assert past["data"] == [] and past["meta"]["total"] == len(expected)


def test_league_filter_lists_only_that_league(client, session):
    for league in LEAGUE_IDS:
        items = all_pages(client, league=league)
        assert {i["team"]["id"] for i in items} == members(session, (league,))
        assert {i["league"]["id"] for i in items} == {league}


def test_search_korean_english_and_ambiguous_alias(client):
    def ids(**query):
        return [i["team"]["id"] for i in all_pages(client, **query)]

    assert ids(q="맨시티") == [CITY]
    assert ids(q="Bayern")[0] == BAYERN
    assert set(ids(q="맨체스터")) == {CITY, UNITED}  # ambiguous: every team it names
    assert ids(q="맨체스터", league=78) == []  # combined with the league filter
    body = client.get("/api/v1/teams", params={"q": "없는팀이름"}).json()
    assert body["data"] == [] and body["meta"]["total"] == 0


def test_past_season_and_uefa_only_teams_are_not_listed(client, session):
    assert WEST_HAM not in members(session)  # relegated in 2025-26
    assert client.get("/api/v1/teams", params={"q": "웨스트햄"}).json()["meta"]["total"] == 0
    # The main search still finds that season's team (chat 05), the browse list does not.
    past = client.get("/api/v1/teams/search", params={"q": "웨스트햄", "season": 2025}).json()
    assert WEST_HAM in [t["id"] for t in past["data"]]
    uefa_only = members(session, UEFA_IDS) - members(session)
    listed = {i["team"]["id"] for i in all_pages(client)}
    assert uefa_only and not uefa_only & listed


def test_unknown_membership_fails_instead_of_short_list(client, session):
    session.execute(
        update(CompetitionSeason)
        .where(
            CompetitionSeason.competition_id == 61,
            CompetitionSeason.season == settings.current_season,
        )
        .values(teams_synced_at=None)
    )
    for query in ({}, {"league": 61}, {"q": "파리"}):
        response = client.get("/api/v1/teams", params=query)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "MEMBERSHIP_UNKNOWN"
    # A league whose list is known still answers.
    assert client.get("/api/v1/teams", params={"league": 39}).status_code == 200

