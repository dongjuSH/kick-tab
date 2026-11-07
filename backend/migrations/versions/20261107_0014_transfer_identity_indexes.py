"""Match transfer uniqueness to the parser's ID-or-name rule (chat 08, N7).

Revision ID: 0014_transfer_identity_indexes
Revises: 0013_transfer_counterpart_key
Create Date: 2026-11-07
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0014_transfer_identity_indexes"
down_revision: str | Sequence[str] | None = "0013_transfer_counterpart_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENTRY = ["team_id", "player_id", "transfer_date", "direction"]


def upgrade() -> None:
    # Build the tighter index before dropping the old constraint. Existing conflicting
    # rows make the migration fail without deleting any transfer history.
    op.create_index(
        "uq_transfers_entry_with_counterpart_id",
        "transfers",
        [*ENTRY, "counterpart_id"],
        unique=True,
        postgresql_where=text("counterpart_id IS NOT NULL"),
    )
    op.create_index(
        "uq_transfers_entry_without_counterpart_id",
        "transfers",
        [*ENTRY, "counterpart_name"],
        unique=True,
        postgresql_where=text("counterpart_id IS NULL"),
        postgresql_nulls_not_distinct=True,
    )
    op.drop_constraint("uq_transfers_entry", "transfers", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_transfers_entry",
        "transfers",
        [*ENTRY, "counterpart_id", "counterpart_name"],
        postgresql_nulls_not_distinct=True,
    )
    op.drop_index("uq_transfers_entry_without_counterpart_id", table_name="transfers")
    op.drop_index("uq_transfers_entry_with_counterpart_id", table_name="transfers")
