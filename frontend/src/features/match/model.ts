import type { BadgeTone } from "@/components/ui/Badge";
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

/** "골 · 레알 마드리드 · 비니시우스 (도움 벨링엄)", "교체 · PSV · A → B" (A off, B on),
 * "골 취소 · 레알 마드리드 · 비니시우스". */
export function eventText(event: MatchEvent, teamNames: { home: string; away: string }): string {
  const team = event.side ? teamNames[event.side] : null;
  const join = (...parts: (string | null | undefined)[]) => parts.filter(Boolean).join(" · ");
  switch (event.type) {
    case "goal": {
      const kind = GOALS[event.detail ?? ""] ?? "골";
      const assist = event.assist && kind !== "페널티킥 실축" ? ` (도움 ${event.assist})` : "";
      return join(kind, team, event.player ? `${event.player}${assist}` : null);
    }
    case "card":
      return join(CARDS[event.detail ?? ""] ?? "카드", team, event.player);
    case "subst":
      return join("교체", team, `${event.player ?? MISSING} → ${event.assist ?? MISSING}`);
    case "var":
      if (event.detail === "Goal cancelled") return join(VAR["Goal cancelled"], team, event.player);
      return join("VAR", VAR[event.detail ?? ""] ?? event.detail, team, event.player);
    default:
      return join(event.detail, team, event.player);
  }
}

const STAT_LABELS: Record<string, string> = {
  "Ball Possession": "점유율",
  "Total Shots": "전체 슈팅",
  "Shots on Goal": "유효 슈팅",
  "Corner Kicks": "코너킥",
  Fouls: "파울",
  Offsides: "오프사이드",
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

export const RESULT_LABEL: Record<FormMatch["result"], { label: string; tone: BadgeTone }> = {
  W: { label: "승", tone: "live" },
  D: { label: "무", tone: "neutral" },
  L: { label: "패", tone: "error" },
};

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
    // PC: a finished match puts the reviews in a narrow column right of the records;
    // live matches keep them below (Figma 52:151 / 161:4161). Mobile always stacks.
    reviewsBeside: reviews && status === "finished",
  };
}

/** "도르트문트 2 : 1 라이프치히" preview of a recent-form match (MAT-005): home first. */
export function formPreview(
  teamName: string,
  match: Pick<FormMatch, "opponentName" | "venue" | "goalsFor" | "goalsAgainst">,
): { home: string; away: string; score: string } {
  const goal = (value: number | null) => (value === null ? MISSING : String(value));
  const home = match.venue === "home";
  return {
    home: home ? teamName : match.opponentName,
    away: home ? match.opponentName : teamName,
    score: home
      ? `${goal(match.goalsFor)} : ${goal(match.goalsAgainst)}`
      : `${goal(match.goalsAgainst)} : ${goal(match.goalsFor)}`,
  };
}
