import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { BrowseTeam, TeamsMeta } from "@/lib/api/types";

export interface TeamsQueryParams {
  league: number | null;
  q: string | null;
  page: number;
}

/** One page of current-season five-league teams (LEAG-003). Team lists change once a day. */
export function teamsQuery(params: TeamsQueryParams) {
  return queryOptions({
    queryKey: queryKeys.teams.list(params),
    queryFn: async ({ signal }): Promise<{ data: BrowseTeam[]; meta: TeamsMeta }> =>
      apiFetch<BrowseTeam[], TeamsMeta>("/teams", {
        query: {
          league: params.league ?? undefined,
          q: params.q ?? undefined,
          page: params.page > 1 ? params.page : undefined,
        },
        signal,
      }),
    staleTime: 10 * 60_000,
  });
}
