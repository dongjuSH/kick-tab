import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

FEEDBACK_BODY_MAX = 1000
FEEDBACK_PAGE_PATH_MAX = 300


class Feedback(Base):
    """User feedback (FEED-002). No IP address is stored."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            f"char_length(body) BETWEEN 1 AND {FEEDBACK_BODY_MAX}", name="body_length"
        ),
        CheckConstraint(
            "type IS NULL OR type IN ('bug', 'suggestion', 'other')", name="type_allowed"
        ),
        CheckConstraint(
            f"page_path IS NULL OR char_length(page_path) <= {FEEDBACK_PAGE_PATH_MAX}",
            name="page_path_length",
        ),
        CheckConstraint(
            "body_hash IS NULL OR char_length(body_hash) = 64", name="body_hash_length"
        ),
        Index("ix_feedback_body_hash_created_at", "body_hash", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # No foreign key yet: chat 02 adds it to users(id) once that table exists.
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    page_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 of the normalised body, used to reject repeats within 24 hours.
    # NULL for rows saved before revision 0002.
    body_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
