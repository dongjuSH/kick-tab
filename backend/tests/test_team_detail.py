"""Team detail rules without a database (chat 08, TEAM-001·002·005·006)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.kst import KST
from app.models.fixture import Fixture
from app.models.team_detail import TeamSync, Transfer
from app.services.standings import IncompleteData
from app.services.team_detail import (
    NO_COACH,
    TransferContext,
    check_squad,
    check_transfers,
    half_range,
    is_due,
    last_refresh_day,
    match_result,
    merge_transfers,
    parse_profile_nationality,
    parse_squad,
    parse_statistics,
    parse_team_players,
    parse_transfers,
    pick_coach,
    season_of,
    shown_first,
)

TEAM = 77
TODAY = date(2026, 11, 7)


def coach(cid, team, career, name="C"):
    return {"id": cid, "name": name, "photo": None, "team": {"id": team}, "career": career}


def spell(team, start, end=None):
    return {"team": {"id": team}, "start": start, "end": end}


def test_current_coach_is_the_open_spell_with_the_latest_start():
    response = [
        coach(1, TEAM, [spell(TEAM, "2023-01-01")], name="Old"),
        coach(2, TEAM, [spell(TEAM, "2026-08-01"), spell(114, "2023-06-01")], name="New"),
        # A former coach now elsewhere still lists this team in his career.
        coach(3, 999, [spell(999, "2026-09-01"), spell(TEAM, "2027-01-01")], name="Gone"),
        coach(4, TEAM, [spell(TEAM, "2027-01-01", "2027-02-01")], name="Ended"),
    ]
    picked = pick_coach(response, TEAM, TODAY)
    assert (picked.coach_id, picked.name, picked.since) == (2, "New", date(2026, 8, 1))


def test_an_announced_coach_is_not_current_before_his_start():
    response = [
        coach(1, TEAM, [spell(TEAM, "2025-07-01")], name="Now"),
        coach(2, TEAM, [spell(TEAM, "2027-01-01")], name="Next"),
    ]
    assert pick_coach(response, TEAM, TODAY).name == "Now"
    assert pick_coach(response, TEAM, date(2027, 1, 1)).name == "Next"


def test_no_current_coach_is_none_never_a_former_one():
    assert pick_coach([], TEAM, TODAY) == NO_COACH
    ended = [coach(1, TEAM, [spell(TEAM, "2020-01-01", "2021-01-01")])]
    assert pick_coach(ended, TEAM, TODAY) == NO_COACH
    with pytest.raises(IncompleteData):
        pick_coach({"error": 1}, TEAM, TODAY)


def test_squad_keeps_missing_numbers_null_and_refuses_another_team():
    response = [{"team": {"id": TEAM}, "players": [
        {"id": 1, "name": "A", "number": 1, "position": "Goalkeeper", "photo": "p"},
        {"id": 2, "name": "B", "number": None, "position": None, "photo": None},
        {"id": 1, "name": "A", "number": 1, "position": "Goalkeeper", "photo": "p"},
    ]}]
    squad = parse_squad(response, TEAM)
    assert [m["player_id"] for m in squad.members] == [1, 2]
    assert squad.members[1] == {"player_id": 2, "number": None, "position": None}
    assert parse_squad([], TEAM).members == []
    with pytest.raises(IncompleteData):
        parse_squad([{"team": {"id": 1}, "players": []}], TEAM)


def side(home, away):
    return {"home": home, "away": away, "total": home + away}


def record():
    return {
        "league": {"id": 61, "season": 2025}, "team": {"id": TEAM},
        "fixtures": {
            "played": side(17, 16), "wins": side(3, 2), "draws": side(4, 4), "loses": side(10, 10),
        },
        "goals": {"for": {"total": side(18, 14)}, "against": {"total": side(30, 28)}},
    }


def test_statistics_must_belong_to_the_team_league_and_season():
    good = record()
    assert parse_statistics(good, TEAM, 61, 2025) == good
    assert parse_statistics([], TEAM, 61, 2025) is None
    with pytest.raises(IncompleteData):
        parse_statistics({**good, "league": {"id": 61, "season": 2026}}, TEAM, 61, 2025)


@pytest.mark.parametrize(
    "cut",
    [
        lambda r: r.update(fixtures={}),                                   # Codex 1차 지적 1
        lambda r: r["fixtures"]["wins"].update(total=None),
        lambda r: r["fixtures"]["played"].update(total=34),                # 33 = W+D+L
        lambda r: r["goals"].pop("against"),
        lambda r: r["goals"]["for"]["total"].update(total=50),            # Codex 2차 N1
        lambda r: r["fixtures"]["wins"].update(home=4),                    # halves vs total
    ],
)
def test_a_cut_season_record_is_refused(cut):
    answer = record()
    cut(answer)
    with pytest.raises(IncompleteData):
        parse_statistics(answer, TEAM, 61, 2025)


def test_a_cut_squad_or_transfer_season_is_refused():
    check_squad(24, 0)
    check_squad(25, 31)  # a summer window: a few players left
    for new, stored in ((1, 27), (17, 0), (0, 0), (20, 31)):
        with pytest.raises(IncompleteData):
            check_squad(new, stored)
    check_transfers(57, 59, 2026)  # the provider dropped a wrong entry or two
    check_transfers(0, 0, 2026)
    for new, stored in ((1, 59), (50, 59), (0, 3)):
        with pytest.raises(IncompleteData):
            check_transfers(new, stored, 2026)


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 6, 1), (2026, 1)),
        (date(2026, 12, 31), (2026, 1)),
        (date(2027, 1, 1), (2026, 2)),
        (date(2027, 5, 31), (2026, 2)),
        (date(2026, 5, 31), (2025, 2)),
    ],
)
def test_every_date_belongs_to_exactly_one_half(day, expected):
    assert season_of(day) == expected
    start, end = half_range(*expected)
    assert start <= day <= end


def test_the_july_1_run_still_picks_up_records_added_on_june_30():
    # 기능 명세서 6.2: a record reflected by June 30 reaches the next 00:00 run, then fixed.
    assert last_refresh_day(2025) == date(2026, 7, 1)


class _Session:
    def __init__(self, row):
        self.row = row

    def get(self, *_):
        return self.row


def kst(day, hour, minute=0):
    """A KST wall-clock moment as an aware UTC datetime."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=KST).astimezone(UTC)


