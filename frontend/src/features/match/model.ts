import type { FormItem } from "@/components/common/RecentForm";
import type { FormMatch, MatchEvent, MatchInfo, StatRow } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";

/**
 * Display rules of the match detail (MAT-002·004·005). Only provider values are shown:
 * no event, statistic or rating is derived or filled in; missing values read "—".
 */

/** "12′", "45+2′"; "—" when the provider gave no minute. */
export function minuteText(event: Pick<MatchEvent, "elapsed" | "extra">): string {
  if (event.elapsed === null) return MISSING;
  return event.extra ? `${event.elapsed}+${event.extra}′` : `${event.elapsed}′`;
}

// Record names follow MAT-002 / Figma 52:151 (골·교체·경고·퇴장·골 취소).
const GOALS: Record<string, string> = {
  "Normal Goal": "골",
  "Own Goal": "자책골",
  Penalty: "페널티킥 골",
  "Missed Penalty": "페널티킥 실축",
};
const CARDS: Record<string, string> = {
  "Yellow Card": "경고",
  "Red Card": "퇴장",
  "Second Yellow card": "경고 누적 퇴장",
};
const VAR: Record<string, string> = {
  "Goal cancelled": "골 취소",
  "Goal confirmed": "골 인정",
  "Penalty confirmed": "페널티킥 인정",
  "Penalty cancelled": "페널티킥 취소",
  "Card upgrade": "카드 상향",
};

export type EventKind = "goal" | "missed" | "subst" | "yellow" | "red" | "cancelled" | "var" | "other";

/** Icon of a timeline record: goal, substitution, yellow card, red card, cancelled goal. */
export function eventKind(event: Pick<MatchEvent, "type" | "detail">): EventKind {
  switch (event.type) {
    case "goal":
      return event.detail === "Missed Penalty" ? "missed" : "goal";
    case "subst":
      return "subst";
    case "card":
      return event.detail === "Yellow Card" ? "yellow" : event.detail ? "red" : "other";
    case "var":
      return event.detail === "Goal cancelled" ? "cancelled" : "var";
    default:
      return "other";
  }
}

/** "골 · 비니시우스 (도움 벨링엄)", "교체 · A → B" (A off, B on), "골 취소 · 비니시우스".
 * The team is shown by the timeline column (home left, away right), not in the text. */
export function eventText(event: MatchEvent): string {
  const join = (...parts: (string | null | undefined)[]) => parts.filter(Boolean).join(" · ");
  switch (event.type) {
    case "goal": {
      const kind = GOALS[event.detail ?? ""] ?? "골";
      const assist = event.assist && kind !== "페널티킥 실축" ? ` (도움 ${event.assist})` : "";
      return join(kind, event.player ? `${event.player}${assist}` : null);
    }
    case "card":
      return join(CARDS[event.detail ?? ""] ?? "카드", event.player);
    case "subst":
      return join("교체", `${event.player ?? MISSING} → ${event.assist ?? MISSING}`);
    case "var":
      if (event.detail === "Goal cancelled") return join(VAR["Goal cancelled"], event.player);
      return join("VAR", VAR[event.detail ?? ""] ?? event.detail, event.player);
    default:
      return join(event.detail, event.player);
  }
}

const STAT_LABELS: Record<string, string> = {
  "Ball Possession": "점유율",
  "Total Shots": "전체 슈팅",
  "Shots on Goal": "유효 슈팅",
  "Corner Kicks": "코너킥",
  Fouls: "파울",
  Offsides: "오프사이드",
  "Free Kicks": "프리킥",
  "Total passes": "패스",
  "Shots off Goal": "빗나간 슈팅",
  "Blocked Shots": "막힌 슈팅",
  "Shots insidebox": "박스 안 슈팅",
  "Shots outsidebox": "박스 밖 슈팅",
  "Goalkeeper Saves": "골키퍼 선방",
  "Passes accurate": "정확한 패스",
  "Passes %": "패스 성공률",
  "Yellow Cards": "경고",
  "Red Cards": "퇴장",
  expected_goals: "기대 득점(xG)",
  goals_prevented: "실점 방지",
};

export function statLabel(row: StatRow): string {
  return STAT_LABELS[row.key] ?? row.key;
}

export function statValue(value: number | null, percent: boolean): string {
  if (value === null) return MISSING;
  const text = Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
  return percent ? `${text}%` : text;
}

/** Bar share of each side; null when a side has no value (no bar is drawn then). */
export function statShares(row: StatRow): { home: number; away: number } | null {
  if (row.home === null || row.away === null) return null;
  const total = row.home + row.away;
  if (total <= 0) return { home: 0.5, away: 0.5 };
  return { home: row.home / total, away: row.away / total };
}

const POSITIONS: Record<string, string> = { G: "GK", D: "DF", M: "MF", F: "FW" };

export function positionText(position: string | null): string {
  return position ? (POSITIONS[position] ?? position) : MISSING;
}

/** Normal results and rulings (awarded / walkover). */
export function isRuling(info: MatchInfo): boolean {
  return info.match.finishType === "awarded" || info.match.finishType === "walkover";
}

/** Areas of the page by state (MAT-001 table). Before kickoff there is no lineup or
 * review area (MAT-004 rule 4, REV-001): only head-to-head and recent form. */
