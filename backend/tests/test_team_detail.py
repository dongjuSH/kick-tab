"""Team detail rules without a database (chat 08, TEAM-001·002·005·006)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.kst import KST
from app.models.fixture import Fixture
from app.models.team_detail import TeamSync, Transfer
from app.services.standings import IncompleteData
from app.services.team_detail import (
    NO_COACH,
    MoveEvidence,
    check_season,
    check_squad,
    check_transfers,
    group_moves,
    half_range,
    is_due,
    is_first_team,
    judge_move,
    last_refresh_day,
    match_result,
    merge_transfers,
    parse_player_season,
    parse_profile_nationality,
    parse_squad,
    parse_statistics,
    parse_team_players,
    parse_transfers,
    pick_coach,
    same_move,
    season_of,
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

def stored_season(moves):
    """`moves` distinct moves (2026, club id 1000+i), each stored twice: the provider's copy
    re-dated a day later (the pairs the D-08-6 merge turns into one move)."""
    rows = []
    for i in range(moves):
        day = date(2026, 7, 1 + i % 28)
        for copy, shift in ((0, 0), (1, 1)):
            rows.append(Transfer(
                id=2 * i + copy + 1, player_id=500 + i, direction="out", counterpart_id=1000 + i,
                counterpart_name=f"C{i}", type_raw="Transfer", season=2026, half=1,
                transfer_date=day + timedelta(days=shift),
            ))
    return rows


def answer_without(rows, missing):
    """The provider's new answer: one copy per move (the later date), `missing` moves gone."""
    later = [r for r in rows if r.id % 2 == 0]
    return [Transfer(**{c: getattr(r, c) for c in (
        "player_id", "direction", "counterpart_id", "counterpart_name", "type_raw", "season",
        "half", "transfer_date")}) for r in later[missing:]]


def test_one_entry_never_stands_for_two_loans_to_the_same_club():
    # Loan out (Aug) · back (Dec) · out again (Feb) to club 300: when the answer drops the
    # second loan, the first loan's entry does not cover it (self-review 2026-11-24).
    def loan(player, direction, day, kind):
        return Transfer(player_id=player, direction=direction, counterpart_id=300,
                        counterpart_name="C300", type_raw=kind, season=2026,
                        half=1 if day.month >= 6 else 2, transfer_date=day)

    stored, answer = [], []
    for player in (1, 2, 3):
        first = loan(player, "out", date(2026, 8, 1), "Loan")
        back = loan(player, "in", date(2026, 12, 20), "Return from loan")
        again = loan(player, "out", date(2027, 2, 1), "Loan")
        stored += [first, back, again]
        answer += [first, back]
    assert not same_move(stored[2], answer[0], {date(2026, 12, 20)})
    # A copy re-dated a day later, with the loan return on the first day, is the same move.
    assert same_move(loan(9, "out", date(2026, 6, 29), "Transfer"),
                     loan(9, "out", date(2026, 6, 30), "Transfer"), {date(2026, 6, 29)})
    with pytest.raises(IncompleteData):  # 3 lost loans of 9 moves > max(2, 10%)
        check_transfers(stored, answer, 2026)


def test_a_deduplicated_answer_is_stored_and_a_cut_one_refused():
    # 2026-11-24: the provider stopped repeating moves — 40 rows → 20, the same 20 moves.
    stored = stored_season(20)
    check_transfers(stored, answer_without(stored, 0), 2026)
    check_transfers([], [], 2026)
    # Lost moves within max(2, 10%) are the provider dropping wrong entries ...
    check_transfers(stored, answer_without(stored, 2), 2026)
    many = stored_season(40)
    check_transfers(many, answer_without(many, 4), 2026)  # 10% of 40
    # ... beyond it the answer is cut and the stored season is kept.
    for rows, missing in ((stored, 3), (many, 5), (stored, 20)):
        with pytest.raises(IncompleteData):
            check_transfers(rows, answer_without(rows, missing), 2026)
    with pytest.raises(IncompleteData):
        check_transfers(stored_season(3), [], 2026)


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


