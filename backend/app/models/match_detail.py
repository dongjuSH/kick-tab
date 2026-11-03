"""Match detail data (chat 04, MAT-002·004·005).

- fixture_details: provider blocks of one fixture (statistics, lineups, players) as returned,
  plus the fixture status they were fetched in, so a block fetched while live is replaced by
  the final one once and a finished one is never fetched again.
- fixture_events: the timeline, replaced as a whole on every successful fetch so a repeated
  collection never duplicates an event (the provider has no event id).
- head_to_head: recent official meetings of the two teams, once per fixture and refreshed
  only after the teams meet again.
- team_forms: a team's recent official results (shared by match detail and TOP 5).
A failed fetch only sets `last_failed_at`; stored data is never overwritten by a failure.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FixtureDetail(Base):
    __tablename__ = "fixture_details"

    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), primary_key=True
    )
    statistics: Mapped[list[Any] | None] = mapped_column(JSONB)
    lineups: Mapped[list[Any] | None] = mapped_column(JSONB)
    players: Mapped[list[Any] | None] = mapped_column(JSONB)
    # Null until the first successful fetch (a row may exist only to record failures).
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_status: Mapped[str | None] = mapped_column(Text)
    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FixtureEvent(Base):
    __tablename__ = "fixture_events"

    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    elapsed: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[int | None] = mapped_column(BigInteger)
    player_name: Mapped[str | None] = mapped_column(Text)
    # Goal: the assisting player; substitution: the player coming on (provider convention).
    assist_name: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)


class HeadToHead(Base):
    __tablename__ = "head_to_head"

    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), primary_key=True
    )
    # Normalised official finished meetings, newest first (at most 5 are shown).
    payload: Mapped[list[Any] | None] = mapped_column(JSONB)
    last_meeting_fixture_id: Mapped[int | None] = mapped_column(BigInteger)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TeamForm(Base):
    __tablename__ = "team_forms"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    # Normalised official finished matches, newest first.
    payload: Mapped[list[Any] | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
