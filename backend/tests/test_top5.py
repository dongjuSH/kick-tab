"""AI weekly TOP 5 rules without a database: validation, public view selection, prompt,
Gemini wrapper and the operator alert."""

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from app.notifications.discord import Top5DelayNotice, build_top5_payload, notify_top5_delay
from app.providers import gemini
from app.providers.gemini import LlmError, generate_structured
from app.services import top5_selection as top5
from app.services.top5_selection import (
    LlmPick,
    LlmSelection,
    SelectionError,
    _form_summary,
    build_prompt,
    load_curation,
    validate_picks,
    week_bounds,
    window_end,
)
from app.services.top_matches import shown_publication

WEEK = date(2026, 11, 2)
IN_WEEK = datetime(2026, 11, 4, 10, tzinfo=UTC)


def candidates(n):
    return {1000 + i: IN_WEEK for i in range(n)}


def picks(*rows):
    return [LlmPick(fixture_id=f, rank=r, reason=reason) for f, r, reason in rows]


def test_week_bounds_are_kst():
    start, end = week_bounds(WEEK)
    assert start == datetime(2026, 11, 1, 15, 0, tzinfo=UTC)  # Monday 00:00 KST
    assert end == datetime(2026, 11, 8, 15, 0, tzinfo=UTC)  # next Monday 00:00 KST, excluded


def test_valid_selection_is_ordered_by_rank():
    items = validate_picks(
        picks(
            (1001, 2, "라이벌전 ·  최근 흐름"), (1000, 1, "상위권 맞대결"), (1002, 3, "순위 경쟁")
        ),
        candidates(3),
        WEEK,
    )
    assert items == [
        (1, 1000, "상위권 맞대결"),
        (2, 1001, "라이벌전 · 최근 흐름"),
        (3, 1002, "순위 경쟁"),
    ]


@pytest.mark.parametrize(
    ("rows", "count", "message"),
    [
        ([(1000, 1, "a"), (1001, 2, "b")], 5, "2 picks, expected 3"),  # min(5, 3)
        ([(1000, 1, "a"), (1000, 2, "b"), (1001, 3, "c")], 3, "duplicate"),
        ([(1000, 1, "a"), (1001, 2, "b"), (9999, 3, "c")], 3, "not a candidate"),
        ([(1000, 1, "a"), (1001, 1, "b"), (1002, 3, "c")], 3, "ranks"),
        ([(1000, 1, "a"), (1001, 2, " "), (1002, 3, "c")], 3, "one short line"),
        ([(1000, 1, "a"), (1001, 2, "x" * 61), (1002, 3, "c")], 3, "one short line"),
    ],
)
def test_invalid_selections_are_refused(rows, count, message):
    with pytest.raises(SelectionError, match=message):
        validate_picks(picks(*rows), candidates(min(count, 3)), WEEK)


def test_selection_outside_the_week_is_refused():
    outside = {1000: datetime(2026, 11, 8, 15, 0, tzinfo=UTC)}  # next Monday 00:00 KST
    with pytest.raises(SelectionError, match="outside"):
        validate_picks(picks((1000, 1, "a")), outside, WEEK)


def publication(version, week_start, kind):
    return SimpleNamespace(version=version, week_start=week_start, kind=kind)


@pytest.mark.parametrize(
    ("latest", "shown"),
    [
        (None, None),
        (publication(3, WEEK, "list"), 3),  # this week's result
        (publication(3, WEEK, "delayed"), 3),  # this week's delay notice
        (publication(2, date(2026, 10, 26), "list"), 2),  # last week kept while selecting
        (publication(2, date(2026, 10, 26), "none"), 2),  # last week's "no matches" kept
        (publication(2, date(2026, 10, 26), "delayed"), None),  # never last week's delay
        (publication(1, date(2026, 10, 19), "list"), None),  # two weeks old: not "last week"
    ],
)
def test_shown_publication(latest, shown):
    session = MagicMock()
    def by_week(query):
        requested = next(iter(query.compile().params.values()))
        return latest if latest is not None and latest.week_start == requested else None

    session.scalar.side_effect = by_week
    result = shown_publication(session, WEEK)
    assert (result.version if result else None) == shown


def test_prompt_lists_rules_and_candidates_only_as_given():
    prompt = build_prompt([{"fixtureId": 1000, "home": {"name": "맨체스터 시티"}}], 1)
    assert "정확히 1개" in prompt
    assert "제공되지 않은 사실" in prompt and "실제 시청률이나 인기 수치가 아니다" in prompt
    assert '"fixtureId":1000' in prompt


