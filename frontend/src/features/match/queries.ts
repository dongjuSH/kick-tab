import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type {
  HeadToHead,
  MatchInfo,
  MatchRecords,
  MatchSummary,
  ReviewList,
  ReviewSort,
  UpdatedMeta,
} from "@/lib/api/types";
import { liveRefetchInterval } from "@/features/schedule/queries";

/**
 * Match detail queries (MAT-001~005, REV-004). Each area is fetched on its own so one
 * failure never hides the others. The match itself follows the schedule's live rule
 * (every minute while live or about to start, only while the tab is visible).
 */
export interface MatchData<T> {
  data: T;
  meta: UpdatedMeta;
}

export const LIVE_POLL_MS = 60_000;

export function matchInfoQuery(id: number) {
  return queryOptions({
    queryKey: queryKeys.matches.info(id),
    queryFn: ({ signal }): Promise<MatchData<MatchInfo>> =>
      apiFetch<MatchInfo, UpdatedMeta>(`/fixtures/${id}`, { signal }),
    refetchInterval: (query) => {
      const match = query.state.data?.data.match;
      return match ? liveRefetchInterval([match]) : false;
    },
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

const LINEUP_LEAD_MS = 60 * 60_000;
const LINEUP_POLL_MS = 10 * 60_000;

/** The server merges requests and enforces its own supplement cooldown. Before kickoff,
 * wake at the lineup window and check every ten minutes until a lineup is available. */
export function matchRecordsQuery(match: MatchSummary) {
  const id = match.id;
  return queryOptions({
    queryKey: queryKeys.matches.records(id),
    queryFn: ({ signal }): Promise<MatchData<MatchRecords>> =>
      apiFetch<MatchRecords, UpdatedMeta>(`/fixtures/${id}/detail`, { signal }),
    refetchInterval: (query) => {
      if (match.status === "live") return LIVE_POLL_MS;
      if (match.status !== "scheduled" || query.state.data?.data.lineups.status === "available") return false;
      const wait = Date.parse(match.kickoffAt) - LINEUP_LEAD_MS - Date.now();
      return wait > 0 ? Math.min(wait + 1_000, 2 ** 31 - 1) : LINEUP_POLL_MS;
    },
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

export function headToHeadQuery(id: number) {
  return queryOptions({
    queryKey: queryKeys.matches.headToHead(id),
    queryFn: ({ signal }): Promise<MatchData<HeadToHead>> =>
      apiFetch<HeadToHead, UpdatedMeta>(`/fixtures/${id}/head-to-head`, { signal }),
    staleTime: 10 * 60_000,
  });
}

export function reviewsQuery(id: number, sort: ReviewSort) {
  return queryOptions({
    queryKey: queryKeys.matches.reviews(id, sort),
    queryFn: async ({ signal }) =>
      (await apiFetch<ReviewList>(`/fixtures/${id}/reviews`, { query: { sort }, signal })).data,
  });
}
