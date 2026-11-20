"""A signing's first-team appearances per club and season (chat 08, 2026-11-20, TEAM-006
rule 6): `player_season_checks` (one /players?id=&season= request per player and season)
and `player_club_seasons` (the appearances it gave per club).

Revision ID: 0018_player_season_checks
Revises: 0017_competition_groups
Create Date: 2026-11-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018_player_season_checks"
down_revision: str | Sequence[str] | None = "0017_competition_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table("player_club_seasons")
    op.drop_table("player_season_checks")
