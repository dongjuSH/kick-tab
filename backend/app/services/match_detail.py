"""Match detail blocks: storage, read model and the one-off supplement (MAT-002·004).

Collection (guide §6.5):
- the live sync stores the events of the live answer and every block of `/fixtures?ids=`
  answers (matches that just finished are read that way), at no extra request;
- the `fixture_details` job reads recently finished matches still missing a final record;
- opening a page fetches `/fixtures?id=` once when nothing usable is stored (see
  `detail_fetch_due`), merging concurrent requests. A failure keeps stored data and only
  sets `last_failed_at`, which also holds back further attempts for a while.
"""

import logging
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.orm import Session

from app.core.locks import single_flight
from app.models.fixture import Fixture
from app.models.match_detail import FixtureDetail, FixtureEvent
from app.providers.api_football import ApiFootballClient, ApiFootballError
from app.schemas.match_detail import (
    BlockStatus,
    EventsBlock,
    LineupPlayer,
    LineupsBlock,
    MatchEvent,
    MatchRecords,
    PlayerRating,
    PlayersBlock,
    Side,
    StatisticsBlock,
    StatRow,
    TeamLineup,
)
from app.services.fixtures import upsert_fixtures
from app.services.match_status import map_status
from app.services.reference import crest

logger = logging.getLogger(__name__)

ClientFactory = Callable[[], ApiFootballClient]

# A failed lookup is not repeated for this long, however many visitors open the page.
FAILURE_COOLDOWN = timedelta(minutes=5)
# A live match is re-read on request at most this often (the live sync runs every minute).
LIVE_REFRESH = timedelta(seconds=90)
# Lineups are usually published about an hour before kickoff; until then nothing is fetched.
LINEUP_LEAD = timedelta(minutes=60)
LINEUP_RECHECK = timedelta(minutes=10)
# Statuses whose record is final once fetched in that status.
FINAL_STATUSES = ("finished", "abandoned")
BEFORE_KICKOFF = ("scheduled", "postponed")

# Display order: the Figma rows first (점유율·전체 슈팅·유효 슈팅·코너킥·파울·오프사이드·패스),
# then the other provider types; unknown types keep the provider order after these.
STAT_ORDER = (
    "Ball Possession",
    "Total Shots",
    "Shots on Goal",
    "Corner Kicks",
    "Fouls",
    "Offsides",
    "Total passes",
    "Shots off Goal",
    "Blocked Shots",
    "Shots insidebox",
    "Shots outsidebox",
    "Goalkeeper Saves",
    "Passes accurate",
    "Passes %",
    "Yellow Cards",
    "Red Cards",
    "expected_goals",
    "goals_prevented",
)
EVENT_TYPES = {"goal": "goal", "card": "card", "subst": "subst", "var": "var"}


# ---- storage ---------------------------------------------------------------------------