def row_move(player, direction, club, half=1, season=2026, day=None, kind="Transfer", mid=None):
    return Transfer(
        id=mid, player_id=player, direction=direction, counterpart_id=club,
        counterpart_name=f"C{club}", type_raw=kind, season=season, half=half,
        transfer_date=day or (date(season, 8, 1) if half == 1 else date(season + 1, 2, 1)),
    )


def evidence(played=(), complete=True, prior=None):
    return MoveEvidence(frozenset(played), complete, prior or {})


def test_moves_with_appearances_here_are_shown_whatever_their_type_or_club():
    ev = evidence(played={1})
    # A departure not in the squad (e.g. Rodri) and a loan out are shown: he played here.
    assert judge_move(row_move(1, "out", 529, kind="Transfer"), ev) == (True, "played_here")
    assert judge_move(row_move(1, "out", 38, kind="Loan"), ev) == (True, "played_here")


def test_moves_are_folded_only_when_complete_records_show_no_appearance():
    youth_loan = row_move(2, "out", 38, kind="Loan")
    assert judge_move(youth_loan, evidence()) == (False, "not_played")
    # Records of an evidence season missing: not decided, so shown (never "not played").
    assert judge_move(youth_loan, evidence(complete=False)) == (True, "records_incomplete")


def test_a_signing_needs_the_club_he_came_from():
    arrival = row_move(3, "in", 211, half=1, season=2026)  # summer 2026: club season 2025
    assert judge_move(arrival, evidence()) == (True, "check_pending")
    played = evidence(prior={(3, 2025): {211: 30, 999: 0}})
    assert judge_move(arrival, played) == (True, "played_before")
    youth = evidence(prior={(3, 2025): {}})  # checked: no first-team line at all
    assert judge_move(arrival, youth) == (False, "not_played")
    no_club = row_move(3, "in", None)
    assert judge_move(no_club, played) == (True, "club_unknown")
    assert judge_move(no_club, evidence()) == (True, "club_unknown")
    # A January move comes from the club's current season.
    winter = row_move(3, "in", 211, half=2, season=2026)
    assert check_season(winter) == 2026
    assert judge_move(winter, played) == (True, "check_pending")


def test_a_loan_return_is_judged_by_this_team_only():
    # Back from a lower-league loan with 30 games there, never played here: folded.
    back = row_move(6, "in", 38, kind="Return from loan")
    loaned = evidence(prior={(6, 2025): {38: 30}})
    assert judge_move(back, loaned) == (False, "not_played")
    assert judge_move(row_move(6, "in", 38, kind="Back from Loan"), loaned)[0] is False
    # The same player with appearances here is shown; undecided records keep it shown.
    assert judge_move(back, evidence(played={6})) == (True, "played_here")
    assert judge_move(back, evidence(complete=False)) == (True, "records_incomplete")
    # A permanent signing from that club is a new signing: the club decides.
    assert judge_move(row_move(6, "in", 38, kind="Transfer"), loaned) == (True, "played_before")


