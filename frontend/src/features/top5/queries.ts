import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { TopMatches, TopMatchesVersion } from "@/lib/api/types";

/**
 * GET /api/v1/top-matches/current: the public result. The strip lives in the root layout
 * and can stay open for hours:
 * - the list itself (latest kickoff/status/score of the fixed items) refreshes every
 *   30 minutes while visible, and on focus or expanding when older than 5 minutes;
 * - a replaced result (new week, delay notice, manual recovery) is detected separately
 *   through `topMatchesVersionQuery` and refetched right away (Top5Strip).
 * A failed refetch keeps the result already on screen.
 */
const TOP5_STALE_MS = 5 * 60_000;
const TOP5_POLL_MS = 30 * 60_000;
/** Public version check: a few bytes, so a replaced result shows within half a minute. */
export const TOP5_VERSION_POLL_MS = 30_000;

export const currentTopMatchesQuery = queryOptions({
  queryKey: queryKeys.topMatches.current(),
  queryFn: async ({ signal }) => (await apiFetch<TopMatches>("/top-matches/current", { signal })).data,
  staleTime: TOP5_STALE_MS,
  refetchInterval: TOP5_POLL_MS,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
});

export const topMatchesVersionQuery = queryOptions({
  queryKey: queryKeys.topMatches.version(),
  queryFn: async ({ signal }) =>
    (await apiFetch<TopMatchesVersion>("/top-matches/version", { signal })).data,
  staleTime: 0,
  refetchInterval: TOP5_VERSION_POLL_MS,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
  retry: false,
});

/** True when the shown result is not the published one any more (or the week changed). */
export function isOutdated(data: TopMatches, version: TopMatchesVersion): boolean {
  return data.version !== version.version || data.currentWeek.start !== version.currentWeekStart;
}
