"""Collected news metadata (chat 03, NEWS-001~004).

Only provider fields are stored (title, description, original link, publish time); no
article body. Rows expire after NEWS_RETENTION_HOURS (V-09 decides the final period).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

NEWS_BADGES = ("EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEFA")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        CheckConstraint(
            f"badge IS NULL OR badge IN ({', '.join(repr(b) for b in NEWS_BADGES)})",
            name="badge_allowed",
        ),
        CheckConstraint("char_length(url_hash) = 64", name="url_hash_length"),
        Index("ix_news_articles_badge_published", "badge", "published_at"),
        Index("ix_news_articles_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # SHA-256 of the normalized original URL: the same article from several queries is
    # stored once (NEWS-003).
    url_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_domain: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Competition badge from explicit title/description evidence; NULL = not shown on main.
    badge: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NewsArticleTeam(Base):
    """Teams named by an unambiguous alias in the article (team news, chat 08)."""

    __tablename__ = "news_article_teams"
    __table_args__ = (Index("ix_news_article_teams_team", "team_id"),)

    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
