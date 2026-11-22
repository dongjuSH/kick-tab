"""Review-writing restriction per member (terms 제9조, 2026-11-22): users.review_restricted_until.
NULL or a past moment means no restriction. No new table.

Revision ID: 0020_review_restrictions
Revises: 0019_member_accounts
Create Date: 2026-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020_review_restrictions"
down_revision: str | Sequence[str] | None = "0019_member_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("review_restricted_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "review_restricted_until")
