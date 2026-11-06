"""Chat 06 parsing and aggregation rules (no DB, no network)."""

from datetime import UTC, datetime

import pytest

from app.services.standings import (
    IncompleteData,
    SavesLine,
    aggregate_saves,
    due_leagues,
    parse_player_pages,
    parse_standings,
    parse_top_list,
    relegation_zone,
)


def standings_answer(league=61, season=2025, rows=None):
    rows = rows or [
        {"rank": 1, "team": {"id": 85, "name": "PSG"}, "points": 76, "goalsDiff": 45,
         "group": "Ligue 1", "form": "LWWDW", "description": "Champions League",
         "all": {"played": 34, "win": 23, "draw": 7, "lose": 4,
                 "goals": {"for": 70, "against": 25}},
         "update": "2026-05-17T00:00:00+00:00"},
        {"rank": 2, "team": {"id": 83, "name": "Nantes"}, "points": 23, "goalsDiff": -23,
         "group": "Ligue 1", "form": None, "description": "Relegation",
         "all": {"played": 33, "win": 5, "draw": 8, "lose": 20,
                 "goals": {"for": None, "against": 40}}},
    ]
    return [{"league": {"id": league, "season": season, "name": "Ligue 1", "standings": [rows]}}]


def test_standings_keep_provider_values_as_given():
    parsed = parse_standings(standings_answer(), 61, 2025)
    nantes = parsed.rows[1]
    # 33 matches stays 33 (never corrected to 34); a missing number stays None, never 0.
    assert nantes["played"] == 33 and nantes["goals_for"] is None and nantes["form"] is None
    assert nantes["description"] == "Relegation" and nantes["group_name"] == "Ligue 1"
    assert {t["id"] for t in parsed.teams} == {85, 83}


def test_standings_of_another_league_or_season_are_refused():
    with pytest.raises(IncompleteData):
        parse_standings(standings_answer(league=78), 61, 2025)
    with pytest.raises(IncompleteData):
        parse_standings(standings_answer(season=2026), 61, 2025)
    with pytest.raises(IncompleteData):
        parse_standings(standings_answer(rows=[{"rank": 1, "team": {}}]), 61, 2025)


@pytest.mark.parametrize(
    ("description", "zone"),
    [
        ("Relegation - Championship", "relegation"),
        ("Relegation", "relegation"),
        ("Relegation Playoffs", "relegation_playoff"),
        ("Play-offs", None),
        ("Promotion - Champions League (League phase)", None),
        (None, None),
    ],
)
def test_relegation_zone_follows_the_season_description(description, zone):
    assert relegation_zone(description) == zone


def top_entry(pid, team, red, yellowred, league=61):
    return {
        "player": {"id": pid, "name": f"P{pid}", "photo": None},
        "statistics": [
            {"team": {"id": 999, "name": "Other"}, "league": {"id": 2, "season": 2025},
             "cards": {"red": 5, "yellowred": 5}},
            {"team": {"id": team, "name": f"T{team}"}, "league": {"id": league, "season": 2025},
             "cards": {"red": red, "yellowred": yellowred}},
        ],
    }


def test_red_list_keeps_order_and_never_adds_second_yellows():
    answer = [top_entry(1, 10, 2, 1), top_entry(2, 11, 1, None), top_entry(3, 12, None, 0)]
    parsed = parse_top_list(answer, "red", 61, 2025)
    assert [(r["position"], r["player_id"], r["value"], r["yellowred"]) for r in parsed.rows] == [
        (1, 1, 2, 1), (2, 2, 1, None), (3, 3, None, 0),
    ]
    # Only this league's line counts (the UEFA line with 5 reds is ignored).
    assert parsed.rows[0]["team_id"] == 10


def test_yellowred_is_kept_only_on_red_lists():
    parsed = parse_top_list([top_entry(1, 10, 2, 1)], "yellow", 61, 2025)
    assert parsed.rows[0]["yellowred"] is None


