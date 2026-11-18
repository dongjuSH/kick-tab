"""Team detail responses (chat 08, TEAM-001~006, guide §6.4).

Each area has its own endpoint so one failing area never hides the others. Parts of the
overview that may be missing are blocks `{ status: available | not_provided | unavailable,
data }`: not_provided = the provider (or our collection) has nothing for this team,
unavailable = never collected or the lookup failed. Missing values are null, never 0.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import CompetitionRef, MatchSummary, TeamRef
from app.schemas.schedule import SeasonItem
from app.schemas.standings import RecentMatch

PartStatus = Literal["available", "not_provided", "unavailable"]


class TeamSyncMeta(ApiModel):
    # Last successful collection of the area; null = never collected.
    updated_at: datetime | None
    # A later collection failed: the stored data is shown (with a notice).
    refresh_failed: bool


# ---------------------------------------------------------------- overview (TEAM-001)


class TeamStanding(ApiModel):
    rank: int
    points: int | None


class StandingBlock(ApiModel):
    status: PartStatus
    data: TeamStanding | None


class CoachInfo(ApiModel):
    name: str


class CoachBlock(ApiModel):
    status: PartStatus
    data: CoachInfo | None


class VenueInfo(ApiModel):
    name: str | None
    capacity: int | None


class VenueBlock(ApiModel):
    status: PartStatus
    data: VenueInfo | None


class TeamOverview(ApiModel):
    team: TeamRef
    # The team's current five-league competition.
    league: CompetitionRef
    season: SeasonItem
    standing: StandingBlock
    coach: CoachBlock
    venue: VenueBlock
    # Last five finished matches of the supported competitions (stored match list),
    # oldest first: the last one is the latest. The preview reads only these values.
    recent: list[RecentMatch]


class TeamOverviewResponse(ApiModel):
    data: TeamOverview
    meta: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------- fixtures (TEAM-003)


class TeamFixtures(ApiModel):
    # Live first, then the nearest scheduled matches (up to 3), current season.
    upcoming: list[MatchSummary]
    # The last finished matches of the current season, newest first (up to 5).
    recent: list[MatchSummary]


class TeamFixturesMeta(ApiModel):
    updated_at: datetime | None
    # Competitions whose whole-season list was never loaded or last failed.
    failed_competition_ids: list[int]


class TeamFixturesResponse(ApiModel):
    data: TeamFixtures
    meta: TeamFixturesMeta


# ---------------------------------------------------------------- squad (TEAM-002)


class SquadPlayerRef(ApiModel):
    id: int
    name: str
    photo_url: str | None


class SquadTotals(ApiModel):
    """Sum of the player's lines for this team this season in the record competitions
    (five leagues + three UEFA). null when a line lacks the value (never 0); no combined
    rating exists."""

    appearances: int | None
    goals: int | None
    assists: int | None


class SquadCompetitionLine(ApiModel):
    competition: CompetitionRef
    appearances: int | None
    goals: int | None
    assists: int | None
    # The provider's rating of this competition (null = not rated).
    rating: Decimal | None


class SquadPlayer(ApiModel):
    player: SquadPlayerRef
    number: int | None
    # Provider position: Goalkeeper | Defender | Midfielder | Attacker (null = not given).
    position: str | None
    # Provider nationality as given (English country name); null = not provided.
    nationality: str | None
    # The country's flag (null = no flag known or image rights not cleared: text only).
    flag_url: str | None
    # null = no line for this team this season in the record competitions.
    totals: SquadTotals | None
    competitions: list[SquadCompetitionLine]


class TeamSquad(ApiModel):
    season: SeasonItem
    players: list[SquadPlayer]
    # Record competitions the team played this season without collected player lines:
    # the totals are partial ("부분 집계"). Empty = complete.
    missing_competitions: list[CompetitionRef]


class TeamSquadResponse(ApiModel):
    data: TeamSquad
    meta: TeamSyncMeta


# ---------------------------------------------------------------- season stats (TEAM-005)


class HomeAway(ApiModel):
    home: int | None
    away: int | None
    total: int | None


class TeamSeasonRecord(ApiModel):
    wins: HomeAway
    draws: HomeAway
    loses: HomeAway
    goals_for: HomeAway
    goals_against: HomeAway
    clean_sheets: HomeAway
    # The formation used most (provider lineups).
    formation: str | None


class TeamSeasonStats(ApiModel):
    season: SeasonItem
    league: CompetitionRef
    # available = record shown; not_participated = the team did not play this league that
    # season (promoted team); not_provided = no record given — never filled from another season.
    status: Literal["available", "not_provided", "not_participated"]
    record: TeamSeasonRecord | None
    # The league table position of that season (the past season's final standing).
    standing: TeamStanding | None


class TeamSeasonStatsResponse(ApiModel):
    data: TeamSeasonStats
    meta: TeamSyncMeta


# ---------------------------------------------------------------- transfers (TEAM-006)


class TransferCounterpart(ApiModel):
    id: int | None
    name: str | None


class TransferItem(ApiModel):
    transfer_date: date
    player_id: int
    player_name: str
    # Arrivals: the club the player came from. Departures: the club the player went to.
    counterpart: TransferCounterpart
    # Provider type text ("Loan", "Free", "€ 10M"); null = not given.
    type: str | None


class TransferHalf(ApiModel):
    half: Literal["first", "second"]
    # "26-27 전반기"
    label: str
    # "2026년 6~12월"
    period: str
    # not_started = the half has not begun (its tab is disabled).
    state: Literal["open", "not_started"]
    # Shown first (표시 기준 B); every other move is in the "other" lists ("기타 이동").
    arrivals: list[TransferItem]
    departures: list[TransferItem]
    other_arrivals: list[TransferItem]
    other_departures: list[TransferItem]


class TeamTransfers(ApiModel):
    season: SeasonItem
    halves: list[TransferHalf]


class TeamTransfersResponse(ApiModel):
    data: TeamTransfers
    meta: TeamSyncMeta
