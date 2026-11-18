"""Team-scoped player records in the record competitions (chat 08, 2026-11-18): the five
leagues and the three UEFA competitions from /players?team=&season=, and the `player_stats`
kind of the per-team sync state.

Revision ID: 0016_team_player_stats
Revises: 0015_text_reviews
Create Date: 2026-11-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016_team_player_stats"
down_revision: str | Sequence[str] | None = "0015_text_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = "kind IN ('coach', 'squad', 'statistics', 'transfers')"
NEW_KINDS = "kind IN ('coach', 'squad', 'statistics', 'transfers', 'player_stats')"


def _fk(column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [f"{target}.id"],
        name=op.f(f"fk_team_player_stats_{column}_{target}"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    op.create_table(
        "team_player_stats",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Numeric(5, 3), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        _fk("competition_id", "competitions"),
        _fk("player_id", "players"),
        _fk("team_id", "teams"),
        sa.PrimaryKeyConstraint(
            "team_id", "player_id", "competition_id", "season", name=op.f("pk_team_player_stats")
        ),
    )
    op.execute("ALTER TABLE team_player_stats ENABLE ROW LEVEL SECURITY")
    op.drop_constraint(op.f("ck_team_syncs_kind_allowed"), "team_syncs", type_="check")
    op.create_check_constraint(op.f("ck_team_syncs_kind_allowed"), "team_syncs", NEW_KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM team_syncs WHERE kind = 'player_stats'")
    op.drop_constraint(op.f("ck_team_syncs_kind_allowed"), "team_syncs", type_="check")
    op.create_check_constraint(op.f("ck_team_syncs_kind_allowed"), "team_syncs", OLD_KINDS)
    op.drop_table("team_player_stats")
