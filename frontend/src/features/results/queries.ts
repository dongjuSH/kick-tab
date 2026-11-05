import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { ResultsMeta, ResultsPage, SeasonItem } from "@/lib/api/types";

/** Season dropdown options (HIST-002); also used by standings (chat 06). */
export const seasonsQuery = queryOptions({
  queryKey: queryKeys.seasons.all,
  queryFn: async ({ signal }) => (await apiFetch<SeasonItem[]>("/seasons", { signal })).data,
  staleTime: 60 * 60_000,
});

export interface ResultsQueryParams {
  season: number | null;
  competitions: readonly number[];
  team: number | null;
  page: number;
}

/** One page of finished matches. Finished results do not change by the minute: no polling. */
export function resultsQuery(params: ResultsQueryParams) {
  return queryOptions({
    queryKey: queryKeys.results.list(params),
    queryFn: async ({ signal }): Promise<{ data: ResultsPage; meta: ResultsMeta }> =>
      apiFetch<ResultsPage, ResultsMeta>("/results", {
        query: {
          season: params.season ?? undefined,
          competitions: params.competitions.length ? params.competitions.join(",") : undefined,
          team: params.team ?? undefined,
          page: params.page > 1 ? params.page : undefined,
        },
        signal,
      }),
    staleTime: 5 * 60_000,
  });
}
