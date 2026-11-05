from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import MatchSummary

# Public TOP 5 UI (TOP 5 policy 2026-11-02 in the planning docs): the selected list,
# "no supported matches" or the delay notice. Job states (selecting, first failure,
# retry) are never sent: during them the previous week's public result is served as it was.
TopMatchesView = Literal["list", "none", "delayed"]


class TopMatchesWeek(ApiModel):
    """KST Monday–Sunday."""

    start: date
    end: date


class TopMatchItem(ApiModel):
    # rank, match id and reason are fixed for the week; match carries the latest
    # kickoff/status/score.
    rank: int = Field(ge=1, le=5)
    reason: str
    # Kickoff when the match was selected; differs from match.kickoffAt after a change.
    selected_kickoff_at: datetime
    match: MatchSummary


class TopMatches(ApiModel):
    # Public version: changes whenever the shown result is replaced (new week's list or
    # "none", the delay notice, a manual recovery). null = nothing was ever published.
    version: int | None
    view: TopMatchesView
    # The week the shown result belongs to (for "delayed": the week being prepared).
    week: TopMatchesWeek
    # The current KST week; `week` before it means last week's result is kept.
    current_week: TopMatchesWeek
    selected_at: datetime | None
    items: list[TopMatchItem] = Field(max_length=5)


class TopMatchesMeta(ApiModel):
    # Latest provider confirmation among the listed matches.
    updated_at: datetime | None


class TopMatchesResponse(ApiModel):
    data: TopMatches
    meta: TopMatchesMeta


class TopMatchesVersion(ApiModel):
    """Cheap check for open screens: refetch the list when either value changes."""

    version: int | None
    current_week_start: date


class TopMatchesVersionResponse(ApiModel):
    data: TopMatchesVersion
    meta: dict[str, object] = Field(default_factory=dict)
