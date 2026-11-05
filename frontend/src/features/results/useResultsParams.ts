"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/** URL conditions that were given but cannot be read (never replaced by "all" or page 1). */
export type InvalidCondition = "team" | "competitions" | "page";

export interface ResultsParams {
  /** Season from the URL; null = not given (the current season). */
  season: number | null;
  /** The URL named something that is not a season number (shown as unsupported). */
  seasonInvalid: boolean;
  /** Selected competition ids; empty = every competition of the season. */
  competitions: number[];
  team: number | null;
  page: number;
  /** Given but unreadable team / competitions / page: shown as an invalid condition. */
  invalid: InvalidCondition[];
}

/** A positive integer, null when the parameter is absent or empty, NaN when unreadable. */
function positive(value: string | null): number | null {
  if (value === null || value === "") return null;
  return /^[1-9]\d{0,9}$/.test(value) ? Number(value) : Number.NaN;
}

/** Comma-separated positive ids; NaN in the list marks an unreadable part. */
function ids(value: string | null): number[] {
  if (value === null || value === "") return [];
  return [...new Set(value.split(",").map((part) => positive(part) ?? Number.NaN))];
}

type Change = Partial<{ season: number; competitions: number[]; team: number | null; page: number }>;

/**
 * Past results filters live in the URL (HIST-002, guide §6.6): `?season=2025&competitions=39,45
 * &team=48&page=2`. Every change is a history step, so Back returns to the previous
 * condition or page. Season, competition and team changes go back to page 1 and keep the
 * other conditions (season change keeps team and competitions; clearing the team keeps
 * season and competitions).
 */
export function useResultsParams() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const season = positive(params.get("season"));
  const competitions = ids(params.get("competitions"));
  const team = positive(params.get("team"));
  const page = positive(params.get("page"));
  const invalid: InvalidCondition[] = [];
  if (Number.isNaN(team)) invalid.push("team");
  if (competitions.some(Number.isNaN)) invalid.push("competitions");
  if (Number.isNaN(page)) invalid.push("page");
  const state: ResultsParams = {
    season: Number.isNaN(season) ? null : season,
    seasonInvalid: Number.isNaN(season),
    competitions: competitions.filter((id) => !Number.isNaN(id)),
    team: Number.isNaN(team) ? null : team,
    page: page === null || Number.isNaN(page) ? 1 : page,
    invalid,
  };

  const go = useCallback(
    (next: URLSearchParams) => {
      const qs = next.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  const update = useCallback(
    (change: Change) => {
      const next = new URLSearchParams(params.toString());
      const set = (key: string, value: string | null) => (value ? next.set(key, value) : next.delete(key));
      if ("season" in change) set("season", String(change.season));
      if ("competitions" in change) set("competitions", change.competitions?.length ? change.competitions.join(",") : null);
      if ("team" in change) set("team", change.team ? String(change.team) : null);
      // A new condition always starts on the first page.
      set("page", "page" in change && change.page && change.page > 1 ? String(change.page) : null);
      go(next);
    },
    [go, params],
  );

  /** Filter reset: the season stays; team, search text, competitions and page are cleared. */
  const reset = useCallback(() => {
    const next = new URLSearchParams();
    const season = params.get("season");
    if (season) next.set("season", season);
    go(next);
  }, [go, params]);

  return { ...state, update, reset };
}
