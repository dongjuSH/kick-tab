import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { MISSING, formatKstTime } from "./kst";

/**
 * Display rules shared by every match list (guide §6.4 status table, LIVE-001·002):
 * schedule cards, favourite schedule and TOP 5.
 */

export function teamName(team: TeamRef): string {
  return team.nameKo ?? team.nameEn;
}

/** Korean competition label on schedule screens (Figma 187:591·187:1946): "챔피언스리그". */
export function competitionName(competition: { nameKo: string | null; shortName: string }): string {
  return (competition.nameKo ?? competition.shortName).replace(/^UEFA\s+/, "");
}

/** Not played yet (scheduled, postponed) → "VS"; a missing score → "—", never 0:0. */
export function scoreText(match: MatchSummary): string {
  if (match.status === "scheduled" || match.status === "postponed") return "VS";
  const { home, away } = match.score;
  return home === null || away === null ? MISSING : `${home} : ${away}`;
}

/** "PK 4:2" under the score of a shoot-out (regular/extra-time score stays separate). */
export function penaltyText(match: MatchSummary): string | null {
  const { penaltyHome, penaltyAway } = match.score;
  return penaltyHome === null || penaltyAway === null ? null : `PK ${penaltyHome}:${penaltyAway}`;
}

/** Kickoff time in KST, "미정" while the provider has not fixed it (TBD / postponed). */
export function kickoffTime(match: MatchSummary): string {
  return match.timeConfirmed ? formatKstTime(match.kickoffAt) : "미정";
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
