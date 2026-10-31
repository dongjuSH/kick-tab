"""Create sync_runs and feedback (chat 01).

Revision ID: 0001_sync_runs_feedback
Revises:
Create Date: 2026-10-31

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_sync_runs_feedback"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job", sa.Text(), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("api_requests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'skipped')",
            name=op.f("ck_sync_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "api_requests >= 0", name=op.f("ck_sync_runs_api_requests_non_negative")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
    )
    op.create_index("ix_sync_runs_job_started_at", "sync_runs", ["job", "started_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        # Foreign key to users(id) is added by chat 02 (P-03 decides ON DELETE).
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("page_path", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(body) BETWEEN 1 AND 1000", name=op.f("ck_feedback_body_length")
        ),
        sa.CheckConstraint(
            "type IS NULL OR type IN ('bug', 'suggestion', 'other')",
            name=op.f("ck_feedback_type_allowed"),
        ),
        sa.CheckConstraint(
            "page_path IS NULL OR char_length(page_path) <= 300",
            name=op.f("ck_feedback_page_path_length"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback")),
    )

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    op.execute("ALTER TABLE sync_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_index("ix_sync_runs_job_started_at", table_name="sync_runs")
    op.drop_table("sync_runs")
