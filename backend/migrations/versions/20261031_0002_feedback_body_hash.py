"""Add feedback.body_hash for duplicate detection (chat 01).

Revision ID: 0002_feedback_body_hash
Revises: 0001_sync_runs_feedback
Create Date: 2026-10-31

Existing rows keep NULL; they are not compared for duplicates.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_feedback_body_hash"
down_revision: str | Sequence[str] | None = "0001_sync_runs_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("body_hash", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_feedback_body_hash_length"),
        "feedback",
        "body_hash IS NULL OR char_length(body_hash) = 64",
    )
    op.create_index(
        "ix_feedback_body_hash_created_at", "feedback", ["body_hash", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_body_hash_created_at", table_name="feedback")
    op.drop_constraint(op.f("ck_feedback_body_hash_length"), "feedback", type_="check")
    op.drop_column("feedback", "body_hash")
