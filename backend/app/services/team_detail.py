"""Team detail (chat 08, TEAM-001~006, FAV-002·003 guest part).

Collection (pure parsing + replace-on-success, like chat 06):
- coach: /coachs?team= — the current coach is the career entry of this team without an end
  date (latest start wins); none = "no current coach given", stored as such.
- squad: /players/squads?team= — the current squad as given (number, position, photo).
- statistics: /teams/statistics?team=&league=&season= — the team's league season block.
  The past season is collected once (never re-collected: it is over) and only when the team
  played that league that season (a promoted team has no record to ask for).
- profiles: /players/profiles?player= — once per squad player whose nationality is missing
  (TEAM-002 "한 번 보완"); a still missing value stays NULL (never the birth country).
- team player records (2026-11-18): /players?team=&season= — every page, one listing per
  player, this team's lines in the competitions held that season (`record_competitions`,
  2026-11-20: leagues, domestic cups, super cups, UEFA, Club World Cup), in
  `team_player_stats` (08's own table; chat 06's league-wide `player_season_stats` has its
  own writer). The current season daily; the last two seasons until stored once.
- signing checks (2026-11-20): /players?id=&season= once per signing still without evidence
  (`pending_checks`) — the first-team clubs of the season he came from.
- transfers: /transfers?team= — entries involving the team, stored as given and classified by
  date: season S is S-06-01 .. (S+1)-05-31, first half June-December, second half
  January-May. Repeated entries are merged when answering (`merge_transfers`). Future-dated
  entries are left out until their date. A season is refreshed through the (S+1)-07-01 00:00
  run (records added up to June 30) and fixed afterwards; one never stored is still stored
  once (first collection). Every unit runs at most once per KST day.
An empty or cut answer never replaces stored rows: the failure is recorded in team_syncs.

Reading: the allow set decides access (current five-league members, D-15). An unknown team
is NOT_FOUND, a known team outside the set TEAM_DETAIL_UNAVAILABLE, and a membership that
cannot be confirmed MEMBERSHIP_UNKNOWN (never "relegated").
"""

import html
import json
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.core.kst import kst_date
from app.models.fixture import Fixture
from app.models.match_detail import TeamForm
from app.models.reference import Competition, CompetitionSeason, Team, TeamCompetitionSeason
from app.models.standings import LeagueSync, Player, Standing
from app.models.team_detail import (
    PlayerClubSeason,
    PlayerSeasonCheck,
    SquadMember,
    TeamCoach,
    TeamPlayerStat,
    TeamSeasonStat,
    TeamSync,
    Transfer,
)
from app.schemas.match import MatchSummary
from app.seed.competitions import LEAGUE_IDS
from app.services.fixtures import LIVE_LAG, to_summary
from app.services.reference import managed_seasons, team_detail_lookup
from app.services.standings import IncompleteData

UPCOMING = 3
RECENT = 5
NOT_GIVEN_TYPES = frozenset({"", "n/a", "na", "-", "?"})
# Completeness of stored answers (Codex 1차 지적 1, see check_squad / check_transfers).
MIN_SQUAD = 18
SQUAD_SHRINK_TOLERANCE = 0.25
TRANSFER_SHRINK_ALLOWANCE = 2
TRANSFER_SHRINK_TOLERANCE = 0.1


# ---------------------------------------------------------------------------- helpers


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


COUNTRIES_PATH = Path(__file__).resolve().parents[1] / "seed" / "countries.json"


def _country_key(name: str) -> str:
    return re.sub(r"[\s\-_]+", " ", name).strip().casefold()


@cache
def _flags() -> dict[str, str]:
    """Country name -> flag image from API-Football /countries (one request, 2026-11-18,
    stored as a seed). Names are compared without case, spaces or hyphens."""
    data = json.loads(COUNTRIES_PATH.read_text(encoding="utf-8"))
    return {_country_key(name): url for name, url in data.items()}


def flag_url(nationality: str | None) -> str | None:
    """The flag of a player's nationality; None when unknown (the name is shown alone)."""
    return _flags().get(_country_key(nationality)) if nationality else None


def display_text(value: str | None) -> str | None:
    """Provider names sometimes carry HTML entities ("O&apos;Reilly"): shown decoded. The
    stored value is left as given."""
    return html.unescape(value) if value else value


def season_of(day: date) -> tuple[int, int]:
    """(season, half): June-December belongs to that year's season (first half),
    January-May to the previous year's season (second half). Every date has one half."""
    return (day.year, 1) if day.month >= 6 else (day.year - 1, 2)


def half_range(season: int, half: int) -> tuple[date, date]:
    if half == 1:
        return date(season, 6, 1), date(season, 12, 31)
    return date(season + 1, 1, 1), date(season + 1, 5, 31)


def last_refresh_day(season: int) -> date:
    """The last KST day a season's transfers are rewritten. TEAM-006 refreshes them until
    June 30 after the season, and a record that appears on June 30 reaches the next 00:00
    run (기능 명세서 6.2): that is the July 1 00:00 run. From July 2 the season is fixed."""
    return date(season + 1, 7, 1)


# ---------------------------------------------------------------------------- parsing


@dataclass(frozen=True)
class ParsedCoach:
    coach_id: int | None
    name: str | None
    photo_url: str | None
    since: date | None


NO_COACH = ParsedCoach(None, None, None, None)


def pick_coach(response: Any, team_id: int, today: date) -> ParsedCoach:
    """The current coach (TEAM-001 rule 2): a coach listed for this team whose career has an
    entry for this team without an end date that has already started (a spell starting after
    `today`, KST, is not current yet); the latest start wins. None found = no coach."""
    if not isinstance(response, list):
        raise IncompleteData("coachs: no response list")
    best: tuple[date, ParsedCoach] | None = None
    for coach in response:
        if not isinstance(coach, Mapping) or not coach.get("id") or not coach.get("name"):
            continue
        if ((coach.get("team") or {}).get("id")) != team_id:
            continue  # a former coach now at another club
        for spell in coach.get("career") or []:
            if ((spell or {}).get("team") or {}).get("id") != team_id or spell.get("end"):
                continue
            start = _date(spell.get("start"))
            if start is not None and start > today:
                continue  # announced, not in charge yet
            key = start or date.min
            if best is None or key > best[0]:
                photo = coach.get("photo") or None
                best = (key, ParsedCoach(coach["id"], coach["name"], photo, start))
    return best[1] if best else NO_COACH