def page(current, total, entries):
    return {"paging": {"current": current, "total": total}, "response": entries}


def player_entry(pid, team, saves, position="Goalkeeper", apps=10):
    return {
        "player": {"id": pid, "name": f"P{pid}"},
        "statistics": [{
            "team": {"id": team, "name": f"T{team}"},
            "league": {"id": 39, "season": 2025},
            "games": {"position": position, "appearences": apps},
            "goals": {"saves": saves},
            "cards": {},
        }],
    }


def full(current, total, first_id):
    """A page with the provider's 20 entries."""
    return page(current, total, [player_entry(first_id + i, 10, 1) for i in range(20)])


def test_player_pages_must_be_complete():
    with pytest.raises(IncompleteData):  # page 2 of 2 never came
        parse_player_pages([full(1, 2, 1)], 39, 2025)
    with pytest.raises(IncompleteData):  # page 1 twice
        parse_player_pages([full(1, 2, 1), full(1, 2, 21)], 39, 2025)
    parsed = parse_player_pages([page(2, 2, [player_entry(99, 10, None)]), full(1, 2, 1)], 39, 2025)
    assert len(parsed.lines) == 21


def test_cut_pages_are_refused():
    """Codex 1차 지적 1: total=2 with an empty second page replaced 693 lines with 20."""
    with pytest.raises(IncompleteData):
        parse_player_pages([full(1, 2, 1), page(2, 2, [])], 39, 2025)
    short = page(1, 2, [player_entry(i, 10, 1) for i in range(1, 11)])  # 10 of 20
    with pytest.raises(IncompleteData):
        parse_player_pages([short, page(2, 2, [player_entry(50, 10, 1)])], 39, 2025)
    # The last page may hold 1..20 entries.
    assert len(parse_player_pages([full(1, 2, 1), full(2, 2, 21)], 39, 2025).lines) == 40


def test_an_empty_player_answer_is_no_data_not_a_failure():
    parsed = parse_player_pages([page(1, 0, [])], 39, 2025)
    assert parsed.lines == []
    with pytest.raises(IncompleteData):  # an empty page that claims more pages is not
        parse_player_pages([page(1, 3, [])], 39, 2025)


def test_numbered_full_page_cannot_repeat_another_pages_players():
    first = full(1, 3, 1)
    repeated = page(3, 3, list(reversed(first["response"])))
    with pytest.raises(IncompleteData, match="page 3 repeats player"):
        parse_player_pages([first, full(2, 3, 21), repeated], 39, 2025)


@pytest.mark.parametrize("overlap", [1, 10, 19])
def test_shifted_pages_with_a_partial_overlap_are_refused(overlap):
    """Page numbers and sizes are right, but page 2 starts with the last players of page 1:
    as many other players were never received."""
    first = full(1, 2, 1)
    shifted = page(2, 2, first["response"][-overlap:] + full(2, 2, 21)["response"][: 20 - overlap])
    with pytest.raises(IncompleteData, match="page 2 repeats player"):
        parse_player_pages([first, shifted], 39, 2025)


def test_one_entry_may_repeat_a_club_line_but_not_contradict_it():
    entry = player_entry(1, 10, 3)
    entry["statistics"].append(dict(entry["statistics"][0]))  # same club line twice
    assert len(parse_player_pages([page(1, 1, [entry])], 39, 2025).lines) == 1
    entry["statistics"][1] = {**entry["statistics"][0], "goals": {"saves": 4}}
    with pytest.raises(IncompleteData, match="two lines for team 10"):
        parse_player_pages([page(1, 1, [entry])], 39, 2025)


def test_standing_ranks_must_run_one_to_n():
    rows = standings_answer()[0]["league"]["standings"][0]
    rows[1]["rank"] = 2  # 1, 2 is fine
    assert len(parse_standings(standings_answer(rows=rows), 61, 2025).rows) == 2
    rows[1]["rank"] = 17  # 1, 17: the table was cut
    with pytest.raises(IncompleteData):
        parse_standings(standings_answer(rows=rows), 61, 2025)


