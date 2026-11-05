"""Fixtures of the supported competitions (chat 03: list, status, score).

Times are UTC; `kickoff_date_kst` groups the schedule by KST calendar date (guide §6.3).
The raw status code and score block are kept so the mapping can be re-applied (§6.4).
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MATCH_STATUSES = (
    "scheduled", "live", "finished", "postponed", "cancelled", "abandoned", "unknown"
)
FINISH_TYPES = ("normal", "aet", "pen", "awarded", "walkover")


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in MATCH_STATUSES)})", name="status_allowed"
        ),
        CheckConstraint(
            f"finish_type IS NULL OR finish_type IN ({', '.join(repr(s) for s in FINISH_TYPES)})",
            name="finish_type_allowed",
        ),
        Index("ix_fixtures_kickoff_date_kst", "kickoff_date_kst"),
        Index("ix_fixtures_home_team_kickoff", "home_team_id", "kickoff_at"),
        Index("ix_fixtures_away_team_kickoff", "away_team_id", "kickoff_at"),
        Index("ix_fixtures_status_kickoff", "status", "kickoff_at"),
        # Past results: finished matches of one season, newest first (chat 05).
        Index("ix_fixtures_season_status_kickoff", "season", "status", "kickoff_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[str | None] = mapped_column(Text)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kickoff_date_kst: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    finish_type: Mapped[str | None] = mapped_column(Text)
    status_short_raw: Mapped[str] = mapped_column(Text, nullable=False)
    status_long_raw: Mapped[str | None] = mapped_column(Text)
    # The provider has no reason field today; kept for a source that supplies one.
    status_reason: Mapped[str | None] = mapped_column(Text)
    elapsed: Mapped[int | None] = mapped_column(Integer)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    goals_home: Mapped[int | None] = mapped_column(Integer)
    goals_away: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    venue_name: Mapped[str | None] = mapped_column(Text)
    venue_city: Mapped[str | None] = mapped_column(Text)
    # Last time a provider response confirmed this row (schedule or live sync).
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