@pytest.mark.parametrize(
    "reason",
    ["분데스리가 1위 · 관심 팀 바이에른 뮌헨", "관심팀끼리의 맞대결", "국내 관심이 큰 경기",
     "관심도 높은 두 팀", "등록 팀 경기"],
)
def test_reason_implying_personal_favourites_is_refused(reason):
    # TOP 5 is not personalised (TOP-002, 2026-11-19): the operator tier is input only.
    with pytest.raises(SelectionError, match="personalisation"):
        validate_picks(picks((1000, 1, reason)), candidates(1), WEEK)


def test_reason_as_one_sentence_is_accepted():
    reason = "단판으로 트로피 주인이 정해지는 결승"
    assert validate_picks(picks((1000, 1, reason)), candidates(1), WEEK) == [(1, 1000, reason)]


def test_prompt_asks_for_a_sentence_without_favourites_or_lists():
    prompt = build_prompt([{"fixtureId": 1000, "home": {"name": "맨체스터 시티"}}], 1)
    assert "한국어 한 문장" in prompt and "40자 이내" in prompt
    assert "' · '나 쉼표로 나열하지 않는다" in prompt
    assert "'관심 팀'" in prompt and "선정 판단에만 쓰고" in prompt
    assert "standing이 null" in prompt and "Final은 단판 결승" in prompt
    # The old list-style example that taught "관심 팀 맞대결" is gone.
    assert "관심 팀 맞대결" not in prompt and "interest" not in prompt


def test_form_summary_counts_the_compact_lines():
    lines = ["W 1-0 H", "L 0-2 A", "D 3-3 H", "W 4-1 H"]
    assert _form_summary(lines) == "2승 1무 1패"
    assert _form_summary([]) is None


def test_curation_seed_has_unique_pairs_and_tiers():
    curation = load_curation()
    assert curation.version
    assert frozenset((42, 47)) in curation.derbies
    assert set(curation.interest.values()) <= {"high", "medium"}


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, models, **kwargs):
        self.models, self.kwargs = models, kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def use_fake(monkeypatch, models):
    created = []

    def factory(**kwargs):
        client = FakeClient(models, **kwargs)
        created.append(client)
        return client

    monkeypatch.setattr(gemini.genai, "Client", factory)
    return created


def test_gemini_structured_answer_is_validated(monkeypatch):
    answer = {"picks": [{"fixture_id": 1, "rank": 1, "reason": "상위권 맞대결"}]}
    models = FakeModels(SimpleNamespace(text=json.dumps(answer), candidates=[]))
    created = use_fake(monkeypatch, models)
    parsed, raw = generate_structured(
        "p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=30
    )
    assert parsed.picks[0].fixture_id == 1 and raw == answer
    options = created[0].kwargs["http_options"]
    assert created[0].kwargs["api_key"] == "k"
    assert options.timeout == 30_000 and options.retry_options.attempts == 1  # ms, no retry
    config = models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["properties"]["picks"]
    assert config.thinking_config is None  # empty level = the model's default
    generate_structured(
        "p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=30,
        thinking_level="low",
    )
    assert models.calls[1]["config"].thinking_config.thinking_level == "LOW"


def test_gemini_failures_are_safe_errors(monkeypatch):
    with pytest.raises(LlmError, match="not configured"):
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr(""), timeout_seconds=5)
    use_fake(monkeypatch, FakeModels(error=TimeoutError("secret-key-in-message")))
    with pytest.raises(LlmError) as info:
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=5)
    assert "secret" not in str(info.value)
    assert info.value.transient  # transport problems may be retried in the attempt
    use_fake(monkeypatch, FakeModels(SimpleNamespace(text='{"picks": "x"}', candidates=[])))
    with pytest.raises(LlmError, match="schema") as info:
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=5)
    assert not info.value.transient
    for code, transient in ((503, True), (504, True), (429, False), (400, False)):
        use_fake(monkeypatch, FakeModels(error=gemini.errors.APIError(code, {})))
        with pytest.raises(LlmError) as info:
            generate_structured("p", LlmSelection, model="m", api_key=SecretStr("k"),
                                timeout_seconds=5)
        assert info.value.transient is transient, code


NOTICE = Top5DelayNotice(WEEK, 2, "LLM failed: Gemini API error 429", IN_WEEK)
WEBHOOK = SecretStr("https://discord.com/api/webhooks/1/top5-token")


def test_delay_alert_payload_and_delivery():
    embed = build_top5_payload(NOTICE)["embeds"][0]
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["대상 주(KST)"] == "2026-11-02 ~ 2026-11-08"
    assert fields["자동 시도"] == "2회 실패"
    assert "app.sync top5" in fields["복구 명령"]
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(204)

    assert notify_top5_delay(NOTICE, webhook_url=WEBHOOK, transport=httpx.MockTransport(handler))
    assert len(sent) == 1


