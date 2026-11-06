"""League standings and player rankings (chat 06, LEAG-001·002·004, CMP-003·004).

Collection (pure parsing + replace-on-success):
- Standings, top lists and player season lines are parsed and checked first. Only a complete,
  consistent answer replaces the stored rows of that league, season and kind (one
  transaction), so a re-run never duplicates and a failure never removes good data.
- "Complete" (Codex 1차 지적 1): a table's ranks run 1..n in every group and never shrink;
  its teams belong to the season's participants and include every team with at least
  REGULAR_TEAM_MATCHES league fixtures that season (play-off opponents from the second tier
  have two, so they are participants but not table teams); a top
  list never gets shorter within a season; every /players page but the last holds exactly
  PLAYER_PAGE_SIZE entries, no two pages repeat the same player set, and the season's lines
  do not drop by more than PLAYER_SHRINK_TOLERANCE. A first load and a normal short list
  (season start) are kept.
- Provider values are stored as given: ranks, played counts, points and the season's
  `description` are never corrected; missing numbers stay NULL.

Reading:
- Team references use the current-season allow set (`team_detail_lookup`), so a relegated
  team shows "not available" and an unknown membership stays `null` (never "relegated").
- Saves are aggregated here from player season lines: goalkeeper lines of the league season,
  summed per player over clubs; a player with any line whose saves are NULL is excluded and
  counted, never ranked with 0. Equal totals share a rank (1, 1, 3).
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.core.kst import kst_today
from app.models.fixture import Fixture
from app.models.reference import (
    Competition,
    CompetitionSeason,
    Team,
    TeamCompetitionSeason,
)
from app.models.standings import (
    LeagueSync,
    Player,
    PlayerRanking,
    PlayerSeasonStat,
    Standing,
)
from app.seed.competitions import LEAGUE_IDS
from app.services.reference import crest, upsert_teams

# Provider endpoint and the statistics value of each top list.
TOP_LISTS: dict[str, tuple[str, tuple[str, str]]] = {
    "goals": ("/players/topscorers", ("goals", "total")),
    "assists": ("/players/topassists", ("goals", "assists")),
    "yellow": ("/players/topyellowcards", ("cards", "yellow")),
    "red": ("/players/topredcards", ("cards", "red")),
}
GOALKEEPER = "Goalkeeper"
# /players answers 20 entries a page (all 188 pages of 2025-26: every page but the last).
PLAYER_PAGE_SIZE = 20
# A league team has 34-38 fixtures a season; a relegation play-off opponent has 2.
REGULAR_TEAM_MATCHES = 3
# Player lines of a season only grow; a small drop (provider merging duplicate players) is
# accepted, a larger one is a cut answer.
PLAYER_SHRINK_TOLERANCE = 0.1


class IncompleteData(Exception):
    """The answer cannot be stored as a whole (wrong league/season, missing ids, pages
    missing or conflicting). The message is safe to store (ids and counts only)."""


# ---------------------------------------------------------------------------- parsing


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _datetime(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _dig(block: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = block
    for key in path:
        value = (value or {}).get(key) if isinstance(value, Mapping) else None
    return value


@dataclass
class ParsedStandings:
    rows: list[dict[str, Any]]
    teams: list[dict[str, Any]]


def parse_standings(response: Any, league: int, season: int) -> ParsedStandings:
    """Rows of every group of the league table, in provider order."""
    if not isinstance(response, list):
        raise IncompleteData("standings: no response list")
    rows: list[dict[str, Any]] = []
    teams: dict[int, dict[str, Any]] = {}
    for entry in response:
        meta = (entry or {}).get("league") or {}
        if meta.get("id") != league or meta.get("season") != season:
            raise IncompleteData(f"standings: answer for {meta.get('id')}/{meta.get('season')}")
        for order, group in enumerate(meta.get("standings") or []):
            for row in group or []:
                team = row.get("team") or {}
                rank = _int(row.get("rank"))
                if not team.get("id") or not team.get("name") or rank is None:
                    raise IncompleteData("standings: row without team or rank")
                teams[team["id"]] = team
                every = row.get("all") or {}
                goals = every.get("goals") or {}
                rows.append({
                    "group_name": row.get("group") or meta.get("name") or "",
                    "group_order": order,
                    "team_id": team["id"],
                    "rank": rank,
                    "points": _int(row.get("points")),
                    "played": _int(every.get("played")),
                    "win": _int(every.get("win")),
                    "draw": _int(every.get("draw")),
                    "lose": _int(every.get("lose")),
                    "goals_for": _int(goals.get("for")),
                    "goals_against": _int(goals.get("against")),
                    "goals_diff": _int(row.get("goalsDiff")),
                    "form": row.get("form") or None,
                    "description": row.get("description") or None,
                    "provider_updated_at": _datetime(row.get("update")),
                })
    keys = [(r["group_name"], r["team_id"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise IncompleteData("standings: a team appears twice in one group")
    ranks: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        ranks[r["group_name"]].append(r["rank"])
    for name, values in ranks.items():
        if sorted(values) != list(range(1, len(values) + 1)):
            raise IncompleteData(f"standings: ranks of {name or 'group'} are not 1..{len(values)}")
    return ParsedStandings(rows, list(teams.values()))


def _player(block: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": block["id"],
        "name": block["name"],
        "firstname": block.get("firstname") or None,
        "lastname": block.get("lastname") or None,
        "nationality": block.get("nationality") or None,
        "birth_date": _date((block.get("birth") or {}).get("date")),
        "photo_url": block.get("photo") or None,
    }


def _league_lines(
    entry: Mapping[str, Any], league: int, season: int
) -> list[Mapping[str, Any]]:
    lines = []
    for stats in entry.get("statistics") or []:
        meta = stats.get("league") or {}
        if meta.get("id") != league:
            continue
        if meta.get("season") not in (season, None):
            raise IncompleteData(f"players: season {meta.get('season')} in a {season} answer")
        lines.append(stats)
    return lines


@dataclass
class ParsedRanking:
    rows: list[dict[str, Any]]
    players: list[dict[str, Any]]
    teams: list[dict[str, Any]]


def parse_top_list(response: Any, kind: str, league: int, season: int) -> ParsedRanking:
    """A provider top list in its order. The shown value is this league's lines summed;
    a missing value stays NULL. Red lists keep `yellowred` apart (never added)."""
    if not isinstance(response, list):
        raise IncompleteData(f"{kind}: no response list")
    path = TOP_LISTS[kind][1]
    rows, players, teams = [], {}, {}
    for position, entry in enumerate(response, start=1):
        player = (entry or {}).get("player") or {}
        if not player.get("id") or not player.get("name"):
            raise IncompleteData(f"{kind}: entry {position} without player")
        lines = _league_lines(entry, league, season)
        if not lines:
            raise IncompleteData(f"{kind}: player {player['id']} has no line in {league}")
        team = lines[0].get("team") or {}
        if team.get("id") and team.get("name"):
            teams[team["id"]] = team
        values = [_int(_dig(line, path)) for line in lines]
        extra = [_int(_dig(line, ("cards", "yellowred"))) for line in lines]
        players[player["id"]] = _player(player)
        rows.append({
            "position": position,
            "player_id": player["id"],
            "team_id": team.get("id") if team.get("name") else None,
            "value": None if None in values else sum(values),  # type: ignore[arg-type]
            "yellowred": (None if None in extra else sum(extra)) if kind == "red" else None,  # type: ignore[arg-type]
        })
    return ParsedRanking(rows, list(players.values()), list(teams.values()))


@dataclass
class ParsedPlayerStats:
    lines: list[dict[str, Any]]
    players: list[dict[str, Any]]
    teams: list[dict[str, Any]]


def parse_player_pages(
    pages: Sequence[Mapping[str, Any]], league: int, season: int
) -> ParsedPlayerStats:
    """Every page of /players?league=&season= (each page's `response` and `paging`).

    The set must be complete (pages 1..total, one total, PLAYER_PAGE_SIZE entries on every page
    but the last, 1..PLAYER_PAGE_SIZE on the last) and every line must belong to the league
    season. The provider lists each player once (one entry, every club in `statistics`; all
    188 pages of 2025-26 had no player twice), so a player on a second page means the pages
    shifted or repeated while being collected and some other player is missing: the whole
    set is refused and the next run collects it again (Codex 2차 지적, also a partial
    overlap). Within one entry, a club line given twice with the same values counts once."""
    if not pages:
        raise IncompleteData("players: no page")
    total = _int((pages[0].get("paging") or {}).get("total"))
    if total == 0 and len(pages) == 1 and not pages[0].get("response"):
        # A normal empty answer (no player lines yet) is "no data", not a failure (CMP-004).
        return ParsedPlayerStats([], [], [])
    currents = [_int((p.get("paging") or {}).get("current")) for p in pages]
    if (
        total is None
        or total < 1
        or len(pages) != total
        or sorted(c or 0 for c in currents) != list(range(1, total + 1))
        or any(_int((p.get("paging") or {}).get("total")) != total for p in pages)
    ):
        raise IncompleteData(f"players: pages {len(pages)} of {total}")
    for page in pages:
        current = _int((page.get("paging") or {}).get("current"))
        size = len(page.get("response") or [])
        expected = (1, PLAYER_PAGE_SIZE) if current == total else (PLAYER_PAGE_SIZE,) * 2
        if not expected[0] <= size <= expected[1]:
            raise IncompleteData(f"players: page {current} of {total} has {size} entries")

    lines: dict[tuple[int, int], dict[str, Any]] = {}
    players: dict[int, dict[str, Any]] = {}
    teams: dict[int, dict[str, Any]] = {}
    seen: dict[int, int | None] = {}
    for page, current in zip(pages, currents, strict=True):
        for entry in page.get("response") or []:
            player = (entry or {}).get("player") or {}
            if not player.get("id") or not player.get("name"):
                raise IncompleteData("players: entry without player")
            if player["id"] in seen:
                raise IncompleteData(
                    f"players: page {current} repeats player {player['id']} "
                    f"from page {seen[player['id']]}"
                )
            seen[player["id"]] = current
            for stats in _league_lines(entry, league, season):
                team = stats.get("team") or {}
                if not team.get("id") or not team.get("name"):
                    raise IncompleteData(f"players: player {player['id']} without team")
                games = stats.get("games") or {}
                goals = stats.get("goals") or {}
                cards = stats.get("cards") or {}
                line = {
                    "player_id": player["id"],
                    "team_id": team["id"],
                    "position": games.get("position") or None,
                    "number": _int(games.get("number")),
                    "appearances": _int(games.get("appearences")),
                    "lineups": _int(games.get("lineups")),
                    "minutes": _int(games.get("minutes")),
                    "rating": _decimal(games.get("rating")),
                    "goals": _int(goals.get("total")),
                    "assists": _int(goals.get("assists")),
                    "conceded": _int(goals.get("conceded")),
                    "saves": _int(goals.get("saves")),
                    "yellow": _int(cards.get("yellow")),
                    "yellowred": _int(cards.get("yellowred")),
                    "red": _int(cards.get("red")),
                    "raw": dict(stats),
                }
                key = (player["id"], team["id"])
                if key in lines and lines[key] != line:
                    raise IncompleteData(
                        f"players: player {player['id']} has two lines for team {team['id']}"
                    )
                lines[key] = line
                players[player["id"]] = _player(player)
                teams[team["id"]] = team
    return ParsedPlayerStats(list(lines.values()), list(players.values()), list(teams.values()))


# ---------------------------------------------------------------------------- saving


def _ensure_teams(session: Session, teams: Iterable[dict[str, Any]], now: datetime) -> None:
    """Teams of a past season may be new to the DB: add their provider identity. Season
    participation and the current allow set are left to the reference job."""
    upsert_teams(session, teams, now)


def _upsert_players(session: Session, players: Sequence[dict[str, Any]], now: datetime) -> None:
    # Id order: the daily list and stats jobs may overlap; one lock order avoids deadlocks.
    players = sorted(players, key=lambda p: p["id"])
    for start in range(0, len(players), 500):
        chunk = [{**p, "updated_at": now} for p in players[start : start + 500]]
        stmt = insert(Player).values(chunk)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Player.id],
                set_={
                    "name": stmt.excluded.name,
                    "firstname": stmt.excluded.firstname,
                    "lastname": stmt.excluded.lastname,
                    "nationality": func.coalesce(stmt.excluded.nationality, Player.nationality),
                    "birth_date": func.coalesce(stmt.excluded.birth_date, Player.birth_date),
                    "photo_url": func.coalesce(stmt.excluded.photo_url, Player.photo_url),
                    "updated_at": now,
                },
            )
        )


def _sync_row(session: Session, league: int, season: int, kind: str) -> LeagueSync:
    row = session.get(LeagueSync, (league, season, kind))
    if row is None:
        row = LeagueSync(competition_id=league, season=season, kind=kind)
        session.add(row)
    return row


def mark_success(
    session: Session, league: int, season: int, kind: str, now: datetime, rows: int
) -> None:
    row = _sync_row(session, league, season, kind)
    row.synced_at, row.row_count = now, rows


def mark_failure(
    session: Session, league: int, season: int, kind: str, now: datetime, reason: str
) -> None:
    row = _sync_row(session, league, season, kind)
    row.failed_at, row.failure = now, reason[:300]


def _stored_count(session: Session, model: Any, league: int, season: int, **where: Any) -> int:
    return session.scalar(
        select(func.count()).select_from(model).where(
            model.competition_id == league,
            model.season == season,
            *(getattr(model, k) == v for k, v in where.items()),
        )
    ) or 0


def _refuse_shrink(label: str, new: int, stored: int, tolerance: float = 0.0) -> None:
    """A stored set is replaced only by one at least as large (minus `tolerance`)."""
    if stored and new < stored * (1 - tolerance):
        raise IncompleteData(f"{label}: {new} rows would replace {stored}")


def check_standings(session: Session, league: int, season: int, parsed: ParsedStandings) -> None:
    """A cut table is refused (see the module notes); the stored one stays."""
    _refuse_shrink("standings", len(parsed.rows), _stored_count(session, Standing, league, season))
    participants = set(
        session.scalars(
            select(TeamCompetitionSeason.team_id).where(
                TeamCompetitionSeason.competition_id == league,
                TeamCompetitionSeason.season == season,
            )
        )
    )
    teams = {r["team_id"] for r in parsed.rows}
    if participants and not teams <= participants:
        raise IncompleteData(f"standings: {len(teams - participants)} teams outside the season")
    if not parsed.rows:
        return  # nothing stored yet and nothing given: a table not published yet
    side = (
        select(Fixture.home_team_id.label("team_id"))
        .where(Fixture.competition_id == league, Fixture.season == season)
        .union_all(
            select(Fixture.away_team_id).where(
                Fixture.competition_id == league, Fixture.season == season
            )
        )
        .subquery()
    )
    regular = set(
        session.scalars(
            select(side.c.team_id)
            .group_by(side.c.team_id)
            .having(func.count() >= REGULAR_TEAM_MATCHES)
        )
    )
    if not regular <= teams:
        raise IncompleteData(f"standings: {len(regular - teams)} league teams missing")


def save_standings(
    session: Session, league: int, season: int, parsed: ParsedStandings, now: datetime
) -> None:
    """Replace the league table. An empty or cut answer never replaces a stored table
    (CMP-004)."""
    check_standings(session, league, season, parsed)
    _ensure_teams(session, parsed.teams, now)
    session.execute(
        delete(Standing).where(Standing.competition_id == league, Standing.season == season)
    )
    if parsed.rows:
        session.execute(
            insert(Standing).values([
                {**r, "competition_id": league, "season": season, "synced_at": now}
                for r in parsed.rows
            ])
        )
    mark_success(session, league, season, "standings", now, len(parsed.rows))


def save_ranking(
    session: Session, league: int, season: int, kind: str, parsed: ParsedRanking, now: datetime
) -> None:
    # A season's top list never gets shorter: a shorter answer is a cut one.
    stored = _stored_count(session, PlayerRanking, league, season, type=kind)
    _refuse_shrink(kind, len(parsed.rows), stored)
    _ensure_teams(session, parsed.teams, now)
    _upsert_players(session, parsed.players, now)
    session.execute(
        delete(PlayerRanking).where(
            PlayerRanking.competition_id == league,
            PlayerRanking.season == season,
            PlayerRanking.type == kind,
        )
    )
    if parsed.rows:
        session.execute(
            insert(PlayerRanking).values([
                {**r, "competition_id": league, "season": season, "type": kind, "synced_at": now}
                for r in parsed.rows
            ])
        )
    mark_success(session, league, season, kind, now, len(parsed.rows))


def save_player_stats(
    session: Session, league: int, season: int, parsed: ParsedPlayerStats, now: datetime
) -> None:
    stored = _stored_count(session, PlayerSeasonStat, league, season)
    _refuse_shrink("players", len(parsed.lines), stored, PLAYER_SHRINK_TOLERANCE)
    _ensure_teams(session, parsed.teams, now)
    _upsert_players(session, parsed.players, now)
    session.execute(
        delete(PlayerSeasonStat).where(
            PlayerSeasonStat.competition_id == league, PlayerSeasonStat.season == season
        )
    )
    for start in range(0, len(parsed.lines), 500):
        session.execute(
            insert(PlayerSeasonStat).values([
                {**line, "competition_id": league, "season": season, "synced_at": now}
                for line in parsed.lines[start : start + 500]
            ])
        )
    mark_success(session, league, season, "player_stats", now, len(parsed.lines))


# ---------------------------------------------------------------------------- schedule

HOURLY = timedelta(minutes=55)
DAILY = timedelta(hours=23)


def is_matchday(session: Session, league: int, season: int, now: datetime) -> bool:
    """The league plays today (KST calendar date) or a match kicked off in the last 4 hours
    (a late match ending after midnight)."""
    return bool(
        session.scalar(
            select(func.count()).select_from(Fixture).where(
                Fixture.competition_id == league,
                Fixture.season == season,
                or_(
                    Fixture.kickoff_date_kst == kst_today(now),
                    Fixture.kickoff_at.between(now - timedelta(hours=4), now),
                ),
            )
        )
    )


def due_leagues(
    session: Session, season: int, kind: str, now: datetime, *, matchday_hourly: bool
) -> list[int]:
    """Leagues whose `kind` should be collected now.

    Current season: daily, or hourly on a matchday when `matchday_hourly`. A past season is
    kept, not re-collected: only when it was never stored. A recent failure waits for the
    next slot, so a broken provider is not asked every minute."""
    due = []
    for league in LEAGUE_IDS:
        state = session.get(LeagueSync, (league, season, kind))
        synced = state.synced_at if state else None
        failed = state.failed_at if state else None
        last_try = max((t for t in (synced, failed) if t), default=None)
        if last_try is not None and now - last_try < HOURLY:
            continue
        if synced is None:
            due.append(league)
        elif season != settings.current_season:
            continue
        elif now - synced >= DAILY or (
            matchday_hourly and is_matchday(session, league, season, now)
        ):
            due.append(league)
    return due


# ---------------------------------------------------------------------------- reading


@dataclass(frozen=True)
class SyncState:
    synced_at: datetime | None
    failed_at: datetime | None

    @property
    def collected(self) -> bool:
        return self.synced_at is not None

    @property
    def refresh_failed(self) -> bool:
        """Stored data is older than a later failed attempt (shown, with a notice)."""
        return self.synced_at is not None and self.failed_at is not None and (
            self.failed_at > self.synced_at
        )


def sync_state(session: Session, league: int, season: int, kind: str) -> SyncState:
    row = session.get(LeagueSync, (league, season, kind))
    return SyncState(row.synced_at if row else None, row.failed_at if row else None)


def league_available(session: Session, league: int, season: int) -> bool:
    row = session.get(CompetitionSeason, (league, season))
    return row is not None and row.availability == "available"


def relegation_zone(description: str | None) -> str | None:
    """The season's own wording: "Relegation…" with play-off → playoff, otherwise relegated.
    Other descriptions (European places, "Play-offs" without relegation) are not zones."""
    text = (description or "").strip().lower()
    if not text.startswith("relegation"):
        return None
    return "relegation_playoff" if "play" in text else "relegation"


@dataclass
class StandingGroupData:
    name: str
    rows: list[tuple[Standing, Team]] = field(default_factory=list)


def read_standings(session: Session, league: int, season: int) -> list[StandingGroupData]:
    groups: dict[str, StandingGroupData] = {}
    for standing, team in session.execute(
        select(Standing, Team)
        .join(Team, Team.id == Standing.team_id)
        .where(Standing.competition_id == league, Standing.season == season)
        .order_by(Standing.group_order, Standing.rank, Standing.team_id)
    ):
        groups.setdefault(standing.group_name, StandingGroupData(standing.group_name)).rows.append(
            (standing, team)
        )
    return list(groups.values())


def league_competitions(session: Session) -> list[Competition]:
    return list(
        session.scalars(
            select(Competition)
            .where(Competition.id.in_(LEAGUE_IDS), Competition.active)
            .order_by(Competition.sort_order)
        )
    )


@dataclass(frozen=True)
class RankedPlayer:
    rank: int
    tied: bool
    player: Player
    team: Team | None
    value: int | None
    yellowred: int | None = None


@dataclass(frozen=True)
class RankingData:
    items: list[RankedPlayer]
    # Saves only: goalkeepers left out because a line had no saves value.
    excluded: int | None


def read_top_list(session: Session, league: int, season: int, kind: str) -> list[RankedPlayer]:
    rows = session.execute(
        select(PlayerRanking, Player, Team)
        .join(Player, Player.id == PlayerRanking.player_id)
        .outerjoin(Team, Team.id == PlayerRanking.team_id)
        .where(
            PlayerRanking.competition_id == league,
            PlayerRanking.season == season,
            PlayerRanking.type == kind,
        )
        .order_by(PlayerRanking.position)
    ).all()
    return [
        RankedPlayer(r.position, False, p, t, r.value, r.yellowred if kind == "red" else None)
        for r, p, t in rows
    ]


@dataclass(frozen=True)
class SavesLine:
    player_id: int
    team_id: int
    saves: int | None
    appearances: int | None


@dataclass(frozen=True)
class SavesTotal:
    rank: int
    tied: bool
    player_id: int
    saves: int
    team_id: int


def aggregate_saves(lines: Iterable[SavesLine]) -> tuple[list[SavesTotal], set[int]]:
    """Goalkeeper lines → ranked totals and excluded player ids.

    Clubs are summed per player; any NULL line excludes the player (never 0). Ties share
    the rank (1, 1, 3); order within a tie is by player id so the list is stable. The shown
    club is the line with the most appearances (the first line given on a tie)."""
    by_player: dict[int, list[SavesLine]] = defaultdict(list)
    for line in lines:
        by_player[line.player_id].append(line)
    excluded = {pid for pid, rows in by_player.items() if any(r.saves is None for r in rows)}
    totals = sorted(
        (
            (sum(r.saves or 0 for r in rows), pid, max(rows, key=lambda r: r.appearances or 0))
            for pid, rows in by_player.items()
            if pid not in excluded
        ),
        key=lambda item: (-item[0], item[1]),
    )
    counts: dict[int, int] = defaultdict(int)
    for saves, _, _ in totals:
        counts[saves] += 1
    ranked, rank, previous = [], 0, None
    for index, (saves, pid, main) in enumerate(totals, start=1):
        if saves != previous:
            rank, previous = index, saves
        ranked.append(SavesTotal(rank, counts[saves] > 1, pid, saves, main.team_id))
    return ranked, excluded


def read_saves(session: Session, league: int, season: int) -> RankingData:
    lines = [
        SavesLine(*row)
        for row in session.execute(
            select(
                PlayerSeasonStat.player_id,
                PlayerSeasonStat.team_id,
                PlayerSeasonStat.saves,
                PlayerSeasonStat.appearances,
            ).where(
                PlayerSeasonStat.competition_id == league,
                PlayerSeasonStat.season == season,
                PlayerSeasonStat.position == GOALKEEPER,
            )
            # Same input order as the stored lines, so a tie on appearances is stable.
            .order_by(PlayerSeasonStat.player_id, PlayerSeasonStat.team_id)
        )
    ]
    ranked, excluded = aggregate_saves(lines)
    players = {
        p.id: p
        for p in session.scalars(select(Player).where(Player.id.in_([r.player_id for r in ranked])))
    }
    teams = {
        t.id: t
        for t in session.scalars(select(Team).where(Team.id.in_({r.team_id for r in ranked})))
    }
    return RankingData(
        [
            RankedPlayer(r.rank, r.tied, players[r.player_id], teams.get(r.team_id), r.saves)
            for r in ranked
        ],
        len(excluded),
    )


def player_photo(player: Player) -> str | None:
    """Same rights rule as crests (guide §6.5, V-10)."""
    return crest(player.photo_url)
