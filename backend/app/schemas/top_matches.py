from datetime import date

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import MatchSummary


class TopMatchesPeriod(ApiModel):
    start: date
    end: date


class TopMatchItem(ApiModel):
    rank: int = Field(ge=1, le=5)
    match: MatchSummary
    # Member rating aggregate shown in the expanded list (Figma 126:111/126:140).
    # average_rating is null when there are no ratings; never shown as 0 (REV aggregate rule).
    average_rating: float | None = Field(ge=1, le=5)
    rating_count: int = Field(ge=0)


class TopMatches(ApiModel):
    period: TopMatchesPeriod | None
    items: list[TopMatchItem] = Field(max_length=5)
