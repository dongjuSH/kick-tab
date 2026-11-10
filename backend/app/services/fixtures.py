"""Fixture storage and read model (SCH-002, LIVE-001~004, FAV-004)."""

import logging
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

logger = logging.getLogger(__name__)

# Inclusive dates for the main schedule, team view and fixture collector.
WINDOW_BEFORE_DAYS = 3
WINDOW_AFTER_DAYS = 17
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
    """Save provider fixtures of supported competitions. Returns the number saved; callers
    compare it with the items they passed to notice a partly stored answer.

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

    # A team new to the DB can be stored only with the provider's name: a fixture naming such
    # a team without one is left out (names are never invented) instead of failing the batch.
    named = {t["id"] for t in teams if t.get("id") and t.get("name")}
    unnamed = {tid for r in rows.values() for tid in (r["home_team_id"], r["away_team_id"])}
    unnamed -= named
    if unnamed:
        unknown = unnamed - set(session.scalars(select(Team.id).where(Team.id.in_(unnamed))))
        if unknown:
            dropped = sorted(
                fid for fid, r in rows.items()
                if r["home_team_id"] in unknown or r["away_team_id"] in unknown
            )
            for fid in dropped:
                del rows[fid]
            participation = [p for p in participation if p[0] not in unknown]
            logger.warning(
                "fixtures skipped, new teams without a name %s: %s", sorted(unknown), dropped
            )

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
    # Oldest last-success time among the competitions and the end of the range every
    # competition has confirmed: the "last normal check" shown while collection lags.
    checked_at: datetime | None = None
    checked_through: date | None = None

    @property
    def delayed(self) -> bool:
        """The 30-minute schedule job missed about two runs (scheduler or provider down)."""
        return self.checked_at is not None and datetime.now(UTC) - self.checked_at > SYNC_DELAY


# `fixtures` runs every 30 minutes: past this, the stored schedule is shown as delayed.
SYNC_DELAY = timedelta(minutes=75)


def sync_state(
    session: Session, season: int | None = None, *, window: tuple[date, date] | None = None
) -> SyncState:
    season = season or settings.current_season
    rows = session.execute(
        select(
            CompetitionSeason.competition_id,
            CompetitionSeason.fixtures_synced_at,
            CompetitionSeason.fixtures_failed_at,
            CompetitionSeason.fixtures_window_start,
            CompetitionSeason.fixtures_window_end,
        ).where(
            CompetitionSeason.season == season,
            CompetitionSeason.availability == "available",
        )
    ).all()
    failed = [
        cid
        for cid, ok_at, failed_at, start, end in rows
        if ok_at is None or (failed_at is not None and failed_at > ok_at)
        or (window is not None and not (start and end and start <= window[0] <= window[1] <= end))
    ]
    synced = [row for row in rows if row.fixtures_synced_at is not None]
    return SyncState(
        failed_competition_ids=sorted(failed),
        never_synced=not synced,
        checked_at=min((row.fixtures_synced_at for row in synced), default=None),
        checked_through=min(
            (row.fixtures_window_end for row in synced if row.fixtures_window_end), default=None
        ),
    )


def fixtures_on(session: Session, day: date) -> tuple[list[MatchSummary], datetime | None]:
    rows = _summaries(session, [Fixture.kickoff_date_kst == day])
    updated = max((f.synced_at for f, _ in rows), default=None)
    return [s for _, s in rows], updated


def team_schedule_window(today: date | None = None) -> tuple[date, date]:
    return collection_window(today)


def fixture_availability(
    session: Session, start: date, end: date
) -> list[tuple[date, list[int], list[int]]]:
    """For each date, stored matches and competitions without complete coverage."""
    sources = session.execute(
        select(Competition.id, CompetitionSeason)
        .outerjoin(
            CompetitionSeason,
            (CompetitionSeason.competition_id == Competition.id)
            & (CompetitionSeason.season == settings.current_season),
        )
        .where(Competition.active)
    ).all()
    observed: dict[date, set[int]] = {}
    for day, cid in session.execute(
        select(Fixture.kickoff_date_kst, Fixture.competition_id)
        .join(Competition, Competition.id == Fixture.competition_id)
        .where(Competition.active, Fixture.kickoff_date_kst.between(start, end))
        .distinct()
    ):
        observed.setdefault(day, set()).add(cid)

    def covered(source: CompetitionSeason | None, day: date) -> bool:
        if source is None:
            return False
        if source.availability == "no_data":
            return True  # the provider has no supported season for this competition
        return bool(
            source.fixtures_synced_at
            and (not source.fixtures_failed_at
                 or source.fixtures_failed_at <= source.fixtures_synced_at)
            and source.fixtures_window_start
            and source.fixtures_window_end
            and source.fixtures_window_start <= day <= source.fixtures_window_end
        )

    days = (start + timedelta(days=i) for i in range((end - start).days + 1))
    return [
        (
            day,
            sorted(observed.get(day, ())),
            sorted(cid for cid, row in sources if not covered(row, day)),
        )
        for day in days
    ]


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
