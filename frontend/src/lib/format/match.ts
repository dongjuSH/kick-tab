import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { MISSING, formatKstTime } from "./kst";

/**
 * Display rules shared by every match list (guide §6.4 status table, LIVE-001·002):
 * schedule cards, favourite schedule and TOP 5.
 */

export function teamName(team: TeamRef): string {
  return team.nameKo ?? team.nameEn;
}

/** The one competition name shown everywhere (COM-003): name_ko as stored, e.g. "UEFA 챔피언스리그", "리그 1". */
export function competitionName(competition: { nameKo: string | null; shortName: string }): string {
  return competition.nameKo ?? competition.shortName;
}

/**
 * "VS" only between the teams of a scheduled match (MatchCard rule, 2026-11-19); any other
 * match without a score (postponed, cancelled, a missing provider score) reads "—", never 0:0.
 */
export function scoreText(match: MatchSummary): string {
  if (match.status === "scheduled") return "VS";
  const { home, away } = match.score;
  return home === null || away === null ? MISSING : `${home} : ${away}`;
}

/** "PK 4:2" under the score of a shoot-out (regular/extra-time score stays separate). */
export function penaltyText(match: MatchSummary): string | null {
  const { penaltyHome, penaltyAway } = match.score;
  return penaltyHome === null || penaltyAway === null ? null : `PK ${penaltyHome}:${penaltyAway}`;
}

/** Kickoff time in KST as HH:mm, "시간 미정" while the provider has not fixed it (TBD / postponed). */
export function kickoffTime(match: MatchSummary): string {
  return match.timeConfirmed ? formatKstTime(match.kickoffAt) : "시간 미정";
}

/** Postponed / cancelled / abandoned / decided by a ruling: shown in the warning colour. */
export function isChanged(match: MatchSummary): boolean {
  return (
    match.status === "postponed" ||
    match.status === "cancelled" ||
    match.status === "abandoned" ||
    match.finishType === "awarded" ||
    match.finishType === "walkover"
  );
}

/** Short status word: badges and TOP 5 strip summaries. */
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

/**
 * Kickoff time has passed but the stored status is still "scheduled": the provider has not
 * confirmed the start yet (live sync pending), so the screen says 상태 확인 중, not 예정.
 */
export function awaitingStatus(match: MatchSummary, now: number): boolean {
  return match.status === "scheduled" && match.timeConfirmed && Date.parse(match.kickoffAt) <= now;
}

/**
 * Notes under a status badge: the abandoned-score notice and the provider's reason, both kept
 * when both apply (e.g. "중단 시점 스코어" + "기상 악화로 경기 중단").
 */
export function statusNotes(match: MatchSummary): string[] {
  const notes = match.status === "abandoned" ? ["중단 시점 스코어"] : [];
  if (match.statusReason) notes.push(match.statusReason);
  return notes;
}
