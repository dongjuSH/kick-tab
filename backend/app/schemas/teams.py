"""Team browse responses (chat 07, guide §6.4)."""

from datetime import datetime

from app.schemas.common import ApiModel
from app.schemas.match import CompetitionRef, TeamRef


class BrowseTeam(ApiModel):
    team: TeamRef
    # The team's current-season five-league competition.
    league: CompetitionRef


class TeamsMeta(ApiModel):
    page: int
    size: int
    total: int
    # Last successful collection of the listed leagues' team lists.
    updated_at: datetime | None


class TeamsResponse(ApiModel):
    data: list[BrowseTeam]
    meta: TeamsMeta
