from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncRun(Base):
    """One execution of a collection job, including its external API request count."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'skipped')", name="status_allowed"
        ),
        CheckConstraint("api_requests >= 0", name="api_requests_non_negative"),
        Index("ix_sync_runs_job_started_at", "job", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    job: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    api_requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text)
