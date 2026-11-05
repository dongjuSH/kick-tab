"""Reference data (chat 03): competitions, seasons, teams, season participation, aliases.

IDs are API-Football IDs (guide §6.3). Values the API leaves empty stay NULL.
"""

from datetime import date, datetime

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COMPETITION_GROUPS = ("EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEFA")
COMPETITION_TYPES = ("league", "cup", "uefa")
SEASON_AVAILABILITY = ("available", "no_data")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Competition(Base):
    """The 14 supported competitions (CMP-001). Seeded from app/seed/competitions.py."""

    __tablename__ = "competitions"
    __table_args__ = (
        CheckConstraint(_in("group_key", COMPETITION_GROUPS), name="group_allowed"),
        CheckConstraint(_in("type", COMPETITION_TYPES), name="type_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    group_key: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    name_ko: Mapped[str | None] = mapped_column(Text)
    short_name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    logo_url: Mapped[str | None] = mapped_column(Text)


class CompetitionSeason(Base):
    """Per competition and season: provider availability and the last sync results.

    `no_data` means the provider has no such season (e.g. Coupe de France 2026, V-16); a
    failed request never changes availability (CMP-004).
    """

    __tablename__ = "competition_seasons"
    __table_args__ = (
        CheckConstraint(_in("availability", SEASON_AVAILABILITY), name="availability_allowed"),
    )

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    availability: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # Last successful team-list sync (5 leagues only): the team-detail allow set is known
    # only when every league has one.
    teams_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fixtures_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fixtures_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fixtures_window_start: Mapped[date | None] = mapped_column(Date)
    fixtures_window_end: Mapped[date | None] = mapped_column(Date)
    # Whole-season list (past results, chat 05): last success / failure of
    # /fixtures?league=&season=. The 21-day sync above never touches these.
    season_fixtures_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    season_fixtures_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    # Korean display name from the alias seed; NULL means "show name_en".
    name_ko: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeamCompetitionSeason(Base):
    """A team took part in a competition season (league team lists and seen fixtures)."""

    __tablename__ = "team_competition_seasons"
    __table_args__ = (Index("ix_team_competition_seasons_season", "season", "competition_id"),)

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )
    season: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)


class TeamAlias(Base):
    """Search and news aliases (P-11). `ambiguous` names match several teams: search shows
    candidates, news never uses them as the only evidence."""

    __tablename__ = "team_aliases"
    __table_args__ = (
        UniqueConstraint("team_id", "normalized", name="uq_team_aliases_team_normalized"),
        CheckConstraint("lang IN ('ko', 'en')", name="lang_allowed"),
        Index("ix_team_aliases_normalized", "normalized"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    for_search: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    for_news: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
