"""League standings and player data (chat 06, LEAG-001·002·004).

- standings: one provider table per league season, rows as given (rank, played, points and
  `description` are never corrected — e.g. Ligue 1 2025-26 teams with 33 matches).
- player_rankings: the provider's top lists (goals, assists, yellow, red) in provider order.
  `yellowred` is kept apart on red rows and never added to the direct red count.
- players / player_season_stats: every player season line of a league (all /players pages),
  keyed by player, team, competition and season. Saves are aggregated from these rows;
  chat 08 reuses them for the team player table. NULL stays NULL (never 0).
- league_syncs: last success / failure per league, season and kind, so the screens can tell
  "not collected yet" from "refresh failed, stored data shown" (CMP-004).
A failed or partial collection never replaces stored rows.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RANKING_TYPES = ("goals", "assists", "yellow", "red")
SYNC_KINDS = ("standings", *RANKING_TYPES, "player_stats")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (Index("ix_standings_season_team", "season", "team_id"),)

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Provider group name ("Premier League"); leagues have one group, kept for completeness.
    group_name: Mapped[str] = mapped_column(Text, primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    # Order of the group within the answer, so groups keep the provider order.
    group_order: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int | None] = mapped_column(Integer)
    played: Mapped[int | None] = mapped_column(Integer)
    win: Mapped[int | None] = mapped_column(Integer)
    draw: Mapped[int | None] = mapped_column(Integer)
    lose: Mapped[int | None] = mapped_column(Integer)
    goals_for: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    goals_diff: Mapped[int | None] = mapped_column(Integer)
    form: Mapped[str | None] = mapped_column(Text)
    # Provider wording of the time ("Relegation - Championship"), kept as it was.
    description: Mapped[str | None] = mapped_column(Text)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlayerRanking(Base):
    __tablename__ = "player_rankings"
    __table_args__ = (CheckConstraint(_in("type", RANKING_TYPES), name="type_allowed"),)

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    type: Mapped[str] = mapped_column(Text, primary_key=True)
    # 1-based position in the provider's answer (the shown rank).
    position: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    value: Mapped[int | None] = mapped_column(Integer)
    # Second-yellow dismissals, stored for `red` only and never added to `value`.
    yellowred: Mapped[int | None] = mapped_column(Integer)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    firstname: Mapped[str | None] = mapped_column(Text)
    lastname: Mapped[str | None] = mapped_column(Text)
    nationality: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    photo_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlayerSeasonStat(Base):
    """One player's line for one team in one competition season (a "spell")."""

    __tablename__ = "player_season_stats"
    __table_args__ = (
        Index("ix_player_season_stats_competition_season", "competition_id", "season"),
        Index("ix_player_season_stats_team_season", "team_id", "season"),
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    position: Mapped[str | None] = mapped_column(Text)
    number: Mapped[int | None] = mapped_column(Integer)
    appearances: Mapped[int | None] = mapped_column(Integer)
    lineups: Mapped[int | None] = mapped_column(Integer)
    minutes: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    conceded: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    yellow: Mapped[int | None] = mapped_column(Integer)
    yellowred: Mapped[int | None] = mapped_column(Integer)
    red: Mapped[int | None] = mapped_column(Integer)
    # The provider statistics block as returned, for fields not in columns (chat 08).
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LeagueSync(Base):
    __tablename__ = "league_syncs"
    __table_args__ = (CheckConstraint(_in("kind", SYNC_KINDS), name="kind_allowed"),)

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Safe summary of the last failure (error class, page or counts only).
    failure: Mapped[str | None] = mapped_column(Text)
    # Rows stored by the last success (teams, list entries or player lines).
    row_count: Mapped[int | None] = mapped_column(Integer)
