"""Team browse (chat 07, LEAG-003): the current season's five-league members.

The list is `team_competition_seasons` of the current season and the five leagues - the
same rows as the team-detail allow set - so past-season and cup/UEFA-only teams never
appear. Membership is known only after that league's team list was collected
(`competition_seasons.teams_synced_at`); otherwise the request fails instead of
answering with a short or empty list. Search uses the shared alias matcher of the main
team search, so an ambiguous alias lists every team it names.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import Competition, CompetitionSeason, Team, TeamCompetitionSeason
from app.seed.competitions import LEAGUE_IDS
from app.services.team_search import match_teams

PAGE_SIZE = 12  # Figma 52:624: four rows of three cards


class MembershipUnknown(Exception):
    """A requested league's current team list was never collected."""


@dataclass(frozen=True)
class BrowseRow:
    team: Team
    league: Competition


@dataclass(frozen=True)
class BrowsePage:
    rows: list[BrowseRow]
    total: int
    updated_at: datetime | None


def browse_teams(
    session: Session, *, league: int | None, query: str | None, page: int
) -> BrowsePage:
    """One page of current members, filtered by league and name (both optional).

    Without a query: league order (Premier League → Ligue 1), then the shown name. With a
    query: best match first (`match_teams`). A page past the end is empty with the total."""
    season = settings.current_season
    leagues = (league,) if league is not None else LEAGUE_IDS
    synced = dict(
        session.execute(
            select(CompetitionSeason.competition_id, CompetitionSeason.teams_synced_at).where(
                CompetitionSeason.season == season,
                CompetitionSeason.competition_id.in_(leagues),
            )
        ).all()
    )
    if any(synced.get(league_id) is None for league_id in leagues):
        raise MembershipUnknown

    competitions = {
        c.id: c for c in session.scalars(select(Competition).where(Competition.id.in_(leagues)))
    }
    members = session.execute(
        select(Team, TeamCompetitionSeason.competition_id)
        .join(TeamCompetitionSeason, TeamCompetitionSeason.team_id == Team.id)
        .where(
            TeamCompetitionSeason.season == season,
            TeamCompetitionSeason.competition_id.in_(leagues),
        )
    ).all()
    position = {league_id: index for index, league_id in enumerate(LEAGUE_IDS)}
    league_of: dict[int, int] = {}
    teams: dict[int, Team] = {}
    for team, league_id in members:
        # A team listed twice keeps its first league in the league order.
        if team.id not in league_of or position[league_id] < position[league_of[team.id]]:
            league_of[team.id] = league_id
        teams[team.id] = team

    if query is not None:
        ordered = match_teams(session, query, teams)
    else:
        ordered = sorted(
            teams,
            key=lambda i: (position[league_of[i]], teams[i].name_ko or teams[i].name_en),
        )
    start = (page - 1) * PAGE_SIZE
    rows = [
        BrowseRow(teams[i], competitions[league_of[i]]) for i in ordered[start : start + PAGE_SIZE]
    ]
    return BrowsePage(rows=rows, total=len(ordered), updated_at=max(synced.values()))