def test_units_run_once_per_kst_day_so_a_manual_run_never_skips_00_00():
    day = date(2026, 11, 7)
    manual = TeamSync(synced_at=kst(day, 11, 40), failed_at=None)
    # The scheduled 00:00 KST run 12 hours later is due (a 23-hour rule skipped it).
    assert is_due(_Session(manual), TEAM, 2026, "transfers", kst(date(2026, 11, 8), 0, 0))
    # A second run on the same KST day is not.
    assert not is_due(_Session(manual), TEAM, 2026, "transfers", kst(day, 23, 59))
    failed = TeamSync(synced_at=None, failed_at=kst(day, 0, 0))
    assert is_due(_Session(failed), TEAM, 2026, "transfers", kst(date(2026, 11, 8), 0, 1))
    assert is_due(_Session(None), TEAM, 2026, "transfers", kst(day, 0, 0))


def move(day, came_to, left_from, kind="Transfer"):
    return {"date": day, "type": kind, "teams": {
        "in": {"id": came_to, "name": f"T{came_to}"},
        "out": {"id": left_from, "name": f"T{left_from}"},
    }}


def test_transfers_keep_only_moves_of_the_team_and_never_future_ones():
    response = [
        {"player": {"id": 1, "name": "P1"}, "transfers": [
            move("2026-07-01", TEAM, 10),            # arrival, first half
            move("2027-01-15", 20, TEAM, "Loan"),    # future: left out
            move("2019-07-01", 30, 40),              # history between other clubs
        ]},
        {"player": {"id": 2, "name": "P2"}, "transfers": [
            move("2026-02-01", 50, TEAM, "N/A"),     # departure, 2025 second half, no type
            move("2026-02-01", 50, TEAM, "N/A"),     # duplicate entry
            move("bad", TEAM, 60),                   # no readable date
        ]},
        {"player": {"id": None, "name": "x"}, "transfers": [move("2026-07-01", TEAM, 1)]},
    ]
    rows = parse_transfers(response, TEAM, date(2026, 11, 7))
    summary = sorted(
        (r["player_id"], r["direction"], r["season"], r["half"], r["type_raw"]) for r in rows
    )
    assert summary == [(1, "in", 2026, 1, "Transfer"), (2, "out", 2025, 2, None)]
    arrival = next(r for r in rows if r["direction"] == "in")
    assert (arrival["counterpart_id"], arrival["counterpart_name"]) == (10, "T10")


def stored(response, today=date(2027, 2, 1)):
    """parse_transfers rows as stored Transfer rows (ids in listing order)."""
    rows = parse_transfers(response, TEAM, today)
    return [Transfer(id=i, team_id=TEAM, **r) for i, r in enumerate(rows, start=1)]


