"""Full-season fixture loads (chat 05, HIST-001~003).

The 21-day schedule sync keeps overwriting `fixtures_synced_at` and its window, so the
state of the whole-season list (past results page) is recorded separately. The index serves
"finished matches of one season, newest first".
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_season_fixtures"
down_revision = "0009_fixture_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "competition_seasons",
        sa.Column("season_fixtures_synced_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "competition_seasons",
        sa.Column("season_fixtures_failed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_fixtures_season_status_kickoff", "fixtures", ["season", "status", "kickoff_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_fixtures_season_status_kickoff", table_name="fixtures")
    op.drop_column("competition_seasons", "season_fixtures_failed_at")
    op.drop_column("competition_seasons", "season_fixtures_synced_at")
