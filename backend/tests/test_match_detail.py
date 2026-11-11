"""Chat 04 match detail rules without a database: parsing, block states, fetch timing,
head-to-head/form filtering and widening."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
from pydantic import SecretStr

from app.providers.api_football import ApiFootballClient, DailyBudget, MinuteRateLimiter
from app.services.head_to_head import (
    fetch_form,
    fetch_meetings,
    is_official_result,
    recent_form,
    result_for,
)
from app.services.match_detail import (
    _event_rows,
    _lineups,
    _ratings,
    _statistics,
    detail_fetch_due,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
FIXTURE = SimpleNamespace(id=1, home_team_id=10, away_team_id=20, status="finished",
                          kickoff_at=NOW - timedelta(hours=3))


def fixture(**changes):
    return SimpleNamespace(**{**vars(FIXTURE), **changes})


def detail(**values):
    base = {"fetched_at": None, "fetched_status": None, "last_failed_at": None, "lineups": None}
    return SimpleNamespace(**{**base, **values})


def test_events_keep_provider_order_and_drop_exact_repeats():
    event = {
        "time": {"elapsed": 12, "extra": None},
        "team": {"id": 10},
        "player": {"name": "A"},
        "assist": {"name": None},
        "type": "Goal",
        "detail": "Normal Goal",
    }
    later = {**event, "time": {"elapsed": 45, "extra": 2}, "type": "Card", "detail": "Yellow Card"}
    rows = _event_rows(1, [event, event, later])
    assert [(r["seq"], r["elapsed"], r["type"]) for r in rows] == [(0, 12, "Goal"), (1, 45, "Card")]


def test_statistics_follow_figma_order_and_keep_missing_values_empty():
    blocks = [
        {"team": {"id": 20}, "statistics": [
            {"type": "Total Shots", "value": 9}, {"type": "Ball Possession", "value": "44%"},
            {"type": "Red Cards", "value": None}, {"type": "expected_goals", "value": "0.83"},
        ]},
        {"team": {"id": 10}, "statistics": [
            {"type": "Ball Possession", "value": "56%"}, {"type": "Total Shots", "value": 14},
            {"type": "Red Cards", "value": None}, {"type": "Fouls", "value": None},
        ]},
    ]
    rows = _statistics(FIXTURE, blocks)
    assert [(r.key, r.home, r.away, r.percent) for r in rows] == [
        ("Ball Possession", 56.0, 44.0, True),
        ("Total Shots", 14.0, 9.0, False),
        ("expected_goals", None, 0.83, False),
    ]  # Red Cards / Fouls had no value at all: not shown, never 0


def test_lineups_home_first_and_ratings_sorted_with_missing_last():
    lineups = _lineups(FIXTURE, [
        {"team": {"id": 20}, "formation": "4-3-3", "coach": {"name": "C"},
         "startXI": [{"player": {"name": "B1", "number": 1, "pos": "G"}}], "substitutes": []},
        {"team": {"id": 10}, "formation": None, "coach": {},
         "startXI": [{"player": {"name": "H1", "number": None, "pos": None}}],
         "substitutes": [{"player": {"name": "H12", "number": 12, "pos": "D"}}]},
    ])
    summary = [(x.side, x.formation, x.coach, x.start_xi[0].name) for x in lineups]
    assert summary == [
        ("home", None, None, "H1"),
        ("away", "4-3-3", "C", "B1"),
    ]

    def player(name, rating, minutes=90):
        return {"player": {"id": 1, "name": name, "photo": None},
                "statistics": [{"games": {"rating": rating, "minutes": minutes}}]}

    ratings = _ratings(FIXTURE, [{"team": {"id": 10}, "players": [
        player("A", "7.1"), player("B", None), player("C", "8.4"), player("Unused", None, None),
        player("Bench", "0", 0),  # provider placeholder for an unused substitute
    ]}])
    assert [(p.name, p.rating) for p in ratings] == [("C", 8.4), ("A", 7.1), ("B", None)]


def test_detail_fetch_timing():
    # Finished: once in the final status; a live record is replaced once, then never again.
    assert detail_fetch_due(FIXTURE, None, NOW)
    assert detail_fetch_due(FIXTURE, detail(fetched_at=NOW, fetched_status="live"), NOW)
    assert not detail_fetch_due(FIXTURE, detail(fetched_at=NOW, fetched_status="finished"), NOW)
    # A failure holds back further attempts for a while.
    assert not detail_fetch_due(FIXTURE, detail(last_failed_at=NOW - timedelta(minutes=1)), NOW)
    assert detail_fetch_due(FIXTURE, detail(last_failed_at=NOW - timedelta(minutes=6)), NOW)
    # Live: at most every 90 seconds.
    live = fixture(status="live")
    assert not detail_fetch_due(live, detail(fetched_at=NOW - timedelta(seconds=60)), NOW)
    assert detail_fetch_due(live, detail(fetched_at=NOW - timedelta(seconds=120)), NOW)
    # Scheduled: never, however close kickoff is (the lineup is shown from kickoff on,
    # MAT-004 rule 4), with or without a stored record.
    later = fixture(status="scheduled", kickoff_at=NOW + timedelta(hours=5))
    soon = fixture(status="scheduled", kickoff_at=NOW + timedelta(minutes=50))
    assert not detail_fetch_due(later, None, NOW)
    assert not detail_fetch_due(soon, None, NOW)
    assert not detail_fetch_due(soon, detail(fetched_at=NOW - timedelta(minutes=11)), NOW)
    # Postponed / cancelled: no request.
    assert not detail_fetch_due(fixture(status="postponed"), None, NOW)
    assert not detail_fetch_due(fixture(status="cancelled"), None, NOW)


def result_item(fid, league_id=39, league="Premier League", short="FT", home=10, away=20,
                goals=(1, 0), winner=(True, False), day=1):
    return {
        "fixture": {"id": fid, "timestamp": int(datetime(2026, 10, day, tzinfo=UTC).timestamp()),
                    "status": {"short": short}},
        "league": {"id": league_id, "name": league, "round": "R"},
        "teams": {"home": {"id": home, "name": "H", "winner": winner[0]},
                  "away": {"id": away, "name": "A", "winner": winner[1]}},
        "goals": {"home": goals[0], "away": goals[1]},
        "score": {"penalty": {"home": None, "away": None}},
    }


def test_friendlies_and_unfinished_matches_are_not_official_results():
    assert is_official_result(result_item(1))
    assert not is_official_result(result_item(1, league_id=667, league="Friendlies Clubs"))
    assert not is_official_result(result_item(1, league_id=9999, league="Club Friendlies 2"))
    assert not is_official_result(result_item(1, short="NS"))
    assert is_official_result(result_item(1, short="PEN"))


def make_client(handler):
    return ApiFootballClient(
        SecretStr("test-key"),
        transport=httpx.MockTransport(handler),
        limiter=MinuteRateLimiter(1000),
        budget=DailyBudget(1000),
        sleep=lambda _: None,
    )


def body(items):
    return httpx.Response(200, json={"errors": [], "results": len(items), "response": items})


def test_meetings_widen_once_when_friendlies_fill_the_first_window():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        if "last" in request.url.params:
            friendlies = [result_item(i, 667, "Friendlies Clubs", day=i + 1) for i in range(7)]
            return body(friendlies + [result_item(100 + i, day=20 + i) for i in range(3)])
        return body([result_item(200 + i, day=1 + i) for i in range(8)])

    rows = fetch_meetings(make_client(handler), 10, 20)
    assert [c.get("last") for c in calls] == ["10", None]
    assert len(rows) == 8 and rows[0]["kickoffAt"] > rows[-1]["kickoffAt"]


def test_form_does_not_widen_when_history_is_short_and_reads_results():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        return body([
            result_item(1, day=3, home=10, away=30, goals=(2, 0), winner=(True, False)),
            result_item(2, day=2, home=40, away=10, goals=(1, 1), winner=(None, None)),
            result_item(3, day=1, home=50, away=10, goals=(3, 1), winner=(True, False)),
        ])

    rows = fetch_form(make_client(handler), 10)
    assert len(calls) == 1  # 3 results < 10 requested: nothing older exists
    assert [result_for(r, 10) for r in recent_form(rows, 10)] == ["W", "D", "L"]
    before = datetime(2026, 10, 2, 12, tzinfo=UTC)
    assert [r["fixtureId"] for r in recent_form(rows, 10, before)] == [2, 3]


def test_provider_names_keep_english_with_html_entities_decoded():
    # The provider sends some names HTML-escaped (seen: "N. O&apos;Reilly"). Names stay in
    # the provider's English (MAT-004 decision 2026-11-11); only the escaping is undone.
    lineups = _lineups(FIXTURE, [
        {"team": {"id": 10}, "formation": "4-3-3", "coach": {"name": "P. O&apos;Neil"},
         "startXI": [{"player": {"name": "N. O&apos;Reilly", "number": 33, "pos": "D"}},
                     {"player": {"name": "  ", "number": 1, "pos": "G"}}],
         "substitutes": [{"player": {"name": "A &amp; B", "number": 12, "pos": "M"}}]},
    ])
    [home] = lineups
    assert [p.name for p in home.start_xi] == ["N. O'Reilly"]  # a blank name is skipped
    assert home.substitutes[0].name == "A & B"
    assert home.coach == "P. O'Neil"
    ratings = _ratings(FIXTURE, [{"team": {"id": 10}, "players": [
        {"player": {"id": 1, "name": "N. O&apos;Reilly", "photo": None},
         "statistics": [{"games": {"rating": "7.0", "minutes": 90}}]}]}])
    assert ratings[0].name == "N. O'Reilly"