def shown(rows):
    return sorted(
        (r.player_id, r.transfer_date.isoformat(), r.direction, r.counterpart_name)
        for r in merge_transfers(rows)
    )


def test_entries_are_stored_as_given_and_merged_only_when_answering():
    response = [{"player": {"id": 1, "name": "Rulli"}, "transfers": [
        move("2026-08-11", TEAM, 81), move("2026-08-10", TEAM, 81),
    ]}]
    rows = stored(response)
    assert len(rows) == 2  # raw: both entries kept
    assert shown(rows) == [(1, "2026-08-10", "in", "T81")]


def test_a_name_only_copy_of_a_move_is_dropped():
    # (가): "PSV" without id next to "PSV Eindhoven" with id, same player/date/direction.
    def named(team):
        return {"date": "2026-07-01", "type": "Transfer", "teams": {
            "in": team, "out": {"id": TEAM, "name": "Us"}}}

    response = [{"player": {"id": 4, "name": "P"}, "transfers": [
        named({"id": 197, "name": "PSV Eindhoven"}), named({"id": None, "name": "PSV"}),
    ]}]
    assert shown(stored(response)) == [(4, "2026-07-01", "out", "PSV Eindhoven")]


def test_a_move_registered_again_in_the_same_season_is_one_move():
    # (나): same player/direction/club/season, weeks apart → earliest date; 12-31 and 01-01
    # belong to the same season; another club stays a separate move.
    response = [
        {"player": {"id": 2, "name": "Year end"}, "transfers": [
            move("2026-12-31", TEAM, 5, "Loan"), move("2027-01-01", TEAM, 5, "Loan"),
        ]},
        {"player": {"id": 3, "name": "Weeks"}, "transfers": [
            move("2026-07-01", TEAM, 9), move("2026-08-15", TEAM, 9), move("2026-07-02", TEAM, 8),
        ]},
    ]
    assert shown(stored(response)) == [
        (2, "2026-12-31", "in", "T5"),
        (3, "2026-07-01", "in", "T9"), (3, "2026-07-02", "in", "T8"),
    ]


def test_a_move_the_other_way_in_between_keeps_both_moves():
    # Codex 1차 지적 8: loan out 08-10, back 08-11, loaned out again to the same club 08-11.
    response = [{"player": {"id": 9, "name": "Loanee"}, "transfers": [
        move("2026-08-10", 40, TEAM, "Loan"),
        move("2026-08-11", TEAM, 40, "Return from loan"),
        move("2026-08-11", 40, TEAM, "Loan"),
    ]}]
    kept = sorted((day, way) for _, day, way, _ in shown(stored(response, date(2026, 11, 7))))
    assert kept == [("2026-08-10", "out"), ("2026-08-11", "in"), ("2026-08-11", "out")]


def test_moves_to_clubs_without_an_id_are_never_merged():
    # Codex 2차 지적 N2: two loans a day apart, the other clubs named but without ids.
    def unnamed(day, name):
        return {"date": day, "type": "Loan", "teams": {
            "in": {"id": None, "name": name}, "out": {"id": TEAM, "name": "Us"},
        }}

    response = [{"player": {"id": 7, "name": "Loanee"}, "transfers": [
        unnamed("2026-08-10", "Club A"), unnamed("2026-08-11", "Club B"),
    ]}]
    assert [name for *_, name in shown(stored(response))] == ["Club A", "Club B"]


def test_same_day_moves_to_two_unnamed_id_clubs_are_two_rows():
    # Codex 3차 지적 N4: loan to A, back from A, loan to B — all on one day, no club ids.
    def loan(came_to, left_from, kind):
        return {"date": "2026-08-31", "type": kind, "teams": {"in": came_to, "out": left_from}}

    us, a, b = {"id": TEAM, "name": "Us"}, {"id": None, "name": "A"}, {"id": None, "name": "B"}
    response = [{"player": {"id": 8, "name": "Loanee"}, "transfers": [
        loan(a, us, "Loan"), loan(us, a, "Back from Loan"), loan(b, us, "Loan"),
    ]}]
    assert sorted((way, name) for *_, way, name in shown(stored(response))) == [
        ("in", "A"), ("out", "A"), ("out", "B"),
    ]