@dataclass
class ParsedSquad:
    members: list[dict[str, Any]]
    players: list[dict[str, Any]]


def parse_squad(response: Any, team_id: int) -> ParsedSquad:
    """The current squad as given. An empty answer is an empty squad (the caller refuses to
    replace a stored squad with it)."""
    if not isinstance(response, list):
        raise IncompleteData("squads: no response list")
    if not response:
        return ParsedSquad([], [])
    entry = next(
        (e for e in response if ((e or {}).get("team") or {}).get("id") == team_id), None
    )
    if entry is None:
        raise IncompleteData(f"squads: answer without team {team_id}")
    members: dict[int, dict[str, Any]] = {}
    players: dict[int, dict[str, Any]] = {}
    for player in entry.get("players") or []:
        if not (player or {}).get("id") or not player.get("name"):
            raise IncompleteData("squads: player without id or name")
        if player["id"] in members:
            continue
        members[player["id"]] = {
            "player_id": player["id"],
            "number": _int(player.get("number")),
            "position": player.get("position") or None,
        }
        players[player["id"]] = {
            "id": player["id"],
            "name": player["name"],
            "photo_url": player.get("photo") or None,
        }
    return ParsedSquad(list(members.values()), list(players.values()))


def parse_statistics(
    response: Any, team_id: int, league: int, season: int
) -> dict[str, Any] | None:
    """The team's league season block; None for an empty answer (no record)."""
    if response in ([], {}, None):
        return None
    if not isinstance(response, Mapping):
        raise IncompleteData("statistics: unexpected answer")
    meta = response.get("league") or {}
    team = response.get("team") or {}
    if meta.get("id") != league or meta.get("season") != season or team.get("id") != team_id:
        raise IncompleteData(
            f"statistics: answer for {team.get('id')}/{meta.get('id')}/{meta.get('season')}"
        )
    check_statistics(response)
    return dict(response)


def _total(block: Any, *path: str) -> Any:
    for key in path:
        block = block.get(key) if isinstance(block, Mapping) else None
    return block


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_statistics(payload: Mapping[str, Any]) -> None:
    """A usable season record (Codex 1차 지적 1): the match counts and goal totals the screen
    shows are all numbers and add up (played = wins + draws + losses, home + away = total).
    Every stored 2025·2026 record passes; a cut answer (an empty fixtures block) does not."""
    fixtures = payload.get("fixtures")
    keys = ("played", "wins", "draws", "loses")
    for key in keys:
        for side in ("home", "away", "total"):
            if not _count(_total(fixtures, key, side)):
                raise IncompleteData(f"statistics: fixtures.{key}.{side} missing")
    for side in ("home", "away", "total"):
        played, results = (
            _total(fixtures, "played", side),
            sum(_total(fixtures, key, side) for key in keys[1:]),
        )
        if played != results:
            raise IncompleteData(f"statistics: {side} played {played} != results {results}")
    blocks = {f"fixtures.{key}": _total(fixtures, key) for key in keys}
    for key in ("for", "against"):
        block = _total(payload, "goals", key, "total")
        if not all(_count(_total(block, side)) for side in ("home", "away", "total")):
            raise IncompleteData(f"statistics: goals.{key} missing")
        blocks[f"goals.{key}"] = block
    # Every shown count adds up: home + away = total (Codex 2차 지적 N1 — a total that
    # disagrees with its own halves is not a usable record).
    for label, block in blocks.items():
        home, away, total = (_total(block, side) for side in ("home", "away", "total"))
        if home + away != total:
            raise IncompleteData(f"statistics: {label} {home} + {away} != {total}")


def parse_transfers(response: Any, team_id: int, today: date) -> list[dict[str, Any]]:
    """Entries that involve the team, one row per (player, date, direction, other club).
    Moves between two other clubs in a player's history are left out; so are entries with
    no readable date (they cannot be placed in a half) and future dates (not happened)."""
    if not isinstance(response, list):
        raise IncompleteData("transfers: no response list")
    rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    for entry in response:
        player = (entry or {}).get("player") or {}
        if not player.get("id") or not player.get("name"):
            continue
        for move in entry.get("transfers") or []:
            teams = (move or {}).get("teams") or {}
            came_to, left_from = teams.get("in") or {}, teams.get("out") or {}
            if came_to.get("id") == team_id and left_from.get("id") != team_id:
                direction, other = "in", left_from
            elif left_from.get("id") == team_id and came_to.get("id") != team_id:
                direction, other = "out", came_to
            else:
                continue
            day = _date(move.get("date"))
            if day is None or day > today:
                continue
            season, half = season_of(day)
            kind = (move.get("type") or "").strip()
            # The other club is its id; without one, its name (Codex 3차 N4: two unnamed-id
            # clubs on the same day are two moves). The DB indexes enforce the same rule.
            club = other.get("id") if other.get("id") is not None else other.get("name") or None
            key = (player["id"], day, direction, club)
            rows[key] = {
                "player_id": player["id"],
                "player_name": player["name"],
                "transfer_date": day,
                "direction": direction,
                "counterpart_id": other.get("id"),
                "counterpart_name": other.get("name") or None,
                "counterpart_logo": other.get("logo") or None,
                "type_raw": None if kind.lower() in NOT_GIVEN_TYPES else kind,
                "season": season,
                "half": half,
            }
    # Stored as given (2026-11-18): the provider's repeated entries are merged when the
    # response is built (`merge_transfers`), never at collection.
    return list(rows.values())


def merge_transfers(rows: Sequence[Transfer]) -> list[Transfer]:
    """One entry per move (D-08-6, 2026-11-18), applied to stored rows when answering.

    (가) Same player, date and direction: when one entry names the other club by id, the
        entries without an id (the provider's name-only copy: "PSV" / "PSV Eindhoven",
        "Hull" / "Hull City", "Stones John") are dropped.
    (나) Same player, direction, club id and season: entries re-registered on later dates
        (1-46 days apart, the old one-day rule included) are one move shown on the earliest
        date — unless a move the other way (any club) falls between them, which makes them
        separate moves. Entries without a club id are never merged by (나).
    The result is in date order."""
    with_id = {(r.player_id, r.transfer_date, r.direction) for r in rows if r.counterpart_id}
    kept = [
        r for r in rows
        if r.counterpart_id or (r.player_id, r.transfer_date, r.direction) not in with_id
    ]
    other_way: dict[tuple[int, str], list[date]] = {}
    for r in kept:
        other_way.setdefault((r.player_id, r.direction), []).append(r.transfer_date)
    opposite = {"in": "out", "out": "in"}
    merged: list[Transfer] = []
    first_of: dict[tuple[Any, ...], date] = {}
    for r in sorted(kept, key=lambda r: (r.transfer_date, r.id or 0)):
        if r.counterpart_id is None:
            merged.append(r)
            continue
        key = (r.player_id, r.direction, r.counterpart_id, r.season)
        previous = first_of.get(key)
        between = previous is not None and any(
            previous <= day <= r.transfer_date
            for day in other_way.get((r.player_id, opposite[r.direction]), [])
        )
        if previous is not None and not between:
            continue  # the same move registered again later
        first_of[key] = r.transfer_date
        merged.append(r)
    return merged


