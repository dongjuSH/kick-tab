"""Team search for the main schedule (SCH-006, D-16): Korean/English aliases.

Candidates are the current-season teams of the supported competitions (five-league lists
plus teams seen in collected fixtures). No result is ever replaced by another team; an
ambiguous alias returns every team it names so the user picks one.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import Team, TeamAlias, TeamCompetitionSeason
from app.schemas.match import TeamRef
from app.services.reference import normalize_name, team_detail_lookup, team_ref

SEARCH_LIMIT = 10


def _rank(query: str, name: str) -> int | None:
    if name == query:
        return 0
    if name.startswith(query):
        return 1
    if query in name:
        return 2
    return None


def search_teams(session: Session, raw_query: str) -> list[TeamRef]:
    query = normalize_name(raw_query)
    if not query:
        return []
    season = settings.current_season
    candidate_ids = select(TeamCompetitionSeason.team_id).where(
        TeamCompetitionSeason.season == season
    )
    teams = {t.id: t for t in session.scalars(select(Team).where(Team.id.in_(candidate_ids)))}
    best: dict[int, int] = {}

    def consider(team_id: int, name: str) -> None:
        rank = _rank(query, name)
        if rank is not None and team_id in teams:
            best[team_id] = min(rank, best.get(team_id, rank))

    for team in teams.values():
        consider(team.id, normalize_name(team.name_en))
    aliases = session.execute(
        select(TeamAlias.team_id, TeamAlias.normalized).where(
            TeamAlias.for_search, TeamAlias.normalized.contains(query, autoescape=True)
        )
    ).all()
    for team_id, normalized in aliases:
        consider(team_id, normalized)

    lookup = team_detail_lookup(session)

    def order(team_id: int) -> tuple[int, bool, bool, str]:
        team = teams[team_id]
        display = team.name_ko or team.name_en
        # Best match first, then names that start with the query ("레알" -> 레알 마드리드
        # before 비야레알), then Korean-named (five-league) teams.
        return (
            best[team_id],
            not normalize_name(display).startswith(query),
            team.name_ko is None,
            display,
        )

    ordered = sorted(best, key=order)
    return [team_ref(teams[i], lookup) for i in ordered[:SEARCH_LIMIT]]
