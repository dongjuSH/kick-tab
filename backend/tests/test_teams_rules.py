"""Chat 07 team browse request rules that are decided before any database read."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app), session
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("league", [0, -1, 2, 45, 999])
def test_unsupported_league_is_404_without_a_list(client, league):
    """0, negative, UEFA, cup or unknown: no browse list and never "every league"."""
    http, session = client
    response = http.get("/api/v1/teams", params={"league": league})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    session.execute.assert_not_called()


@pytest.mark.parametrize(
    "query", [{"league": "abc"}, {"page": 0}, {"page": "x"}, {"q": ""}, {"q": "x" * 41}]
)
def test_unreadable_conditions_are_422(client, query):
    http, _ = client
    response = http.get("/api/v1/teams", params=query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
