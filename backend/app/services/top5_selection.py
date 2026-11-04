"""AI weekly TOP 5 selection (TOP-001·002, docs/TOP5_POLICY 2026-11-02 revision).

One attempt = candidates -> evidence -> one Gemini request -> server validation -> one
atomic publication. Week rules (stored in `top5_weeks`):
- 00:00 KST Monday (`scheduled`): first automatic attempt. Failure -> `retry_scheduled`.
- 00:05 KST Monday (`retry`): second and last automatic attempt (also the first one if the
  00:00 run was missed). Failure -> `delayed`: the delay notice is published, an operator
  alert is sent once (a failed alert is only logged), nothing else is scheduled.
- `manual` (operator command): only for the current week while it is not published.
A published week is never selected again. Until a new result is published, users keep
seeing last week's public result (services.top_matches).

Concurrency: a session-level advisory lock per week admits one attempt at a time; each
attempt has a deadline, and only the attempt that is still the week's current, running
and within its deadline may publish (checked under a row lock), so a late or replaced
attempt can never overwrite the public result.
"""

import json
import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import Engine, event, select, text
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.core.kst import KST
from app.core.locks import advisory_key
from app.models.fixture import Fixture
from app.models.match_detail import HeadToHead, TeamForm
from app.models.reference import Competition, CompetitionSeason, Team
from app.models.top_matches import Top5Attempt, Top5Publication, Top5Week, WeeklyTopMatch
from app.notifications.discord import Top5DelayNotice, notify_top5_delay
from app.providers.api_football import ApiFootballClient, ApiFootballError
from app.providers.gemini import LlmError, generate_structured
from app.services.fixtures import sync_state
from app.services.head_to_head import (
    EvidenceError,
    ensure_form,
    ensure_meetings,
    recent_form,
    result_for,
)
from app.services.top_matches import current_kst_week

logger = logging.getLogger(__name__)

Trigger = Literal["scheduled", "retry", "manual"]
SessionFactory = Callable[[], Session]
ClientFactory = Callable[[], ApiFootballClient]
Clock = Callable[[], datetime]

PROMPT_VERSION = "2026-11-04.1"
CURATION_PATH = Path(__file__).resolve().parents[1] / "seed" / "top5_curation.json"
TOP_N = 5
RETRY_MINUTE = 5
REASON_MAX = 60
# The schedule must have been collected recently and completely (TOP-001 완전성).
SCHEDULE_MAX_AGE = timedelta(minutes=90)
EVIDENCE_WORKERS = 4
# Upper bound of the single Gemini request; never beyond the attempt deadline.
LLM_TIMEOUT_CAP = 150.0
DB_WAIT_MS = 5_000
RETRY_GRACE = timedelta(seconds=60)


class SelectionError(Exception):
    """Internal failure cause. Messages are safe to store and to send to the operator."""


def _bounded_session(
    factory: SessionFactory, clock: Clock, deadline: datetime | None = None
) -> Session:
    """Bound every transaction, including transactions reopened by single_flight."""
    session = factory()

    @event.listens_for(session, "after_begin")
    def limits(session, transaction, connection):
        wait = DB_WAIT_MS
        if deadline is not None:
            remaining = int((deadline - clock()).total_seconds() * 1000)
            if remaining <= 0:
                raise SelectionError("No time left for evidence queries")
            wait = min(wait, remaining)
        connection.execute(
            text("SELECT set_config('statement_timeout', :wait, true), "
                 "set_config('lock_timeout', :wait, true)"),
            {"wait": f"{wait}ms"},
        )

    return session