def parse_profile_nationality(response: Any, player_id: int) -> str | None:
    """The requested player's nationality (None = the profile has none). An empty answer is
    the provider's normal "no profile" (checked, never asked again); an answer for another
    player is not an answer for this one and is refused, so the player is asked again
    (Codex 1차 지적 6)."""
    if not isinstance(response, list):
        raise IncompleteData("profiles: no response list")
    if not response:
        return None
    for entry in response:
        player = (entry or {}).get("player") or {}
        if player.get("id") == player_id:
            return player.get("nationality") or None
    raise IncompleteData(f"profiles: answer without player {player_id}")


# ---------------------------------------------------------------------------- saving


def _sync_row(session: Session, team_id: int, season: int, kind: str) -> TeamSync:
    row = session.get(TeamSync, (team_id, season, kind))
    if row is None:
        row = TeamSync(team_id=team_id, season=season, kind=kind)
        session.add(row)
    return row


def mark_success(
    session: Session, team_id: int, season: int, kind: str, now: datetime, rows: int
) -> None:
    row = _sync_row(session, team_id, season, kind)
    row.synced_at, row.row_count = now, rows


def mark_failure(
    session: Session, team_id: int, season: int, kind: str, now: datetime, reason: str
) -> None:
    row = _sync_row(session, team_id, season, kind)
    row.failed_at, row.failure = now, reason[:300]


def save_coach(session: Session, team_id: int, coach: ParsedCoach, now: datetime) -> None:
    stmt = insert(TeamCoach).values(
        team_id=team_id, coach_id=coach.coach_id, name=coach.name, photo_url=coach.photo_url,
        since=coach.since, synced_at=now,
    )
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[TeamCoach.team_id],
            set_={c: getattr(stmt.excluded, c) for c in
                  ("coach_id", "name", "photo_url", "since", "synced_at")},
        )
    )
    found = int(coach.name is not None)
    mark_success(session, team_id, settings.current_season, "coach", now, found)


def _add_players(session: Session, players: Sequence[dict[str, Any]], now: datetime) -> None:
    """Squad players new to the DB get their provider identity; a stored player keeps its
    name and nationality from the league player lists, only a missing photo is filled."""
    for start in range(0, len(players), 500):
        chunk = [{**p, "updated_at": now} for p in sorted(players, key=lambda p: p["id"])][
            start : start + 500
        ]
        stmt = insert(Player).values(chunk)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Player.id],
                set_={"photo_url": func.coalesce(Player.photo_url, stmt.excluded.photo_url)},
            )
        )


def check_squad(new: int, stored: int) -> None:
    """A complete current squad (Codex 1차 지적 1): a five-league squad lists at least
    MIN_SQUAD players (the smallest stored on 2026-11-07 had 24, the mean 31), and it never
    shrinks by more than SQUAD_SHRINK_TOLERANCE at once (a summer window moves a few players,
    a cut answer drops most of them). A refused answer keeps the stored squad."""
    if new < MIN_SQUAD:
        raise IncompleteData(f"squads: {new} players (at least {MIN_SQUAD} expected)")
    if stored and new < stored * (1 - SQUAD_SHRINK_TOLERANCE):
        raise IncompleteData(f"squads: {new} players would replace {stored}")


def save_squad(session: Session, team_id: int, parsed: ParsedSquad, now: datetime) -> None:
    stored = session.scalar(
        select(func.count()).select_from(SquadMember).where(SquadMember.team_id == team_id)
    ) or 0
    check_squad(len(parsed.members), stored)
    _add_players(session, parsed.players, now)
    session.execute(delete(SquadMember).where(SquadMember.team_id == team_id))
    if parsed.members:
        session.execute(
            insert(SquadMember).values(
                [{**m, "team_id": team_id, "synced_at": now} for m in parsed.members]
            )
        )
    mark_success(session, team_id, settings.current_season, "squad", now, len(parsed.members))


def save_statistics(
    session: Session, team_id: int, league: int, season: int,
    payload: dict[str, Any] | None, now: datetime,
) -> None:
    stored = session.get(TeamSeasonStat, (team_id, league, season))
    if payload is None:
        if stored is not None:
            raise IncompleteData("statistics: empty answer would replace a stored record")
        mark_success(session, team_id, season, "statistics", now, 0)
        return
    if stored is not None:
        # A season record only grows: fewer matches than stored is an old or cut answer.
        before = _total(stored.payload.get("fixtures"), "played", "total")
        after = _total(payload.get("fixtures"), "played", "total")
        if _count(before) and after < before:
            raise IncompleteData(f"statistics: {after} matches would replace {before}")
    stmt = insert(TeamSeasonStat).values(
        team_id=team_id, competition_id=league, season=season, payload=payload, synced_at=now
    )
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[
                TeamSeasonStat.team_id, TeamSeasonStat.competition_id, TeamSeasonStat.season
            ],
            set_={"payload": stmt.excluded.payload, "synced_at": now},
        )
    )
    mark_success(session, team_id, season, "statistics", now, 1)


def same_move(a: Transfer, b: Transfer, other_way: Collection[date] = ()) -> bool:
    """The same move in two answers, by the D-08-6 identity: same player and direction, and
    either the same club id in the same season with no move the other way strictly between
    their dates (`other_way` — the provider re-dates its copies, but loan out · back · out
    again to one club are separate moves), or, when a club id is missing on one side, the
    same date (a name-only copy, or two unnamed-id clubs with the same name)."""
    if (a.player_id, a.direction) != (b.player_id, b.direction):
        return False
    if a.counterpart_id is not None and b.counterpart_id is not None:
        low, high = sorted((a.transfer_date, b.transfer_date))
        return (
            a.counterpart_id == b.counterpart_id
            and a.season == b.season
            and not any(low < day < high for day in other_way)
        )
    return a.transfer_date == b.transfer_date and (
        a.counterpart_id is not None
        or b.counterpart_id is not None
        or a.counterpart_name == b.counterpart_name
    )


