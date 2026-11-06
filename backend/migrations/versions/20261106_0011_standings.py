"""Create standings and player tables (chat 06): standings, player rankings, players,
player season stats and per-kind league sync state.

Revision ID: 0011_standings
Revises: 0010_season_fixtures
Create Date: 2026-11-06

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_standings"
down_revision: str | Sequence[str] | None = "0010_season_fixtures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("standings", "players", "player_rankings", "player_season_stats", "league_syncs")


def _fk(table: str, column: str, target: str, ondelete: str = "CASCADE") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [f"{target}.id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        ondelete=ondelete,
    )


def upgrade() -> None:
    tz = sa.DateTime(timezone=True)
    op.create_table(
        "standings",
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("group_order", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("played", sa.Integer(), nullable=True),
        sa.Column("win", sa.Integer(), nullable=True),
        sa.Column("draw", sa.Integer(), nullable=True),
        sa.Column("lose", sa.Integer(), nullable=True),
        sa.Column("goals_for", sa.Integer(), nullable=True),
        sa.Column("goals_against", sa.Integer(), nullable=True),
        sa.Column("goals_diff", sa.Integer(), nullable=True),
        sa.Column("form", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider_updated_at", tz, nullable=True),
        sa.Column("synced_at", tz, nullable=False),
        _fk("standings", "competition_id", "competitions"),
        _fk("standings", "team_id", "teams"),
        sa.PrimaryKeyConstraint(
            "competition_id", "season", "group_name", "team_id", name=op.f("pk_standings")
        ),
    )
    op.create_index("ix_standings_season_team", "standings", ["season", "team_id"])
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("firstname", sa.Text(), nullable=True),
        sa.Column("lastname", sa.Text(), nullable=True),
        sa.Column("nationality", sa.Text(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("updated_at", tz, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_table(
        "player_rankings",
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("yellowred", sa.Integer(), nullable=True),
        sa.Column("synced_at", tz, nullable=False),
        sa.CheckConstraint(
            "type IN ('goals', 'assists', 'yellow', 'red')",
            name=op.f("ck_player_rankings_type_allowed"),
        ),
        _fk("player_rankings", "competition_id", "competitions"),
        _fk("player_rankings", "player_id", "players"),
        _fk("player_rankings", "team_id", "teams", "SET NULL"),
        sa.PrimaryKeyConstraint(
            "competition_id", "season", "type", "position", name=op.f("pk_player_rankings")
        ),
    )
    op.create_table(
        "player_season_stats",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("lineups", sa.Integer(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Numeric(5, 3), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("conceded", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("yellow", sa.Integer(), nullable=True),
        sa.Column("yellowred", sa.Integer(), nullable=True),
        sa.Column("red", sa.Integer(), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synced_at", tz, nullable=False),
        _fk("player_season_stats", "player_id", "players"),
        _fk("player_season_stats", "team_id", "teams"),
        _fk("player_season_stats", "competition_id", "competitions"),
        sa.PrimaryKeyConstraint(
            "player_id", "team_id", "competition_id", "season",
            name=op.f("pk_player_season_stats"),
        ),
    )
    op.create_index(
        "ix_player_season_stats_competition_season",
        "player_season_stats",
        ["competition_id", "season"],
    )
    op.create_index(
        "ix_player_season_stats_team_season", "player_season_stats", ["team_id", "season"]
    )
    op.create_table(
        "league_syncs",
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("synced_at", tz, nullable=True),
        sa.Column("failed_at", tz, nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('standings', 'goals', 'assists', 'yellow', 'red', 'player_stats')",
            name=op.f("ck_league_syncs_kind_allowed"),
        ),
        _fk("league_syncs", "competition_id", "competitions"),
        sa.PrimaryKeyConstraint("competition_id", "season", "kind", name=op.f("pk_league_syncs")),
    )

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("league_syncs")
    op.drop_index("ix_player_season_stats_team_season", table_name="player_season_stats")
    op.drop_index("ix_player_season_stats_competition_season", table_name="player_season_stats")
    op.drop_table("player_season_stats")
    op.drop_table("player_rankings")
    op.drop_table("players")
    op.drop_index("ix_standings_season_team", table_name="standings")
    op.drop_table("standings")
