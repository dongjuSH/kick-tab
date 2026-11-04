"""Record the calendar bounds of each successful competition schedule sync."""

import sqlalchemy as sa
from alembic import op

revision = "0009_fixture_coverage"
down_revision = "0008_top5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Leave existing coverage unknown until a sync requests the new range.
    op.add_column("competition_seasons", sa.Column("fixtures_window_start", sa.Date()))
    op.add_column("competition_seasons", sa.Column("fixtures_window_end", sa.Date()))


def downgrade() -> None:
    op.drop_column("competition_seasons", "fixtures_window_end")
    op.drop_column("competition_seasons", "fixtures_window_start")