def check_transfers(stored: Sequence[Transfer], new: Sequence[Transfer], season: int) -> None:
    """A season's moves only accumulate (Codex 1차 지적 1). Compared move by move after the
    D-08-6 merge (2026-11-24): a stored move counts as lost only when the new answer has no
    entry of the same move (`same_move`, with the player's moves the other way in either
    answer). Fewer rows because the provider stopped repeating a move (it now keeps one
    copy, often dated a day later) lose nothing. Up to max(TRANSFER_SHRINK_ALLOWANCE, 10% of
    the stored moves) lost moves are taken as the provider dropping wrong entries; more is a
    cut answer and keeps the stored season."""
    days: dict[tuple[int, str], set[date]] = {}
    for r in (*stored, *new):
        days.setdefault((r.player_id, r.direction), set()).add(r.transfer_date)
    opposite = {"in": "out", "out": "in"}
    moves = merge_transfers(stored)
    lost = [
        m for m in moves
        if not any(
            same_move(m, n, days.get((m.player_id, opposite[m.direction]), ())) for n in new
        )
    ]
    allowed = max(TRANSFER_SHRINK_ALLOWANCE, int(len(moves) * TRANSFER_SHRINK_TOLERANCE))
    if len(lost) > allowed:
        raise IncompleteData(
            f"transfers: {len(lost)} of {len(moves)} moves of {season} missing from the answer"
        )


def save_transfers(
    session: Session, team_id: int, season: int, rows: Sequence[dict[str, Any]], now: datetime
) -> None:
    """Replace one season of the team's transfers (only rows of that season are given)."""
    check_transfers(
        read_transfers(session, team_id, season), [Transfer(**r) for r in rows], season
    )
    session.execute(delete(Transfer).where(Transfer.team_id == team_id, Transfer.season == season))
    if rows:
        session.execute(
            insert(Transfer).values([{**r, "team_id": team_id, "synced_at": now} for r in rows])
        )
    mark_success(session, team_id, season, "transfers", now, len(rows))


def save_nationality(
    session: Session, player_id: int, nationality: str | None, now: datetime
) -> None:
    """After one profile lookup: fill a missing nationality, and never ask again."""
    player = session.get(Player, player_id)
    if player is None:
        return
    if player.nationality is None and nationality:
        player.nationality = nationality
    player.profile_checked_at = now


# ------------------------------------------------- team player records (2026-11-18)

TEAM_PAGE_SIZE = 20
TEAM_LINES_SHRINK_TOLERANCE = 0.1


@dataclass
class ParsedTeamPlayers:
    lines: list[dict[str, Any]]
    players: list[dict[str, Any]]


def record_competitions(session: Session, season: int) -> frozenset[int]:
    """The competitions a team's season total counts (TEAM-002 rules 1·7, 2026-11-20): every
    active competition of the shared master (leagues, domestic cups, super cups, UEFA, Club
    World Cup) except those the provider says were not held that season (`no_data`, e.g. the
    Club World Cup of 2026). No list of excluded competitions is kept: friendlies and other
    competitions are not in the master. A season without a master row (2024, kept as move
    evidence only) counts every active competition."""
    not_held = select(CompetitionSeason.competition_id).where(
        CompetitionSeason.season == season, CompetitionSeason.availability == "no_data"
    )
    return frozenset(
        session.scalars(
            select(Competition.id).where(Competition.active, Competition.id.not_in(not_held))
        )
    )


def parse_team_players(
    pages: Sequence[Mapping[str, Any]],
    team_id: int,
    season: int,
    competitions: Collection[int],
) -> ParsedTeamPlayers:
    """Every page of /players?team=&season= (each page's `response` and `paging`).

    The set must be complete: pages 1..total with one total, TEAM_PAGE_SIZE entries on every
    page but the last (1..TEAM_PAGE_SIZE there). The provider lists each player once, so a
    player listed again (pages shifted: someone else is missing) refuses the set. Only this
    team's lines in `competitions` (`record_competitions` of the season) are kept; other
    clubs' lines and competitions outside the master (friendlies, youth competitions) are
    dropped. Missing values stay None."""
    if not pages:
        raise IncompleteData("team players: no page")
    total = _int((pages[0].get("paging") or {}).get("total"))
    if total == 0 and len(pages) == 1 and not pages[0].get("response"):
        return ParsedTeamPlayers([], [])
    currents = [_int((p.get("paging") or {}).get("current")) for p in pages]
    if (
        total is None
        or total < 1
        or len(pages) != total
        or sorted(c or 0 for c in currents) != list(range(1, total + 1))
        or any(_int((p.get("paging") or {}).get("total")) != total for p in pages)
    ):
        raise IncompleteData(f"team players: pages {len(pages)} of {total}")
    for page, current in zip(pages, currents, strict=True):
        size = len(page.get("response") or [])
        low = 1 if current == total else TEAM_PAGE_SIZE
        if not low <= size <= TEAM_PAGE_SIZE:
            raise IncompleteData(f"team players: page {current} of {total} has {size} entries")

    lines: dict[tuple[int, int], dict[str, Any]] = {}
    players: dict[int, dict[str, Any]] = {}
    for page in pages:
        for entry in page.get("response") or []:
            player = (entry or {}).get("player") or {}
            if not player.get("id") or not player.get("name"):
                raise IncompleteData("team players: entry without player")
            if player["id"] in players:
                # The provider lists a player once; a repeat means the pages shifted and
                # another player was left out (Codex 1차 지적 1): the whole answer is refused.
                raise IncompleteData(f"team players: player {player['id']} listed twice")
            players[player["id"]] = {
                "id": player["id"],
                "name": player["name"],
                "photo_url": player.get("photo") or None,
                "nationality": player.get("nationality") or None,
            }
            for stats in entry.get("statistics") or []:
                league = stats.get("league") or {}
                if (stats.get("team") or {}).get("id") != team_id:
                    continue
                if league.get("id") not in competitions:
                    continue
                if league.get("season") not in (season, None):
                    raise IncompleteData(f"team players: season {league.get('season')}")
                games = stats.get("games") or {}
                goals = stats.get("goals") or {}
                line = {
                    "player_id": player["id"],
                    "competition_id": league["id"],
                    "appearances": _int(games.get("appearences")),
                    "goals": _int(goals.get("total")),
                    "assists": _int(goals.get("assists")),
                    "rating": _rating(games.get("rating")),
                }
                key = (player["id"], league["id"])
                if key in lines and lines[key] != line:
                    raise IncompleteData(
                        f"team players: player {player['id']} has two lines in {league['id']}"
                    )
                lines[key] = line
    return ParsedTeamPlayers(list(lines.values()), list(players.values()))


