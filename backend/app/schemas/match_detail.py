"""Match detail responses (chat 04, MAT-001~005, REV-004).

Provider blocks that may be missing per match are wrapped as
`{ status: available | not_provided | not_yet | unavailable, data }` (guide §6.4):
not_yet = not published yet (lineups before the announcement), not_provided = the provider
has nothing for this match, unavailable = the lookup failed. Missing values are null.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.match import MatchSummary

BlockStatus = Literal["available", "not_provided", "not_yet", "unavailable"]
Side = Literal["home", "away"]


class MatchInfo(ApiModel):
    match: MatchSummary
    round: str | None
    season_label: str
    # Provider wording and code, shown for rulings (e.g. "Technical loss" / AWD).
    status_long: str | None
    status_code: str
    # Match reviews are open (read publicly; members may write, chat 02) from kickoff to a
    # normal finish on the same match id (REV-001, `review_open`). Closed before kickoff,
    # for postponed/cancelled/abandoned matches and rulings (AWD/WO).
    reviews_available: bool
    # MAT-005: head-to-head and recent form only before kickoff (scheduled/postponed).
    head_to_head_available: bool


class UpdatedMeta(ApiModel):
    updated_at: datetime | None


class MatchInfoResponse(ApiModel):
    data: MatchInfo
    # updatedAt: last provider confirmation of the match (schedule or live sync).
    meta: UpdatedMeta


class MatchEvent(ApiModel):
    elapsed: int | None
    extra: int | None
    side: Side | None
    type: Literal["goal", "card", "subst", "var", "other"]
    # Provider detail, e.g. "Normal Goal", "Own Goal", "Yellow Card", "Goal cancelled".
    detail: str | None
    # Goal/card: the player. Substitution: the player going off.
    player: str | None
    # Goal: the assist. Substitution: the player coming on.
    assist: str | None


class EventsBlock(ApiModel):
    status: BlockStatus
    data: list[MatchEvent] | None


class StatRow(ApiModel):
    # Provider statistic type, e.g. "Ball Possession", "Total Shots".
    key: str
    home: float | None
    away: float | None
    percent: bool


class StatisticsBlock(ApiModel):
    status: BlockStatus
    data: list[StatRow] | None


class LineupPlayer(ApiModel):
    number: int | None
    name: str
    # Provider position letter: G, D, M, F.
    position: str | None


class TeamLineup(ApiModel):
    side: Side
    formation: str | None
    coach: str | None
    start_xi: list[LineupPlayer]
    substitutes: list[LineupPlayer]


class LineupsBlock(ApiModel):
    status: BlockStatus
    data: list[TeamLineup] | None


class PlayerRating(ApiModel):
    player_id: int | None
    name: str
    photo_url: str | None
    side: Side
    # Provider match rating (not a member rating); null when not provided.
    rating: float | None


class PlayersBlock(ApiModel):
    status: BlockStatus
    data: list[PlayerRating] | None


class MatchRecords(ApiModel):
    events: EventsBlock
    statistics: StatisticsBlock
    lineups: LineupsBlock
    players: PlayersBlock


class MatchRecordsResponse(ApiModel):
    data: MatchRecords
    # updatedAt: last successful provider fetch of the detail blocks (null = never).
    meta: UpdatedMeta


class PastMeeting(ApiModel):
    kickoff_date_kst: date
    competition: str
    home_name: str
    away_name: str
    # True when this meeting's home team is the current match's home team.
    home_is_current_home: bool
    score_home: int | None
    score_away: int | None
    penalty_home: int | None
    penalty_away: int | None


class MeetingSummary(ApiModel):
    # From the current match's point of view.
    home_wins: int
    draws: int
    away_wins: int


class MeetingsBlock(ApiModel):
    status: BlockStatus
    data: list[PastMeeting] | None = Field(max_length=5)
    summary: MeetingSummary | None


class FormMatch(ApiModel):
    kickoff_date_kst: date
    competition: str
    opponent_name: str
    venue: Side
    goals_for: int | None
    goals_against: int | None
    result: Literal["W", "D", "L"]


class FormBlock(ApiModel):
    status: BlockStatus
    data: list[FormMatch] | None = Field(max_length=5)


class HeadToHead(ApiModel):
    meetings: MeetingsBlock
    home_form: FormBlock
    away_form: FormBlock


class HeadToHeadResponse(ApiModel):
    data: HeadToHead
    meta: UpdatedMeta


class ReviewItem(ApiModel):
    id: int
    # Filled from `users` by chat 02 (null until members exist).
    author_nickname: str | None
    # Text review: 1-300 characters, no star rating (REV, 04 개선).
    body: str
    likes: int
    dislikes: int
    created_at: datetime
    updated_at: datetime


class ReviewSummary(ApiModel):
    # Valid reviews of the match (one per member). No average is computed (REV-004).
    count: int


class ReviewList(ApiModel):
    summary: ReviewSummary
    items: list[ReviewItem]


class ReviewListResponse(ApiModel):
    data: ReviewList
    meta: dict[str, object] = Field(default_factory=dict)
