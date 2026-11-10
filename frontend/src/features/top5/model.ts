import type { TopMatchItem, TopMatches } from "@/lib/api/types";
import { formatKstDateTime, formatKstMonthDayTime } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";

/**
 * Presentation rules of the AI weekly TOP 5 (PRD v1.8 15장, 기능 명세서 v1.8 TOP-001~003,
 * guide §6.4, Figma 159:923 strip / 159:924 panel). Three public UIs: the list, "no
 * supported matches" and the delay notice. Last week's result kept while the new week is
 * selected, fewer than five matches and changed matches are data of the same list.
 */

export const TOP5_TITLE = "이번 주 주목 경기 TOP 5";
export const TOP5_MAX = 5;
/** Shown next to last week's real period while this week is selected (Figma 304:3824). */
export const PREPARING = "이번 주 결과 준비 중";
/** Panel footnote under the list (Figma 159:218). */
export const LIST_FOOTNOTE = "AI 선정 · 순서와 이유는 해당 주 동안 유지됩니다.";
/** Figma ShortListNotice (243:2697). */
export const SHORT_LIST_NOTICE = `선정 당시 후보가 ${TOP5_MAX}개 미만이어서 해당 경기만 표시합니다.`;

/** Last week's public result kept while the new week is being selected. */
export function isPrevious(data: TopMatches): boolean {
  return data.week.start < data.currentWeek.start;
}

/** "11/9" from "2026-11-09" (a calendar date, no time zone shift). */
function monthDay(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  return `${month}/${day}`;
}

/** "11/9–11/15" (Figma 159:923 / 159:924 show the week without weekdays). */
export function periodText(data: TopMatches): string {
  return `${monthDay(data.week.start)}–${monthDay(data.week.end)}`;
}

/** "11/9–11/15" or "지난주 11/2–11/8": the real week of the shown result. */
export function weekLabel(data: TopMatches): string {
  return isPrevious(data) ? `지난주 ${periodText(data)}` : periodText(data);
}

export function selectedText(data: TopMatches): string | null {
  return data.selectedAt && `선정 시각 ${formatKstDateTime(data.selectedAt)}`;
}

export type Top5Notice = "none" | "delayed";

export function noticeCopy(notice: Top5Notice, data: TopMatches): { title: string; description: string } {
  if (notice === "delayed") {
    return {
      title: "이번 주 주목 경기 업데이트가 지연되고 있습니다.",
      description: "준비가 완료되면 새 목록을 안내하겠습니다.",
    };
  }
  // Kept from last week: the sentence follows the week shown, never "this week".
  const title = isPrevious(data)
    ? "지난주 지원 대회의 예정 경기가 없었습니다"
    : "이번 주 지원 대회의 예정 경기가 없습니다";
  return { title, description: "표시된 기간의 지원 대회 기준입니다." };
}

/** The notice to show instead of a list, or null when there are items to list. */
export function noticeOf(data: TopMatches): Top5Notice | null {
  if (data.view === "delayed") return "delayed";
  return data.view === "list" && data.items.length ? null : "none";
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

/** Strip lineup in rank order: "1위 맨체스터 시티 vs 아스널". */
export function lineupItems(data: TopMatches): string[] {
  return data.items.map(({ rank, match }) => `${rank}위 ${teamName(match.home)} vs ${teamName(match.away)}`);
}
