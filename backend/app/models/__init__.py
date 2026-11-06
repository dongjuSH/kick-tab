"""ORM models. Import every model here so Alembic sees the full metadata."""

from app.models.feedback import Feedback
from app.models.fixture import Fixture
from app.models.match_detail import FixtureDetail, FixtureEvent, HeadToHead, TeamForm
from app.models.news import NewsArticle, NewsArticleTeam
from app.models.reference import (
    Competition,
    CompetitionSeason,
    Team,
    TeamAlias,
    TeamCompetitionSeason,
)
from app.models.review import Review, ReviewReaction
from app.models.standings import (
    LeagueSync,
    Player,
    PlayerRanking,
    PlayerSeasonStat,
    Standing,
)
from app.models.sync_run import SyncRun
from app.models.top_matches import Top5Attempt, Top5Publication, Top5Week, WeeklyTopMatch

__all__ = [
    "Competition",
    "CompetitionSeason",
    "Feedback",
    "Fixture",
    "FixtureDetail",
    "FixtureEvent",
    "HeadToHead",
    "LeagueSync",
    "NewsArticle",
    "NewsArticleTeam",
    "Player",
    "PlayerRanking",
    "PlayerSeasonStat",
    "Review",
    "ReviewReaction",
    "Standing",
    "SyncRun",
    "Team",
    "TeamAlias",
    "TeamCompetitionSeason",
    "TeamForm",
    "Top5Attempt",
    "Top5Publication",
    "Top5Week",
    "WeeklyTopMatch",
]
