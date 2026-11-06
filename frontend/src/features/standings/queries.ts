import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type {
  LeagueStandings,
  PlayerRankings,
  RankingType,
  StandingsMeta,
  StandingsSummary,
} from "@/lib/api/types";

/** Tables change at most hourly on a matchday (guide §6.5): no polling, refetch on focus. */
const STALE = 5 * 60_000;

/** One league season table (LEAG-002). `season` null = the current season. */
export function standingsQuery(league: number, season: number | null) {
  return queryOptions({
    queryKey: queryKeys.standings.table(league, season),
    queryFn: async ({ signal }): Promise<{ data: LeagueStandings; meta: StandingsMeta }> =>
      apiFetch<LeagueStandings, StandingsMeta>("/standings", {
        query: { league, season: season ?? undefined },
        signal,
      }),
    staleTime: STALE,
  });
}

/** Main page compact tables of the five leagues, current season (LEAG-001). */
export const standingsSummaryQuery = queryOptions({
  queryKey: queryKeys.standings.summary(),
  queryFn: async ({ signal }) => (await apiFetch<StandingsSummary>("/standings/summary", { signal })).data,
  staleTime: STALE,
});

/** Player ranking of one type (LEAG-004). */
export function playerRankingsQuery(league: number, season: number | null, type: RankingType) {
  return queryOptions({
    queryKey: queryKeys.playerRankings.list(league, season, type),
    queryFn: async ({ signal }): Promise<{ data: PlayerRankings; meta: StandingsMeta }> =>
      apiFetch<PlayerRankings, StandingsMeta>("/player-rankings", {
        query: { league, season: season ?? undefined, type },
        signal,
      }),
    staleTime: STALE,
  });
}