def _rating(value: Any) -> Decimal | None:
    """The provider's per-competition rating; "0" is its placeholder for "not rated"."""
    try:
        rating = Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None
    return rating if rating else None


def save_team_player_stats(
    session: Session, team_id: int, season: int, parsed: ParsedTeamPlayers, now: datetime
) -> None:
    """Replace the team's lines of one season. A season's lines only grow: an empty answer or
    a drop of more than TEAM_LINES_SHRINK_TOLERANCE keeps the stored lines (a cut answer)."""
    stored = session.scalar(
        select(func.count()).select_from(TeamPlayerStat).where(
            TeamPlayerStat.team_id == team_id, TeamPlayerStat.season == season
        )
    ) or 0
    if stored and len(parsed.lines) < stored * (1 - TEAM_LINES_SHRINK_TOLERANCE):
        raise IncompleteData(f"team players: {len(parsed.lines)} lines would replace {stored}")
    listed = {line["player_id"] for line in parsed.lines}
    _add_record_players(session, [p for p in parsed.players if p["id"] in listed], now)
    session.execute(
        delete(TeamPlayerStat).where(
            TeamPlayerStat.team_id == team_id, TeamPlayerStat.season == season
        )
    )
    if parsed.lines:
        session.execute(
            insert(TeamPlayerStat).values(
                [{**line, "team_id": team_id, "season": season, "synced_at": now}
                 for line in parsed.lines]
            )
        )
    mark_success(session, team_id, season, "player_stats", now, len(parsed.lines))


def _add_record_players(
    session: Session, players: Sequence[dict[str, Any]], now: datetime
) -> None:
    """Players of the record lines: new ones get their provider identity; stored ones keep
    their values and only gain a missing photo or nationality (never set back to NULL)."""
    ordered = sorted(players, key=lambda p: p["id"])
    for start in range(0, len(ordered), 500):
        chunk = [{**p, "updated_at": now} for p in ordered[start : start + 500]]
        stmt = insert(Player).values(chunk)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Player.id],
                set_={
                    "photo_url": func.coalesce(Player.photo_url, stmt.excluded.photo_url),
                    "nationality": func.coalesce(Player.nationality, stmt.excluded.nationality),
                },
            )
        )


# ---------------------------------------------------------------------------- schedule


def current_members(session: Session) -> dict[int, int]:
    """team_id -> league_id of the current five-league members (league order on ties).
    Leagues whose team list was never collected are left out (reported by the caller)."""
    season = settings.current_season
    synced = {
        cid for cid, at in session.execute(
            select(CompetitionSeason.competition_id, CompetitionSeason.teams_synced_at).where(
                CompetitionSeason.season == season,
                CompetitionSeason.competition_id.in_(LEAGUE_IDS),
            )
        )
        if at is not None
    }
    members: dict[int, int] = {}
    for team_id, league in session.execute(
        select(TeamCompetitionSeason.team_id, TeamCompetitionSeason.competition_id).where(
            TeamCompetitionSeason.season == season,
            TeamCompetitionSeason.competition_id.in_(synced),
        )
    ):
        if team_id not in members or LEAGUE_IDS.index(league) < LEAGUE_IDS.index(members[team_id]):
            members[team_id] = league
    return members


def unsynced_leagues(session: Session) -> list[int]:
    season = settings.current_season
    done = set(
        session.scalars(
            select(CompetitionSeason.competition_id).where(
                CompetitionSeason.season == season,
                CompetitionSeason.competition_id.in_(LEAGUE_IDS),
                CompetitionSeason.teams_synced_at.is_not(None),
            )
        )
    )
    return [league for league in LEAGUE_IDS if league not in done]


def _last_try(row: TeamSync | None) -> datetime | None:
    if row is None:
        return None
    return max((t for t in (row.synced_at, row.failed_at) if t), default=None)


def is_due(session: Session, team_id: int, season: int, kind: str, now: datetime) -> bool:
    """Once per KST day: never tried, or the last try (success or failure) was on an earlier
    KST date. A manual run at noon therefore never makes the next 00:00 run skip a day."""
    last = _last_try(session.get(TeamSync, (team_id, season, kind)))
    return last is None or kst_date(last) < kst_date(now)


def never_stored(session: Session, team_id: int, season: int, kind: str) -> bool:
    row = session.get(TeamSync, (team_id, season, kind))
    return row is None or row.synced_at is None


def played_league(session: Session, team_id: int, league: int, season: int) -> bool:
    return bool(
        session.get(TeamCompetitionSeason, (team_id, league, season))
    )


def final_refresh_done(session: Session, team_id: int, season: int) -> bool:
    """The season was stored on or after its last refresh day (the July 1 00:00 run or later):
    its fixed data includes everything reflected by June 30."""
    row = session.get(TeamSync, (team_id, season, "transfers"))
    return bool(row and row.synced_at and kst_date(row.synced_at) >= last_refresh_day(season))


def transfer_seasons(session: Session, team_id: int, today: date) -> list[int]:
    """Seasons whose transfers the next answer may write: still in their refresh window, or
    not yet stored by a run on/after the last refresh day — never stored (first collection of
    the past season) or the final July 1 refresh failed (Codex 1차 지적 3: retried daily until
    it succeeds, the stored rows shown meanwhile with the refresh-failed notice)."""
    return [
        season for season in managed_seasons()
        if today <= last_refresh_day(season) or not final_refresh_done(session, team_id, season)
    ]


def missing_nationalities(session: Session, team_ids: Iterable[int]) -> list[int]:
    """Squad players of these teams whose nationality is missing and never looked up."""
    return list(
        session.scalars(
            select(Player.id)
            .join(SquadMember, SquadMember.player_id == Player.id)
            .where(
                SquadMember.team_id.in_(list(team_ids)),
                Player.nationality.is_(None),
                Player.profile_checked_at.is_(None),
            )
            .distinct()
            .order_by(Player.id)
        )
    )


