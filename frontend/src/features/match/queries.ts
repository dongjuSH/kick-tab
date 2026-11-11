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

/** Records exist from kickoff on: the page asks for them only then (no lineup polling
 * before kickoff, MAT-004 rule 4). The query has no timer of its own: `MatchRecords`
 * re-reads it once per match update while live and once on a status change, so a finish
 * costs exactly one final read (LIVE-004). The server merges requests and keeps its own
 * supplement cooldown. */
export function matchRecordsQuery(match: Pick<MatchSummary, "id">) {
  const id = match.id;
  return queryOptions({
    queryKey: queryKeys.matches.records(id),
    queryFn: ({ signal }): Promise<MatchData<MatchRecords>> =>
      apiFetch<MatchRecords, UpdatedMeta>(`/fixtures/${id}/detail`, { signal }),
    refetchOnWindowFocus: false,
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
