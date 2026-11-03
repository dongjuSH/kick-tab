"""Fixture storage and read model (SCH-002, LIVE-001~004, FAV-004)."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.core.kst import kst_date, kst_today
from app.models.fixture import Fixture
from app.models.reference import Competition, CompetitionSeason, Team
from app.schemas.match import MatchScore, MatchSummary
from app.seed.competitions import COMPETITION_IDS
from app.services.match_status import map_status
from app.services.reference import (
    DetailLookup,
    add_participation,
    competition_ref,
    team_detail_lookup,
    team_ref,
    upsert_teams,
)

# Collection window around today (KST): yesterday for late results, then about two weeks
# (guide §6.5). The schedule screen shows today..today+13.
WINDOW_BEFORE_DAYS = 1
WINDOW_AFTER_DAYS = 15
# Live sync runs when a match is live, starts within this lead time, or should have started
# within the lag (kickoff passed but the provider has not switched it to live yet).
LIVE_LEAD = timedelta(minutes=30)
LIVE_LAG = timedelta(hours=3)


def collection_window(today: date | None = None) -> tuple[date, date]:
    today = today or kst_today()
    return today - timedelta(days=WINDOW_BEFORE_DAYS), today + timedelta(days=WINDOW_AFTER_DAYS)


def _parse_kickoff(item: dict[str, Any]) -> datetime | None:
    fixture = item.get("fixture") or {}
    if isinstance(fixture.get("timestamp"), int):
        return datetime.fromtimestamp(fixture["timestamp"], UTC)
    try:
        return datetime.fromisoformat(fixture["date"]).astimezone(UTC)
    except (KeyError, TypeError, ValueError):
        return None


def upsert_fixtures(session: Session, items: Iterable[dict[str, Any]], now: datetime) -> int:
    """Save provider fixtures of supported competitions. Returns the number saved.

    Only rows the provider returned are touched; a missing fixture is never deleted or
    marked finished (LIVE-003). A postponed match keeps its id and moves to the new date.
    """
    rows: dict[int, dict[str, Any]] = {}
    teams: list[dict[str, Any]] = []
    participation: list[tuple[int, int, int]] = []
    for item in items:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        home = (item.get("teams") or {}).get("home") or {}
        away = (item.get("teams") or {}).get("away") or {}
        kickoff = _parse_kickoff(item)
        if (
            not fixture.get("id")
            or league.get("id") not in COMPETITION_IDS
            or not home.get("id")
            or not away.get("id")
            or kickoff is None
        ):
            continue
        status = fixture.get("status") or {}
        short = (status.get("short") or "").strip()
        mapped = map_status(short)
        goals = item.get("goals") or {}
        venue = fixture.get("venue") or {}
        rows[fixture["id"]] = (
            {
                "id": fixture["id"],
                "competition_id": league["id"],
                "season": league.get("season") or settings.current_season,
                "round": league.get("round"),
                "kickoff_at": kickoff,
                "kickoff_date_kst": kst_date(kickoff),
                "status": mapped.status,
                "finish_type": mapped.finish_type,
                "status_short_raw": short or "?",
                "status_long_raw": status.get("long"),
                "elapsed": status.get("elapsed"),
                "home_team_id": home["id"],
                "away_team_id": away["id"],
                "goals_home": goals.get("home"),
                "goals_away": goals.get("away"),
                "score": item.get("score"),
                "venue_name": venue.get("name"),
                "venue_city": venue.get("city"),
                "synced_at": now,
            }
        )
        teams += [home, away]
        season = league.get("season") or settings.current_season
        participation += [(home["id"], league["id"], season), (away["id"], league["id"], season)]

    if not rows:
        return 0
    upsert_teams(session, teams, now)
    add_participation(session, participation)
    values = list(rows.values())
    stmt = insert(Fixture).values(values)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[Fixture.id],
            set_={c: getattr(stmt.excluded, c) for c in values[0] if c != "id"},
        )
    )
    return len(rows)


def live_targets(session: Session, now: datetime) -> list[int]:
    """Fixtures to re-check by id: live ones and those whose kickoff passed recently."""
    return list(
        session.scalars(
            select(Fixture.id).where(
                or_(
                    Fixture.status == "live",
                    Fixture.status.in_(("scheduled", "unknown"))
                    & Fixture.kickoff_at.between(now - LIVE_LAG, now),
                )
            )
        )
    )


def needs_live_sync(session: Session, now: datetime) -> bool:
    return bool(
        session.scalar(
            select(Fixture.id)
            .where(
                or_(
                    Fixture.status == "live",
                    Fixture.status.in_(("scheduled", "unknown"))
                    & Fixture.kickoff_at.between(now - LIVE_LAG, now + LIVE_LEAD),
                )
            )
            .limit(1)
        )
    )


# ---- read side ------------------------------------------------------------------------


def _score(fixture: Fixture) -> MatchScore:
    penalty = (fixture.score or {}).get("penalty") or {}
    if fixture.status in ("scheduled", "postponed", "cancelled"):
        # No result exists yet (or ever): the provider's 0-0 placeholder is not a score.
        return MatchScore(home=None, away=None, penalty_home=None, penalty_away=None)
    return MatchScore(
        home=fixture.goals_home,
        away=fixture.goals_away,
        penalty_home=penalty.get("home") if fixture.finish_type == "pen" else None,
        penalty_away=penalty.get("away") if fixture.finish_type == "pen" else None,
    )


def to_summary(
    fixture: Fixture, competition: Competition, home: Team, away: Team, lookup: DetailLookup
) -> MatchSummary:
    return MatchSummary(
        id=fixture.id,
        competition=competition_ref(competition),
        kickoff_at=fixture.kickoff_at,
        kickoff_date_kst=fixture.kickoff_date_kst,
        time_confirmed=map_status(fixture.status_short_raw).time_confirmed,
        status=fixture.status,
        finish_type=fixture.finish_type,
        elapsed=fixture.elapsed if fixture.status == "live" else None,
        status_reason=fixture.status_reason,
        home=team_ref(home, lookup),
        away=team_ref(away, lookup),
        score=_score(fixture),
    )


def _summaries(session: Session, where: Sequence[Any]) -> list[tuple[Fixture, MatchSummary]]:
    home, away = aliased(Team), aliased(Team)
    rows = session.execute(
        select(Fixture, Competition, home, away)
        .join(Competition, Competition.id == Fixture.competition_id)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(Competition.active, *where)
        .order_by(Fixture.kickoff_at, Competition.sort_order, Fixture.id)
    ).all()
    lookup = team_detail_lookup(session)
    return [(f, to_summary(f, c, h, a, lookup)) for f, c, h, a in rows]


def summaries_by_ids(
    session: Session, fixture_ids: Sequence[int]
) -> tuple[dict[int, MatchSummary], datetime | None]:
    """Latest summaries of given matches (TOP 5 items) and their last provider sync."""
    if not fixture_ids:
        return {}, None
    rows = _summaries(session, [Fixture.id.in_(fixture_ids)])
    updated = max((f.synced_at for f, _ in rows), default=None)
    return {f.id: s for f, s in rows}, updated


@dataclass(frozen=True)
class SyncState:
    """Freshness of the stored schedule, so 'no matches' and 'not collected' differ."""

    failed_competition_ids: list[int]
    never_synced: bool


def sync_state(session: Session, season: int | None = None) -> SyncState:
    season = season or settings.current_season
    rows = session.execute(
        select(
            CompetitionSeason.competition_id,
            CompetitionSeason.fixtures_synced_at,
            CompetitionSeason.fixtures_failed_at,
        ).where(
            CompetitionSeason.season == season,
            CompetitionSeason.availability == "available",
        )
    ).all()
    failed = [
        cid
        for cid, ok_at, failed_at in rows
        if ok_at is None or (failed_at is not None and failed_at > ok_at)
    ]
    return SyncState(
        failed_competition_ids=sorted(failed),
        never_synced=not rows or all(ok_at is None for _, ok_at, _ in rows),
    )


def fixtures_on(session: Session, day: date) -> tuple[list[MatchSummary], datetime | None]:
    rows = _summaries(session, [Fixture.kickoff_date_kst == day])
    updated = max((f.synced_at for f, _ in rows), default=None)
    return [s for _, s in rows], updated


# Team view of the main schedule: today .. today+13 KST (SCHEDULE_UX_POLICY 2026-11-02).
TEAM_SCHEDULE_DAYS = 14


def team_schedule_window(today: date | None = None) -> tuple[date, date]:
    today = today or kst_today()
    return today, today + timedelta(days=TEAM_SCHEDULE_DAYS - 1)


def team_schedule(
    session: Session, team_id: int, start: date, end: date
) -> tuple[Team | None, list[MatchSummary], datetime | None]:
    """Every stored match of one team in [start, end] (KST dates), by kickoff. Only the
    collected schedule is read: no provider request per date or per team."""
    team = session.get(Team, team_id)
    if team is None:
        return None, [], None
    rows = _summaries(
        session,
        [
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
            Fixture.kickoff_date_kst.between(start, end),
        ],
    )
    updated = max((f.synced_at for f, _ in rows), default=None)
    return team, [s for _, s in rows], updated


def next_for_teams(
    session: Session, team_ids: Sequence[int], now: datetime
) -> tuple[list[Team], list[MatchSummary], datetime | None]:
    """FAV-004: per team the live match, else the nearest upcoming one; live first, then
    by kickoff; a match between two favourites appears once. Uses stored fixtures only."""
    teams = {t.id: t for t in session.scalars(select(Team).where(Team.id.in_(team_ids)))}
    rows = _summaries(
        session,
        [
            or_(Fixture.home_team_id.in_(team_ids), Fixture.away_team_id.in_(team_ids)),
            or_(
                Fixture.status == "live",
                (Fixture.status == "scheduled") & (Fixture.kickoff_at >= now - LIVE_LAG),
            ),
        ],
    )
    chosen: dict[int, tuple[Fixture, MatchSummary]] = {}
    for team_id in team_ids:
        mine = [r for r in rows if team_id in (r[0].home_team_id, r[0].away_team_id)]
        live = [r for r in mine if r[0].status == "live"]
        pick = (live or mine or [None])[0]
        if pick is not None:
            chosen[pick[0].id] = pick
    ordered = sorted(
        chosen.values(), key=lambda r: (r[0].status != "live", r[0].kickoff_at, r[0].id)
    )
    updated = max((f.synced_at for f, _ in ordered), default=None)
    return [teams[i] for i in team_ids if i in teams], [s for _, s in ordered], updated