def test_saves_sum_clubs_exclude_missing_and_share_ranks():
    lines = [
        SavesLine(1, 10, 12, 10),
        SavesLine(2, 11, 7, 5), SavesLine(2, 12, 5, 8),  # two clubs: 12 in total
        SavesLine(3, 13, 30, 20), SavesLine(3, 14, None, 0),  # one missing line: excluded
        SavesLine(4, 15, 8, 9),
        SavesLine(5, 16, None, 0),
    ]
    ranked, excluded = aggregate_saves(lines)
    assert [(r.player_id, r.saves, r.rank, r.tied) for r in ranked] == [
        (1, 12, 1, True), (2, 12, 1, True), (4, 8, 3, False),
    ]
    assert excluded == {3, 5}
    # The shown club of a two-club keeper is the one with more appearances.
    assert ranked[1].team_id == 12


class _State:
    def __init__(self, synced=None, failed=None):
        self.synced_at, self.failed_at = synced, failed


class _Session:
    """Only `get` (sync state) and `scalar` (matchday count) are used."""

    def __init__(self, states, matchday=0):
        self.states, self.matchday = states, matchday

    def get(self, _model, key):
        return self.states.get(key[0])

    def scalar(self, _query):
        return self.matchday


NOW = datetime(2026, 11, 7, 12, tzinfo=UTC)


def test_current_season_is_daily_and_hourly_only_on_matchdays(monkeypatch):
    from app.services import standings as module

    monkeypatch.setattr(module.settings, "current_season", 2026)
    states = {
        39: _State(datetime(2026, 11, 7, 10, tzinfo=UTC)),  # 2 h ago
        140: _State(datetime(2026, 11, 7, 11, 30, tzinfo=UTC)),  # 30 min ago
        135: _State(datetime(2026, 11, 6, 12, tzinfo=UTC)),  # a day ago
        78: _State(None, datetime(2026, 11, 7, 11, 40, tzinfo=UTC)),  # never, failed just now
    }
    idle = due_leagues(_Session(states, 0), 2026, "standings", NOW, matchday_hourly=True)
    assert idle == [135, 61]
    assert due_leagues(_Session(states, 1), 2026, "standings", NOW, matchday_hourly=True) == [
        39, 135, 61,
    ]


def test_past_season_is_collected_once_and_kept(monkeypatch):
    from app.services import standings as module

    monkeypatch.setattr(module.settings, "current_season", 2026)
    states = {league: _State(datetime(2026, 1, 1, tzinfo=UTC)) for league in (39, 140, 135, 78)}
    assert due_leagues(_Session(states, 1), 2025, "standings", NOW, matchday_hourly=True) == [61]


@pytest.mark.parametrize("params", [{"season": "2019"}, {"season": "abc"}, {"league": "45"}])
def test_bad_parameters_reach_the_run_so_the_failure_is_recorded(params):
    from app.sync.standings import _standings_precheck

    # The precheck lets the run start; the job itself raises and sync_runs records it.
    assert _standings_precheck(_Session({}), params) is True


def test_shrink_rule_keeps_stored_sets():
    from app.services.standings import PLAYER_SHRINK_TOLERANCE, _refuse_shrink

    _refuse_shrink("goals", 5, 0)  # first load: any size
    _refuse_shrink("goals", 20, 20)
    with pytest.raises(IncompleteData):
        _refuse_shrink("goals", 19, 20)  # a top list never gets shorter in a season
    _refuse_shrink("players", 630, 693, PLAYER_SHRINK_TOLERANCE)  # small provider merge
    with pytest.raises(IncompleteData):
        _refuse_shrink("players", 20, 693, PLAYER_SHRINK_TOLERANCE)  # Codex case: cut answer
