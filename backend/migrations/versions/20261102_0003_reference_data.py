"""Create reference data tables (chat 03): competitions, seasons, teams, aliases.

Revision ID: 0003_reference_data
Revises: 0002_feedback_body_hash
Create Date: 2026-11-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_reference_data"
down_revision: str | Sequence[str] | None = "0002_feedback_body_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "competitions",
    "competition_seasons",
    "teams",
    "team_competition_seasons",
    "team_aliases",
)


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("group_key", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_ko", sa.Text(), nullable=True),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "group_key IN ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'UEFA')",
            name=op.f("ck_competitions_group_allowed"),
        ),
        sa.CheckConstraint(
            "type IN ('league', 'cup', 'uefa')", name=op.f("ck_competitions_type_allowed")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_competitions")),
    )
    op.create_table(
        "competition_seasons",
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("availability", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("teams_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fixtures_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fixtures_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "availability IN ('available', 'no_data')",
            name=op.f("ck_competition_seasons_availability_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            name=op.f("fk_competition_seasons_competition_id_competitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("competition_id", "season", name=op.f("pk_competition_seasons")),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_ko", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
    )
    op.create_table(
        "team_competition_seasons",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            name=op.f("fk_team_competition_seasons_competition_id_competitions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_team_competition_seasons_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "team_id", "competition_id", "season", name=op.f("pk_team_competition_seasons")
        ),
    )
    op.create_index(
        "ix_team_competition_seasons_season",
        "team_competition_seasons",
        ["season", "competition_id"],
    )
    op.create_table(
        "team_aliases",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("normalized", sa.Text(), nullable=False),
        sa.Column("lang", sa.Text(), nullable=False),
        sa.Column("ambiguous", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("for_search", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("for_news", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("lang IN ('ko', 'en')", name=op.f("ck_team_aliases_lang_allowed")),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_team_aliases_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team_aliases")),
        sa.UniqueConstraint("team_id", "normalized", name="uq_team_aliases_team_normalized"),
    )
    op.create_index("ix_team_aliases_normalized", "team_aliases", ["normalized"])

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_team_aliases_normalized", table_name="team_aliases")
    op.drop_table("team_aliases")
    op.drop_index("ix_team_competition_seasons_season", table_name="team_competition_seasons")
    op.drop_table("team_competition_seasons")
    op.drop_table("teams")
    op.drop_table("competition_seasons")
    op.drop_table("competitions")
