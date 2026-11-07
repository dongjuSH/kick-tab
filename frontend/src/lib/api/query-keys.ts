/**
 * TanStack Query key rules (guide §6.6):
 * - Root = the API resource in kebab-case, matching the /api/v1 path segment.
 * - Then the scope ("current", "list", "detail", ...), then one params object or id.
 * - Always build keys through this file so invalidation after a mutation can target a
 *   whole resource, e.g. queryClient.invalidateQueries({ queryKey: queryKeys.topMatches.all }).
 * - Member-only data goes under "me" so logout can drop it with queryKeys.me.all.
 */
export const queryKeys = {
  topMatches: {
    all: ["top-matches"] as const,
    current: () => ["top-matches", "current"] as const,
    version: () => ["top-matches", "version"] as const,
  },
  matches: {
    info: (id: number) => ["matches", "info", { id }] as const,
    records: (id: number) => ["matches", "records", { id }] as const,
    headToHead: (id: number) => ["matches", "head-to-head", { id }] as const,
    reviews: (id: number, sort: string) => ["matches", "reviews", { id, sort }] as const,
  },
  competitions: {
    all: ["competitions"] as const,
  },
  seasons: {
    all: ["seasons"] as const,
  },
  results: {
    list: (params: { season: number | null; competitions: readonly number[]; team: number | null; page: number }) =>
      ["results", "list", { ...params, competitions: params.competitions.join(",") }] as const,
  },
  standings: {
    table: (league: number, season: number | null) => ["standings", "table", { league, season }] as const,
    summary: () => ["standings", "summary"] as const,
  },
  playerRankings: {
    list: (league: number, season: number | null, type: string) =>
      ["player-rankings", "list", { league, season, type }] as const,
  },
  fixtures: {
    byDate: (date: string) => ["fixtures", "date", { date }] as const,
    team: (teamId: number, today: string) => ["fixtures", "team", { teamId, today }] as const,
    next: (teamIds: readonly number[]) => ["fixtures", "next", { teams: teamIds.join(",") }] as const,
  },
  teams: {
    /** season null = the current season (main schedule). */
    search: (q: string, season: number | null = null) => ["teams", "search", { q, season }] as const,
    /** Team browse (chat 07): league null = all five leagues, q null = no search. */
    list: (params: { league: number | null; q: string | null; page: number }) => ["teams", "list", params] as const,
    /** Team detail (chat 08): one key per area so one failure never hides the others. */
    detail: (id: number) => ["teams", "detail", { id }] as const,
    fixtures: (id: number) => ["teams", "fixtures", { id }] as const,
    squad: (id: number) => ["teams", "squad", { id }] as const,
    seasonStats: (id: number, season: number) => ["teams", "season-stats", { id, season }] as const,
    transfers: (id: number, season: number) => ["teams", "transfers", { id, season }] as const,
  },
  news: {
    list: (badge: string | null) => ["news", "list", { badge }] as const,
    team: (teamId: number) => ["news", "team", { teamId }] as const,
    link: (id: number) => ["news", "link", { id }] as const,
  },
  me: {
    all: ["me"] as const,
  },
} as const;