def test_failed_delay_alert_is_reported_not_retried():
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(500)

    assert not notify_top5_delay(
        NOTICE, webhook_url=WEBHOOK, transport=httpx.MockTransport(handler)
    )
    assert len(sent) == 1
    assert not notify_top5_delay(NOTICE, webhook_url=SecretStr(""))


def fake_call(results):
    """generate_structured stand-in: pops one result (an answer or an exception) per call."""
    calls = []

    def call(prompt, schema, *, model, api_key, timeout_seconds, thinking_level):
        calls.append((model, timeout_seconds, thinking_level))
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return LlmSelection(picks=[]), result

    return call, calls


class FakeClock:
    """monotonic stand-in: `sleep` and each call advance it."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def model_setup(monkeypatch, thinking="low"):
    monkeypatch.setattr(top5.settings, "top5_llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(top5.settings, "top5_llm_thinking_level", thinking)


def timed_call(clock, results):
    """generate_structured stand-in: each result is (seconds the request takes, answer or
    exception); the fake clock advances by that time."""
    calls = []

    def call(prompt, schema, *, model, api_key, timeout_seconds, thinking_level):
        calls.append((clock.now, timeout_seconds, thinking_level))
        took, result = results.pop(0)
        clock.now += took
        if isinstance(result, Exception):
            raise result
        return LlmSelection(picks=[]), result

    return call, calls


BUSY = LlmError("Gemini API error 503 UNAVAILABLE", transient=True)
SLOW = LlmError("Gemini API error 504 DEADLINE_EXCEEDED", transient=True)


def test_first_request_runs_until_the_00_05_slot_with_the_thinking_level(monkeypatch):
    # The 00:00 attempt's model time is 705 s (until 00:11:45): slots at 300 s and 600 s.
    model_setup(monkeypatch)
    clock = FakeClock()
    call, calls = timed_call(clock, [(23, {"picks": []})])
    _, raw = top5.gemini_generate("p", 705, call=call, clock=clock, sleep=clock.sleep)
    assert calls == [(0.0, 300.0, "low")]  # never past the next slot
    assert raw["model"] == "gemini-3.8-flash"


def test_errors_are_asked_again_only_at_00_05_and_00_10(monkeypatch):
    model_setup(monkeypatch)
    clock = FakeClock()
    call, calls = timed_call(clock, [(3, BUSY), (300, SLOW), (23, {"picks": []})])
    _, raw = top5.gemini_generate("p", 705, call=call, clock=clock, sleep=clock.sleep)
    # 503 at 3 s -> wait for 00:05 (300 s); 504 lasting until 00:10 -> the 00:10 slot at once.
    assert [c[0] for c in calls] == [0.0, 300.0, 600.0]
    assert [c[1] for c in calls] == [300.0, 300.0, 105.0]  # the last one until the end
    assert raw["model"] == "gemini-3.8-flash"


def test_at_most_three_requests_then_failure_names_every_error(monkeypatch):
    model_setup(monkeypatch)
    clock = FakeClock()
    call, calls = timed_call(clock, [(2, LlmError(f"Gemini API error 503 #{i}", transient=True))
                                     for i in range(4)])
    with pytest.raises(top5.ModelFailed) as info:
        top5.gemini_generate("p", 705, call=call, clock=clock, sleep=clock.sleep)
    assert len(calls) == top5.MAX_REQUESTS == 3
    assert str(info.value).startswith("gemini-3.8-flash: Gemini API error 503 #0 → ")


def test_no_retry_for_lasting_errors(monkeypatch):
    model_setup(monkeypatch)
    clock = FakeClock()
    call, calls = timed_call(clock, [(1, LlmError("Gemini API error 429 RESOURCE_EXHAUSTED"))])
    with pytest.raises(top5.ModelFailed):
        top5.gemini_generate("p", 705, call=call, clock=clock, sleep=clock.sleep)
    assert len(calls) == 1  # quota, bad request or bad answer: not asked again


def test_late_evidence_starts_at_the_next_usable_slot(monkeypatch):
    model_setup(monkeypatch)
    # Evidence ready at 00:04:45 (285 s into the 705 s): 15 s before 00:05 is too short,
    # so the first request is the 00:05 one; with under 30 s in total nothing is sent.
    clock = FakeClock()
    call, calls = timed_call(clock, [(23, {"picks": []})])
    top5.gemini_generate("p", 420, call=call, clock=clock, sleep=clock.sleep)
    assert calls == [(15.0, 300.0, "low")]
    clock = FakeClock()
    call, calls = timed_call(clock, [(23, {"picks": []})])
    with pytest.raises(top5.ModelFailed, match="not requested"):
        top5.gemini_generate("p", 29, call=call, clock=clock, sleep=clock.sleep)
    assert calls == []


def test_window_end_is_monday_0012_kst():
    assert window_end(WEEK) == datetime(2026, 11, 1, 15, 12, tzinfo=UTC)
