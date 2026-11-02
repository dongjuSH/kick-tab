"""Create news tables (chat 03): collected article metadata and team links.

Revision ID: 0005_news
Revises: 0004_fixtures
Create Date: 2026-11-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_news"
down_revision: str | Sequence[str] | None = "0004_fixtures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("url_hash", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("badge", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "badge IS NULL OR badge IN ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'UEFA')",
            name=op.f("ck_news_articles_badge_allowed"),
        ),
        sa.CheckConstraint(
            "char_length(url_hash) = 64", name=op.f("ck_news_articles_url_hash_length")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_news_articles")),
        sa.UniqueConstraint("url_hash", name=op.f("uq_news_articles_url_hash")),
    )
    op.create_index(
        "ix_news_articles_badge_published", "news_articles", ["badge", "published_at"]
    )
    op.create_index("ix_news_articles_expires_at", "news_articles", ["expires_at"])
    op.create_table(
        "news_article_teams",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["news_articles.id"],
            name=op.f("fk_news_article_teams_article_id_news_articles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_news_article_teams_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("article_id", "team_id", name=op.f("pk_news_article_teams")),
    )
    op.create_index("ix_news_article_teams_team", "news_article_teams", ["team_id"])

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    op.execute("ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE news_article_teams ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_news_article_teams_team", table_name="news_article_teams")
    op.drop_table("news_article_teams")
    op.drop_index("ix_news_articles_expires_at", table_name="news_articles")
    op.drop_index("ix_news_articles_badge_published", table_name="news_articles")
    op.drop_table("news_articles")
