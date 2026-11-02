"""Chat 03 pure rules: status mapping, names, news classification, URL dedupe, cursors."""

from datetime import UTC, datetime

import pytest

from app.models.fixture import Fixture
from app.services.fixtures import _score
from app.services.match_status import map_status
from app.services.news import InvalidCursor, decode_cursor, encode_cursor
from app.services.news_classify import (
    _BADGE_OF,
    AliasIndex,
    Classification,
    _mentioned,
    _parts,
    classify,
    plain_text,
)
from app.services.reference import normalize_name
from app.sync.news import normalize_url, url_hash


def competition_badges(title: str, description: str) -> set[str]:
    """Badges whose competition is named in the text (exclusions applied, no subject rule)."""
    return {_BADGE_OF[c] for c in _mentioned(*_parts(title, description))}


@pytest.mark.parametrize(
    ("short", "status", "finish", "confirmed"),
    [
        ("NS", "scheduled", None, True),
        ("TBD", "scheduled", None, False),
        ("1H", "live", None, True),
        ("HT", "live", None, True),
        ("ET", "live", None, True),
        ("BT", "live", None, True),
        ("P", "live", None, True),
        ("LIVE", "live", None, True),
        ("SUSP", "live", None, True),
        ("INT", "live", None, True),
        ("FT", "finished", "normal", True),
        ("AET", "finished", "aet", True),
        ("PEN", "finished", "pen", True),
        ("AWD", "finished", "awarded", True),
        ("WO", "finished", "walkover", True),
        ("PST", "postponed", None, False),
        ("CANC", "cancelled", None, True),
        ("Canc", "cancelled", None, True),
        ("ABD", "abandoned", None, True),
        ("XYZ", "unknown", None, True),
        ("", "unknown", None, True),
    ],
)
def test_status_table(short, status, finish, confirmed):
    mapped = map_status(short)
    assert (mapped.status, mapped.finish_type, mapped.time_confirmed) == (
        status,
        finish,
        confirmed,
    )


def _fixture(status, finish=None, goals=(0, 0), penalty=(None, None)):
    return Fixture(
        status=status,
        finish_type=finish,
        goals_home=goals[0],
        goals_away=goals[1],
        score={"penalty": {"home": penalty[0], "away": penalty[1]}},
    )


def test_score_never_invents_results():
    # The provider sends 0-0 for cancelled/not-started matches: that is not a score.
    for status in ("scheduled", "postponed", "cancelled"):
        score = _score(_fixture(status))
        assert (score.home, score.away) == (None, None)
    pen = _score(_fixture("finished", "pen", goals=(1, 1), penalty=(4, 2)))
    assert (pen.home, pen.away, pen.penalty_home, pen.penalty_away) == (1, 1, 4, 2)
    normal = _score(_fixture("finished", "normal", goals=(2, 0), penalty=(None, None)))
    assert (normal.penalty_home, normal.penalty_away) == (None, None)
    abandoned = _score(_fixture("abandoned", goals=(1, 1)))
    assert (abandoned.home, abandoned.away) == (1, 1)  # score at the stoppage
    missing = _score(_fixture("live", goals=(None, None)))
    assert (missing.home, missing.away) == (None, None)


def test_normalize_name():
    assert normalize_name("Man. City") == normalize_name("man city") == "mancity"
    assert normalize_name("맨체스터 시티") == "맨체스터시티"
    assert normalize_name("Atlético Madrid") == "atleticomadrid"
    assert normalize_name("1. FC Köln") == "1fckoln"


INDEX = AliasIndex.build(
    [
        ("맨시티", 50),
        ("맨체스터 시티", 50),
        ("Man City", 50),
        ("레알 마드리드", 541),
        ("Real Madrid", 541),
        ("토트넘", 47),
        ("아스널", 42),
    ]
)


def test_uefa_and_several_teams():
    result = classify("맨시티·레알 마드리드, 챔스 리그 페이즈 맞대결", "", INDEX)
    assert result.badge == "UEFA" and result.team_ids == (50, 541) and result.keep


def test_uefa_wins_over_domestic_league():
    assert classify("토트넘, 프리미어리그 이어 챔피언스리그도 승리", "", INDEX).badge == "UEFA"


def test_league_badge_needs_explicit_competition():
    # Team names alone never imply the league badge.
    only_team = classify("토트넘, 아스널전 앞두고 훈련", "", INDEX)
    assert only_team.badge is None and only_team.team_ids == (42, 47) and only_team.keep
    assert classify("손흥민 프리미어리그 복귀설", "", INDEX).badge == "EPL"


def test_ambiguous_aliases_are_not_evidence():
    result = classify("시티, 레알과 비교되는 이유", "", INDEX)
    assert result.team_ids == () and result.badge is None and not result.keep


def test_two_domestic_leagues_are_ambiguous():
    result = classify("프리미어리그·라리가 구단 동시 이적 관심", "", INDEX)
    assert result.badge is None and result.excluded_reason == "several_leagues"


def test_competition_name_without_football_context_is_excluded():
    sponsor = classify("스포츠 브랜드, 카드사와 제휴…챔피언스리그 자산 활용", "", INDEX)
    assert sponsor.excluded_reason == "no_football_context" and not sponsor.keep


@pytest.mark.parametrize(
    "text",
    [
        "울산, AFC 챔피언스리그 엘리트 16강",
        "ACL 엘리트 조별리그 첫 경기",
        "K리그 팀의 챔피언스리그 도전",
    ],
)
def test_other_confederations_are_not_uefa(text):
    assert "UEFA" not in competition_badges(text, "")


