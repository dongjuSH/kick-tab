"""AI weekly TOP 5 (TOP-001~003, TOP 5 policy 2026-11-02 in the planning docs).

The internal job state of a target week (`top5_weeks`, `top5_attempts`) is kept apart from
what users see (`top5_publications` + `weekly_top_matches`). A publication row is the
public version: every switch of the public result (this week's list, "no matches", or the
delay notice) inserts one, in the same transaction as its items, so readers see either the
old version or the whole new one.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

WEEK_STATUSES = ("running", "retry_scheduled", "delayed", "published")
ATTEMPT_TRIGGERS = ("scheduled", "retry", "manual")
ATTEMPT_OUTCOMES = ("running", "published", "failed", "timeout")
PUBLICATION_KINDS = ("list", "none", "delayed")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Top5Week(Base):
    """Job state of one target week (KST Monday). Never shown to users as such."""

    __tablename__ = "top5_weeks"
    __table_args__ = (CheckConstraint(_in("status", WEEK_STATUSES), name="status_allowed"),)

    week_start: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    # Automatic attempts used (00:00 and 00:05 KST): at most 2 per week.
    auto_attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    current_attempt_id: Mapped[int | None] = mapped_column(BigInteger)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    needs_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    alert_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Top5Attempt(Base):
    """One selection attempt with its inputs and the model output, kept for review."""

    __tablename__ = "top5_attempts"
    __table_args__ = (
        CheckConstraint(_in("trigger", ATTEMPT_TRIGGERS), name="trigger_allowed"),
        CheckConstraint(_in("outcome", ATTEMPT_OUTCOMES), name="outcome_allowed"),
        Index("ix_top5_attempts_week_started", "week_start", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    curation_version: Mapped[str | None] = mapped_column(Text)
    candidate_count: Mapped[int | None] = mapped_column(Integer)
    api_requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    llm_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Top5Publication(Base):
    """Public version. The latest row decides what the strip shows (see services)."""

    __tablename__ = "top5_publications"
    __table_args__ = (
        CheckConstraint(_in("kind", PUBLICATION_KINDS), name="kind_allowed"),
        Index("ix_top5_publications_week", "week_start"),
    )

    version: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_id: Mapped[int | None] = mapped_column(BigInteger)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WeeklyTopMatch(Base):
    """Fixed items of a published week: id, order and reason never change afterwards."""

    __tablename__ = "weekly_top_matches"
    __table_args__ = (
        UniqueConstraint("week_start", "fixture_id", name="uq_weekly_top_matches_week_fixture"),
        CheckConstraint("rank BETWEEN 1 AND 5", name="rank_range"),
    )

    week_start: Mapped[date] = mapped_column(Date, primary_key=True)
    rank: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # Kickoff when selected; a later change is shown as the changed date (D-01-10).
    selected_kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
