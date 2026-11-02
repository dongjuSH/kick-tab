import type { BadgeTone } from "@/components/ui/Badge";
import type { MatchSummary, TeamRef, TopMatches } from "@/lib/api/types";
import { MISSING, formatKstMonthDayTime, formatPeriod, formatShortDate } from "@/lib/format/kst";

/**
 * Presentation rules for the AI weekly TOP 5 (docs/TOP5_POLICY_2026-11-01.md, guide §6.4,
 * Figma 159:923 strip / 159:924 panel). The 7 Figma states come from `state` + item count:
 * five / few = ready, none = no_candidates, loading = pending, source-error, ai-error, and
 * changed = a ready item whose match was postponed/cancelled/abandoned/awarded.
 */

export const TOP5_TITLE = "이번 주 주목 경기 TOP 5";
export const TOP5_MAX = 5;

export const POLICY_NOTICE =
  "매주 월요일 00:00(KST), 경기 일정과 팀 성적 등을 바탕으로 AI가 선정합니다. " +
  "실제 이용자 인기 순위가 아니며 선정 목록과 순서는 한 주 동안 유지됩니다.";

/** States without a list. Never shown as an empty ready week (TOP-003). */
export type Top5Notice = "no_candidates" | "pending" | "source_error" | "ai_error";

interface NoticeCopy {
  title: string;
  description: string;
  note: string;
  tone: "neutral" | "error";
}

export const NOTICES: Record<Top5Notice, NoticeCopy> = {
  no_candidates: {
    title: "이번 주 지원 대회의 예정 경기가 없습니다",
    description: "다음 주 선정 목록을 확인해 주세요.",
    note: "지난주 경기나 지원 밖 경기로 채우지 않습니다.",
    tone: "neutral",
  },
  pending: {
    title: "이번 주 주목 경기를 선정하고 있습니다",
    description: "선정이 완료되면 이번 주 목록을 안내합니다.",
    note: "이전 주 선정 목록을 이번 주 목록으로 표시하지 않습니다.",
    tone: "neutral",
  },
  source_error: {
    title: "경기 정보를 확인하지 못했습니다",
    description: "후보 경기 조회에 실패했습니다. 잠시 후 다시 확인해 주세요.",
    note: "후보 없음과 다른 상태이며, 지난주 목록으로 대체하지 않습니다.",
    tone: "error",
  },
  ai_error: {
    title: "이번 주 AI 선정 목록을 준비하지 못했습니다",
    description: "선정 작업에 실패했습니다. 잠시 후 다시 확인해 주세요.",
    note: "후보 없음과 다른 상태이며, 지난주 목록으로 대체하지 않습니다.",
    tone: "error",
  },
};

/** The notice to show instead of a list, or null when there are items to list. */
export function noticeOf(data: TopMatches): Top5Notice | null {
  if (data.state !== "ready") return data.state;
  // A ready week always has 1–5 items; an empty one is reported as "no candidates".
  return data.items.length ? null : "no_candidates";
}

export function teamName(team: TeamRef): string {
  return team.nameKo ?? team.nameEn;
}

/** Not played yet (scheduled, postponed) → "VS"; a missing score → "—", never 0:0. */
export function scoreText(match: MatchSummary): string {
  if (match.status === "scheduled" || match.status === "postponed") return "VS";
  const { home, away } = match.score;
  return home === null || away === null ? MISSING : `${home} : ${away}`;
}

/** Kickoff in KST; the time is left out while the provider has not fixed it (TBD). */
export function kickoffText(match: MatchSummary): string {
  return match.timeConfirmed
    ? `${formatKstMonthDayTime(match.kickoffAt)} KST`
    : `${formatShortDate(match.kickoffDateKst)} 시간 미정`;
}

/** Selected, then postponed / cancelled / abandoned / decided by a ruling (policy "changed"). */
export function isChanged(match: MatchSummary): boolean {
  return (
    match.status === "postponed" ||
    match.status === "cancelled" ||
    match.status === "abandoned" ||
    match.finishType === "awarded" ||
    match.finishType === "walkover"
  );
}

/** Short status word (guide §6.4 status table): strip summaries and the status badge. */
export function statusWord(match: MatchSummary): string {
  if (match.finishType === "awarded" || match.finishType === "walkover") return "행정 종료";
  switch (match.status) {
    case "scheduled":
      return "예정";
    case "live":
      return "진행 중";
    case "finished":
      return "종료";
    case "postponed":
      return "연기";
    case "cancelled":
      return "취소";
    case "abandoned":
      return "경기 중단";
    default:
      return "확인 필요";
  }
}

export function statusBadge(match: MatchSummary): { label: string; tone: BadgeTone } {
  const label = statusWord(match);
  if (match.status === "live") {
    return { label: match.elapsed === null ? label : `${label} ${match.elapsed}′`, tone: "live" };
  }
  return { label, tone: isChanged(match) ? "warning" : "neutral" };
}

/**
 * "변경 일시 11/12(목) 03:00 KST" / "변경 일시 미정 · 대회 일정 조정". A postponed match keeps
 * its id and gets the new kickoff (guide §6.4 PST), so the latest kickoff is the new time.
 */
export function changeText(match: MatchSummary): string | null {
  if (!isChanged(match)) return null;
  const when =
    match.status === "postponed" && match.timeConfirmed
      ? `${formatKstMonthDayTime(match.kickoffAt)} KST`
      : "미정";
  return [`변경 일시 ${when}`, match.statusReason].filter(Boolean).join(" · ");
}

export function periodText(data: TopMatches): string {
  return formatPeriod(data.week.start, data.week.end);
}

export function weekText(data: TopMatches): string {
  return `${periodText(data)} · KST`;
}

/** Desktop strip summary: the first two items, or the state message (Figma 159:122…159:417). */
export function desktopSummary(data: TopMatches): string {
  const notice = noticeOf(data);
  if (notice) return NOTICES[notice].title;
  if (data.items.length < TOP5_MAX) return `후보 ${data.items.length}경기 · 있는 경기만 안내합니다`;
  return data.items
    .slice(0, 2)
    .map(({ rank, match }) =>
      `${rank} ${teamName(match.home)} ${scoreText(match)} ${teamName(match.away)} · ${statusWord(match)}`,
    )
    .join("  |  ");
}

const STATUS_GROUPS = ["예정", "진행", "종료", "확인 필요"] as const;

function statusGroup(match: MatchSummary): (typeof STATUS_GROUPS)[number] {
  if (match.status === "scheduled") return "예정";
  if (match.status === "live") return "진행";
  if (match.status === "finished") return "종료";
  return "확인 필요";
}

/** Mobile strip second line after the week (Figma 159:523…159:824). */
export function mobileSummary(data: TopMatches): string {
  const notice = noticeOf(data);
  if (notice) return NOTICES[notice].title;
  const count = `${data.items.length}경기`;
  if (data.items.length < TOP5_MAX) return `${count} · 후보 부족`;
  const matches = data.items.map((item) => item.match);
  const changed = [...new Set(matches.filter(isChanged).map(statusWord))];
  if (changed.length) return `${count} · ${changed.join("·")} 포함`;
  const groups = new Set(matches.map(statusGroup));
  return `${count} · ${STATUS_GROUPS.filter((g) => groups.has(g)).join("·")}`;
}
