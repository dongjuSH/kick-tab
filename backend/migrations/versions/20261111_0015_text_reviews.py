"""Text-only match reviews (04 개선, REV-001~004).

The member star rating is removed (no rating, no average: the valid review count is shown)
and the body becomes required and must not be blank (max 300 stays). The table has no row
yet; chat 02 adds writing.

Revision ID: 0015_text_reviews
Revises: 0014_transfer_identity_indexes
Create Date: 2026-11-11
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_text_reviews"
down_revision: str | Sequence[str] | None = "0014_transfer_identity_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Not blank = has a character Python's str.isspace() does not treat as whitespace (same
# class as `app.models.review.REVIEW_BODY_SPACE_CLASS`, copied so the migration is fixed).
VISIBLE = (
    r"body ~ '[^\t\n\v\f\r\u001c-\u001f \u0085   -   "
    r"  　]'"
)


def upgrade() -> None:
    # A review without a visible body cannot be kept as a text review: fail, never guess.
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM reviews WHERE body IS NULL OR NOT ("
        + VISIBLE
        + ")) THEN RAISE EXCEPTION 'reviews without a body exist; resolve them first';"
        " END IF; END $$"
    )
    op.drop_constraint(op.f("ck_reviews_rating_range"), "reviews", type_="check")
    op.drop_column("reviews", "rating")
    op.alter_column("reviews", "body", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(op.f("ck_reviews_body_not_blank"), "reviews", VISIBLE)


def downgrade() -> None:
    # A star rating cannot be invented for text reviews written after the upgrade.
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM reviews) THEN RAISE EXCEPTION"
        " 'text reviews exist; a rating cannot be restored for them'; END IF; END $$"
    )
    op.drop_constraint(op.f("ck_reviews_body_not_blank"), "reviews", type_="check")
    op.alter_column("reviews", "body", existing_type=sa.Text(), nullable=True)
    op.add_column("reviews", sa.Column("rating", sa.SmallInteger(), nullable=False))
    op.create_check_constraint(
        op.f("ck_reviews_rating_range"), "reviews", "rating BETWEEN 1 AND 5"
    )
