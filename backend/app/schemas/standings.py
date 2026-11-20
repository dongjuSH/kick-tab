"""League standings and player ranking responses (chat 06, guide §6.4)."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import CompetitionRef, FinishType, MatchScore, MatchStatus, TeamRef
from app.schemas.schedule import SeasonItem

RankingType = Literal["goals", "assists", "yellow", "red", "saves"]
KnockoutStage = Literal["playoff", "r16", "qf", "sf", "final"]


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


class TeamName(ApiModel):
    id: int
    name_ko: str | None
    name_en: str


class RecentMatch(ApiModel):
    """One finished match of the recent five (LEAG-002 rule 4, TEAM-001 rule 3): the preview
    shows "date · competition" and "home – score – away" without asking the provider.
    Tables use their own stored matches; team detail the team's official matches."""

    fixture_id: int
    kickoff_at: datetime
    kickoff_date_kst: date
    # name_ko of a supported competition, the provider's name for any other official one.
    competition: str
    home: TeamName
    away: TeamName
    goals_home: int
    goals_away: int
    # The row team's result.
    result: Literal["W", "D", "L"]


class TableRow(StandingRow):
    # Up to 5 finished matches of this table, oldest first (the last one is the latest).
    recent: list[RecentMatch]


class StandingGroup(ApiModel):
    name: str
    rows: list[TableRow]


class LeagueStandings(ApiModel):
    league: CompetitionRef
    season: SeasonItem
    # Empty = collected but the provider has no table yet (not a failure).
    groups: list[StandingGroup]
    # Every match of the table is over (league season / UEFA league phase): zones are final
    # results ("강등", "16강 직행") instead of current positions ("강등권", "16강 직행권").
    complete: bool


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


class KnockoutTeamSlot(ApiModel):
    """A known team, or the winner of an undecided previous tie (`winnerOf`: its two teams).
    Both null = no team yet ("상대 미정" when the other side is known)."""

    team: TeamRef | None
    winner_of: list[TeamRef] | None


class KnockoutLeg(ApiModel):
    fixture_id: int
    # 1 / 2 only when every leg of the tie is stored; null when a leg is missing, because a
    # single stored match cannot tell whether it is the first or the second leg.
    leg: int | None
    kickoff_at: datetime
    time_confirmed: bool
    status: MatchStatus
    finish_type: FinishType | None
    home: TeamRef
    away: TeamRef
    score: MatchScore


class KnockoutTie(ApiModel):
    # finished: winner known · live: a leg in play · scheduled: teams or paths known ·
    # undecided: "예정 · 대진 미정".
    state: Literal["finished", "live", "scheduled", "undecided"]
    home: KnockoutTeamSlot
    away: KnockoutTeamSlot
    # Stored legs in kick-off order; fewer than `legsNeeded` means the rest is not stored yet
    # (shown as "일시 미정" without saying which leg is missing).
    legs: list[KnockoutLeg]
    legs_needed: int
    # Totals over the legs for `home` / `away` (finished ties only) and the deciding shoot-out.
    aggregate_home: int | None
    aggregate_away: int | None
    penalty_home: int | None
    penalty_away: int | None
    winner: TeamRef | None


class KnockoutRound(ApiModel):
    league: CompetitionRef
    season: SeasonItem
    stage: KnockoutStage
    ties: list[KnockoutTie]


class KnockoutsResponse(ApiModel):
    data: KnockoutRound
    meta: StandingsMeta
