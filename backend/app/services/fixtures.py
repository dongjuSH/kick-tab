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

# Main schedule period (SCH-002·003, 2026-11-19): match days, not calendar days - the last
# three KST dates before today with a stored match, today when it has one, and the next 17.
PAST_MATCH_DAYS = 3
FUTURE_MATCH_DAYS = 17
# Live sync runs when a match is live or should have started within the lag (kickoff passed
# but the provider has not switched it to live yet). Not before kickoff: `/fixtures?live=`
# lists started matches only, so earlier calls would bring nothing (2026-11-22).
LIVE_LAG = timedelta(hours=3)
# Provider codes of a break in a live match (half time, break before extra time).
LIVE_BREAKS = {"HT": "half_time", "BT": "extra_time"}


@dataclass(frozen=True)
class SchedulePeriod:
    """The common match-day set every main view shares (date bar, team view, filters)."""

    today: date
    dates: tuple[date, ...]

    @property
    def start(self) -> date | None:
        return self.dates[0] if self.dates else None

    @property
    def end(self) -> date | None:
        return self.dates[-1] if self.dates else None

    def bounds(self) -> tuple[date, date]:
        """Calendar range the period spans, always including today (collection, lookups)."""
        return min(self.start or self.today, self.today), max(self.end or self.today, self.today)


def schedule_period(session: Session, today: date | None = None) -> SchedulePeriod:
    """Match days from the stored schedule of every active competition (any season): a day
    counts once however many matches it has; cancelled matches do not make a match day.
    Short announced schedules give fewer days - nothing is invented to fill the count."""
    today = today or kst_today()
    days = (
        select(Fixture.kickoff_date_kst)
        .join(Competition, Competition.id == Fixture.competition_id)
        .where(Competition.active, Fixture.status != "cancelled")
        .distinct()
    )
    past = session.scalars(
        days.where(Fixture.kickoff_date_kst < today)
        .order_by(Fixture.kickoff_date_kst.desc())
        .limit(PAST_MATCH_DAYS)
    ).all()
    ahead = session.scalars(
        days.where(Fixture.kickoff_date_kst >= today)
        .order_by(Fixture.kickoff_date_kst)
        .limit(FUTURE_MATCH_DAYS + 1)
    ).all()
    future = [day for day in ahead if day > today][:FUTURE_MATCH_DAYS]
    return SchedulePeriod(
        today, (*sorted(past), *((today,) if today in ahead else ()), *future)
    )


def _season_rows(session: Session) -> list[CompetitionSeason]:
    """Every managed season row of the active competitions."""
    return list(
        session.scalars(
            select(CompetitionSeason)
            .join(Competition, Competition.id == CompetitionSeason.competition_id)
            .where(
                Competition.active,
                CompetitionSeason.season.between(settings.first_season, settings.current_season),
            )
        )
    )


def overlaps(
    row: CompetitionSeason, start: date, end: date, stored: set[tuple[int, int]] | None = None
) -> bool:
    """The season can have matches in [start, end]. Unknown dates count for the current season,
    and for a past season whose stored matches fall in the range (`stored` = competition and
    season pairs with a stored match there, from `stored_seasons`)."""
    if row.start_date and row.end_date:
        return row.start_date <= end and start <= row.end_date
    if row.season == settings.current_season:
        return True
    return stored is not None and (row.competition_id, row.season) in stored


def stored_seasons(session: Session, start: date, end: date) -> set[tuple[int, int]]:
    """Competition seasons with a stored match on a KST date in [start, end]."""
    return {
        (cid, season)
        for cid, season in session.execute(
            select(Fixture.competition_id, Fixture.season)
            .where(Fixture.kickoff_date_kst.between(start, end))
            .distinct()
        )
    }


def _job_ok(row: CompetitionSeason) -> bool:
    return bool(
        row.fixtures_synced_at
        and (not row.fixtures_failed_at or row.fixtures_failed_at <= row.fixtures_synced_at)
    )


def _season_ok(row: CompetitionSeason) -> bool:
    return bool(
        row.season_fixtures_synced_at
        and (
            not row.season_fixtures_failed_at
            or row.season_fixtures_failed_at <= row.season_fixtures_synced_at
        )
    )


def covered(row: CompetitionSeason, start: date, end: date) -> bool:
    """[start, end] of this competition season is confirmed. The part inside the 30-minute
    schedule job's window needs that job's result (a failed run is not hidden by the daily
    load); any part outside it needs the whole-season load, so a range crossing the window's
    edge needs both. A season without provider data is confirmed."""
    if row.availability == "no_data":
        return True
    ws, we = row.fixtures_window_start, row.fixtures_window_end
    if ws and we and ws <= end and start <= we:
        if not _job_ok(row):
            return False
        if ws <= start and end <= we:
            return True
    return _season_ok(row)


def _parse_kickoff(item: dict[str, Any]) -> datetime | None:
    fixture = item.get("fixture") or {}
    if isinstance(fixture.get("timestamp"), int):
        return datetime.fromtimestamp(fixture["timestamp"], UTC)
    try:
        return datetime.fromisoformat(fixture["date"]).astimezone(UTC)
    except (KeyError, TypeError, ValueError):
        return None


