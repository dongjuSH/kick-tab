"""Shared match shapes (guide §6.4). Chat 01 defines them; chat 03 fills them with data."""

from datetime import date, datetime
from typing import Literal

from app.schemas.common import ApiModel

MatchStatus = Literal[
    "scheduled", "live", "finished", "postponed", "cancelled", "abandoned", "unknown"
]
FinishType = Literal["normal", "aet", "pen", "awarded", "walkover"]


class TeamRef(ApiModel):
    id: int
    name_ko: str | None
    name_en: str
    crest_url: str | None
    # null = membership unknown (loading/failed); never shown as relegation (D-15).
    detail_available: bool | None


class CompetitionRef(ApiModel):
    id: int
    name_ko: str | None
    short_name: str


class MatchScore(ApiModel):
    home: int | None
    away: int | None
    penalty_home: int | None
    penalty_away: int | None


class MatchSummary(ApiModel):
    """Used by match cards, TOP 5 and team fixture lists."""

    id: int
    competition: CompetitionRef
    kickoff_at: datetime
    kickoff_date_kst: date
    time_confirmed: bool
    status: MatchStatus
    finish_type: FinishType | None
    elapsed: int | None
    status_reason: str | None
    home: TeamRef
    away: TeamRef
    score: MatchScore