def test_youth_competitions_and_friendlies_are_not_first_team():
    answer = [{"player": {"id": 9}, "statistics": [
        {"team": {"id": 7197}, "league": {"name": "Premier League 2 Division One", "season": 2025},
         "games": {"appearences": 12}},
        {"team": {"id": 15381}, "league": {"name": "U18 Premier League - South", "season": 2025},
         "games": {"appearences": 5}},
        {"team": {"id": 50}, "league": {"name": "UEFA Youth League", "season": 2025},
         "games": {"appearences": 4}},
        {"team": {"id": 50}, "league": {"name": "Friendlies Clubs", "season": 2025},
         "games": {"appearences": 3}},
        {"team": {"id": 50}, "league": {"name": "Premier League", "season": 2025},
         "games": {"appearences": 0}},
        {"team": {"id": 50}, "league": {"name": "FA Cup", "season": 2025},
         "games": {"appearences": 1}},
        {"team": {"id": 38}, "league": {"name": "Championship", "season": 2025},
         "games": {"appearences": 8}},
        {"team": {"id": 40}, "league": {"name": "Serie B", "season": 2025},
         "games": {"appearences": None}},
    ]}]
    assert parse_player_season(answer, 9, 2025) == {50: 1, 38: 8, 40: 0}
    assert parse_player_season([], 9, 2025) == {}  # no answer: no appearances anywhere
    with pytest.raises(IncompleteData):
        parse_player_season([{"player": {"id": 8}, "statistics": []}], 9, 2025)
    assert is_first_team("Primavera 1") is False and is_first_team("Serie A") is True


def line_of(team, league, apps):
    return {"team": {"id": team}, "league": {"name": league, "season": 2025},
            "games": {"appearences": apps}}


@pytest.mark.parametrize("values,expected", [
    ([0, None], 0), ([None, 0], 0), ([None], 0), ([0, 0], 0), ([None, 2], 2),
])
def test_empty_null_club_lines_count_as_zero(values, expected):
    answer = [{"player": {"id": 9}, "statistics": [line_of(38, "Championship", a) for a in values]}]
    assert parse_player_season(answer, 9, 2025) == {38: expected}


@pytest.mark.parametrize("field,value", [("goals", 0), ("assists", 2), ("rating", "7.287")])
def test_a_valued_null_club_line_proves_an_appearance(field, value):
    line = line_of(38, "Championship", None)
    if field == "rating":
        line["games"]["rating"] = value
    else:
        line["goals"] = {"total" if field == "goals" else "assists": value}
    assert parse_player_season([{"player": {"id": 9}, "statistics": [line]}], 9, 2025) == {38: 1}


def test_unidentifiable_nonempty_lines_are_refused():
    for broken in (line_of(None, "Championship", 10), line_of(38, None, 10)):
        with pytest.raises(IncompleteData):
            parse_player_season([{"player": {"id": 9}, "statistics": [broken]}], 9, 2025)
    valued = line_of(None, None, None)
    valued["goals"] = {"assists": 2}
    with pytest.raises(IncompleteData):
        parse_player_season([{"player": {"id": 9}, "statistics": [valued]}], 9, 2025)
    for apps in (None, 0):
        answer = [{"player": {"id": 9}, "statistics": [line_of(None, None, apps)]}]
        assert parse_player_season(answer, 9, 2025) == {}
    assert judge_move(row_move(7, "out", 38), evidence(played={7}, complete=False)) == (
        True, "records_incomplete",
    )


def test_one_row_per_player_and_half_keeps_every_move():
    # Akanji: back from loan at Inter, then sold to Inter — two moves, one row, both kept.
    back = row_move(4, "in", 505, day=date(2026, 6, 29), kind="Return from loan", mid=1)
    sold = row_move(4, "out", 505, day=date(2026, 6, 30), kind="Transfer", mid=2)
    youth_in = row_move(5, "in", 38, day=date(2026, 7, 1), mid=3)
    youth_out = row_move(5, "out", 39, day=date(2026, 8, 1), mid=4)
    winter = row_move(4, "in", 506, half=2, day=date(2027, 1, 10), mid=5)
    ev = evidence(played={4}, prior={(5, 2025): {38: 0}})
    groups = group_moves([sold, youth_out, back, winter, youth_in], ev)
    rows = [(g.player_id, g.direction, g.shown, [m.id for m in g.moves]) for g in groups]
    assert rows == [
        (4, "out", True, [1, 2]),  # oldest first; the row goes where he ended up
        (5, "out", False, [3, 4]),  # folded: every move confirmed without appearances
        (4, "in", True, [5]),  # another half is another row
    ]
    # One shown move shows the whole row.
    mixed = group_moves([youth_in, row_move(5, "out", 39, day=date(2026, 8, 1), mid=6)],
                        evidence(complete=True, prior={(5, 2025): {38: 2}}))
    assert [(g.shown, len(g.moves)) for g in mixed] == [(True, 2)]


