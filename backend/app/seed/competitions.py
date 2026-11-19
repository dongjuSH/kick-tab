"""The 21 supported competitions (CMP-001·002, PRD 5장). IDs verified 2026-10-29; the seven
super cups / club world cup added 2026-11-19 (00 /leagues check, all type Cup).

name_ko is the one name shown everywhere (COM-003, '리그 1' kept by user decision 2026-11-19);
short_name stays the provider-style English label (search aliases, logs). group_key is the
picker group: the five countries with their domestic cups and super cup, UEFA, FIFA.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CompetitionSeed:
    id: int
    group_key: str
    type: str
    name_ko: str
    short_name: str


COMPETITIONS: tuple[CompetitionSeed, ...] = (
    CompetitionSeed(39, "EPL", "league", "프리미어리그", "Premier League"),
    CompetitionSeed(45, "EPL", "cup", "FA컵", "FA Cup"),
    CompetitionSeed(48, "EPL", "cup", "EFL컵", "EFL Cup"),
    CompetitionSeed(528, "EPL", "cup", "FA 커뮤니티 실드", "Community Shield"),
    CompetitionSeed(140, "LaLiga", "league", "라리가", "LaLiga"),
    CompetitionSeed(143, "LaLiga", "cup", "코파 델 레이", "Copa del Rey"),
    CompetitionSeed(556, "LaLiga", "cup", "스페인 슈퍼컵", "Super Cup"),
    CompetitionSeed(135, "SerieA", "league", "세리에 A", "Serie A"),
    CompetitionSeed(137, "SerieA", "cup", "코파 이탈리아", "Coppa Italia"),
    CompetitionSeed(547, "SerieA", "cup", "이탈리아 슈퍼컵", "Super Cup"),
    CompetitionSeed(78, "Bundesliga", "league", "분데스리가", "Bundesliga"),
    CompetitionSeed(81, "Bundesliga", "cup", "DFB 포칼", "DFB-Pokal"),
    CompetitionSeed(529, "Bundesliga", "cup", "독일 슈퍼컵", "Super Cup"),
    CompetitionSeed(61, "Ligue1", "league", "리그 1", "Ligue 1"),
    CompetitionSeed(66, "Ligue1", "cup", "쿠프 드 프랑스", "Coupe de France"),
    CompetitionSeed(526, "Ligue1", "cup", "프랑스 슈퍼컵", "Trophée des Champions"),
    CompetitionSeed(2, "UEFA", "uefa", "UEFA 챔피언스리그", "Champions League"),
    CompetitionSeed(3, "UEFA", "uefa", "UEFA 유로파리그", "Europa League"),
    CompetitionSeed(848, "UEFA", "uefa", "UEFA 컨퍼런스리그", "Conference League"),
    # One-match cups: no team lists (UEFA_IDS stays the three club competitions).
    CompetitionSeed(531, "UEFA", "cup", "UEFA 슈퍼컵", "UEFA Super Cup"),
    CompetitionSeed(15, "FIFA", "cup", "FIFA 클럽 월드컵", "FIFA Club World Cup"),
)

COMPETITION_IDS = frozenset(c.id for c in COMPETITIONS)
# The five leagues: team browse, standings and the team-detail allow set (D-15).
LEAGUE_IDS = tuple(c.id for c in COMPETITIONS if c.type == "league")
UEFA_IDS = tuple(c.id for c in COMPETITIONS if c.type == "uefa")


def season_label(season: int) -> str:
    """2026 -> "2026-27" (CMP-003)."""
    return f"{season}-{(season + 1) % 100:02d}"
