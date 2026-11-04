import type { TopMatchItem, TopMatches } from "@/lib/api/types";
import { formatKstDateTime, formatKstMonthDayTime, formatPeriod } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";

/**
 * Presentation rules of the AI weekly TOP 5 (docs/TOP5_POLICY 2026-11-02 revision, guide
 * §6.4, Figma 159:923 strip / 159:924 panel). Three public UIs: the list, "no supported
 * matches" and the delay notice. Last week's result, fewer than five matches and changed
 * matches are data of the same list, never separate screens.
 */

export const TOP5_MAX = 5;

export const POLICY_NOTICE =
  "매주 월요일 00:00(KST)에 AI가 새 주의 주목 경기를 선정합니다. 새 결과가 준비되면 교체하며, " +
  "공개한 목록과 순서는 해당 주 동안 유지합니다. 실제 이용자 인기 순위는 아닙니다.";
/** Figma PreviousNotice (243:2696). */
export const PREVIOUS_NOTICE = "새 주 결과가 준비되기 전까지 지난주 공개 결과를 안내합니다.";
/** Figma ShortListNotice (243:2697). */
export const SHORT_LIST_NOTICE = `선정 당시 후보가 ${TOP5_MAX}개 미만이어서 해당 경기만 표시합니다.`;

/** Last week's public result kept while the new week is being selected. */
export function isPrevious(data: TopMatches): boolean {
  return data.week.start < data.currentWeek.start;
}

export function titleOf(data: TopMatches): string {
  return isPrevious(data) ? "지난주 주목 경기 TOP 5" : "이번 주 주목 경기 TOP 5";
}

export type Top5Notice = "none" | "delayed";

interface NoticeCopy {
  title: string;
  description: string;
  /** Mobile strip line (Figma 159:708 / 159:795). */
  short: string;
}

export function noticeCopy(notice: Top5Notice, data: TopMatches): NoticeCopy {
  if (notice === "delayed") {
    return {
      title: "이번 주 주목 경기 업데이트가 지연되고 있습니다.",
      description: "준비가 완료되면 새 목록을 안내하겠습니다.",
      short: "이번 주 주목 경기 업데이트 지연",
    };
  }
  // Kept from last week: the sentence follows the week shown, never "this week".
  const title = isPrevious(data)
    ? "지난주 지원 대회의 예정 경기가 없었습니다"
    : "이번 주 지원 대회의 예정 경기가 없습니다";
  return { title, description: "표시된 기간의 지원 대회 기준입니다.", short: title };
}

/** The notice to show instead of a list, or null when there are items to list. */
export function noticeOf(data: TopMatches): Top5Notice | null {
  if (data.view === "delayed") return "delayed";
  return data.view === "list" && data.items.length ? null : "none";
}

export function periodText(data: TopMatches): string {
  return formatPeriod(data.week.start, data.week.end);
}

export function metadataText(data: TopMatches): string {
  const selected = data.selectedAt && `선정 시각 ${formatKstDateTime(data.selectedAt)}`;
  return [periodText(data), selected].filter(Boolean).join(" · ");
}

/** Kickoff as selected (D-01-10); a later change appears on the change line. */
export function kickoffText(item: TopMatchItem): string {
  return formatKstMonthDayTime(item.selectedKickoffAt);
}

/**
 * "변경 일시 11/12(목) 03:00" when the kickoff moved after the selection, "변경 일시 미정"
 * while a postponed match has no new time. A postponed match keeps its id (guide §6.4 PST).
 */
export function changeText(item: TopMatchItem): string | null {
  const { match } = item;
  const reason = match.statusReason ? ` · ${match.statusReason}` : "";
  if (match.status === "postponed" && !match.timeConfirmed) return `변경 일시 미정${reason}`;
  if (Date.parse(match.kickoffAt) !== Date.parse(item.selectedKickoffAt)) {
    const when = match.timeConfirmed ? formatKstMonthDayTime(match.kickoffAt) : "미정";
    return `변경 일시 ${when}${reason}`;
  }
  return null;
}

export function lineupText(data: TopMatches): string {
  return data.items
    .map(({ rank, match }) =>
      `${rank}. ${teamName(match.home)} vs ${teamName(match.away)}`,
    )
    .join(" · ");
}
