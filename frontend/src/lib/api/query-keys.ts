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
  },
  competitions: {
    all: ["competitions"] as const,
  },
  fixtures: {
    byDate: (date: string) => ["fixtures", "date", { date }] as const,
    team: (teamId: number, today: string) => ["fixtures", "team", { teamId, today }] as const,
    next: (teamIds: readonly number[]) => ["fixtures", "next", { teams: teamIds.join(",") }] as const,
  },
  teams: {
    search: (q: string) => ["teams", "search", { q }] as const,
  },
  news: {
    list: (badge: string | null) => ["news", "list", { badge }] as const,
    link: (id: number) => ["news", "link", { id }] as const,
  },
  me: {
    all: ["me"] as const,
  },
} as const;