export function areasOf(info: MatchInfo) {
  const status = info.match.status;
  const reviews = info.reviewsAvailable;
  return {
    // Timeline / team stats / lineups / player ratings tabs.
    records: status === "live" || status === "finished" || status === "abandoned",
    headToHead: info.headToHeadAvailable,
    // Live and normally finished matches, decided by the server (`review_open`).
    reviews,
    // PC: live and finished matches put the reviews in a narrow column right of the records
    // (Figma 52:151; user decision 2026-11-22 for live too). Mobile always stacks.
    reviewsBeside: reviews && (status === "live" || status === "finished"),
  };
}

/**
 * A team's recent official results (MAT-005, newest first from the API) as the shared
 * recent-five row: oldest first, each with its home and away side (06 개선 2026-11-20).
 */
export function formItems(teamName: string, matches: readonly FormMatch[]): FormItem[] {
  return matches
    .map((match, index): FormItem => {
      const home = match.venue === "home";
      return {
        key: `${match.kickoffDateKst}-${index}`,
        date: match.kickoffDateKst,
        competition: match.competition,
        home: home ? teamName : match.opponentName,
        away: home ? match.opponentName : teamName,
        goalsHome: home ? match.goalsFor : match.goalsAgainst,
        goalsAway: home ? match.goalsAgainst : match.goalsFor,
        result: match.result,
      };
    })
    .reverse();
}

/** A timeline row: one provider event, or a period row on the centre line (Figma 161:4161). */
export type TimelineRow =
  | { kind: "event"; event: MatchEvent }
  | { kind: "period"; minute: string; label: string };

// Status row at the top: where the match is now (live) or how it ended. Half time (HT) is
// the '45′ 전반 종료' row itself, so that half-time substitutions sit above it.
const STATUS_ROW: Record<string, string> = {
  "1H": "전반 진행 중",
  "2H": "후반 진행 중",
  BT: "연장 전 휴식",
  ET: "연장 진행 중",
  P: "승부차기 진행 중",
  SUSP: "경기 중단",
  INT: "경기 중단",
  FT: "경기 종료",
  AET: "경기 종료",
  PEN: "경기 종료",
};
const PAST_FIRST_HALF = new Set(["HT", "2H", "BT", "ET", "P", "FT", "AET", "PEN"]);
const EXTRA_TIME = new Set(["ET", "P", "AET", "PEN"]);
const REGULAR_END: Record<string, number> = { FT: 90, AET: 120, PEN: 120 };

/**
 * Half-time substitutions: the provider files them at 45′ with no stoppage minute, after
 * every first-half event. A substitution at exactly 45′ followed by no other first-half
 * event is made in the break, so it belongs above '전반 종료'.
 */
function halfTimeSubstitutions(events: MatchEvent[]): Set<MatchEvent> {
  const subs = new Set<MatchEvent>();
  for (let i = events.length - 1; i >= 0; i--) {
    const event = events[i];
    if (event.elapsed === null || event.elapsed > 45) continue;
    if (event.type !== "subst" || event.elapsed !== 45 || event.extra) break;
    subs.add(event);
  }
  return subs;
}

/**
 * Timeline rows, latest first: the events with period rows on the centre line — '전반 종료'
 * from half time on (half-time substitutions above it), '후반 종료' before extra time, and
 * the match status on top. With no event yet the period rows still show. The provider gives
 * no stoppage minutes of a finished period (`periods`/`extra` are empty), so a period end
 * shows its regular minute (45′, 90′); the top row takes the status minute, or the latest
 * event's minute when that is later (e.g. 90+3′).
 */
export function timelineRows(
  events: MatchEvent[],
  info: Pick<MatchInfo, "statusCode"> & { match: Pick<MatchInfo["match"], "elapsed"> },
): TimelineRow[] {
  const code = info.statusCode;
  const elapsed = info.match.elapsed;
  const marks: { after: number; minute: string; label: string }[] = [];
  if (PAST_FIRST_HALF.has(code) || ((code === "SUSP" || code === "INT") && (elapsed ?? 0) > 45)) {
    marks.push({ after: 45, minute: "45′", label: "전반 종료" });
  }
  if (EXTRA_TIME.has(code)) marks.push({ after: 90, minute: "90′", label: "후반 종료" });
  const breakSubs = marks.length ? halfTimeSubstitutions(events) : new Set<MatchEvent>();
  const rows: TimelineRow[] = [];
  let next = 0;
  for (const event of events) {
    while (
      next < marks.length &&
      ((event.elapsed !== null && event.elapsed > marks[next].after) ||
        (marks[next].after === 45 && breakSubs.has(event)))
    ) {
      const { minute, label } = marks[next++];
      rows.push({ kind: "period", minute, label });
    }
    rows.push({ kind: "event", event });
  }
  for (const { minute, label } of marks.slice(next)) rows.push({ kind: "period", minute, label });
  const label = STATUS_ROW[code];
  if (label) {
    // The API sends `elapsed` for live matches only: a finished match ends at its regular minute.
    const fixed = code === "BT" ? 90 : (elapsed ?? REGULAR_END[code] ?? null);
    let minute = fixed === null ? MISSING : `${fixed}′`;
    const last = events.at(-1);
    if (fixed !== null && last?.elapsed === fixed && last.extra) minute = minuteText(last);
    rows.push({ kind: "period", minute, label });
  }
  return rows.reverse();
}
