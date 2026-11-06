"""League standings and player ranking responses (chat 06, guide §6.4)."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import CompetitionRef, TeamRef
from app.schemas.schedule import SeasonItem

RankingType = Literal["goals", "assists", "yellow", "red", "saves"]
# Relegation wording of the season itself (description), shown for past seasons.
RelegationZone = Literal["relegation", "relegation_playoff"]


class StandingRow(ApiModel):
    rank: int
    team: TeamRef
    played: int | None
    win: int | None
    draw: int | None
    lose: int | None
    goals_for: int | None
    goals_against: int | None
    goals_diff: int | None
    points: int | None
    # Provider letters (W/D/L) in provider order; null = not provided.
    form: str | None
    # Provider description as stored for that season ("Relegation - Championship").
    description: str | None
    zone: RelegationZone | None


class StandingGroup(ApiModel):
    name: str
    rows: list[StandingRow]


class LeagueStandings(ApiModel):
    league: CompetitionRef
    season: SeasonItem
    # Empty = collected but the provider has no table yet (not a failure).
    groups: list[StandingGroup]


class StandingsMeta(ApiModel):
    # Last successful collection of this table.
    updated_at: datetime | None
    # A later refresh failed: the stored table is shown as it was.
    refresh_failed: bool


class StandingsResponse(ApiModel):
    data: LeagueStandings
    meta: StandingsMeta


class StandingsSummaryLeague(ApiModel):
    league: CompetitionRef
    # not_collected: never stored (the other leagues still show).
    status: Literal["available", "not_collected"]
    refresh_failed: bool
    updated_at: datetime | None
    # Top rows of the first group (main page compact table).
    rows: list[StandingRow]


class StandingsSummary(ApiModel):
    season: SeasonItem
    leagues: list[StandingsSummaryLeague]


class StandingsSummaryResponse(ApiModel):
    data: StandingsSummary
    meta: dict[str, object] = Field(default_factory=dict)


class PlayerRef(ApiModel):
    id: int
    name: str
    photo_url: str | None


class PlayerRankItem(ApiModel):
    # Top lists: provider position. Saves: shared rank for equal totals (`tied`).
    rank: int
    tied: bool
    player: PlayerRef
    team: TeamRef | None
    value: int | None
    # Red list only: second-yellow dismissals, kept apart and never added to `value`.
    yellow_red: int | None


class PlayerRankings(ApiModel):
    type: RankingType
    league: CompetitionRef
    season: SeasonItem
    items: list[PlayerRankItem]
    # Saves only: goalkeepers left out because a saves value was missing (never 0).
    excluded: int | None


class PlayerRankingsResponse(ApiModel):
    data: PlayerRankings
    meta: StandingsMeta
