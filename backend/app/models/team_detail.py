"""Team detail data (chat 08, TEAM-001·002·005·006).

- team_coaches: the current coach chosen from /coachs (career entry of this team with no end,
  latest start). A row with coach_id NULL means "collected, no current coach given".
- squad_members: the current squad from /players/squads (number and position as given).
- team_season_stats: the /teams/statistics block of a team's league season, kept as given.
- transfers: /transfers entries that involve the team, one row per team and direction,
  classified by date into season halves (June-December = first, January-May = second).
  Names come from the provider answer (counterpart clubs may not be stored teams).
- team_syncs: last success / failure per team, season and kind, so screens can tell
  "never collected" from "refresh failed, stored data shown" (CMP-004).
Values the provider leaves empty stay NULL; a failed or cut answer never replaces stored rows.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TEAM_SYNC_KINDS = ("coach", "squad", "statistics", "transfers")
TRANSFER_DIRECTIONS = ("in", "out")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class TeamCoach(Base):
    __tablename__ = "team_coaches"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    coach_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    # Start of the current spell at this team, as given.
    since: Mapped[date | None] = mapped_column(Date)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SquadMember(Base):
    __tablename__ = "squad_members"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    number: Mapped[int | None] = mapped_column(Integer)
    # Provider position: Goalkeeper / Defender / Midfielder / Attacker.
    position: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TeamSeasonStat(Base):
    __tablename__ = "team_season_stats"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(_in("direction", TRANSFER_DIRECTIONS), name="direction_allowed"),
        CheckConstraint("half IN (1, 2)", name="half_allowed"),
        Index(
            "uq_transfers_entry_with_counterpart_id",
            "team_id",
            "player_id",
            "transfer_date",
            "direction",
            "counterpart_id",
            unique=True,
            postgresql_where=text("counterpart_id IS NOT NULL"),
        ),
        Index(
            "uq_transfers_entry_without_counterpart_id",
            "team_id",
            "player_id",
            "transfer_date",
            "direction",
            "counterpart_name",
            unique=True,
            postgresql_where=text("counterpart_id IS NULL"),
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_transfers_team_season", "team_id", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    player_name: Mapped[str] = mapped_column(Text, nullable=False)
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False)
    # in = the team signed the player (teams.in), out = the team let the player go.
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    # The other club of the move, as named in the answer (NULL when not given).
    counterpart_id: Mapped[int | None] = mapped_column(Integer)
    counterpart_name: Mapped[str | None] = mapped_column(Text)
    counterpart_logo: Mapped[str | None] = mapped_column(Text)
    # Provider type text ("Loan", "Free", "€ 10M"); NULL when not given or "N/A".
    type_raw: Mapped[str | None] = mapped_column(Text)
    # Season S = S-06-01 .. (S+1)-05-31; half 1 = June-December, 2 = January-May.
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    half: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TeamSync(Base):
    __tablename__ = "team_syncs"
    __table_args__ = (CheckConstraint(_in("kind", TEAM_SYNC_KINDS), name="kind_allowed"),)

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure: Mapped[str | None] = mapped_column(Text)
    row_count: Mapped[int | None] = mapped_column(Integer)
