"""Transfers unique key includes the other club's name (chat 08, Codex 3차 지적 N4): two moves
of one player on the same day to clubs without a provider id are two rows, not one.

Revision ID: 0013_transfer_counterpart_key
Revises: 0012_team_detail
Create Date: 2026-11-07

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_transfer_counterpart_key"
down_revision: str | Sequence[str] | None = "0012_team_detail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = ["team_id", "player_id", "transfer_date", "direction", "counterpart_id"]


def upgrade() -> None:
    op.drop_constraint("uq_transfers_entry", "transfers", type_="unique")
    op.create_unique_constraint(
        "uq_transfers_entry",
        "transfers",
        [*OLD, "counterpart_name"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    # Rows that differ only by the club name cannot satisfy the old key: keep the first.
    op.execute(
        """
        DELETE FROM transfers t USING transfers o
        WHERE t.id > o.id AND t.team_id = o.team_id AND t.player_id = o.player_id
          AND t.transfer_date = o.transfer_date AND t.direction = o.direction
          AND t.counterpart_id IS NOT DISTINCT FROM o.counterpart_id
        """
    )
    op.drop_constraint("uq_transfers_entry", "transfers", type_="unique")
    op.create_unique_constraint(
        "uq_transfers_entry", "transfers", OLD, postgresql_nulls_not_distinct=True
    )