def upsert_fixtures(session: Session, items: Iterable[dict[str, Any]], now: datetime) -> int:
    """Save fixtures and return the count for collection coverage checks."""
    return len(upsert_fixture_items(session, items, now))


def upsert_fixture_items(
    session: Session, items: Iterable[dict[str, Any]], now: datetime
) -> list[dict[str, Any]]:
    """Save provider fixtures and return the exact items accepted for record storage.

    Only rows the provider returned are touched; a missing fixture is never deleted or
    marked finished (LIVE-003). A postponed match keeps its id and moves to the new date.
    A fixture naming the same team on both sides is a broken answer: it is skipped and the
    stored row stays as it was (06 개선, Codex 4차 지적).
    """
    rows: dict[int, dict[str, Any]] = {}
    accepted: dict[int, dict[str, Any]] = {}
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
        if home["id"] == away["id"]:
            logger.warning("fixture %s skipped: team %s on both sides", fixture["id"], home["id"])
            continue
        status = fixture.get("status") or {}
        short = (status.get("short") or "").strip()
        mapped = map_status(short)
        goals = item.get("goals") or {}
        venue = fixture.get("venue") or {}
        accepted[fixture["id"]] = item
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
        return []
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
    return [accepted[fixture_id] for fixture_id in rows]


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
                    & Fixture.kickoff_at.between(now - LIVE_LAG, now),
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
        live_break=LIVE_BREAKS.get(fixture.status_short_raw) if fixture.status == "live" else None,
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
    # With a window: the competitions that can play in it, the set "every one failed" is
    # judged against (Codex 2차 N8: not the whole season's list).
    relevant_competition_ids: tuple[int, ...] = ()

    @property
    def all_failed(self) -> bool:
        """Every competition that can play in the window is unconfirmed."""
        return bool(self.relevant_competition_ids) and set(self.relevant_competition_ids) <= set(
            self.failed_competition_ids
        )

    @property
    def delayed(self) -> bool:
        """The 30-minute schedule job missed about two runs (scheduler or provider down)."""
        return self.checked_at is not None and datetime.now(UTC) - self.checked_at > SYNC_DELAY


# `fixtures` runs every 30 minutes: past this, the stored schedule is shown as delayed.
SYNC_DELAY = timedelta(minutes=75)


def sync_state(
    session: Session, season: int | None = None, *, window: tuple[date, date] | None = None
) -> SyncState:
    """Without `window`: the current season's schedule job (TOP 5 freshness). With a window:
    every managed competition season that can play in it (a period may cross seasons, e.g. a
    super cup of the previous season), failed when its stored rows are not confirmed."""
    if window is not None:
        start, end = window
        stored = stored_seasons(session, start, end)
        seasons = _season_rows(session)
        rows = [
            row for row in seasons
            if row.availability == "available" and overlaps(row, start, end, stored)
        ]
        jobbed = [row for row in rows if row.fixtures_synced_at is not None]
        return SyncState(
            failed_competition_ids=sorted(
                {row.competition_id for row in rows if not covered(row, start, end)}
            ),
            # "Never collected" only before any success: a later failed refresh keeps the
            # stored matches visible with the failure meta (CMP-004).
            # A day outside every season is empty, not uncollected; only that empty
            # relevant set falls back to the managed seasons' collection history.
            never_synced=not any(
                row.fixtures_synced_at or row.season_fixtures_synced_at
                for row in (rows or seasons)
            ),
            checked_at=min((row.fixtures_synced_at for row in jobbed), default=None),
            checked_through=min(
                (row.fixtures_window_end for row in jobbed if row.fixtures_window_end),
                default=None,
            ),
            relevant_competition_ids=tuple(sorted({row.competition_id for row in rows})),
        )
    season = season or settings.current_season
    rows = list(session.scalars(
        select(CompetitionSeason).where(
            CompetitionSeason.season == season,
            CompetitionSeason.availability == "available",
        )
    ))
    # A failed schedule run marks the competition; one the 30-minute job never had to ask
    # (no match in the period, e.g. a super cup months away) relies on the season load.
    failed = [
        row.competition_id
        for row in rows
        if (row.fixtures_failed_at is not None and not _job_ok(row))
        or (row.fixtures_synced_at is None and not _season_ok(row))
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


def fixture_availability(
    session: Session, dates: Sequence[date]
) -> list[tuple[date, list[int], list[int]]]:
    """For each match day: competitions with a stored match, and competitions whose season can
    play that day but is not confirmed (SCH-004: a filter never treats those as empty)."""
    if not dates:
        return []
    rows = [row for row in _season_rows(session) if row.availability == "available"]
    observed: dict[date, set[int]] = {}
    stored: dict[date, set[tuple[int, int]]] = {}
    for day, cid, season in session.execute(
        select(Fixture.kickoff_date_kst, Fixture.competition_id, Fixture.season)
        .join(Competition, Competition.id == Fixture.competition_id)
        .where(Competition.active, Fixture.kickoff_date_kst.in_(dates))
        .distinct()
    ):
        observed.setdefault(day, set()).add(cid)
        stored.setdefault(day, set()).add((cid, season))
    return [
        (
            day,
            sorted(observed.get(day, ())),
            sorted({
                row.competition_id for row in rows
                if overlaps(row, day, day, stored.get(day)) and not covered(row, day, day)
            }),
        )
        for day in dates
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
