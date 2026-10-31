import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { TopMatches } from "@/lib/api/types";

/** GET /api/v1/top-matches/current. Rankings are recomputed every few hours (TOP-003). */
export const currentTopMatchesQuery = queryOptions({
  queryKey: queryKeys.topMatches.current(),
  queryFn: async ({ signal }) => (await apiFetch<TopMatches>("/top-matches/current", { signal })).data,
  staleTime: 5 * 60_000,
});
