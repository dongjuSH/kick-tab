"""Main schedule responses (chat 03): competitions, fixtures by date, favourite teams, team
search and news. Typed meta objects so the front end gets generated types (guide §6.4)."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import MatchSummary, TeamRef

CompetitionGroup = Literal["EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEFA"]
NewsBadge = CompetitionGroup


class CompetitionSeasonInfo(ApiModel):
    season: int
    label: str
    # no_data: the provider has no data for this season (CMP-004, V-16).
    availability: Literal["available", "no_data"]


class CompetitionItem(ApiModel):
    id: int
    name_ko: str | None
    short_name: str
    group: CompetitionGroup
    current_season: CompetitionSeasonInfo | None


class CompetitionsResponse(ApiModel):
    data: list[CompetitionItem]
    meta: dict[str, object] = Field(default_factory=dict)


class ScheduleMeta(ApiModel):
    # Latest provider confirmation among the listed matches (live sync every minute).
    updated_at: datetime | None
    # Competitions whose last schedule sync failed: their matches may be missing or stale.
    failed_competition_ids: list[int]


class FixturesResponse(ApiModel):
    data: list[MatchSummary]
    meta: ScheduleMeta


class FavoriteSchedule(ApiModel):
    # Requested teams known to the service, in request order (favourite buttons).
    teams: list[TeamRef]
    # Live first, then the nearest upcoming match per team; a shared match appears once.
    matches: list[MatchSummary]


class FavoriteScheduleResponse(ApiModel):
    data: FavoriteSchedule
    meta: ScheduleMeta


class TeamSchedule(ApiModel):
    team: TeamRef
    # Inclusive KST dates of the view: today .. today+13.
    start: date
    end: date
    matches: list[MatchSummary]


class TeamScheduleResponse(ApiModel):
    data: TeamSchedule
    meta: ScheduleMeta


class TeamSearchResponse(ApiModel):
    data: list[TeamRef]
    meta: dict[str, object] = Field(default_factory=dict)


class NewsItem(ApiModel):
    id: int
    badge: NewsBadge | None
    title: str
    description: str | None
    url: str
    # Host of the original link. Not a verified press name (NEWS-001).
    source_domain: str
    published_at: datetime


class NewsMeta(ApiModel):
    next_cursor: str | None
    # Last successful collection; null when news was never collected.
    updated_at: datetime | None
    # The latest collection failed: older stored articles are shown.
    stale: bool


class NewsResponse(ApiModel):
    data: list[NewsItem]
    meta: NewsMeta


class NewsLink(ApiModel):
    url: str
    # gone = the original answered 404/410; unknown = could not confirm (not "deleted").
    status: Literal["reachable", "gone", "unknown"]


class NewsLinkResponse(ApiModel):
    data: NewsLink
    meta: dict[str, object] = Field(default_factory=dict)
