import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { TopMatches } from "@/lib/api/types";

/**
 * GET /api/v1/top-matches/current. The strip lives in the root layout and can stay on
 * screen for hours, so freshness is explicit (cross-review #6):
 * - polls every 30 minutes while the tab is visible (no background polling): the Monday
 *   00:00 KST selection, a new week and the latest match status/score appear within 30 min;
 * - refetches when the window regains focus or the list is expanded, if older than 5 min.
 */
const TOP5_STALE_MS = 5 * 60_000;
const TOP5_POLL_MS = 30 * 60_000;

export const currentTopMatchesQuery = queryOptions({
  queryKey: queryKeys.topMatches.current(),
  queryFn: async ({ signal }) => (await apiFetch<TopMatches>("/top-matches/current", { signal })).data,
  staleTime: TOP5_STALE_MS,
  refetchInterval: TOP5_POLL_MS,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
});