# ---------------------------------------------------------------------------- reading


class TeamNotFound(Exception):
    pass


class DetailUnavailable(Exception):
    pass


class MembershipUnknown(Exception):
    pass


@dataclass(frozen=True)
class TeamAccess:
    team: Team
    league: Competition


def detail_access(session: Session, team_id: int) -> TeamAccess:
    """The same decision as team links (D-15) and team browse (07)."""
    team = session.get(Team, team_id)
    if team is None:
        raise TeamNotFound
    allowed = team_detail_lookup(session)(team_id)
    if allowed is False:
        raise DetailUnavailable
    league = current_members(session).get(team_id) if allowed else None
    if league is None:
        # Not confirmed by a collected league team list (the link decides the same: null).
        raise MembershipUnknown
    return TeamAccess(team, session.get(Competition, league))


def sync_meta(
    session: Session, team_id: int, season: int, kind: str
) -> tuple[datetime | None, bool]:
    row = session.get(TeamSync, (team_id, season, kind))
    synced = row.synced_at if row else None
    failed = row.failed_at if row else None
    return synced, bool(synced and failed and failed > synced)


def read_standing(session: Session, team_id: int, league: int, season: int) -> Standing | None:
    return session.scalar(
        select(Standing)
        .where(
            Standing.team_id == team_id,
            Standing.competition_id == league,
            Standing.season == season,
        )
        .order_by(Standing.group_order)
        .limit(1)
    )


def standings_collected(session: Session, league: int, season: int) -> bool:
    row = session.get(LeagueSync, (league, season, "standings"))
    return row is not None and row.synced_at is not None


@dataclass(frozen=True)
class RecentResult:
    fixture: Fixture
    competition: Competition
    home: Team
    away: Team
    result: str  # W / D / L for this team


def match_result(fixture: Fixture, team_id: int) -> str:
    """W / D / L for the team: goals (extra time included); a shoot-out decides a level match."""
    mine, theirs = (
        (fixture.goals_home, fixture.goals_away)
        if fixture.home_team_id == team_id
        else (fixture.goals_away, fixture.goals_home)
    )
    if mine == theirs and fixture.finish_type == "pen":
        penalty = (fixture.score or {}).get("penalty") or {}
        home, away = penalty.get("home"), penalty.get("away")
        if isinstance(home, int) and isinstance(away, int) and home != away:
            won = home > away if fixture.home_team_id == team_id else away > home
            return "W" if won else "L"
    return "W" if mine > theirs else "L" if mine < theirs else "D"


def official_form(session: Session, team_id: int) -> list[dict[str, Any]] | None:
    """The team's last RECENT official results (TEAM-001 rule 3, 06 개선 2026-11-20), oldest
    first: the 04 head-to-head source — `/fixtures?team=&last=10` without friendlies, cached
    per team in `team_forms` (`head_to_head.ensure_form`), so unsupported official matches
    (super cups, Club World Cup, other cups) count too. None while the team was never read
    (the caller then falls back to the stored match list); a failed refresh keeps the last
    stored list. Normalised rows without a score are skipped."""
    row = session.get(TeamForm, team_id)
    if row is None or row.fetched_at is None:
        return None
    scored = [
        r
        for r in row.payload or []
        if r.get("goalsHome") is not None and r.get("goalsAway") is not None
    ]
    return list(reversed(scored[:RECENT]))


def recent_results(session: Session, team_id: int) -> list[RecentResult]:
    """Fallback of `official_form`: the team's last RECENT finished matches in the supported
    competitions (stored match list: leagues, cups, super cups, UEFA, Club World Cup),
    oldest first — the last one is the latest. A match without a score is skipped. Read from
    the DB only: no provider request."""
    home, away = aliased(Team), aliased(Team)
    rows = session.execute(
        select(Fixture, Competition, home, away)
        .join(Competition, Competition.id == Fixture.competition_id)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(
            Competition.active,
            Fixture.status == "finished",
            Fixture.goals_home.is_not(None),
            Fixture.goals_away.is_not(None),
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
        )
        .order_by(Fixture.kickoff_at.desc(), Fixture.id.desc())
        .limit(RECENT)
    ).all()
    return [
        RecentResult(f, c, h, a, match_result(f, team_id)) for f, c, h, a in reversed(rows)
    ]


def team_fixtures(
    session: Session, team_id: int, now: datetime
) -> tuple[list[MatchSummary], list[MatchSummary], datetime | None]:
    """Current-season stored matches of every supported competition (no provider request)."""
    home, away = aliased(Team), aliased(Team)
    base = (
        select(Fixture, Competition, home, away)
        .join(Competition, Competition.id == Fixture.competition_id)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(
            Competition.active,
            Fixture.season == settings.current_season,
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
        )
    )
    upcoming = session.execute(
        base.where(
            or_(
                Fixture.status == "live",
                (Fixture.status == "scheduled") & (Fixture.kickoff_at >= now - LIVE_LAG),
            )
        )
        .order_by((Fixture.status != "live"), Fixture.kickoff_at, Fixture.id)
        .limit(UPCOMING)
    ).all()
    recent = session.execute(
        base.where(Fixture.status == "finished")
        .order_by(Fixture.kickoff_at.desc(), Fixture.id.desc())
        .limit(RECENT)
    ).all()
    lookup = team_detail_lookup(session)
    rows = [*upcoming, *recent]
    updated = max((f.synced_at for f, *_ in rows), default=None)
    return (
        [to_summary(f, c, h, a, lookup) for f, c, h, a in upcoming],
        [to_summary(f, c, h, a, lookup) for f, c, h, a in recent],
        updated,
    )


def season_never_loaded(session: Session) -> bool:
    """No current-season whole list was ever loaded: "no matches" cannot be claimed."""
    return session.scalar(
        select(CompetitionSeason.competition_id).where(
            CompetitionSeason.season == settings.current_season,
            CompetitionSeason.season_fixtures_synced_at.is_not(None),
        ).limit(1)
    ) is None


