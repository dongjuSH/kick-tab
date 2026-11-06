"""Team search (SCH-006, HIST-002, D-16): Korean/English aliases.

Candidates are one season's teams of the supported competitions (five-league lists plus
teams seen in collected fixtures): the current season on the main schedule, the selected
season on past results - including teams without a current team detail (chat 05).
No result is ever replaced by another team; an
ambiguous alias returns every team it names so the user picks one.

`match_teams()` is the shared matcher: team browse (chat 07) filters the current five-league
members with it, so both screens find the same teams for the same words.
"""

from collections.abc import Mapping

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


def match_teams(session: Session, raw_query: str, teams: Mapping[int, Team]) -> list[int]:
    """Ids of `teams` whose English name or search alias contains the query, best first.

    Order: exact > prefix > contained match, then names that start with the query ("레알" ->
    레알 마드리드 before 비야레알), then Korean-named (five-league) teams, then the name."""
    query = normalize_name(raw_query)
    if not query:
        return []
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

    def order(team_id: int) -> tuple[int, bool, bool, str]:
        team = teams[team_id]
        display = team.name_ko or team.name_en
        return (
            best[team_id],
            not normalize_name(display).startswith(query),
            team.name_ko is None,
            display,
        )

    return sorted(best, key=order)


def search_teams(
    session: Session, raw_query: str, *, season: int | None = None
) -> list[TeamRef]:
    if not normalize_name(raw_query):
        return []
    season = season or settings.current_season
    candidate_ids = select(TeamCompetitionSeason.team_id).where(
        TeamCompetitionSeason.season == season
    )
    teams = {t.id: t for t in session.scalars(select(Team).where(Team.id.in_(candidate_ids)))}
    ordered = match_teams(session, raw_query, teams)
    # Detail availability always follows the current season's allow set (past teams: false).
    lookup = team_detail_lookup(session)
    return [team_ref(teams[i], lookup) for i in ordered[:SEARCH_LIMIT]]
