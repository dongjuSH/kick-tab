"""Rule-based news classification (PRD 17장, NEWS-002·003, P-08). No AI, no article body.

Only the title and the provider description are read. Missing an article is preferred to
a wrong label:
- a competition badge needs an explicit competition name in the text, and the story must be
  about it: the headline names the competition, or names a team playing in that very
  competition this season; a team's league or next opponent alone is never used;
- UEFA wins over a domestic league named in the same article; two domestic leagues and no
  UEFA is ambiguous (no badge);
- other confederations (AFC·CAF…) and other-country leagues invalidate the matching
  evidence; women's football and other sports exclude the article;
- teams are linked only by unambiguous aliases (team_aliases.for_news), several per article.
"""

import html
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

_TAG = re.compile(r"<[^>]*>")
_COMPACT_DROP = re.compile(r"[\s.\-·'’`_/&()\[\]「」『』\"“”,:;!?…]+")


def plain_text(value: str) -> str:
    """Provider text without <b> tags and HTML entities."""
    return html.unescape(_TAG.sub("", value or "")).strip()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped).casefold()


def _compact(text: str) -> str:
    return _COMPACT_DROP.sub("", _fold(text))


@dataclass(frozen=True)
class CompetitionRule:
    """Explicit names of one competition. UEFA's three competitions are kept apart so a
    team's participation is checked against the competition actually named."""

    competition_id: int
    badge: str
    # Matched in the compact text (Korean, no spaces) / as whole words (English).
    ko: tuple[str, ...]
    en: tuple[str, ...]


COMPETITION_RULES: tuple[CompetitionRule, ...] = (
    CompetitionRule(39, "EPL", ("프리미어리그",), ("premier league", "epl")),
    CompetitionRule(140, "LaLiga", ("라리가", "프리메라리가"), ("laliga", "la liga")),
    CompetitionRule(135, "SerieA", ("세리에a",), ("serie a",)),
    CompetitionRule(78, "Bundesliga", ("분데스리가",), ("bundesliga",)),
    CompetitionRule(61, "Ligue1", ("리그앙",), ("ligue 1", "ligue1")),
    CompetitionRule(2, "UEFA", ("챔피언스리그", "챔스"), ("champions league", "ucl")),
    CompetitionRule(3, "UEFA", ("유로파리그",), ("europa league", "uel")),
    CompetitionRule(848, "UEFA", ("컨퍼런스리그", "콘퍼런스리그"), ("conference league", "uecl")),
)

_OTHER_COUNTRY = (
    "러시아|우크라이나|이집트|인도|카자흐스탄|벨라루스|아르메니아|바레인|쿠웨이트|이라크|요르단|"
    "레바논|시리아|팔레스타인|가나|케냐|탄자니아|우간다|잠비아|말라위|홍콩|캐나다|싱가포르|"
    "스코틀랜드|북아일랜드|웨일스|몰타|오스트리아|브라질|에콰도르|볼리비아|베트남|태국"
)

# Compact-text patterns showing the text may mean another competition: any match drops
# that badge's evidence for the whole article.
BADGE_EXCLUDES: dict[str, tuple[str, ...]] = {
    "UEFA": (
        # Latin codes only as whole tokens ("lafc" is a club, not the AFC).
        r"(?<![a-z])(afc|caf|ofc|concacaf)(?![a-z])|아시아|아시안|아프리카|북중미|오세아니아|k리그",
        # AFC Champions League Elite / Two ("ACL" alone also means a knee ligament).
        r"acl(엘리트|2)|챔피언스리그(엘리트|2)",
    ),
    "EPL": (rf"({_OTHER_COUNTRY}|인디언|다트)프리미어리그", r"프리미어리그2"),
    "LaLiga": (r"라리가2",),
    "SerieA": (rf"({_OTHER_COUNTRY})세리에a",),
    "Bundesliga": (rf"({_OTHER_COUNTRY}|2)분데스리가", r"분데스리가2"),
}

