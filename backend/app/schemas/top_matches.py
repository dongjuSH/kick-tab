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


class TopMatches(ApiModel):
    period: TopMatchesPeriod | None
    items: list[TopMatchItem] = Field(max_length=5)
