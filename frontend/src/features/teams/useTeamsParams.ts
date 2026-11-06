"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { LEAGUES } from "@/features/standings/model";

/** URL conditions that were given but cannot be used (never replaced by "all" or page 1). */
export type InvalidCondition = "league" | "q" | "page";

export const SEARCH_MAX = 40;

export interface TeamsParams {
  /** Five-league id; null = every league (also when the URL names an unreadable one). */
  league: number | null;
  /** Trimmed search text; null = no search. */
  q: string | null;
  page: number;
  invalid: InvalidCondition[];
  /** The whole query string, to notice any URL change (the search field's typing session). */
  urlKey: string;
}

/** A positive integer, null when the parameter is absent or empty, NaN when unreadable. */
function positive(value: string | null): number | null {
  if (value === null || value === "") return null;
  return /^[1-9]\d{0,9}$/.test(value) ? Number(value) : Number.NaN;
}

type Change = Partial<{ league: number | null; q: string | null; page: number }>;

/**
 * Team browse state lives in the URL (LEAG-003, guide §6.6): `/teams?league=39&q=맨시&page=2`.
 * Every change is a history step unless `replace` is asked (later keystrokes of one search),
 * so Back returns to the previous league, search or page. A league or search change starts on
 * the first page and keeps the other condition. A league outside the five, an unreadable page
 * or an over-long search is reported, never swapped for "all" or page 1.
 */
export function useTeamsParams() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const league = positive(params.get("league"));
  const q = (params.get("q") ?? "").trim();
  const page = positive(params.get("page"));
  const invalid: InvalidCondition[] = [];
  const knownLeague = league !== null && LEAGUES.some((l) => l.id === league);
  if (league !== null && !knownLeague) invalid.push("league");
  if (q.length > SEARCH_MAX) invalid.push("q");
  if (Number.isNaN(page)) invalid.push("page");
  const state: TeamsParams = {
    league: knownLeague ? league : null,
    q: q && q.length <= SEARCH_MAX ? q : null,
    page: page === null || Number.isNaN(page) ? 1 : page,
    invalid,
    urlKey: params.toString(),
  };

  const update = useCallback(
    (change: Change, options: { replace?: boolean } = {}) => {
      const next = new URLSearchParams(params.toString());
      const set = (key: string, value: string | null) => (value ? next.set(key, value) : next.delete(key));
      if ("league" in change) set("league", change.league ? String(change.league) : null);
      if ("q" in change) set("q", change.q?.trim() || null);
      // A new league or search always starts on the first page.
      set("page", "page" in change && change.page && change.page > 1 ? String(change.page) : null);
      const qs = next.toString();
      const url = qs ? `${pathname}?${qs}` : pathname;
      if (options.replace) router.replace(url, { scroll: false });
      else router.push(url, { scroll: false });
    },
    [params, pathname, router],
  );

  /** Clears league, search and page. */
  const reset = useCallback(() => router.push(pathname, { scroll: false }), [pathname, router]);

  return { ...state, update, reset };
}