def test_moves_shown_first_follow_rule_b():
    context = TransferContext(players=frozenset({1}), clubs=frozenset({500}))

    def row(player, direction, kind, club_id, club_name):
        return Transfer(player_id=player, direction=direction, type_raw=kind,
                        counterpart_id=club_id, counterpart_name=club_name)

    assert shown_first(row(1, "out", "Loan", 900, "Lower"), context)  # ① squad player
    assert shown_first(row(2, "in", "Free agent", 900, "Lower"), context)  # ② signing
    assert not shown_first(row(2, "in", "Transfer", 901, "Tottenham Hotspur U21"), context)
    assert not shown_first(row(2, "in", "Return from loan", 900, "Lower"), context)
    assert shown_first(row(3, "out", "Loan", 500, "Benfica"), context)  # ③ league/UEFA club
    assert not shown_first(row(3, "out", "Loan", 900, "Watford"), context)


def players_page(current, total, entries):
    return {"paging": {"current": current, "total": total}, "response": entries}


def entry(pid, *lines):
    return {"player": {"id": pid, "name": f"P{pid}", "nationality": "England"},
            "statistics": list(lines)}


def line(team, league, apps, goals=0, rating="7.1"):
    return {"team": {"id": team}, "league": {"id": league, "season": 2026},
            "games": {"appearences": apps, "rating": rating},
            "goals": {"total": goals, "assists": None}}


def test_team_player_lines_keep_only_this_team_in_record_competitions():
    page = players_page(1, 1, [
        entry(1, line(TEAM, 39, 10, 9), line(TEAM, 2, 3, 5, None), line(TEAM, 45, 2, 1),
              line(TEAM, 15, 3), line(TEAM, 667, 4), line(600, 39, 5)),
        entry(2, line(TEAM, 848, 1, 0, "0")),
    ])
    parsed = parse_team_players([page], TEAM, 2026)
    kept = sorted((x["player_id"], x["competition_id"], x["appearances"], x["goals"],
                   x["assists"], x["rating"]) for x in parsed.lines)
    assert kept == [
        (1, 2, 3, 5, None, None), (1, 39, 10, 9, None, Decimal("7.1")),
        (2, 848, 1, 0, None, None),
    ]
    assert len(parsed.players) == 2


def test_a_missing_or_short_page_is_refused():
    full = [entry(i, line(TEAM, 39, 1)) for i in range(1, 21)]
    with pytest.raises(IncompleteData):
        parse_team_players([players_page(1, 2, full)], TEAM, 2026)
    with pytest.raises(IncompleteData):
        parse_team_players(
            [players_page(1, 2, full[:19]), players_page(2, 2, [entry(30)])], TEAM, 2026
        )


def test_a_player_listed_twice_refuses_the_whole_set():
    # Codex 1차 지적 1: page 2 repeats page 1's last player in place of another one (shifted
    # pages) — the first collection, a later one and a conflicting repeat are all refused.
    full = [entry(i, line(TEAM, 39, 1)) for i in range(1, 21)]
    shifted = [players_page(1, 2, full), players_page(2, 2, [entry(20, line(TEAM, 39, 1))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(shifted, TEAM, 2026)
    conflicting = [players_page(1, 2, full), players_page(2, 2, [entry(20, line(TEAM, 39, 5))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(conflicting, TEAM, 2026)
    same_page = [players_page(1, 1, [entry(1, line(TEAM, 39, 1)), entry(1, line(TEAM, 2, 1))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(same_page, TEAM, 2026)


def fixture(home, away, gh, ga, finish=None, pen=None):
    return Fixture(home_team_id=home, away_team_id=away, goals_home=gh, goals_away=ga,
                   finish_type=finish, score={"penalty": pen} if pen else None)


def test_match_result_uses_the_shoot_out_for_level_matches():
    assert match_result(fixture(TEAM, 1, 2, 1), TEAM) == "W"
    assert match_result(fixture(1, TEAM, 2, 1), TEAM) == "L"
    assert match_result(fixture(1, TEAM, 1, 1), TEAM) == "D"
    level = fixture(1, TEAM, 1, 1, "pen", {"home": 3, "away": 4})
    assert match_result(level, TEAM) == "W"


def test_profile_nationality_stays_missing_when_the_profile_has_none():
    assert parse_profile_nationality([{"player": {"id": 5, "nationality": None}}], 5) is None
    found = [{"player": {"id": 5, "nationality": "France"}}]
    assert parse_profile_nationality(found, 5) == "France"
    assert parse_profile_nationality([], 5) is None  # no profile: checked once
    with pytest.raises(IncompleteData):  # another player's answer: asked again
        parse_profile_nationality([{"player": {"id": 6, "nationality": "Spain"}}], 5)