def _collect_evidence(
    jobs: list[Callable[[Session], None]],
    session_factory: SessionFactory,
    deadline: datetime,
    cancelled: threading.Event,
    clock: Clock,
) -> None:
    """Small daemon pool: no executor atexit join, and no queued work after cancellation.

    In-flight HTTP requests retain the provider client's bounded timeouts. Database
    transactions are bounded separately; abandoned workers cannot publish a result.
    """
    pending: Queue[Callable[[Session], None]] = Queue()
    for job in jobs:
        pending.put(job)
    errors: list[BaseException] = []

    def worker() -> None:
        while not cancelled.is_set() and clock() < deadline:
            try:
                job = pending.get_nowait()
            except Empty:
                return
            try:
                if cancelled.is_set():
                    return
                with _bounded_session(session_factory, clock, deadline) as session:
                    job(session)
            except BaseException as exc:  # noqa: BLE001 - passed to the attempt thread
                errors.append(exc)
                cancelled.set()
                return

    threads = [
        threading.Thread(target=worker, name=f"top5-evidence-{i}", daemon=True)
        for i in range(min(EVIDENCE_WORKERS, len(jobs)))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        while thread.is_alive() and not cancelled.is_set() and clock() < deadline:
            thread.join(timeout=0.05)
    if errors:
        error = errors[0]
        detail = (
            str(error) if isinstance(error, EvidenceError | ApiFootballError)
            else type(error).__name__
        )
        raise SelectionError(f"Evidence failed: {detail}") from None
    if cancelled.is_set() or clock() >= deadline or not pending.empty():
        cancelled.set()
        raise SelectionError("Cancelled after the attempt deadline")


# ---- operator-managed inputs ⑤·⑥ ------------------------------------------------------


@dataclass(frozen=True)
class Curation:
    version: str
    derbies: dict[frozenset[int], str]
    interest: dict[int, str]


@lru_cache(maxsize=1)
def load_curation(path: Path = CURATION_PATH) -> Curation:
    raw = json.loads(path.read_text(encoding="utf-8"))
    derbies = {frozenset(int(t) for t in d["teams"]): d["name"] for d in raw["derbies"]}
    interest = {int(t): tier for tier, teams in raw["interest"].items() for t in teams}
    return Curation(version=raw["version"], derbies=derbies, interest=interest)


# ---- model answer and validation --------------------------------------------------------


class LlmPick(BaseModel):
    fixture_id: int = Field(description="후보 목록의 fixtureId")
    rank: int = Field(ge=1, le=TOP_N, description="1부터 시작하는 순위")
    reason: str = Field(description="한국어 한 줄 선정 이유(40자 이내)")


class LlmSelection(BaseModel):
    picks: list[LlmPick]


def validate_picks(
    picks: list[LlmPick], candidates: dict[int, datetime], week_start: date
) -> list[tuple[int, int, str]]:
    """Candidates only, in the week, no duplicates, exactly min(5, n) ranked 1..n."""
    expected = min(TOP_N, len(candidates))
    if len(picks) != expected:
        raise SelectionError(f"Validation: {len(picks)} picks, expected {expected}")
    ids = [p.fixture_id for p in picks]
    if len(set(ids)) != len(ids):
        raise SelectionError("Validation: duplicate fixture ids")
    unknown = [i for i in ids if i not in candidates]
    if unknown:
        raise SelectionError(f"Validation: not a candidate {unknown[:5]}")
    if sorted(p.rank for p in picks) != list(range(1, expected + 1)):
        raise SelectionError("Validation: ranks are not 1..n")
    start, end = week_bounds(week_start)
    if any(not start <= candidates[i] < end for i in ids):
        raise SelectionError("Validation: kickoff outside the target week")
    items = []
    for pick in sorted(picks, key=lambda p: p.rank):
        reason = " ".join(pick.reason.split())
        if not reason or len(reason) > REASON_MAX or "\n" in pick.reason.strip():
            raise SelectionError(f"Validation: reason of {pick.fixture_id} is not one short line")
        items.append((pick.rank, pick.fixture_id, reason))
    return items


# ---- candidates and evidence --------------------------------------------------------------


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    """KST Monday 00:00 (inclusive) .. next Monday 00:00 (exclusive), in UTC."""
    start = datetime.combine(week_start, time(0, 0), KST).astimezone(UTC)
    return start, start + timedelta(days=7)


def retry_slot(week_start: date) -> datetime:
    return datetime.combine(week_start, time(0, RETRY_MINUTE), KST).astimezone(UTC)


def check_schedule(session: Session, now: datetime) -> None:
    """A failed or stale schedule collection is a failure, never "no candidates"."""
    state = sync_state(session)
    if state.never_synced:
        raise SelectionError("Schedule never collected")
    if state.failed_competition_ids:
        raise SelectionError(
            f"Schedule incomplete: competitions {state.failed_competition_ids} failed"
        )
    oldest = session.scalar(
        select(CompetitionSeason.fixtures_synced_at)
        .where(
            CompetitionSeason.season == settings.current_season,
            CompetitionSeason.availability == "available",
        )
        .order_by(CompetitionSeason.fixtures_synced_at)
        .limit(1)
    )
    if oldest is None or now - oldest > SCHEDULE_MAX_AGE:
        raise SelectionError("Schedule not refreshed within 90 minutes")


def candidate_rows(session: Session, week_start: date, now: datetime):
    """Scheduled matches of the week with a fixed kickoff and both teams, not started yet."""
    start, end = week_bounds(week_start)
    home, away = aliased(Team), aliased(Team)
    return session.execute(
        select(Fixture, Competition, home, away)
        .join(Competition, Competition.id == Fixture.competition_id)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(
            Competition.active,
            Fixture.status == "scheduled",
            Fixture.status_short_raw == "NS",  # TBD = time not fixed
            Fixture.kickoff_at >= start,
            Fixture.kickoff_at < end,
            Fixture.kickoff_at > now,
        )
        .order_by(Fixture.kickoff_at, Competition.sort_order, Fixture.id)
    ).all()


def fetch_standings(client: ApiFootballClient, competition_id: int, season: int):
    """team id -> {rank, points, played, group} of one competition's table(s)."""
    result = client.get("/standings", {"league": competition_id, "season": season})
    table: dict[int, dict[str, Any]] = {}
    for entry in result.response or []:
        for group in (entry.get("league") or {}).get("standings") or []:
            for row in group:
                team_id = (row.get("team") or {}).get("id")
                if team_id:
                    table[team_id] = {
                        "rank": row.get("rank"),
                        "points": row.get("points"),
                        "played": (row.get("all") or {}).get("played"),
                        "group": row.get("group"),
                    }
    return table


def _form_entries(payload: list[dict[str, Any]], team_id: int, before: datetime) -> list[str]:
    """Compact lines, newest first: "2026-11-01 W 6-1 H vs Alaves (La Liga)"."""
    lines = []
    for r in recent_form(payload, team_id, before):
        home = r["homeId"] == team_id
        goals = (r["goalsHome"], r["goalsAway"])
        mine, theirs = goals if home else goals[::-1]
        opponent = r["awayName"] if home else r["homeName"]
        lines.append(
            f"{r['kickoffAt'][:10]} {result_for(r, team_id)} {mine}-{theirs} "
            f"{'H' if home else 'A'} vs {opponent} ({r.get('leagueName')})"
        )
    return lines


def _kickoff_kst(moment: datetime) -> str:
    local = moment.astimezone(KST)
    weekday = "월화수목금토일"[local.weekday()]
    return f"{local:%m/%d}({weekday}) {local:%H:%M}"


@dataclass
class Selection:
    items: list[tuple[int, int, str]]
    kickoffs: dict[int, datetime]
    candidate_count: int
    evidence: dict[str, Any]
    llm_output: dict[str, Any] | None = None
    curation_version: str | None = None


def build_prompt(candidates: list[dict[str, Any]], picks: int) -> str:
    return (
        "너는 축구 경기 일정 서비스 KickTab의 'AI 선정 이번 주 주목 경기 TOP 5' 선정자다.\n"
        f"아래 후보 경기 중에서만 이번 주에 볼 만한 경기를 정확히 {picks}개 골라 1위부터 "
        f"{picks}위까지 순위를 매겨라.\n"
        "규칙:\n"
        "- fixtureId는 후보 목록에 있는 값만 쓰고 중복하지 않는다.\n"
        "- 근거는 제공된 여섯 지표만 쓴다: 대회·경기 단계(competition, round), 같은 대회 순위·"
        "승점 차이(standing, pointsGap), 최근 공식 5경기(recentForm), 최근 맞대결"
        "(headToHead), 운영자 더비 목록(derby), 운영자 팀 관심도(interest).\n"
        "- 값이 null이거나 비어 있으면 미제공이다. 제공되지 않은 사실(선수, 부상, 이적, 감독, "
        "과거 우승 등)을 만들거나 기억으로 보완하지 않는다.\n"
        "- 첫 판단 기준은 국내 팬이 이번 주 일정을 찾아 시청할 만한 대진인지다. 운영자 팀 "
        "관심도(interest)는 국내 관심을 가늠하는 첫 신호이며, 실제 시청률이나 인기 수치가 "
        "아니다. 한 팀의 이름만으로 자동 선정하지 말고 상대와 경기 단계도 함께 본다.\n"
        "- 결승·토너먼트·진출 또는 우승 등 구체적 이해관계가 확인되면 관심도만 높은 일반 "
        "리그 경기보다 우선할 수 있다. 대회별 할당은 두지 않는다.\n"
        "- 리그는 라운드(round)와 양 팀 경기 수(standing.played)를 보고 시즌의 진행 정도를 "
        "판단한다. 초반 순위와 근소한 승점 차이, 특히 중상위권의 단순 맞대결은 강한 근거가 "
        "아니다. 라운드나 경기 수가 불명확하면 순위만 보고 우승·진출 경쟁이라 단정하지 "
        "않는다. 서로 다른 대회나 조의 순위를 직접 비교하지 않는다. UEFA 리그 페이즈는 "
        "토너먼트가 아니다.\n"
        "- 등록된 더비라는 사실만으로 우선하지 않는다. 시청 관심이나 현재 경기의 중요도가 "
        "다른 지표로도 뒷받침되는지 확인한다. 최근 폼과 맞대결은 비슷한 후보를 비교하는 "
        "보조 근거로 쓴다.\n"
        "- recentForm은 최신순 '날짜 결과(W/D/L) 득점-실점 H(홈)/A(원정) vs 상대 (대회)'이다.\n"
        "- reason은 한국어 한 줄, 40자 이내로 지표 기반 핵심을 ' · '로 나열한다 "
        "(예: 챔피언스리그 토너먼트 · 관심 팀 맞대결).\n"
        f"후보 경기({len(candidates)}개, 킥오프는 KST):\n"
        + json.dumps(candidates, ensure_ascii=False, separators=(",", ":"))
    )


def select_week(
    week_start: date,
    now: datetime,
    session_factory: SessionFactory,
    client_factory: ClientFactory,
    generate: Callable[[str, float], tuple[LlmSelection, dict[str, Any]]],
    deadline: datetime,
    cancelled: threading.Event,
    *,
    clock: Clock | None = None,
) -> Selection:
    clock = clock or (lambda: datetime.now(UTC))
    curation = load_curation()
    with _bounded_session(session_factory, clock, deadline) as session:
        check_schedule(session, now)
        rows = candidate_rows(session, week_start, now)
        if not rows:
            # Confirmed empty week of the supported competitions: no model request.
            return Selection([], {}, 0, {"candidates": []}, None, curation.version)
        fixtures = {f.id: f for f, _, _, _ in rows}
        team_ids = sorted({t for f in fixtures.values() for t in (f.home_team_id, f.away_team_id)})
        tabled = sorted(
            {(c.id, f.season) for f, c, _, _ in rows if c.type in ("league", "uefa")}
        )

    standings: dict[int, dict[int, dict[str, Any]]] = {}
    client = client_factory()
    try:
        for competition_id, season in tabled:
            if cancelled.is_set() or clock() >= deadline:
                raise SelectionError("Cancelled after the attempt deadline")
            standings[competition_id] = fetch_standings(client, competition_id, season)
    except ApiFootballError as exc:
        raise SelectionError(f"Standings failed: {type(exc).__name__}") from None
    finally:
        client.close()

    jobs: list[Callable[[Session], None]] = []
    for team_id in team_ids:
        jobs.append(lambda s, t=team_id: ensure_form(s, t, now, client_factory, strict=True))
    for fixture_id in fixtures:
        jobs.append(
            lambda s, f=fixture_id: ensure_meetings(
                s, s.get(Fixture, f), now, client_factory, strict=True
            )
        )
    _collect_evidence(jobs, session_factory, deadline, cancelled, clock)

    with _bounded_session(session_factory, clock, deadline) as session:
        forms = {r.team_id: r.payload or [] for r in session.scalars(
            select(TeamForm).where(TeamForm.team_id.in_(team_ids))
        )}
        meetings = {r.fixture_id: r.payload or [] for r in session.scalars(
            select(HeadToHead).where(HeadToHead.fixture_id.in_(list(fixtures)))
        )}
        candidates = []
        kickoffs: dict[int, datetime] = {}
        for fixture, competition, home, away in candidate_rows(session, week_start, now):
            kickoffs[fixture.id] = fixture.kickoff_at
            table = standings.get(competition.id, {})

            def side(team: Team, table: dict[int, dict[str, Any]] = table) -> dict[str, Any]:
                return {
                    "teamId": team.id,
                    "name": team.name_ko or team.name_en,
                    "standing": table.get(team.id),
                    "recentForm": _form_entries(forms.get(team.id, []), team.id, now),
                    "interest": curation.interest.get(team.id),
                }

            past = [m for m in meetings.get(fixture.id, []) if m["kickoffAt"] < now.isoformat()]
            past = past[:5]
            h_rank, a_rank = table.get(home.id), table.get(away.id)
            gap = (
                abs(h_rank["points"] - a_rank["points"])
                if h_rank and a_rank and h_rank.get("points") is not None
                and a_rank.get("points") is not None
                and h_rank.get("group") == a_rank.get("group")
                else None
            )
            candidates.append(
                {
                    "fixtureId": fixture.id,
                    "competition": competition.name_ko or competition.short_name,
                    "competitionType": competition.type,
                    "round": fixture.round,
                    "kickoffKst": _kickoff_kst(fixture.kickoff_at),
                    "home": side(home),
                    "away": side(away),
                    "pointsGap": gap,
                    "headToHead": {
                        "meetings": len(past),
                        "homeWins": sum(result_for(m, home.id) == "W" for m in past),
                        "draws": sum(result_for(m, home.id) == "D" for m in past),
                        "awayWins": sum(result_for(m, away.id) == "W" for m in past),
                        "recent": [
                            f"{m['kickoffAt'][:10]} {m['homeName']} {m['goalsHome']}-"
                            f"{m['goalsAway']} {m['awayName']}"
                            for m in past
                        ],
                    },
                    "derby": curation.derbies.get(frozenset((home.id, away.id))),
                }
            )
    if not candidates:
        return Selection([], {}, 0, {"candidates": []}, None, curation.version)

    picks = min(TOP_N, len(candidates))
    evidence = {"candidates": candidates, "standingsCompetitions": [c for c, _ in tabled]}
    remaining = (deadline - clock()).total_seconds() - 5
    if remaining <= 5 or cancelled.is_set():
        raise SelectionError("No time left for the model request")
    try:
        answer, raw = generate(build_prompt(candidates, picks), min(LLM_TIMEOUT_CAP, remaining))
    except LlmError as exc:
        error = SelectionError(f"LLM failed: {exc}")
        error.evidence = evidence  # type: ignore[attr-defined]
        raise error from None
    try:
        items = validate_picks(answer.picks, kickoffs, week_start)
    except SelectionError as exc:
        exc.evidence = evidence  # type: ignore[attr-defined]
        exc.llm_output = raw  # type: ignore[attr-defined]
        raise
    return Selection(items, kickoffs, len(candidates), evidence, raw, curation.version)


def gemini_generate(prompt: str, timeout_seconds: float) -> tuple[LlmSelection, dict[str, Any]]:
    return generate_structured(
        prompt,
        LlmSelection,
        model=settings.top5_llm_model,
        api_key=settings.gemini_api_key,
        timeout_seconds=timeout_seconds,
    )


# ---- week state, publication ----------------------------------------------------------------


@dataclass
class AttemptOutcome:
    status: Literal["published", "failed", "skipped"]
    week_start: date
    attempt_id: int | None = None
    kind: str | None = None
    message: str | None = None
    api_requests: int = 0
    alert_sent: bool | None = None


@contextmanager
def week_lock(engine: Engine, week_start: date) -> Iterator[bool]:
    """One attempt per week at a time, across processes (held for the whole attempt)."""
    key = advisory_key(f"kicktab-top5:{week_start.isoformat()}")
    with engine.connect() as connection:
        acquired = bool(
            connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar()
        )
        connection.commit()
        try:
            yield acquired
        finally:
            if acquired:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                connection.commit()


def _publish_delay(session: Session, week_start: date) -> None:
    latest = session.scalar(
        select(Top5Publication)
        .where(Top5Publication.week_start == week_start)
        .order_by(Top5Publication.version.desc())
        .limit(1)
    )
    if latest is None or latest.kind != "delayed":
        session.add(Top5Publication(week_start=week_start, kind="delayed"))


def _fail(
    session: Session,
    week: Top5Week,
    attempt: Top5Attempt,
    previous: str | None,
    error: str,
    now: datetime,
    *,
    timed_out: bool = False,
) -> bool:
    """Record a failed attempt. Returns True when the operator must be alerted."""
    attempt.outcome = "timeout" if timed_out else "failed"
    attempt.error = error[:1000]
    attempt.finished_at = now
    week.last_error = error[:1000]
    week.updated_at = now
    if week.week_start != current_kst_week(now).start:
        # An old attempt may finish after midnight; it must not add a public version.
        week.status = "delayed"
        week.needs_manual = False
        week.next_retry_at = None
        return False
    if attempt.trigger == "scheduled":
        week.status = "retry_scheduled"
        week.next_retry_at = retry_slot(week.week_start)
        return False
    if attempt.trigger == "manual" and previous in ("retry_scheduled", "delayed"):
        # A failed recovery keeps the current public state and the remaining auto slot.
        week.status = previous
        week.next_retry_at = retry_slot(week.week_start) if previous == "retry_scheduled" else None
        return False
    week.status = "delayed"
    week.needs_manual = True
    week.next_retry_at = None
    _publish_delay(session, week.week_start)
    return attempt.trigger == "retry" and week.alert_sent_at is None


def _start(
    session: Session, week_start: date, trigger: Trigger, now: datetime, timeout: float
) -> tuple[Top5Attempt | None, str | None, str | None, bool]:
    """Create the attempt if this trigger may run. Returns (attempt, previous status,
    skip reason, alert needed for an interrupted attempt)."""
    week = session.get(Top5Week, week_start, with_for_update=True)
    alert = False
    if week is not None and week.status == "running":
        # The week lock is free, so the process that ran this attempt is gone.
        stale = session.get(Top5Attempt, week.current_attempt_id)
        if stale is not None and stale.outcome == "running":
            previous = (
                "retry_scheduled" if stale.trigger == "manual" and week.next_retry_at else None
            )
            alert = _fail(
                session, week, stale, previous, "Attempt interrupted", now, timed_out=True
            )
    status = week.status if week else None
    if status == "published":
        return None, status, "This week's result is already published", alert
    allowed = {
        "scheduled": status is None,
        "retry": status in (None, "retry_scheduled"),
        "manual": status in (None, "retry_scheduled", "delayed"),
    }[trigger]
    if trigger != "manual" and week is not None and week.auto_attempts >= 2:
        allowed = False
    if not allowed:
        return None, status, f"Not allowed for a week in state {status}", alert
    if week is None:
        week = Top5Week(week_start=week_start, status="running", auto_attempts=0)
        session.add(week)
    attempt = Top5Attempt(
        week_start=week_start,
        trigger=trigger,
        started_at=now,
        deadline_at=now + timedelta(seconds=timeout),
        outcome="running",
        model=settings.top5_llm_model,
        prompt_version=PROMPT_VERSION,
    )
    session.add(attempt)
    session.flush()
    week.status = "running"
    week.current_attempt_id = attempt.id
    # Preserve the remaining fixed slot if a manual recovery is itself interrupted.
    if trigger != "manual" or status != "retry_scheduled":
        week.next_retry_at = None
    week.updated_at = now
    if trigger != "manual":
        week.auto_attempts += 1
    return attempt, status, None, alert


def _publish(
    session: Session, attempt_id: int, selection: Selection, *, clock: Clock | None = None
) -> str:
    """Atomic publication; refused for an attempt that is no longer the week's current one."""
    attempt = session.get(Top5Attempt, attempt_id, with_for_update=True)
    week = session.get(Top5Week, attempt.week_start, with_for_update=True)
    published = session.scalar(
        select(Top5Publication.version).where(
            Top5Publication.week_start == week.week_start,
            Top5Publication.kind.in_(("list", "none")),
        )
    )
    # Read the clock after all lock/query waits, not when evidence finished.
    now = (clock or (lambda: datetime.now(UTC)))()
    if (
        week.current_attempt_id != attempt_id
        or week.status != "running"
        or attempt.outcome != "running"
        or now >= attempt.deadline_at
        or attempt.week_start != current_kst_week(now).start
    ):
        raise SelectionError("Attempt is no longer current; result not published")
    if published is not None:
        raise SelectionError("Week already published")
    kind = "list" if selection.items else "none"
    for rank, fixture_id, reason in selection.items:
        session.add(
            WeeklyTopMatch(
                week_start=week.week_start,
                rank=rank,
                fixture_id=fixture_id,
                reason=reason,
                selected_kickoff_at=selection.kickoffs[fixture_id],
                attempt_id=attempt_id,
            )
        )
    session.add(
        Top5Publication(
            week_start=week.week_start, kind=kind, selected_at=now, attempt_id=attempt_id
        )
    )
    attempt.outcome = "published"
    attempt.finished_at = now
    week.status = "published"
    week.needs_manual = False
    week.last_error = None
    week.next_retry_at = None
    week.updated_at = now
    return kind


def _send_alert(
    session_factory: SessionFactory,
    week_start: date,
    error: str,
    now: datetime,
    alert: Callable[[Top5DelayNotice], bool],
) -> bool:
    with _bounded_session(session_factory, lambda: now) as session:
        week = session.get(Top5Week, week_start)
        attempts = week.auto_attempts if week else 0
    sent = alert(Top5DelayNotice(week_start, attempts, error, now))
    if sent:
        with _bounded_session(session_factory, lambda: now) as session:
            week = session.get(Top5Week, week_start)
            week.alert_sent_at = now
            session.commit()
    else:
        logger.warning("TOP 5 delay alert for %s was not delivered", week_start)
    return sent


def run_attempt(
    trigger: Trigger,
    *,
    session_factory: SessionFactory,
    client_factory: ClientFactory = ApiFootballClient,
    generate: Callable[[str, float], tuple[LlmSelection, dict[str, Any]]] = gemini_generate,
    alert: Callable[[Top5DelayNotice], bool] = notify_top5_delay,
    now: datetime | None = None,
    timeout_seconds: float | None = None,
    clock: Clock | None = None,
) -> AttemptOutcome:
    clock = clock or (lambda: datetime.now(UTC))
    now = now or clock()
    week_start = current_kst_week(now).start
    timeout = float(timeout_seconds or settings.top5_attempt_timeout_seconds)
    if trigger == "scheduled":
        timeout = min(timeout, (retry_slot(week_start) - now).total_seconds() - 10)
        if timeout <= 0:
            return AttemptOutcome("skipped", week_start, message="First automatic slot passed")
    with session_factory() as session:
        # A Connection (tests) or an Engine; the week lock needs its own connection.
        engine = session.get_bind().engine

    with week_lock(engine, week_start) as acquired:
        if not acquired:
            return AttemptOutcome("skipped", week_start, message="Another attempt is running")
        with _bounded_session(session_factory, clock) as session:
            attempt, previous, skip, reap_alert = _start(session, week_start, trigger, now, timeout)
            attempt_id = attempt.id if attempt else None
            deadline = attempt.deadline_at if attempt else now
            session.commit()
        if attempt_id is None:
            sent = (
                _send_alert(session_factory, week_start, "Attempt interrupted", now, alert)
                if reap_alert
                else None
            )
            return AttemptOutcome("skipped", week_start, message=skip, alert_sent=sent)

        if reap_alert:
            _send_alert(session_factory, week_start, "Attempt interrupted", clock(), alert)

        clients: list[ApiFootballClient] = []

        def counted_client() -> ApiFootballClient:
            client = client_factory()
            clients.append(client)
            return client

        box: dict[str, Any] = {}
        done, cancelled = threading.Event(), threading.Event()

        def work() -> None:
            try:
                box["selection"] = select_week(
                    week_start, now, session_factory, counted_client, generate, deadline, cancelled,
                    clock=clock,
                )
            except BaseException as exc:  # noqa: BLE001 - reported by the waiting thread
                box["error"] = exc
            finally:
                done.set()

        # A daemon thread: a timed-out attempt is abandoned (it can no longer publish).
        threading.Thread(target=work, name=f"top5-attempt-{attempt_id}", daemon=True).start()
        finished = done.wait(timeout)
        if not finished:
            cancelled.set()
        requests = sum(c.request_count for c in clients)
        finished_at = clock()

        error: str | None = None
        selection: Selection | None = box.get("selection")
        failure = box.get("error")
        if not finished:
            error = f"Timed out after {int(timeout)} s"
        elif failure is not None:
            error = (
                str(failure)
                if isinstance(failure, SelectionError)
                else f"Unexpected error: {type(failure).__name__}"
            )
        with _bounded_session(session_factory, clock) as session:
            row = session.get(Top5Attempt, attempt_id)
            row.api_requests = requests
            if selection is not None:
                row.candidate_count = selection.candidate_count
                row.curation_version = selection.curation_version
                row.evidence = selection.evidence
                row.llm_output = selection.llm_output
            elif failure is not None:
                row.evidence = getattr(failure, "evidence", None)
                row.llm_output = getattr(failure, "llm_output", None)
                if row.evidence:
                    row.candidate_count = len(row.evidence.get("candidates", []))
            session.commit()
        if error is None and selection is not None:
            with _bounded_session(session_factory, clock) as session:
                try:
                    kind = _publish(session, attempt_id, selection, clock=clock)
                    session.commit()
                except SelectionError as exc:
                    session.rollback()
                    error = str(exc)
                else:
                    logger.info("TOP 5 %s published (%s, attempt %s)", week_start, kind, attempt_id)
                    return AttemptOutcome(
                        "published", week_start, attempt_id, kind, api_requests=requests
                    )
        with _bounded_session(session_factory, clock) as session:
            week = session.get(Top5Week, week_start, with_for_update=True)
            row = session.get(Top5Attempt, attempt_id, with_for_update=True)
            needs_alert = _fail(
                session, week, row, previous, error, clock(), timed_out=not finished
            )
            session.commit()
        logger.warning("TOP 5 %s attempt %s failed: %s", week_start, attempt_id, error)
        sent = (
            _send_alert(session_factory, week_start, error, finished_at, alert)
            if needs_alert
            else None
        )
        return AttemptOutcome(
            "failed", week_start, attempt_id, message=error, api_requests=requests, alert_sent=sent
        )


def retry_due(session: Session, now: datetime) -> bool:
    """00:05 precheck: run only when the 00:00 attempt failed (or never ran)."""
    week = session.get(Top5Week, current_kst_week(now).start)
    return week is None or week.status in ("retry_scheduled", "running")


def first_attempt_due(session: Session, now: datetime) -> bool:
    return session.get(Top5Week, current_kst_week(now).start) is None


def _recovery_weeks(session: Session, now: datetime) -> list[date]:
    rows = session.execute(
        select(Top5Week.week_start, Top5Week.status, Top5Attempt.deadline_at)
        .outerjoin(Top5Attempt, Top5Attempt.id == Top5Week.current_attempt_id)
        .where(Top5Week.status.in_(("running", "retry_scheduled")))
    ).all()
    return [
        week for week, status, deadline in rows
        if (status == "running" and (deadline is None or deadline <= now))
        or (status == "retry_scheduled" and now > retry_slot(week) + RETRY_GRACE)
    ]


def recovery_due(session: Session, now: datetime) -> bool:
    """DB-only precheck. Recovery records failures; it never starts a selection."""
    return bool(_recovery_weeks(session, now))


def reconcile_attempts(
    *, session_factory: SessionFactory,
    alert: Callable[[Top5DelayNotice], bool] = notify_top5_delay,
    clock: Clock | None = None,
) -> int:
    """Repair interrupted attempts under their week lock, without another model call.

    A first failure can still use the fixed 00:05 slot. If the service missed that slot
    (including its normal one-minute grace), stop automation and ask for manual recovery.
    An old week is closed internally without publishing or alerting for the new week.
    """
    clock = clock or (lambda: datetime.now(UTC))
    with _bounded_session(session_factory, clock) as session:
        engine = session.get_bind().engine
        targets = _recovery_weeks(session, clock())
    repaired = 0
    for week_start in targets:
        with week_lock(engine, week_start) as acquired:
            if not acquired:
                continue  # a live owner still holds the lock
            with _bounded_session(session_factory, clock) as session:
                week = session.get(Top5Week, week_start, with_for_update=True)
                if week is None or week.status not in ("running", "retry_scheduled"):
                    continue
                attempt = session.get(Top5Attempt, week.current_attempt_id, with_for_update=True)
                now = clock()
                send = False
                if week.status == "running":
                    if attempt is None or attempt.deadline_at > now:
                        continue
                    previous = (
                        "retry_scheduled" if attempt.trigger == "manual" and week.next_retry_at
                        else None
                    )
                    send = _fail(
                        session, week, attempt, previous, "Attempt interrupted", now, timed_out=True
                    )
                if week.status == "retry_scheduled" and now > retry_slot(week_start) + RETRY_GRACE:
                    week.status = "delayed"
                    week.next_retry_at = None
                    week.needs_manual = week_start == current_kst_week(now).start
                    week.last_error = "Automatic retry slot missed after interruption"
                    week.updated_at = now
                    if week.needs_manual:
                        _publish_delay(session, week_start)
                        send = week.alert_sent_at is None
                error = week.last_error or "Attempt interrupted"
                session.commit()
            repaired += 1
            if send:
                _send_alert(session_factory, week_start, error, clock(), alert)
    return repaired