def _event_rows(fixture_id: int, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Provider events in provider order without exact repeats (no provider event id)."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for event in events:
        time = event.get("time") or {}
        player = event.get("player") or {}
        assist = event.get("assist") or {}
        row = {
            "elapsed": time.get("elapsed"),
            "extra": time.get("extra"),
            "team_id": (event.get("team") or {}).get("id"),
            "player_name": player.get("name"),
            "assist_name": assist.get("name"),
            "type": str(event.get("type") or "").strip() or "unknown",
            "detail": event.get("detail"),
            "comments": event.get("comments"),
        }
        key = tuple(row.values())
        if key in seen:
            continue
        seen.add(key)
        rows.append({"fixture_id": fixture_id, "seq": len(rows), **row})
    return rows


def save_events(session: Session, fixture_id: int, events: Iterable[dict[str, Any]]) -> None:
    """Replace the stored timeline of one fixture with a provider answer."""
    rows = _event_rows(fixture_id, events)
    session.execute(delete(FixtureEvent).where(FixtureEvent.fixture_id == fixture_id))
    if rows:
        session.execute(insert(FixtureEvent), rows)


def save_provider_items(session: Session, items: Iterable[dict[str, Any]], now: datetime) -> int:
    """Store the detail parts present in fixture answers (call after `upsert_fixtures`).

    A live answer carries events only; `/fixtures?id(s)=` answers carry all four blocks.
    Only fixtures already stored are touched. Returns the number of full records saved.
    """
    full = 0
    for item in items:
        fixture_id = (item.get("fixture") or {}).get("id")
        if not fixture_id or session.get(Fixture, fixture_id) is None:
            continue
        if "events" in item:
            save_events(session, fixture_id, item.get("events") or [])
        if not all(key in item for key in ("lineups", "statistics", "players")):
            continue
        status = map_status(((item.get("fixture") or {}).get("status") or {}).get("short"))
        row = session.get(FixtureDetail, fixture_id) or FixtureDetail(fixture_id=fixture_id)
        row.statistics = item.get("statistics") or []
        row.lineups = item.get("lineups") or []
        row.players = item.get("players") or []
        row.fetched_at = now
        row.fetched_status = status.status
        row.last_failed_at = None
        session.add(row)
        full += 1
    return full


# ---- final record after the finish (fixture_details job) -------------------------------

# Matches that finished within this window and still lack a final record are read once.
FINAL_RECORD_WINDOW = timedelta(days=2)
FINAL_RECORD_RETRY = timedelta(minutes=10)


def _final_record_query(now: datetime):
    return (
        select(Fixture.id)
        .outerjoin(FixtureDetail, FixtureDetail.fixture_id == Fixture.id)
        .where(
            Fixture.status.in_(FINAL_STATUSES),
            Fixture.kickoff_at >= now - FINAL_RECORD_WINDOW,
            or_(
                FixtureDetail.fixture_id.is_(None),
                FixtureDetail.fetched_status.is_distinct_from(Fixture.status),
            ),
            or_(
                FixtureDetail.last_failed_at.is_(None),
                FixtureDetail.last_failed_at < now - FINAL_RECORD_RETRY,
            ),
        )
        .order_by(Fixture.kickoff_at)
    )


def needs_final_records(session: Session, now: datetime) -> bool:
    return session.scalar(_final_record_query(now).limit(1)) is not None


def final_record_targets(session: Session, now: datetime) -> list[int]:
    return list(session.scalars(_final_record_query(now).limit(100)))


def mark_record_failures(session: Session, fixture_ids: Iterable[int], now: datetime) -> None:
    for fixture_id in fixture_ids:
        row = session.get(FixtureDetail, fixture_id) or FixtureDetail(fixture_id=fixture_id)
        row.last_failed_at = now
        session.add(row)


# ---- supplement on request ------------------------------------------------------------


def detail_fetch_due(fixture: Fixture, row: FixtureDetail | None, now: datetime) -> bool:
    """Whether opening the page should read the provider once (no request otherwise)."""
    if row is not None and row.last_failed_at and now - row.last_failed_at < FAILURE_COOLDOWN:
        return False
    fetched = row is not None and row.fetched_at is not None
    if fixture.status in FINAL_STATUSES:
        # Once per final status: a record taken while live is replaced by the final one.
        return not fetched or row.fetched_status != fixture.status
    if fixture.status == "live":
        return not fetched or now - row.fetched_at > LIVE_REFRESH
    if fixture.status == "scheduled" and fixture.kickoff_at - now <= LINEUP_LEAD:
        return not fetched or (not row.lineups and now - row.fetched_at > LINEUP_RECHECK)
    return False


def ensure_records(
    session: Session, fixture: Fixture, now: datetime, client_factory: ClientFactory
) -> None:
    """Fetch the detail record once if due. Never raises for provider failures."""
    if not detail_fetch_due(fixture, session.get(FixtureDetail, fixture.id), now):
        return
    session.commit()  # end the read transaction before taking the lock
    with single_flight(session, f"kicktab-detail:{fixture.id}"):
        session.expire_all()
        fresh = session.get(Fixture, fixture.id)
        row = session.get(FixtureDetail, fixture.id)
        if fresh is None or not detail_fetch_due(fresh, row, now):
            return  # another request fetched it while this one waited
        client = client_factory()
        try:
            result = client.get("/fixtures", {"id": fixture.id, "timezone": "UTC"})
            items = result.response or []
            if not items:
                raise ApiFootballError(f"API-Football returned no fixture {fixture.id}")
        except ApiFootballError as exc:
            logger.warning("Detail fetch for fixture %s failed: %s", fixture.id, type(exc).__name__)
            row = row or FixtureDetail(fixture_id=fixture.id)
            row.last_failed_at = now
            session.add(row)
            return
        finally:
            logger.info(
                "Detail fetch for fixture %s: %d request(s)", fixture.id, client.request_count
            )
            client.close()
        upsert_fixtures(session, items, now)
        save_provider_items(session, items, now)
    session.expire_all()


# ---- read side --------------------------------------------------------------------------


def _side(fixture: Fixture, team_id: Any) -> Side | None:
    if team_id == fixture.home_team_id:
        return "home"
    if team_id == fixture.away_team_id:
        return "away"
    return None


def _number(value: Any) -> tuple[float | None, bool]:
    """Provider statistic value -> (number, is_percent). Missing stays None, never 0."""
    if value is None or isinstance(value, bool):
        return None, False
    if isinstance(value, int | float):
        return float(value), False
    text = str(value).strip()
    percent = text.endswith("%")
    try:
        return float(text.rstrip("%")), percent
    except ValueError:
        return None, False


def _statistics(fixture: Fixture, blocks: list[dict[str, Any]]) -> list[StatRow]:
    values: dict[str, dict[str, tuple[float | None, bool]]] = {}
    order: list[str] = []
    for block in blocks:
        side = _side(fixture, (block.get("team") or {}).get("id"))
        if side is None:
            continue
        for stat in block.get("statistics") or []:
            key = str(stat.get("type") or "").strip()
            if not key:
                continue
            if key not in values:
                values[key] = {}
                order.append(key)
            values[key][side] = _number(stat.get("value"))
    rank = {key: index for index, key in enumerate(STAT_ORDER)}
    rows: list[StatRow] = []
    for key in sorted(order, key=lambda k: (rank.get(k, len(rank)), order.index(k))):
        home, home_pct = values[key].get("home", (None, False))
        away, away_pct = values[key].get("away", (None, False))
        if home is None and away is None:
            continue  # the type is listed but no value was given: nothing to show
        rows.append(StatRow(key=key, home=home, away=away, percent=home_pct or away_pct))
    return rows


def _players(entries: list[dict[str, Any]]) -> list[LineupPlayer]:
    players: list[LineupPlayer] = []
    for entry in entries:
        player = entry.get("player") or {}
        if not player.get("name"):
            continue
        players.append(
            LineupPlayer(
                number=player.get("number"), name=player["name"], position=player.get("pos")
            )
        )
    return players


def _lineups(fixture: Fixture, blocks: list[dict[str, Any]]) -> list[TeamLineup]:
    lineups: list[TeamLineup] = []
    for block in blocks:
        side = _side(fixture, (block.get("team") or {}).get("id"))
        start = _players(block.get("startXI") or [])
        if side is None or not start:
            continue
        lineups.append(
            TeamLineup(
                side=side,
                formation=block.get("formation"),
                coach=(block.get("coach") or {}).get("name"),
                start_xi=start,
                substitutes=_players(block.get("substitutes") or []),
            )
        )
    return sorted(lineups, key=lambda lineup: lineup.side != "home")


def _ratings(fixture: Fixture, blocks: list[dict[str, Any]]) -> list[PlayerRating]:
    ratings: list[PlayerRating] = []
    for block in blocks:
        side = _side(fixture, (block.get("team") or {}).get("id"))
        if side is None:
            continue
        for entry in block.get("players") or []:
            player = entry.get("player") or {}
            games = ((entry.get("statistics") or [{}])[0] or {}).get("games") or {}
            rating, _ = _number(games.get("rating"))
            # Unused substitutes come with minutes 0 and rating "0": a placeholder, not a
            # rating. Players without minutes did not play and are left out.
            if not rating:
                rating = None
            if not player.get("name") or (rating is None and not games.get("minutes")):
                continue
            ratings.append(
                PlayerRating(
                    player_id=player.get("id"),
                    name=player["name"],
                    photo_url=crest(player.get("photo")),
                    side=side,
                    rating=rating,
                )
            )
    return sorted(ratings, key=lambda p: (p.rating is None, -(p.rating or 0), p.name))


def _lookup_open(fixture: Fixture, now: datetime) -> bool:
    """Whether the provider is read for this match now (see `detail_fetch_due`). A failure
    from an earlier window (e.g. before a postponement) is not offered as retryable."""
    if fixture.status in BEFORE_KICKOFF:
        return fixture.status == "scheduled" and fixture.kickoff_at - now <= LINEUP_LEAD
    return True


def _empty_status(fixture: Fixture, fetched: bool, failed: bool, now: datetime) -> BlockStatus:
    if not fetched and failed and _lookup_open(fixture, now):
        return "unavailable"
    if fixture.status in BEFORE_KICKOFF:
        return "not_yet"
    return "not_provided"


def read_records(
    session: Session, fixture: Fixture, now: datetime
) -> tuple[MatchRecords, datetime | None]:
    row = session.get(FixtureDetail, fixture.id)
    fetched = row is not None and row.fetched_at is not None
    failed = row is not None and row.last_failed_at is not None
    empty = _empty_status(fixture, fetched, failed, now)

    events = [
        MatchEvent(
            elapsed=e.elapsed,
            extra=e.extra,
            side=_side(fixture, e.team_id),
            type=EVENT_TYPES.get(e.type.casefold(), "other"),
            detail=e.detail,
            player=e.player_name,
            assist=e.assist_name,
        )
        for e in session.scalars(
            select(FixtureEvent)
            .where(FixtureEvent.fixture_id == fixture.id)
            .order_by(FixtureEvent.seq)
        )
    ]
    if events or (fixture.status == "live" and fetched):
        # A live match without events yet has an empty but valid timeline.
        events_block = EventsBlock(status="available", data=events)
    else:
        events_block = EventsBlock(status=empty, data=None)

    stats = _statistics(fixture, row.statistics or []) if fetched else []
    lineups = _lineups(fixture, row.lineups or []) if fetched else []
    ratings = _ratings(fixture, row.players or []) if fetched else []
    has_rating = any(p.rating is not None for p in ratings)
    records = MatchRecords(
        events=events_block,
        statistics=StatisticsBlock(status="available", data=stats)
        if stats
        else StatisticsBlock(status=empty, data=None),
        lineups=LineupsBlock(status="available", data=lineups)
        if lineups
        else LineupsBlock(status=empty, data=None),
        players=PlayersBlock(status="available", data=ratings)
        if has_rating
        else PlayersBlock(status=empty, data=None),
    )
    return records, row.fetched_at if row else None
