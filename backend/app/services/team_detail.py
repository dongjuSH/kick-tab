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
- transfers: /transfers?team= — entries involving the team, classified by date: season S is
  S-06-01 .. (S+1)-05-31, first half June-December, second half January-May. Future-dated
  entries are left out until their date. A season is refreshed through the (S+1)-07-01 00:00
  run (records added up to June 30) and fixed afterwards; one never stored is still stored
  once (first collection). Every unit runs at most once per KST day.
An empty or cut answer never replaces stored rows: the failure is recorded in team_syncs.

Reading: the allow set decides access (current five-league members, D-15). An unknown team
is NOT_FOUND, a known team outside the set TEAM_DETAIL_UNAVAILABLE, and a membership that
cannot be confirmed MEMBERSHIP_UNKNOWN (never "relegated").
"""

import html
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.core.kst import kst_date
from app.models.fixture import Fixture
from app.models.match_detail import TeamForm
from app.models.reference import Competition, CompetitionSeason, Team, TeamCompetitionSeason
from app.models.standings import LeagueSync, Player, PlayerSeasonStat, Standing
from app.models.team_detail import SquadMember, TeamCoach, TeamSeasonStat, TeamSync, Transfer
from app.schemas.match import MatchSummary
from app.schemas.match_detail import FormBlock, FormMatch
from app.seed.competitions import LEAGUE_IDS
from app.services.fixtures import LIVE_LAG, to_summary
from app.services.head_to_head import (
    competition_names,
    recent_form,
    result_for,
    team_names,
)
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
    # The provider often lists one move twice, the second a day later (same player, club,
    # direction and type: e.g. 08-10 and 08-11). Such a pair is one move: the first date is
    # kept, so the move is shown once (and the pair never splits across two halves). It is
    # merged only when nothing else happened to the player on those two days: a move the
    # other way on either day (loan out 08-10, back 08-11, out again 08-11) makes them two
    # real moves, and both are kept (Codex 1차 지적 8).
    days = {(r["player_id"], r["transfer_date"], r["direction"]) for r in rows.values()}
    opposite = {"in": "out", "out": "in"}
    kept: list[dict[str, Any]] = []
    last: dict[tuple[Any, ...], date] = {}
    for row in sorted(rows.values(), key=lambda r: (r["transfer_date"], r["player_id"])):
        if row["counterpart_id"] is None:
            # The other club cannot be identified (name only, 933 such rows on 2026-11-07):
            # never merged, so two different moves are not taken for one (Codex 2차 지적 N2).
            kept.append(row)
            continue
        same = (row["player_id"], row["direction"], row["counterpart_id"], row["type_raw"])
        previous = last.get(same)
        last[same] = row["transfer_date"]
        if (
            previous is not None
            and row["transfer_date"] - previous == timedelta(days=1)
            and not any(
                (row["player_id"], day, opposite[row["direction"]]) in days
                for day in (previous, row["transfer_date"])
            )
        ):
            continue
        kept.append(row)
    return kept


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


def check_transfers(new: int, stored: int, season: int) -> None:
    """A season's moves only accumulate (Codex 1차 지적 1): the provider may drop a wrong
    entry or two, but a larger drop (more than max(TRANSFER_SHRINK_ALLOWANCE, 10%)) is a cut
    answer and keeps the stored season."""
    allowed = max(TRANSFER_SHRINK_ALLOWANCE, int(stored * TRANSFER_SHRINK_TOLERANCE))
    if stored - new > allowed:
        raise IncompleteData(f"transfers: {new} rows would replace {stored} of {season}")


def save_transfers(
    session: Session, team_id: int, season: int, rows: Sequence[dict[str, Any]], now: datetime
) -> None:
    """Replace one season of the team's transfers (only rows of that season are given)."""
    stored = session.scalar(
        select(func.count()).select_from(Transfer).where(
            Transfer.team_id == team_id, Transfer.season == season
        )
    ) or 0
    check_transfers(len(rows), stored, season)
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


def form_block(session: Session, team_id: int) -> FormBlock:
    row = session.get(TeamForm, team_id)
    if row is None or row.fetched_at is None:
        return FormBlock(status="unavailable", data=None)
    rows = recent_form(row.payload or [], team_id)
    if not rows:
        return FormBlock(status="not_provided", data=None)
    names, teams = competition_names(session), team_names(session, [row.payload or []])
    data = []
    for r in rows:
        home = r["homeId"] == team_id
        other = "away" if home else "home"
        data.append(
            FormMatch(
                kickoff_date_kst=kst_date(datetime.fromisoformat(r["kickoffAt"])),
                competition=names.get(r.get("leagueId")) or r.get("leagueName") or "—",
                opponent_name=teams.get(r[f"{other}Id"]) or r[f"{other}Name"] or "—",
                venue="home" if home else "away",
                goals_for=r["goalsHome"] if home else r["goalsAway"],
                goals_against=r["goalsAway"] if home else r["goalsHome"],
                result=result_for(r, team_id),
            )
        )
    return FormBlock(status="available", data=data)


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
    line: PlayerSeasonStat | None


def read_squad(session: Session, team_id: int, league: int) -> list[SquadRow]:
    """Current squad joined with this team's league line of the current season. A player's
    lines at other clubs stay apart (never added), so each player appears once."""
    season = settings.current_season
    rows = session.execute(
        select(SquadMember, Player, PlayerSeasonStat)
        .join(Player, Player.id == SquadMember.player_id)
        .outerjoin(
            PlayerSeasonStat,
            (PlayerSeasonStat.player_id == SquadMember.player_id)
            & (PlayerSeasonStat.team_id == team_id)
            & (PlayerSeasonStat.competition_id == league)
            & (PlayerSeasonStat.season == season),
        )
        .where(SquadMember.team_id == team_id)
        .order_by(SquadMember.player_id)
    ).all()
    return [SquadRow(m, p, s) for m, p, s in rows]


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
