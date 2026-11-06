"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import type { RankingType } from "@/lib/api/types";
import { DEFAULT_LEAGUE, LEAGUES, isRankingType } from "./model";

export interface StandingsParams {
  /** League from the URL (default Premier League); null when the URL names another one. */
  league: number | null;
  /** Season from the URL; null = not given (the current season). */
  season: number | null;
  /** The URL named something that is not a season number (shown as unsupported). */
  seasonInvalid: boolean;
  type: RankingType;
  /** The URL named a ranking type that does not exist (shown, never replaced). */
  typeInvalid: boolean;
}

function positive(value: string | null): number | null {
  if (value === null || value === "") return null;
  return /^[1-9]\d{0,9}$/.test(value) ? Number(value) : Number.NaN;
}

/**
 * Standings state lives in the URL (LEAG-002, guide §6.6): `/standings?league=78&season=2025
 * &type=saves`. League and season changes are history steps (Back returns to the previous
 * table); the ranking type is kept across them and only replaces the current entry, like a
 * tab. A league, season or type the service does not offer is reported, never swapped.
 */
export function useStandingsParams() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const rawLeague = positive(params.get("league"));
  const season = positive(params.get("season"));
  const rawType = params.get("type");
  const state: StandingsParams = {
    league:
      rawLeague === null ? DEFAULT_LEAGUE : LEAGUES.some((l) => l.id === rawLeague) ? rawLeague : null,
    season: Number.isNaN(season) ? null : season,
    seasonInvalid: Number.isNaN(season),
    type: isRankingType(rawType) ? rawType : "goals",
    typeInvalid: rawType !== null && rawType !== "" && !isRankingType(rawType),
  };

  const href = useCallback(
    (change: Partial<{ league: number; season: number; type: RankingType }>) => {
      const next = new URLSearchParams(params.toString());
      if (change.league !== undefined) next.set("league", String(change.league));
      if (change.season !== undefined) next.set("season", String(change.season));
      if (change.type !== undefined) next.set("type", change.type);
      return `${pathname}?${next.toString()}`;
    },
    [params, pathname],
  );

  const select = useCallback(
    (change: { league?: number; season?: number }) => router.push(href(change), { scroll: false }),
    [href, router],
  );

  /** Same table, another list: no server round trip and no extra Back step (guide §3.1). */
  const selectType = useCallback(
    (type: RankingType) => window.history.replaceState(null, "", href({ type })),
    [href],
  );

  return { ...state, select, selectType };
}
