import { infiniteQueryOptions, queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type {
  NewsItem,
  NewsMeta,
  TeamFixtures,
  TeamFixturesMeta,
  TeamOverview,
  TeamSeasonStats,
  TeamSquad,
  TeamSyncMeta,
  TeamTransfers,
} from "@/lib/api/types";
import { liveRefetchInterval } from "@/features/schedule/queries";

/**
 * Team detail areas (TEAM-001~006). Each area has its own request, so one failure is shown in
 * that area only. Collected data changes at most hourly; the fixtures follow the schedule's
 * live rule while a listed match is live or about to start.
 */
const COLLECTED_STALE_MS = 5 * 60_000;

export function teamOverviewQuery(id: number) {
  return queryOptions({
    queryKey: queryKeys.teams.detail(id),
    queryFn: ({ signal }) => apiFetch<TeamOverview>(`/teams/${id}`, { signal }),
    staleTime: COLLECTED_STALE_MS,
    // 404 / 503 are answers about the team, not hiccups: show them at once.
    retry: (count, error) => count < 2 && !(isApiError(error) && (error.status === 404 || error.status === 503)),
  });
}

export function teamFixturesQuery(id: number) {
  return queryOptions({
    queryKey: queryKeys.teams.fixtures(id),
    queryFn: ({ signal }) => apiFetch<TeamFixtures, TeamFixturesMeta>(`/teams/${id}/fixtures`, { signal }),
    refetchInterval: (query) => {
      const data = query.state.data?.data;
      return data ? liveRefetchInterval(data.upcoming) : false;
    },
    refetchIntervalInBackground: false,
  });
}

export function teamSquadQuery(id: number) {
  return queryOptions({
    queryKey: queryKeys.teams.squad(id),
    queryFn: ({ signal }) => apiFetch<TeamSquad, TeamSyncMeta>(`/teams/${id}/squad`, { signal }),
    staleTime: COLLECTED_STALE_MS,
  });
}

export function teamSeasonStatsQuery(id: number, season: number) {
  return queryOptions({
    queryKey: queryKeys.teams.seasonStats(id, season),
    queryFn: ({ signal }) =>
      apiFetch<TeamSeasonStats, TeamSyncMeta>(`/teams/${id}/season-stats`, { query: { season }, signal }),
    staleTime: COLLECTED_STALE_MS,
  });
}

export function teamTransfersQuery(id: number, season: number) {
  return queryOptions({
    queryKey: queryKeys.teams.transfers(id, season),
    queryFn: ({ signal }) =>
      apiFetch<TeamTransfers, TeamSyncMeta>(`/teams/${id}/transfers`, { query: { season }, signal }),
    staleTime: COLLECTED_STALE_MS,
  });
}

const TEAM_NEWS_PAGE = 6;

export function teamNewsQuery(teamId: number) {
  return infiniteQueryOptions({
    queryKey: queryKeys.news.team(teamId),
    queryFn: ({ pageParam, signal }) =>
      apiFetch<NewsItem[], NewsMeta>("/news", {
        query: { team: teamId, cursor: pageParam, size: TEAM_NEWS_PAGE },
        signal,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.meta.nextCursor,
    staleTime: COLLECTED_STALE_MS,
  });
}
