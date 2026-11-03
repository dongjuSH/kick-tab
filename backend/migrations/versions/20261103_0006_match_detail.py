"""Create match detail tables (chat 04): detail blocks, events, head-to-head, team form.

Revision ID: 0006_match_detail
Revises: 0005_news
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_match_detail"
down_revision: str | Sequence[str] | None = "0005_news"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("fixture_details", "fixture_events", "head_to_head", "team_forms")


def _fixture_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["fixture_id"],
        ["fixtures.id"],
        name=op.f(f"fk_{table}_fixture_id_fixtures"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table(
        "fixture_details",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("statistics", jsonb, nullable=True),
        sa.Column("lineups", jsonb, nullable=True),
        sa.Column("players", jsonb, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_status", sa.Text(), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        _fixture_fk("fixture_details"),
        sa.PrimaryKeyConstraint("fixture_id", name=op.f("pk_fixture_details")),
    )
    op.create_table(
        "fixture_events",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("elapsed", sa.Integer(), nullable=True),
        sa.Column("extra", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.BigInteger(), nullable=True),
        sa.Column("player_name", sa.Text(), nullable=True),
        sa.Column("assist_name", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        _fixture_fk("fixture_events"),
        sa.PrimaryKeyConstraint("fixture_id", "seq", name=op.f("pk_fixture_events")),
    )
    op.create_table(
        "head_to_head",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", jsonb, nullable=True),
        sa.Column("last_meeting_fixture_id", sa.BigInteger(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        _fixture_fk("head_to_head"),
        sa.PrimaryKeyConstraint("fixture_id", name=op.f("pk_head_to_head")),
    )
    op.create_table(
        "team_forms",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("payload", jsonb, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_team_forms_team_id_teams"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("team_id", name=op.f("pk_team_forms")),
    )

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
