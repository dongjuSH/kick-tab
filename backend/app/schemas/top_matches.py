from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import MatchSummary

# Weekly AI selection state (docs/TOP5_POLICY_2026-11-01.md, guide §6.4). Failures and
# "still selecting" are never reported as an empty ready week.
TopMatchesState = Literal["ready", "pending", "no_candidates", "source_error", "ai_error"]


class TopMatchesWeek(ApiModel):
    """KST Monday–Sunday the selection belongs to (the week key)."""

    start: date
    end: date


class TopMatchItem(ApiModel):
    # rank, match id and reason are fixed for the week; match carries the latest
    # kickoff/status/score.
    rank: int = Field(ge=1, le=5)
    reason: str
    match: MatchSummary


class TopMatches(ApiModel):
    week: TopMatchesWeek
    state: TopMatchesState
    selected_at: datetime | None
    items: list[TopMatchItem] = Field(max_length=5)