def season_fixture_failures(session: Session, team_id: int) -> list[int]:
    """Competitions the team plays this season whose whole season list was never loaded or
    last failed: its matches there may be missing, so "no matches" is not claimed."""
    rows = session.execute(
        select(
            CompetitionSeason.competition_id,
            CompetitionSeason.season_fixtures_synced_at,
            CompetitionSeason.season_fixtures_failed_at,
        )
        .join(
            TeamCompetitionSeason,
            (TeamCompetitionSeason.competition_id == CompetitionSeason.competition_id)
            & (TeamCompetitionSeason.season == CompetitionSeason.season),
        )
        .where(
            TeamCompetitionSeason.team_id == team_id,
            CompetitionSeason.season == settings.current_season,
            CompetitionSeason.availability == "available",
        )
    ).all()
    return sorted(
        cid for cid, ok, failed in rows if ok is None or (failed is not None and failed > ok)
    )


@dataclass(frozen=True)
class SquadRow:
    member: SquadMember
    player: Player
    # This team's lines of the current season, one per competition held this season.
    lines: list[tuple[TeamPlayerStat, Competition]]


def read_squad(session: Session, team_id: int) -> list[SquadRow]:
    """Current squad with each player's lines for this team this season in the record
    competitions. Other clubs' lines and other competitions are never added."""
    season = settings.current_season
    members = session.execute(
        select(SquadMember, Player)
        .join(Player, Player.id == SquadMember.player_id)
        .where(SquadMember.team_id == team_id)
        .order_by(SquadMember.player_id)
    ).all()
    lines: dict[int, list[tuple[TeamPlayerStat, Competition]]] = {}
    for line, competition in session.execute(
        select(TeamPlayerStat, Competition)
        .join(Competition, Competition.id == TeamPlayerStat.competition_id)
        .where(TeamPlayerStat.team_id == team_id, TeamPlayerStat.season == season)
        .order_by(Competition.sort_order)
    ):
        lines.setdefault(line.player_id, []).append((line, competition))
    return [SquadRow(m, p, lines.get(p.id, [])) for m, p in members]


def missing_record_competitions(session: Session, team_id: int) -> list[int]:
    """Record competitions the team played this season (a finished stored match) without any
    collected player line: the season totals are partial ("부분 집계")."""
    season = settings.current_season
    played = set(
        session.scalars(
            select(Fixture.competition_id)
            .where(
                Fixture.season == season,
                Fixture.status == "finished",
                Fixture.competition_id.in_(record_competitions(session, season)),
                or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
            )
            .distinct()
        )
    )
    covered = set(
        session.scalars(
            select(TeamPlayerStat.competition_id)
            .where(TeamPlayerStat.team_id == team_id, TeamPlayerStat.season == season)
            .distinct()
        )
    )
    return sorted(played - covered)


# ------------------------------- moves shown first (TEAM-006 rule 6, 2026-11-20)

# Competitions whose appearances are not first-team appearances: youth competitions and
# friendlies, by the provider's competition names in /players?id=&season= answers (seen
# 2026-11-20: "U18 Premier League - South", "Premier League 2 Division One", "UEFA U19
# Championship", "UEFA Youth League", "Friendlies Clubs"; Primavera, reserve and junior
# leagues by name).
NOT_FIRST_TEAM = re.compile(
    r"\bU-?\d{2}\b|premier league 2|youth|primavera|reserve|junior|juvenil|friendl",
    re.IGNORECASE,
)


def is_first_team(competition_name: str | None) -> bool:
    return bool(competition_name) and not NOT_FIRST_TEAM.search(competition_name or "")


def parse_player_season(
    response: Any, player_id: int, season: int
) -> dict[int, int]:
    """Official club appearance evidence (user decision B, 2026-11-21).

    Empty NULL lines count as zero. A NULL count with goals, assists or a non-placeholder
    rating proves at least one appearance: store 1 as a lower bound, never an exact count.
    This internal cache is only used to decide whether appearances exist, not for totals.
    Other-player/season answers and unidentifiable non-empty lines are refused.
    """
    if not isinstance(response, list):
        raise IncompleteData("player season: no response list")
    clubs: dict[int, int] = {}
    for entry in response:
        if ((entry or {}).get("player") or {}).get("id") != player_id:
            raise IncompleteData(f"player season: answer for another player than {player_id}")
        for stats in entry.get("statistics") or []:
            league, team = stats.get("league") or {}, stats.get("team") or {}
            if league.get("season") not in (season, None):
                raise IncompleteData(f"player season: season {league.get('season')}")
            games, goals = stats.get("games") or {}, stats.get("goals") or {}
            apps = _int(games.get("appearences"))
            if apps is None:
                has_value = any(v is not None for v in (
                    _int(goals.get("total")), _int(goals.get("assists")),
                    _rating(games.get("rating")),
                ))
                apps = 1 if has_value else 0
            if not team.get("id") or not league.get("name"):
                if apps == 0:
                    continue
                raise IncompleteData("player season: a line without club or competition")
            if not is_first_team(league.get("name")):
                continue
            clubs[team["id"]] = clubs.get(team["id"], 0) + apps
    return clubs


def save_player_season(
    session: Session, player_id: int, season: int, clubs: Mapping[int, int],
    now: datetime,
) -> None:
    session.execute(
        delete(PlayerClubSeason).where(
            PlayerClubSeason.player_id == player_id, PlayerClubSeason.season == season
        )
    )
    if clubs:
        session.execute(
            insert(PlayerClubSeason).values([
                {"player_id": player_id, "season": season, "team_id": t, "appearances": a}
                for t, a in clubs.items()
            ])
        )
    row = session.get(PlayerSeasonCheck, (player_id, season))
    if row is None:
        row = PlayerSeasonCheck(player_id=player_id, season=season)
        session.add(row)
    row.checked_at, row.failure = now, None


def mark_player_season_failure(
    session: Session, player_id: int, season: int, now: datetime, reason: str
) -> None:
    row = session.get(PlayerSeasonCheck, (player_id, season))
    if row is None:
        row = PlayerSeasonCheck(player_id=player_id, season=season)
        session.add(row)
    row.failed_at, row.failure = now, reason[:500]


def evidence_seasons(season: int) -> list[int]:
    """This team's seasons whose appearances back a move of `season`: the one before, the
    season itself and the one after (when it has begun)."""
    return [s for s in (season - 1, season, season + 1) if s <= settings.current_season]


def check_season(row: Transfer) -> int:
    """The season of the club a signing came from: a June-December move follows the
    previous season; a January-May move comes in the middle of its own season."""
    return row.season - 1 if row.half == 1 else row.season


@dataclass(frozen=True)
class MoveEvidence:
    """What decides whether a move of one team and season is shown first."""

    played: frozenset[int]  # players with this team's official appearances (evidence seasons)
    complete: bool  # every evidence season of this team's records was collected
    # (player, season) → club appearances, for checked signings only
    prior: Mapping[tuple[int, int], Mapping[int, int]]