def players_page(current, total, entries):
    return {"paging": {"current": current, "total": total}, "response": entries}


def entry(pid, *lines):
    return {"player": {"id": pid, "name": f"P{pid}", "nationality": "England"},
            "statistics": list(lines)}


def line(team, league, apps, goals=0, rating="7.1"):
    return {"team": {"id": team}, "league": {"id": league, "season": 2026},
            "games": {"appearences": apps, "rating": rating},
            "goals": {"total": goals, "assists": None}}


# The season's competition master (`record_competitions`): leagues, domestic cups, super
# cups, UEFA and the Club World Cup when held — friendlies (667) are not in it.
SCOPE = frozenset({39, 45, 48, 528, 2, 848, 531, 15})


def test_team_player_lines_keep_this_team_in_the_season_competition_master():
    page = players_page(1, 1, [
        entry(1, line(TEAM, 39, 10, 9), line(TEAM, 2, 3, 5, None), line(TEAM, 45, 2, 1),
              line(TEAM, 528, 1), line(TEAM, 15, 3), line(TEAM, 667, 4), line(600, 39, 5)),
        entry(2, line(TEAM, 848, 1, 0, "0")),
    ])
    parsed = parse_team_players([page], TEAM, 2026, SCOPE)
    kept = sorted((x["player_id"], x["competition_id"], x["appearances"], x["goals"],
                   x["assists"], x["rating"]) for x in parsed.lines)
    assert kept == [  # domestic cup, super cup and Club World Cup kept; friendly, other club out
        (1, 2, 3, 5, None, None), (1, 15, 3, 0, None, Decimal("7.1")),
        (1, 39, 10, 9, None, Decimal("7.1")), (1, 45, 2, 1, None, Decimal("7.1")),
        (1, 528, 1, 0, None, Decimal("7.1")), (2, 848, 1, 0, None, None),
    ]
    assert len(parsed.players) == 2
    # A season the Club World Cup was not held: its master leaves it out.
    without = parse_team_players([page], TEAM, 2026, SCOPE - {15})
    assert 15 not in {x["competition_id"] for x in without.lines}


def test_a_missing_or_short_page_is_refused():
    full = [entry(i, line(TEAM, 39, 1)) for i in range(1, 21)]
    with pytest.raises(IncompleteData):
        parse_team_players([players_page(1, 2, full)], TEAM, 2026, SCOPE)
    with pytest.raises(IncompleteData):
        parse_team_players(
            [players_page(1, 2, full[:19]), players_page(2, 2, [entry(30)])], TEAM, 2026, SCOPE
        )


def test_a_player_listed_twice_refuses_the_whole_set():
    # Codex 1차 지적 1: page 2 repeats page 1's last player in place of another one (shifted
    # pages) — the first collection, a later one and a conflicting repeat are all refused.
    full = [entry(i, line(TEAM, 39, 1)) for i in range(1, 21)]
    shifted = [players_page(1, 2, full), players_page(2, 2, [entry(20, line(TEAM, 39, 1))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(shifted, TEAM, 2026, SCOPE)
    conflicting = [players_page(1, 2, full), players_page(2, 2, [entry(20, line(TEAM, 39, 5))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(conflicting, TEAM, 2026, SCOPE)
    same_page = [players_page(1, 1, [entry(1, line(TEAM, 39, 1)), entry(1, line(TEAM, 2, 1))])]
    with pytest.raises(IncompleteData, match="listed twice"):
        parse_team_players(same_page, TEAM, 2026, SCOPE)


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