def test_club_names_containing_afc_are_not_the_afc():
    assert competition_badges("LAFC 이적 손흥민, 유로파리그 우승 회상", "") == {"UEFA"}


def test_headline_competition_wins_over_passing_mentions():
    result = classify("라치오, 세리에A 선두 질주", "챔피언스리그 진출 경쟁도 본격화", INDEX)
    assert result.badge == "SerieA"


TOTTENHAM, PALACE = 47, 52
PARTICIPATION = {TOTTENHAM: frozenset({39, 2}), 42: frozenset({39, 2})}


def test_description_mention_needs_a_headline_team_in_that_competition():
    # No competition and no team in the headline: a mention lower down is background.
    assert classify("감독 경질설", "프리미어리그 9라운드 패배 이후 비판", INDEX).badge is None
    # A headline team playing in the named competition makes it the subject.
    match = classify("토트넘, 2-0 완승", "프리미어리그 9라운드에서 승리했다", INDEX, PARTICIPATION)
    assert match.badge == "EPL"


def test_description_lead_team_is_the_subject_when_the_headline_has_none():
    report = classify(
        "김민재 풀타임 혹평", "토트넘은 1일 프리미어리그 9라운드에서", INDEX, PARTICIPATION
    )
    assert report.badge == "EPL"
    # A headline team decides; another club leading the description does not relabel it.
    other = classify(
        "토트넘, 한국인 골잡이 주목",
        "아스널전 활약 이후 프리미어리그 구단들이",
        INDEX,
        {42: frozenset({39})},
    )
    assert other.badge is None


def test_past_competition_of_a_club_is_not_the_subject():
    # Tottenham plays the Champions League this season; a Europa League memory is history.
    result = classify(
        "토트넘 절친의 속사정", "토트넘은 지난해 유로파리그 정상에 올랐다", INDEX, PARTICIPATION
    )
    assert result.badge is None and result.team_ids == (TOTTENHAM,) and result.keep


def test_story_set_in_another_league_is_not_labelled():
    # A former Premier League player now in MLS: "EPL" in the headline is only contrast.
    result = classify(
        "'EPL도 아닌데' 손흥민 길어지는 침묵",
        "LAFC는 서부 컨퍼런스 6위에 머물렀다",
        INDEX,
        PARTICIPATION,
    )
    assert result.badge is None and not result.keep
    # A Premier League club in the headline still counts despite a Saudi transfer rumour.
    rumour = classify(
        "아스널 공격수, 알힐랄 이적설", "프리미어리그 선두 아스널의 주전", INDEX, PARTICIPATION
    )
    assert rumour.badge == "EPL"


def test_acl_knee_injury_is_not_asian_competition():
    assert competition_badges("ACL 부상 복귀 앞둔 챔피언스리그", "") == {"UEFA"}


@pytest.mark.parametrize(
    ("text", "badge"),
    [
        ("브라질 세리에A 우승 경쟁", None),
        ("러시아 프리미어리그 이적", None),
        ("오스트리아 분데스리가 득점왕", None),
        ("2. 분데스리가 승격 경쟁", None),
        ("K리그1 파이널A 확정", None),
        ("리그앙 선두 PSG", "Ligue1"),
        ("Série A 최고 수비수", "SerieA"),
    ],
)
def test_other_country_leagues(text, badge):
    found = competition_badges(text, "")
    assert (next(iter(found)) if len(found) == 1 else None) == badge


def test_other_sports_and_betting_are_excluded():
    assert classify("PDC 프리미어리그 다트 우승", "", INDEX).excluded_reason == "other_sport"
    assert classify("축구토토 승무패 회차 결과 - 챔피언스리그", "", INDEX).keep is False


@pytest.mark.parametrize(
    "title, description",
    [
        ("아스널 위민 여자축구 승리", "아스널 여자축구팀이 승리했다"),
        ("맨시티, 여자 프리미어리그 선두", "맨시티 여자팀이 이겼다"),
        ("바르셀로나 라리가F 우승", ""),
        ("여자 챔피언스리그 결승", "바르셀로나 승리"),
        ("WSL 득점왕, 프리미어리그 시상식", ""),
    ],
)
def test_womens_football_is_dropped_before_team_links(title, description):
    result = classify(title, description, INDEX)
    assert result == Classification(None, (), "women") and not result.keep


def test_fc_after_a_league_name_is_not_liga_f():
    description = "스페인 프리메라리가(라리가) FC바르셀로나가 승리했다"
    result = classify("라리가 바르셀로나 승리", description, INDEX)
    assert result.excluded_reason is None and result.badge == "LaLiga"


def test_plain_text_strips_markup():
    assert plain_text("<b>맨시티</b> &quot;승리&quot;") == '맨시티 "승리"'


def test_english_aliases_match_whole_words():
    index = AliasIndex.build([("Inter", 505)])
    assert index.teams("Inter beat Milan", "") == {505}
    assert index.teams("International break", "") == set()


def test_url_normalization_merges_duplicates():
    a = normalize_url("https://www.example.com/news/1/?utm_source=naver#top")
    b = normalize_url("http://m.example.com/news/1")
    assert a == b == "https://example.com/news/1"
    assert url_hash(a) == url_hash(b) and len(url_hash(a)) == 64
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("ftp://example.com/a") is None


def test_news_cursor_round_trip():
    stamp = datetime(2026, 11, 2, 6, 26, tzinfo=UTC)
    assert decode_cursor(encode_cursor(stamp, 42)) == (stamp, 42)
    with pytest.raises(InvalidCursor):
        decode_cursor("not-a-cursor")
