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
    # Every managed season (2025 .. current) known for this competition, newest first.
    # Past results and standings offer a competition only where it is `available`.
    seasons: list[CompetitionSeasonInfo]


class SeasonItem(ApiModel):
    """A season the service offers (season dropdown, HIST-002 / LEAG)."""

    season: int
    label: str
    current: bool


class SeasonsResponse(ApiModel):
    data: list[SeasonItem]
    meta: dict[str, object] = Field(default_factory=dict)


class CompetitionsResponse(ApiModel):
    data: list[CompetitionItem]
    meta: dict[str, object] = Field(default_factory=dict)


class ScheduleMeta(ApiModel):
    # Latest provider confirmation among the listed matches (live sync every minute).
    updated_at: datetime | None
    # Competitions whose last schedule sync failed: their matches may be missing or stale.
    failed_competition_ids: list[int]
    # Last time every competition's schedule was confirmed and the last date all of them
    # cover; `delayed` once the 30-minute collection has missed about two runs.
    checked_at: datetime | None = None
    checked_through: date | None = None
    delayed: bool = False


class FixturesResponse(ApiModel):
    data: list[MatchSummary]
    meta: ScheduleMeta


class FixtureDateAvailability(ApiModel):
    date: date
    competition_ids: list[int]
    unknown_competition_ids: list[int]


class FixtureAvailability(ApiModel):
    start: date
    end: date
    dates: list[FixtureDateAvailability]


class FixtureAvailabilityResponse(ApiModel):
    data: FixtureAvailability
    meta: dict[str, object] = Field(default_factory=dict)


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
    # Inclusive KST dates: today-3 .. today+17.
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
    total: int
    no_new: bool = False
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


class ResultsPage(ApiModel):
    """Past results of one season (chat 05): the resolved season, the selected team (null
    without a team filter) and one page of finished matches, newest first."""

    season: SeasonItem
    team: TeamRef | None
    matches: list[MatchSummary]


class ResultsMeta(ApiModel):
    page: int
    size: int
    total: int
    updated_at: datetime | None
    # Available competitions whose whole-season list was never loaded or last failed: their
    # results may be missing, so "no results" is never claimed for them.
    failed_competition_ids: list[int]


class ResultsResponse(ApiModel):
    data: ResultsPage
    meta: ResultsMeta
