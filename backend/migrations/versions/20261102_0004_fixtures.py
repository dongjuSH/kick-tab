"""Create fixtures (chat 03): schedule, status and score of supported competitions.

Revision ID: 0004_fixtures
Revises: 0003_reference_data
Create Date: 2026-11-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_fixtures"
down_revision: str | Sequence[str] | None = "0003_reference_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fixtures",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("round", sa.Text(), nullable=True),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kickoff_date_kst", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("finish_type", sa.Text(), nullable=True),
        sa.Column("status_short_raw", sa.Text(), nullable=False),
        sa.Column("status_long_raw", sa.Text(), nullable=True),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("elapsed", sa.Integer(), nullable=True),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("goals_home", sa.Integer(), nullable=True),
        sa.Column("goals_away", sa.Integer(), nullable=True),
        sa.Column("score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("venue_name", sa.Text(), nullable=True),
        sa.Column("venue_city", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "finish_type IS NULL OR finish_type IN ('normal', 'aet', 'pen', 'awarded', 'walkover')",
            name=op.f("ck_fixtures_finish_type_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'live', 'finished', 'postponed', 'cancelled', 'abandoned', "
            "'unknown')",
            name=op.f("ck_fixtures_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["teams.id"], name=op.f("fk_fixtures_away_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            name=op.f("fk_fixtures_competition_id_competitions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["teams.id"], name=op.f("fk_fixtures_home_team_id_teams")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fixtures")),
    )
    op.create_index("ix_fixtures_away_team_kickoff", "fixtures", ["away_team_id", "kickoff_at"])
    op.create_index("ix_fixtures_home_team_kickoff", "fixtures", ["home_team_id", "kickoff_at"])
    op.create_index("ix_fixtures_kickoff_date_kst", "fixtures", ["kickoff_date_kst"])
    op.create_index("ix_fixtures_status_kickoff", "fixtures", ["status", "kickoff_at"])

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    op.execute("ALTER TABLE fixtures ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_fixtures_status_kickoff", table_name="fixtures")
    op.drop_index("ix_fixtures_kickoff_date_kst", table_name="fixtures")
    op.drop_index("ix_fixtures_home_team_kickoff", table_name="fixtures")
    op.drop_index("ix_fixtures_away_team_kickoff", table_name="fixtures")
    op.drop_table("fixtures")
