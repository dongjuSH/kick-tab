import type { MatchSummary } from "@/lib/api/types";

/**
 * Favourite-team matches from `GET /fixtures/next` (FAV-004). The server already picks each
 * team's live match, else its nearest upcoming one, and lists them live first, then by
 * kickoff; a match between two favourites appears once. Shared by the schedule's favourite
 * panel and my page. Fixed by `tests/mypage.test.mjs`.
 */

/** The matches of the current list: a released team's match leaves before the next fetch. */
export function favoriteMatches(matches: readonly MatchSummary[], ids: readonly number[]): MatchSummary[] {
  return matches.filter((match) => ids.includes(match.home.id) || ids.includes(match.away.id));
}

/**
 * One team's match: the first listed match it plays in. In that order the team's own pick
 * (live, else the earliest) always comes before any later match another favourite picked, so
 * a match between two favourites shows on both teams' rows.
 */
export function teamNextMatch(matches: readonly MatchSummary[], teamId: number): MatchSummary | null {
  return matches.find((match) => match.home.id === teamId || match.away.id === teamId) ?? null;
}
