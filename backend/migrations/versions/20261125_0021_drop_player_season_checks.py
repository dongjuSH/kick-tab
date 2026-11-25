"""Drop the signing checks (chat 08, user decision 2026-11-25): the transfer list now shows a
move first only for a player with first-team appearances for the team itself, so the
previous club's appearances (`player_season_checks`, `player_club_seasons` from 0018) are
no longer read or collected.

Revision ID: 0021_drop_player_season_checks
Revises: 0020_review_restrictions
Create Date: 2026-11-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021_drop_player_season_checks"
down_revision: str | Sequence[str] | None = "0020_review_restrictions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("player_club_seasons")
    op.drop_table("player_season_checks")


def downgrade() -> None:
    # The tables come back empty: their rows were a re-collectable cache.
    op.create_table(
        "player_season_checks",
        sa.Column("player_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("player_id", "season", name=op.f("pk_player_season_checks")),
    )
    op.execute("ALTER TABLE player_season_checks ENABLE ROW LEVEL SECURITY")
    op.create_table(
        "player_club_seasons",
        sa.Column("player_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("season", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("team_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint(
            "player_id", "season", "team_id", name=op.f("pk_player_club_seasons")
        ),
    )
    op.execute("ALTER TABLE player_club_seasons ENABLE ROW LEVEL SECURITY")