# The story happens in a league outside the supported ones (e.g. a former Premier League
# player now in MLS): a competition named only as background is not the subject.
OTHER_LEAGUE_CONTEXT = (
    r"(?<![a-z])(lafc|mls)(?![a-z])|메이저리그사커|인터마이애미|서부컨퍼런스|동부컨퍼런스|"
    r"알나스르|알힐랄|알이티하드|사우디프로리그|j리그|중국슈퍼리그"
)

_CLAUSE_BOUNDARY = re.compile(r"[,.;!?…]+")
_BACKGROUND = re.compile(
    r"출신|시절|과거|전직|옛\s|\b전\s+|몸담았|활약했|회상|비교|지난해|"
    r"전\s*소속|\bformer\b|\bpreviously\b|\bcompared\b", re.IGNORECASE
)


def subject_text(value: str) -> str:
    """A historical/comparative clause alone is insufficient evidence for a badge."""
    return " ".join(
        clause for clause in _CLAUSE_BOUNDARY.split(plain_text(value))
        if not _BACKGROUND.search(clause)
    )


def other_league(*texts: str) -> bool:
    folded, compact = _parts(*texts)
    return bool(re.search(OTHER_LEAGUE_CONTEXT, folded) or re.search(OTHER_LEAGUE_CONTEXT, compact))

# Women's football is out of scope (P-08): the whole article is dropped before any team is
# linked, since the aliases name the men's clubs (남녀 대회 혼동 배제).
WOMEN_MARKERS = (
    # "라리가F" (Liga F), not "프리메라리가 FC바르셀로나" once spaces are gone.
    r"여자축구|여자부|여자팀|wsl|위민|라리가f(?!c)|"
    r"(여자|여성)(프리미어리그|라리가|프리메라리가|세리에a|분데스리가|리그앙|챔피언스리그|챔스)"
)

# A competition name alone (e.g. a sponsor's "UEFA Champions League" partnership) is not
# football news: the article must also name a team or one of these match/club words.
FOOTBALL_CONTEXT = (
    "축구", "경기", "골", "감독", "선수", "득점", "승리", "패배", "무승부", "라운드", "강전",
    "조별", "리그페이즈", "원정", "이적", "부상", "선발", "우승", "결승",
)

# Articles about another sport, a game title or sports betting are dropped entirely.
OTHER_SPORTS = (
    "다트", "크리켓", "배구", "농구", "핸드볼", "e스포츠", "이스포츠", "당구", "럭비", "하키",
    "fc온라인", "fc모바일", "피파온라인", "풋볼매니저",
    "축구토토", "승무패", "프로토", "베트맨",
)


def _english(text: str, words: Iterable[str]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text) for w in words)


def _mentioned(folded: str, compact: str) -> set[int]:
    """Competition ids named in the text, minus badges whose evidence is excluded."""
    excluded = {
        badge for badge, patterns in BADGE_EXCLUDES.items()
        if any(re.search(p, compact) for p in patterns)
    }
    return {
        rule.competition_id
        for rule in COMPETITION_RULES
        if rule.badge not in excluded
        and (any(k in compact for k in rule.ko) or _english(folded, rule.en))
    }


def _parts(*texts: str) -> tuple[str, str]:
    raw = " ".join(plain_text(t) for t in texts)
    return _fold(raw), _compact(raw)


_BADGE_OF = {rule.competition_id: rule.badge for rule in COMPETITION_RULES}


def choose_badge(badges: set[str]) -> str | None:
    if "UEFA" in badges:
        return "UEFA"
    return next(iter(badges)) if len(badges) == 1 else None


