"""Past results (chat 05, HIST-001~003, CMP-003·004): finished matches of one whole season.

Only `finished` matches are listed: normal results and rulings (finishType awarded /
walkover) alike, newest first. Scheduled, live, postponed, cancelled and abandoned matches
never appear. No date filter and no 21-day window apply (HIST-002). Team-detail links use
the current-season allow set, so a past team is listed but marked `detailAvailable: false`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.models.fixture import Fixture
from app.models.reference import Competition, CompetitionSeason, Team
from app.schemas.match import MatchSummary
from app.schemas.schedule import SeasonItem
from app.seed.competitions import season_label
from app.services.fixtures import to_summary
from app.services.reference import managed_seasons, team_detail_lookup

PAGE_SIZE = 10


def season_item(season: int) -> SeasonItem:
    return SeasonItem(
        season=season, label=season_label(season), current=season == settings.current_season
    )


def supported_seasons(session: Session) -> list[SeasonItem]:
    """Managed seasons with at least one competition the provider has data for, newest
    first. A season never shows up as another one (HIST-002)."""
    seasons = set(
        session.scalars(
            select(CompetitionSeason.season)
            .join(Competition, Competition.id == CompetitionSeason.competition_id)
            .where(
                Competition.active,
                CompetitionSeason.availability == "available",
                CompetitionSeason.season.in_(managed_seasons()),
            )
            .distinct()
        )
    )
    return [season_item(s) for s in sorted(seasons, reverse=True)]


@dataclass(frozen=True)
class SeasonCoverage:
    """Which available competitions of a season have a usable whole-season list."""

    available_ids: list[int]
    # Results may be missing: never loaded, or the last load failed (or stored only part of
    # the answer) after the last success. Stored rows of a failed refresh are still shown.
    failed_ids: list[int]
    # Never loaded successfully: nothing confirmed to show yet ("not collected").
    never_loaded_ids: list[int]

    def loaded_any(self, scope: Sequence[int]) -> bool:
        return any(cid not in self.never_loaded_ids for cid in scope)


def season_coverage(session: Session, season: int) -> SeasonCoverage:
    rows = session.execute(
        select(
            CompetitionSeason.competition_id,
            CompetitionSeason.season_fixtures_synced_at,
            CompetitionSeason.season_fixtures_failed_at,
        )
        .join(Competition, Competition.id == CompetitionSeason.competition_id)
        .where(
            Competition.active,
            CompetitionSeason.season == season,
            CompetitionSeason.availability == "available",
        )
        .order_by(Competition.sort_order)
    ).all()
    failed = [
        cid for cid, ok_at, failed_at in rows
        if ok_at is None or (failed_at is not None and failed_at > ok_at)
    ]
    return SeasonCoverage(
        available_ids=[r[0] for r in rows],
        failed_ids=failed,
        never_loaded_ids=[cid for cid, ok_at, _ in rows if ok_at is None],
    )


def finished_results(
    session: Session,
    season: int,
    *,
    competition_ids: Sequence[int] = (),
    team_id: int | None = None,
    page: int = 1,
    size: int = PAGE_SIZE,
) -> tuple[list[MatchSummary], int, datetime | None]:
    """One page of finished matches (newest first) and the total for the conditions."""
    where = [Competition.active, Fixture.season == season, Fixture.status == "finished"]
    if competition_ids:
        where.append(Fixture.competition_id.in_(competition_ids))
    if team_id is not None:
        where.append(or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id))

    total = session.scalar(
        select(func.count())
        .select_from(Fixture)
        .join(Competition, Competition.id == Fixture.competition_id)
        .where(*where)
    ) or 0
    home, away = aliased(Team), aliased(Team)
    rows = session.execute(
        select(Fixture, Competition, home, away)
        .join(Competition, Competition.id == Fixture.competition_id)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(*where)
        .order_by(Fixture.kickoff_at.desc(), Competition.sort_order, Fixture.id.desc())
        .limit(size)
        .offset((page - 1) * size)
    ).all()
    lookup = team_detail_lookup(session)
    updated = max((f.synced_at for f, *_ in rows), default=None)
    return [to_summary(f, c, h, a, lookup) for f, c, h, a in rows], total, updated
