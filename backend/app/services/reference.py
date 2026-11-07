"""Reference data helpers: competitions, teams, aliases and the team-detail allow set."""

import json
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import (
    Competition,
    CompetitionSeason,
    Team,
    TeamAlias,
    TeamCompetitionSeason,
)
from app.schemas.match import CompetitionRef, TeamRef
from app.seed.competitions import COMPETITIONS, LEAGUE_IDS

ALIAS_SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "team_aliases.json"
UEFA_NAMES_PATH = ALIAS_SEED_PATH.with_name("uefa_team_names.json")
_IGNORED_CHARS = frozenset(" \t\n.-·'’`_/&()")


def normalize_name(text: str) -> str:
    """Lowercase, accents and spaces/punctuation removed: "Man. City" == "mancity",
    "맨체스터 시티" == "맨체스터시티", "Atlético" == "atletico". Hangul stays composed."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    composed = unicodedata.normalize("NFC", stripped).casefold()
    return "".join(ch for ch in composed if ch not in _IGNORED_CHARS)


def managed_seasons() -> list[int]:
    """Seasons kept for every competition, oldest first (2025 .. current, CMP-003)."""
    return list(range(settings.first_season, settings.current_season + 1))


def upsert_competitions(session: Session) -> None:
    """Seeded rows; name_en and logo come from the provider later and are kept."""
    for order, seed in enumerate(COMPETITIONS):
        stmt = insert(Competition).values(
            id=seed.id,
            group_key=seed.group_key,
            type=seed.type,
            name_en=seed.short_name,
            name_ko=seed.name_ko,
            short_name=seed.short_name,
            sort_order=order,
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Competition.id],
                set_={
                    "group_key": stmt.excluded.group_key,
                    "type": stmt.excluded.type,
                    "name_ko": stmt.excluded.name_ko,
                    "short_name": stmt.excluded.short_name,
                    "sort_order": stmt.excluded.sort_order,
                },
            )
        )


def upsert_teams(session: Session, teams: Iterable[dict[str, Any]], now: datetime) -> None:
    """Provider identity only; the Korean name from the alias seed is never overwritten.

    A team dict may carry the `venue` block of /teams?league=&season= (chat 08): a field it
    gives (`name`, `capacity`) is stored as given (null clears it); a field it leaves out, or
    an answer without a venue block (fixtures, player lists), keeps the stored value
    (Codex 1차 지적 5)."""
    rows = {t["id"]: t for t in teams if t.get("id") and t.get("name")}
    for team in rows.values():
        venue = team.get("venue") if isinstance(team.get("venue"), dict) else {}
        values: dict[str, Any] = {
            "id": team["id"],
            "name_en": team["name"],
            "logo_url": team.get("logo") or None,
            "country": team.get("country") or None,
            "updated_at": now,
        }
        if "name" in venue:
            values["venue_name"] = venue["name"] or None
        if "capacity" in venue:
            capacity = venue["capacity"]
            usable = isinstance(capacity, int) and not isinstance(capacity, bool) and capacity > 0
            values["venue_capacity"] = capacity if usable else None
        stmt = insert(Team).values(**values)
        update = {"name_en": stmt.excluded.name_en, "updated_at": now}
        update["logo_url"] = func.coalesce(stmt.excluded.logo_url, Team.logo_url)
        for column in ("venue_name", "venue_capacity"):
            if column in values:
                update[column] = getattr(stmt.excluded, column)
        if team.get("country"):
            update["country"] = stmt.excluded.country
        session.execute(stmt.on_conflict_do_update(index_elements=[Team.id], set_=update))


def add_participation(session: Session, pairs: Iterable[tuple[int, int, int]]) -> None:
    """(team_id, competition_id, season) rows; existing ones are left as they are."""
    values = [
        {"team_id": t, "competition_id": c, "season": s} for t, c, s in set(pairs)
    ]
    if values:
        session.execute(insert(TeamCompetitionSeason).values(values).on_conflict_do_nothing())


@dataclass(frozen=True)
class AliasSeedResult:
    teams_named: int
    aliases: int
    missing_team_ids: tuple[int, ...]


def load_alias_seed(path: Path = ALIAS_SEED_PATH) -> dict[str, Any]:
    seed = json.loads(path.read_text(encoding="utf-8"))
    if path == ALIAS_SEED_PATH:
        existing = {entry["id"] for entry in seed["teams"]}
        for entry in json.loads(UEFA_NAMES_PATH.read_text(encoding="utf-8")):
            if entry["id"] in existing:
                continue
            # Do not turn short names such as Riga, Viking or Bravo into news evidence.
            # Korean display names and full provider names are still searchable.
            aliases = entry["aliases"]
            search_only = [*aliases]
            if " " not in entry["en"]:
                search_only.extend([entry["en"], entry["nameKo"]])
            seed["teams"].append({
                "id": entry["id"], "nameKo": entry["nameKo"],
                "ko": aliases, "en": [entry["en"]], "searchOnly": search_only,
            })
    return seed


def apply_alias_seed(session: Session, seed: dict[str, Any]) -> AliasSeedResult:
    """Replace every alias row with the seed (P-11). Teams not in the DB yet are skipped
    and reported; they are applied on the next run after the team is collected."""
    known = set(session.scalars(select(Team.id)))
    session.execute(delete(TeamAlias))
    rows: dict[tuple[int, str], dict[str, Any]] = {}
    missing: list[int] = []
    named = 0

    def add(team_id: int, alias: str, *, ambiguous: bool, for_news: bool) -> None:
        normalized = normalize_name(alias)
        if not normalized:
            return
        lang = "en" if alias.isascii() else "ko"
        key = (team_id, normalized)
        if key in rows and not ambiguous:
            return  # an explicit team alias wins over an ambiguous group entry
        rows[key] = {
            "team_id": team_id,
            "alias": alias,
            "normalized": normalized,
            "lang": lang,
            "ambiguous": ambiguous,
            "for_search": True,
            "for_news": for_news and not ambiguous,
        }

    for entry in seed["teams"]:
        team_id = int(entry["id"])
        if team_id not in known:
            missing.append(team_id)
            continue
        session.execute(
            Team.__table__.update().where(Team.id == team_id).values(name_ko=entry["nameKo"])
        )
        named += 1
        # Search-only aliases: short forms that are clear in a search box but too risky as
        # the only evidence in a headline (e.g. a city name shared with another club).
        search_only = set(entry.get("searchOnly", []))
        for alias in [entry["nameKo"], *entry.get("ko", []), *entry.get("en", [])]:
            add(team_id, alias, ambiguous=False, for_news=alias not in search_only)

    for alias, team_ids in seed.get("ambiguous", {}).items():
        for team_id in team_ids:
            if int(team_id) in known:
                add(int(team_id), alias, ambiguous=True, for_news=False)

    if rows:
        session.execute(insert(TeamAlias).values(list(rows.values())))
    return AliasSeedResult(named, len(rows), tuple(missing))


def crest(url: str | None) -> str | None:
    """Only rights-cleared images are sent when IMAGE_RIGHTS_ENFORCED (guide §6.5, V-10).
    No asset is cleared yet, so enforcement means the placeholder everywhere."""
    return None if settings.image_rights_enforced else url


DetailLookup = Callable[[int], bool | None]


def team_detail_lookup(session: Session, season: int | None = None) -> DetailLookup:
    """Team detail is offered only to current-season five-league teams (D-15).

    A team is allowed only as a member of a league whose current team list was collected
    (`teams_synced_at`): rows that came from fixtures alone do not confirm membership, so the
    links and the team-detail direct URL decide alike (08, Codex 1차 지적 2). The set is
    complete once every league's list has been collected; until then a team outside it is
    `None` (unknown), never "not available"."""
    season = season or settings.current_season
    synced = set(
        session.scalars(
            select(CompetitionSeason.competition_id).where(
                CompetitionSeason.season == season,
                CompetitionSeason.competition_id.in_(LEAGUE_IDS),
                CompetitionSeason.teams_synced_at.is_not(None),
            )
        )
    )
    allowed = set(
        session.scalars(
            select(TeamCompetitionSeason.team_id).where(
                TeamCompetitionSeason.season == season,
                TeamCompetitionSeason.competition_id.in_(synced),
            )
        )
    )
    complete = len(synced) == len(LEAGUE_IDS)
    return lambda team_id: True if team_id in allowed else (False if complete else None)


def team_ref(team: Team, lookup: DetailLookup) -> TeamRef:
    return TeamRef(
        id=team.id,
        name_ko=team.name_ko,
        name_en=team.name_en,
        crest_url=crest(team.logo_url),
        detail_available=lookup(team.id),
    )


def competition_ref(competition: Competition) -> CompetitionRef:
    return CompetitionRef(
        id=competition.id, name_ko=competition.name_ko, short_name=competition.short_name
    )