@dataclass
class AliasIndex:
    """Unambiguous news aliases: Korean by compact substring, English by whole words."""

    ko: list[tuple[str, int]] = field(default_factory=list)
    en: list[tuple[re.Pattern[str], int]] = field(default_factory=list)

    @classmethod
    def build(cls, aliases: Iterable[tuple[str, int]]) -> "AliasIndex":
        index = cls()
        for alias, team_id in aliases:
            if alias.isascii():
                word = _fold(alias).strip()
                if word:
                    pattern = re.compile(
                        rf"(?<![a-z0-9]){re.escape(word).replace(r'\ ', r'\s+')}(?![a-z0-9])"
                    )
                    index.en.append((pattern, team_id))
            else:
                compact = _compact(alias)
                if compact:
                    index.ko.append((compact, team_id))
        return index

    def lead_team(self, text: str) -> int | None:
        """The team named first: the subject of a description that opens with it."""
        folded, compact = _parts(text)
        hits = [(compact.find(a) / max(len(compact), 1), t) for a, t in self.ko if a in compact]
        for pattern, team in self.en:
            match = pattern.search(folded)
            if match:
                hits.append((match.start() / max(len(folded), 1), team))
        return min(hits)[1] if hits else None

    def teams(self, title: str, description: str) -> set[int]:
        raw = f"{plain_text(title)} {plain_text(description)}"
        folded, compact = _fold(raw), _compact(raw)
        found = {team for alias, team in self.ko if alias in compact}
        found |= {team for pattern, team in self.en if pattern.search(folded)}
        return found


@dataclass(frozen=True)
class Classification:
    badge: str | None
    team_ids: tuple[int, ...]
    excluded_reason: str | None = None

    @property
    def keep(self) -> bool:
        return self.excluded_reason is None and (self.badge is not None or bool(self.team_ids))


Participation = Mapping[int, frozenset[int]]


def subject_competitions(
    title: str, description: str, index: "AliasIndex", participation: Participation
) -> set[int]:
    """Competitions the story is about, not merely mentions (PRD 17장: 명시된 근거).

    A named competition counts when the headline names it, or when the story's subject team
    takes part in that very competition this season (a Europa League memory does not label
    a story about a club now in the Champions League). The subject team is the headline's
    team, or, with no team in the headline, the first team in the description. When the
    text is set in another league (MLS, Saudi…), only a headline team counts.
    """
    original_title, original_description = title, description
    title, description = subject_text(title), subject_text(description)
    mentioned = _mentioned(*_parts(title, description)) & _mentioned(
        *_parts(original_title, original_description)
    )
    in_title = _mentioned(*_parts(title))
    title_teams = index.teams(title, "")

    def played_by(teams: Iterable[int]) -> set[int]:
        return {c for c in mentioned if any(c in participation.get(t, ()) for t in teams)}

    if other_league(original_title, original_description):
        return played_by(title_teams)
    lead = index.lead_team(description)
    subjects = title_teams or ({lead} if lead is not None else set())
    return (mentioned & in_title) | played_by(subjects)


def classify(
    title: str,
    description: str,
    index: "AliasIndex",
    participation: Participation | None = None,
) -> Classification:
    compact = _compact(f"{plain_text(title)} {plain_text(description)}")
    if any(word in compact for word in OTHER_SPORTS):
        return Classification(None, (), "other_sport")
    if re.search(WOMEN_MARKERS, compact):
        return Classification(None, (), "women")
    subjects = subject_competitions(title, description, index, participation or {})
    badges = {_BADGE_OF[c] for c in subjects}
    badge = choose_badge(badges)
    title_teams = index.teams(subject_text(title), "")
    linked = index.teams(subject_text(title), subject_text(description))
    # A team named only in the background of an out-of-scope story is not a team news item.
    teams = tuple(sorted(title_teams if other_league(title, description) else linked))
    if not teams and not any(word in compact for word in FOOTBALL_CONTEXT):
        reason = "no_football_context"
    elif badge is None and len(badges) > 1:
        reason = "several_leagues"
    elif badge is None and not teams:
        reason = "no_evidence"
    else:
        reason = None
    return Classification(badge, teams, reason)
