"""Create AI weekly TOP 5 tables (chat 04): week job state, attempts, public versions, items.

Revision ID: 0008_top5
Revises: 0007_reviews
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_top5"
down_revision: str | Sequence[str] | None = "0007_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("top5_weeks", "top5_attempts", "top5_publications", "weekly_top_matches")


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    now = sa.text("now()")
    op.create_table(
        "top5_weeks",
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("auto_attempts", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("current_attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("needs_manual", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("alert_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'retry_scheduled', 'delayed', 'published')",
            name=op.f("ck_top5_weeks_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("week_start", name=op.f("pk_top5_weeks")),
    )
    op.create_table(
        "top5_attempts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("curation_version", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=True),
        sa.Column("api_requests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evidence", jsonb, nullable=True),
        sa.Column("llm_output", jsonb, nullable=True),
        sa.CheckConstraint(
            "outcome IN ('running', 'published', 'failed', 'timeout')",
            name=op.f("ck_top5_attempts_outcome_allowed"),
        ),
        sa.CheckConstraint(
            "trigger IN ('scheduled', 'retry', 'manual')",
            name=op.f("ck_top5_attempts_trigger_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_top5_attempts")),
    )
    op.create_index(
        "ix_top5_attempts_week_started", "top5_attempts", ["week_start", "started_at"]
    )
    op.create_table(
        "top5_publications",
        sa.Column("version", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.CheckConstraint(
            "kind IN ('list', 'none', 'delayed')", name=op.f("ck_top5_publications_kind_allowed")
        ),
        sa.PrimaryKeyConstraint("version", name=op.f("pk_top5_publications")),
    )
    op.create_index("ix_top5_publications_week", "top5_publications", ["week_start"])
    op.create_table(
        "weekly_top_matches",
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("selected_kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("rank BETWEEN 1 AND 5", name=op.f("ck_weekly_top_matches_rank_range")),
        sa.ForeignKeyConstraint(
            ["fixture_id"],
            ["fixtures.id"],
            name=op.f("fk_weekly_top_matches_fixture_id_fixtures"),
        ),
        sa.PrimaryKeyConstraint("week_start", "rank", name=op.f("pk_weekly_top_matches")),
        sa.UniqueConstraint("week_start", "fixture_id", name="uq_weekly_top_matches_week_fixture"),
    )

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("weekly_top_matches")
    op.drop_index("ix_top5_publications_week", table_name="top5_publications")
    op.drop_table("top5_publications")
    op.drop_index("ix_top5_attempts_week_started", table_name="top5_attempts")
    op.drop_table("top5_attempts")
    op.drop_table("top5_weeks")
