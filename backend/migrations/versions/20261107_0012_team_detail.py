"""Create team detail tables (chat 08): coaches, squads, team season stats, transfers and
per-team sync state; add team venues and the one-time player profile check.

Revision ID: 0012_team_detail
Revises: 0011_standings
Create Date: 2026-11-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_team_detail"
down_revision: str | Sequence[str] | None = "0011_standings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("squad_members", "team_coaches", "team_season_stats", "team_syncs", "transfers")


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"), ondelete="CASCADE"
    )


def upgrade() -> None:
    tz = sa.DateTime(timezone=True)
    op.create_table(
        "squad_members",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column("synced_at", tz, nullable=False),
        _fk("squad_members", "player_id", "players"),
        _fk("squad_members", "team_id", "teams"),
        sa.PrimaryKeyConstraint("team_id", "player_id", name=op.f("pk_squad_members")),
    )
    op.create_table(
        "team_coaches",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("since", sa.Date(), nullable=True),
        sa.Column("synced_at", tz, nullable=False),
        _fk("team_coaches", "team_id", "teams"),
        sa.PrimaryKeyConstraint("team_id", name=op.f("pk_team_coaches")),
    )
    op.create_table(
        "team_season_stats",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synced_at", tz, nullable=False),
        _fk("team_season_stats", "competition_id", "competitions"),
        _fk("team_season_stats", "team_id", "teams"),
        sa.PrimaryKeyConstraint(
            "team_id", "competition_id", "season", name=op.f("pk_team_season_stats")
        ),
    )
    op.create_table(
        "team_syncs",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("synced_at", tz, nullable=True),
        sa.Column("failed_at", tz, nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('coach', 'squad', 'statistics', 'transfers')",
            name=op.f("ck_team_syncs_kind_allowed"),
        ),
        _fk("team_syncs", "team_id", "teams"),
        sa.PrimaryKeyConstraint("team_id", "season", "kind", name=op.f("pk_team_syncs")),
    )
    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("counterpart_id", sa.Integer(), nullable=True),
        sa.Column("counterpart_name", sa.Text(), nullable=True),
        sa.Column("counterpart_logo", sa.Text(), nullable=True),
        sa.Column("type_raw", sa.Text(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("half", sa.SmallInteger(), nullable=False),
        sa.Column("synced_at", tz, nullable=False),
        sa.CheckConstraint(
            "direction IN ('in', 'out')", name=op.f("ck_transfers_direction_allowed")
        ),
        sa.CheckConstraint("half IN (1, 2)", name=op.f("ck_transfers_half_allowed")),
        _fk("transfers", "team_id", "teams"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfers")),
        sa.UniqueConstraint(
            "team_id",
            "player_id",
            "transfer_date",
            "direction",
            "counterpart_id",
            name="uq_transfers_entry",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_transfers_team_season", "transfers", ["team_id", "season"], unique=False)
    op.add_column("players", sa.Column("profile_checked_at", tz, nullable=True))
    op.add_column("teams", sa.Column("venue_name", sa.Text(), nullable=True))
    op.add_column("teams", sa.Column("venue_capacity", sa.Integer(), nullable=True))
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_column("teams", "venue_capacity")
    op.drop_column("teams", "venue_name")
    op.drop_column("players", "profile_checked_at")
    op.drop_index("ix_transfers_team_season", table_name="transfers")
    for table in reversed(TABLES):
        op.drop_table(table)
