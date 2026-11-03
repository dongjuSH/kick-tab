"""Create review tables (chat 04): member reviews and reactions, read publicly.

`user_id` has no foreign key until chat 02 creates `users`; chat 02 then adds
REFERENCES users(id) ON DELETE CASCADE on both tables (P-03).

Revision ID: 0007_reviews
Revises: 0006_match_detail
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_reviews"
down_revision: str | Sequence[str] | None = "0006_match_detail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = sa.text("now()")
    op.create_table(
        "reviews",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.CheckConstraint("char_length(body) <= 300", name=op.f("ck_reviews_body_length")),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_reviews_rating_range")),
        sa.ForeignKeyConstraint(
            ["fixture_id"],
            ["fixtures.id"],
            name=op.f("fk_reviews_fixture_id_fixtures"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
        sa.UniqueConstraint("user_id", "fixture_id", name="uq_reviews_user_fixture"),
    )
    op.create_index("ix_reviews_fixture_created", "reviews", ["fixture_id", "created_at"])
    op.create_table(
        "review_reactions",
        sa.Column("review_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.CheckConstraint("value IN (-1, 1)", name=op.f("ck_review_reactions_value_allowed")),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name=op.f("fk_review_reactions_review_id_reviews"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("review_id", "user_id", name=op.f("pk_review_reactions")),
    )

    # Block the Supabase Data API: RLS on, no policies (guide §6.3).
    op.execute("ALTER TABLE reviews ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE review_reactions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("review_reactions")
    op.drop_index("ix_reviews_fixture_created", table_name="reviews")
    op.drop_table("reviews")
