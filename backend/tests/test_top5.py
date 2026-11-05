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
    build_prompt,
    load_curation,
    retry_slot,
    validate_picks,
    week_bounds,
)
from app.services.top_matches import shown_publication

WEEK = date(2026, 11, 2)
IN_WEEK = datetime(2026, 11, 4, 10, tzinfo=UTC)


def candidates(n):
    return {1000 + i: IN_WEEK for i in range(n)}


def picks(*rows):
    return [LlmPick(fixture_id=f, rank=r, reason=reason) for f, r, reason in rows]


def test_week_bounds_and_retry_slot_are_kst():
    start, end = week_bounds(WEEK)
    assert start == datetime(2026, 11, 1, 15, 0, tzinfo=UTC)  # Monday 00:00 KST
    assert end == datetime(2026, 11, 8, 15, 0, tzinfo=UTC)  # next Monday 00:00 KST, excluded
    assert retry_slot(WEEK) == datetime(2026, 11, 1, 15, 5, tzinfo=UTC)  # fixed 00:05 KST


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


def test_gemini_failures_are_safe_errors(monkeypatch):
    with pytest.raises(LlmError, match="not configured"):
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr(""), timeout_seconds=5)
    use_fake(monkeypatch, FakeModels(error=TimeoutError("secret-key-in-message")))
    with pytest.raises(LlmError) as info:
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=5)
    assert "secret" not in str(info.value)
    use_fake(monkeypatch, FakeModels(SimpleNamespace(text='{"picks": "x"}', candidates=[])))
    with pytest.raises(LlmError, match="schema"):
        generate_structured("p", LlmSelection, model="m", api_key=SecretStr("k"), timeout_seconds=5)


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

    def call(prompt, schema, *, model, api_key, timeout_seconds):
        calls.append((model, timeout_seconds))
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return LlmSelection(picks=[]), result

    return call, calls


def models(monkeypatch, primary="gemini-3.8-flash", fallback="gemini-3.5-flash-lite"):
    monkeypatch.setattr(top5.settings, "top5_llm_model", primary)
    monkeypatch.setattr(top5.settings, "top5_llm_fallback_model", fallback)


def test_main_model_answer_skips_fallback(monkeypatch):
    models(monkeypatch)
    call, calls = fake_call([{"picks": []}])
    _, raw = top5.gemini_generate("p", 100, call=call, clock=lambda: 0.0)
    assert calls == [("gemini-3.8-flash", 60.0)]  # main model gets its share of the budget
    assert raw["model"] == "gemini-3.8-flash"


def test_request_error_falls_back_to_lower_model(monkeypatch):
    models(monkeypatch)
    call, calls = fake_call([LlmError("Gemini API error 503 UNAVAILABLE"), {"picks": []}])
    _, raw = top5.gemini_generate("p", 100, call=call, clock=lambda: 0.0)
    assert [m for m, _ in calls] == ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
    assert calls[1][1] == 98.0  # the rest of the budget
    assert raw["model"] == "gemini-3.5-flash-lite"


def test_both_models_failing_is_reported_as_all_failed(monkeypatch):
    models(monkeypatch)
    call, _ = fake_call([LlmError("Gemini API error 503"), LlmError("Gemini API error 429")])
    with pytest.raises(top5.AllModelsFailed) as info:
        top5.gemini_generate("p", 100, call=call, clock=lambda: 0.0)
    assert "gemini-3.8-flash: Gemini API error 503" in str(info.value)
    assert "gemini-3.5-flash-lite: Gemini API error 429" in str(info.value)


def test_no_fallback_without_time_or_when_disabled(monkeypatch):
    models(monkeypatch)
    ticks = iter([0.0, 95.0])
    call, calls = fake_call([LlmError("timeout")])
    with pytest.raises(top5.AllModelsFailed, match="not tried"):
        top5.gemini_generate("p", 100, call=call, clock=lambda: next(ticks))
    assert len(calls) == 1
    models(monkeypatch, fallback="")
    call, calls = fake_call([LlmError("Gemini API error 503")])
    with pytest.raises(LlmError) as info:
        top5.gemini_generate("p", 100, call=call, clock=lambda: 0.0)
    assert not isinstance(info.value, top5.AllModelsFailed) and calls == [("gemini-3.8-flash", 100)]


def test_models_failed_alert_payload_names_next_step():
    retry_at = datetime(2026, 11, 1, 15, 5, tzinfo=UTC)  # 11/02 00:05 KST
    notice = Top5DelayNotice(WEEK, 1, "LLM failed: a; b", IN_WEEK, "models_failed", retry_at)
    embed = build_top5_payload(notice)["embeds"][0]
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert "모두 실패" in embed["title"]
    assert fields["다음 단계"] == "11/02 00:05 KST 자동 재시도 예정"
    manual = Top5DelayNotice(WEEK, 2, "x", IN_WEEK, "models_failed", None)
    fields = {f["name"]: f["value"] for f in build_top5_payload(manual)["embeds"][0]["fields"]}
    assert "app.sync top5" in fields["다음 단계"]
