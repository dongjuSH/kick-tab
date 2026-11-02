import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { CompetitionItem, FavoriteSchedule, MatchSummary, ScheduleMeta, TeamSchedule } from "@/lib/api/types";

/**
 * Live refresh (LIVE-004, guide §6.5): the server collects every minute while a match is
 * live or about to start; the screen polls the stored data only in that window, and only
 * while the tab is visible. Otherwise lists refresh on focus after a minute.
 */
const LIVE_POLL_MS = 60_000;
const LEAD_MS = 30 * 60_000;
const LAG_MS = 3 * 60 * 60_000;

function needsLiveRefresh(matches: readonly MatchSummary[]): boolean {
  if (matches.length === 0) return false; // also keeps the clock out of the server prerender
  const now = Date.now();
  return matches.some((m) => {
    if (m.status === "live") return true;
    if (m.status !== "scheduled" && m.status !== "unknown") return false;
    const kickoff = Date.parse(m.kickoffAt);
    return kickoff - LEAD_MS <= now && now <= kickoff + LAG_MS;
  });
}

/**
 * `refetchInterval` for match lists: every minute inside the live window; otherwise one
 * fetch when the next listed match enters it (30 minutes before kickoff), after which the
 * minute polling takes over. Never while the tab is hidden (refetchIntervalInBackground).
 */
function liveRefetchInterval(matches: readonly MatchSummary[]): number | false {
  if (matches.length === 0) return false; // no clock in the server prerender
  if (needsLiveRefresh(matches)) return LIVE_POLL_MS;
  const now = Date.now();
  const waits = matches
    .filter((m) => m.status === "scheduled" || m.status === "unknown")
    .map((m) => Date.parse(m.kickoffAt) - LEAD_MS - now)
    .filter((ms) => ms > 0);
  // setTimeout holds at most ~24.8 days; the lists span about two weeks.
  return waits.length ? Math.min(Math.min(...waits) + 1_000, 2 ** 31 - 1) : false;
}

export interface ScheduleData<T> {
  data: T;
  meta: ScheduleMeta;
}

export const competitionsQuery = queryOptions({
  queryKey: queryKeys.competitions.all,
  queryFn: async ({ signal }) => (await apiFetch<CompetitionItem[]>("/competitions", { signal })).data,
  staleTime: 60 * 60_000,
});

export function fixturesByDateQuery(date: string) {
  return queryOptions({
    queryKey: queryKeys.fixtures.byDate(date),
    queryFn: async ({ signal }): Promise<ScheduleData<MatchSummary[]>> =>
      apiFetch<MatchSummary[], ScheduleMeta>("/fixtures", { query: { date }, signal }),
    refetchInterval: (query) => liveRefetchInterval(query.state.data?.data ?? []),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

export function favoriteScheduleQuery(teamIds: readonly number[]) {
  return queryOptions({
    queryKey: queryKeys.fixtures.next(teamIds),
    queryFn: async ({ signal }): Promise<ScheduleData<FavoriteSchedule>> =>
      apiFetch<FavoriteSchedule, ScheduleMeta>("/fixtures/next", { query: { teams: teamIds }, signal }),
    enabled: teamIds.length > 0,
    refetchInterval: (query) => liveRefetchInterval(query.state.data?.data.matches ?? []),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Team view: the team's stored matches today .. today+13 (schedule UX policy 2026-11-02).
 * The server picks the window; `today` is in the key only so a new KST day fetches again.
 */
export function teamScheduleQuery(teamId: number, today: string) {
  return queryOptions({
    queryKey: queryKeys.fixtures.team(teamId, today),
    queryFn: async ({ signal }): Promise<ScheduleData<TeamSchedule>> =>
      apiFetch<TeamSchedule, ScheduleMeta>("/fixtures/team", { query: { team: teamId }, signal }),
    refetchInterval: (query) => liveRefetchInterval(query.state.data?.data.matches ?? []),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}