def move_evidence(
    session: Session, team_id: int, season: int, rows: Sequence[Transfer]
) -> MoveEvidence:
    seasons = evidence_seasons(season)
    played = frozenset(
        session.scalars(
            select(TeamPlayerStat.player_id).where(
                TeamPlayerStat.team_id == team_id,
                TeamPlayerStat.season.in_(seasons),
                or_(
                    TeamPlayerStat.appearances > 0,
                    TeamPlayerStat.appearances.is_(None) & or_(
                        TeamPlayerStat.goals.is_not(None),
                        TeamPlayerStat.assists.is_not(None),
                        TeamPlayerStat.rating.is_not(None),
                    ),
                ),
            )
        )
    )
    collected = set(
        session.scalars(
            select(TeamSync.season).where(
                TeamSync.team_id == team_id,
                TeamSync.kind == "player_stats",
                TeamSync.season.in_(seasons),
                TeamSync.synced_at.is_not(None),
            )
        )
    )
    wanted = {
        (r.player_id, check_season(r))
        for r in rows
        if r.direction == "in" and not is_loan_return(r)
    }
    prior: dict[tuple[int, int], dict[int, int]] = {}
    if wanted:
        checked = session.execute(
            select(PlayerSeasonCheck.player_id, PlayerSeasonCheck.season).where(
                PlayerSeasonCheck.player_id.in_({p for p, _ in wanted}),
                PlayerSeasonCheck.checked_at.is_not(None),
            )
        ).all()
        prior = {(p, s): {} for p, s in checked if (p, s) in wanted}
        for club in session.scalars(
            select(PlayerClubSeason).where(
                PlayerClubSeason.player_id.in_({p for p, _ in prior})
            )
        ):
            key = (club.player_id, club.season)
            if key not in prior:
                continue
            if club.appearances is None:
                # Not written since decision B (2026-11-21); a stray old row means the
                # check is not usable, so the signing waits as `check_pending`.
                del prior[key]
            else:
                prior[key][club.team_id] = club.appearances
    return MoveEvidence(played, collected >= set(seasons), prior)


LOAN_RETURNS = frozenset({"return from loan", "back from loan"})


def is_loan_return(row: Transfer) -> bool:
    return row.direction == "in" and (row.type_raw or "").strip().lower() in LOAN_RETURNS


def judge_move(row: Transfer, evidence: MoveEvidence) -> tuple[bool, str]:
    """(shown first, reason). Shown: the player has official appearances for this team in
    the evidence seasons (`played_here`), or a signing with first-team appearances for the
    club he came from (`played_before`). Folded ("기타 이동"): only when the team's records
    are complete and show no appearance, and — for a signing — the club he came from is
    confirmed without first-team appearances (`not_played`). Anything that cannot be decided
    stays shown with its reason (not "not played"): `records_incomplete`, `check_pending`
    (signing not asked yet or not answered), `club_unknown` (no club id). The squad, the
    other club's league, age or youth-sounding names never decide.

    A loan return is the team's own player coming back, not a new signing (TEAM-006 rule 6
    asks the previous club for new signings only): like a departure it is decided by this
    team's appearances alone, so a youth back from a lower-league loan is folded when he
    never played here. The type only tells a return from a signing; it never shows a move."""
    if not evidence.complete:
        return True, "records_incomplete"
    if row.player_id in evidence.played:
        return True, "played_here"
    if row.direction == "out" or is_loan_return(row):
        return False, "not_played"
    if row.counterpart_id is None:
        return True, "club_unknown"
    clubs = evidence.prior.get((row.player_id, check_season(row)))
    if clubs is None:
        return True, "check_pending"
    apps = clubs.get(row.counterpart_id, 0)  # not listed: no first-team line for that club
    return (True, "played_before") if apps > 0 else (False, "not_played")


def pending_checks(session: Session, team_ids: Iterable[int]) -> list[tuple[int, int]]:
    """(player, season) still to ask: signings of the managed seasons whose move waits for
    the club they came from (`check_pending`). Never-asked first, then failed ones."""
    wanted: set[tuple[int, int]] = set()
    for team in team_ids:
        for season in managed_seasons():
            rows = merge_transfers(read_transfers(session, team, season))
            evidence = move_evidence(session, team, season, rows)
            for row in rows:
                if judge_move(row, evidence)[1] == "check_pending":
                    wanted.add((row.player_id, check_season(row)))
    failed = {
        (player, season)
        for player, season in session.execute(
            select(PlayerSeasonCheck.player_id, PlayerSeasonCheck.season).where(
                PlayerSeasonCheck.checked_at.is_(None)
            )
        )
    }
    return sorted(wanted - failed) + sorted(wanted & failed)


@dataclass
class MoveGroup:
    """One player's moves within one half, shown as one row (TEAM-006 추가 검수): every move
    keeps its own date, type and club; the row is shown first when any of them is."""

    player_id: int
    moves: list[Transfer]
    shown: bool

    @property
    def direction(self) -> str:
        return self.moves[-1].direction  # where the player ended up within the half


def group_moves(rows: Sequence[Transfer], evidence: MoveEvidence) -> list[MoveGroup]:
    groups: dict[tuple[int, int], MoveGroup] = {}
    for row in sorted(rows, key=lambda r: (r.transfer_date, r.id or 0)):
        shown = judge_move(row, evidence)[0]
        group = groups.get((row.half, row.player_id))
        if group is None:
            groups[(row.half, row.player_id)] = MoveGroup(row.player_id, [row], shown)
        else:
            group.moves.append(row)
            group.shown = group.shown or shown
    return list(groups.values())


def read_season_stat(
    session: Session, team_id: int, league: int, season: int
) -> TeamSeasonStat | None:
    return session.get(TeamSeasonStat, (team_id, league, season))


def read_transfers(session: Session, team_id: int, season: int) -> list[Transfer]:
    return list(
        session.scalars(
            select(Transfer)
            .where(Transfer.team_id == team_id, Transfer.season == season)
            .order_by(Transfer.transfer_date, Transfer.player_name, Transfer.id)
        )
    )


def counterpart_names(session: Session, ids: Iterable[int | None]) -> dict[int, Team]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    return {t.id: t for t in session.scalars(select(Team).where(Team.id.in_(wanted)))}
