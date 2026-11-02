"""ORM models. Import every model here so Alembic sees the full metadata."""

from app.models.feedback import Feedback
from app.models.fixture import Fixture
from app.models.news import NewsArticle, NewsArticleTeam
from app.models.reference import (
    Competition,
    CompetitionSeason,
    Team,
    TeamAlias,
    TeamCompetitionSeason,
)
from app.models.sync_run import SyncRun

__all__ = [
    "Competition",
    "CompetitionSeason",
    "Feedback",
    "Fixture",
    "NewsArticle",
    "NewsArticleTeam",
    "SyncRun",
    "Team",
    "TeamAlias",
    "TeamCompetitionSeason",
]
