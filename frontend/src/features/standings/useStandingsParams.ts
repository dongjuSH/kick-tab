"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import type { RankingType } from "@/lib/api/types";
import { DEFAULT_LEAGUE, LEAGUES, UEFA, isRankingType, isStage, isUefa, type UefaStage } from "./model";

export interface StandingsParams {
  /** Competition from the URL (default Premier League); null when the URL names another one. */
  league: number | null;
  /** Season from the URL; null = not given (the current season). */
  season: number | null;
  /** The URL named something that is not a season number (shown as unsupported). */
  seasonInvalid: boolean;
  /** UEFA stage (default the league phase); unused for the five leagues. */
  stage: UefaStage;
  /** The URL named a stage that does not exist (shown, never replaced). */
  stageInvalid: boolean;
  type: RankingType;
  /** The URL named a ranking type that does not exist (shown, never replaced). */
  typeInvalid: boolean;
}

function positive(value: string | null): number | null {
  if (value === null || value === "") return null;
  return /^[1-9]\d{0,9}$/.test(value) ? Number(value) : Number.NaN;
}

type Change = Partial<{ league: number; season: number; stage: UefaStage }>;

/**
 * Standings state lives in the URL (LEAG-002, guide §6.6): `/standings?league=2&season=2025
 * &stage=r16` or `/standings?league=78&type=saves`. Competition, season and stage changes are
 * history steps (Back returns to the previous view); a new competition opens on its default
 * (UEFA: the league phase, rule 2). The ranking type is kept across them and only replaces
 * the current entry, like a tab. Anything the service does not offer is reported, never
 * swapped for something else.
 */
export function useStandingsParams() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const rawLeague = positive(params.get("league"));
  const season = positive(params.get("season"));
  const rawStage = params.get("stage");
  const rawType = params.get("type");
  const known = [...LEAGUES, ...UEFA].some((c) => c.id === rawLeague);
  const state: StandingsParams = {
    league: rawLeague === null ? DEFAULT_LEAGUE : known ? rawLeague : null,
    season: Number.isNaN(season) ? null : season,
    seasonInvalid: Number.isNaN(season),
    stage: isStage(rawStage) ? rawStage : "league",
    stageInvalid: rawStage !== null && rawStage !== "" && !isStage(rawStage),
    type: isRankingType(rawType) ? rawType : "goals",
    typeInvalid: rawType !== null && rawType !== "" && !isRankingType(rawType),
  };

  const href = useCallback(
    (change: Change & { type?: RankingType }) => {
      const next = new URLSearchParams(params.toString());
      if (change.league !== undefined) {
        next.set("league", String(change.league));
        next.delete("stage");
      }
      if (change.season !== undefined) next.set("season", String(change.season));
      if (change.stage !== undefined) {
        if (change.stage === "league") next.delete("stage");
        else next.set("stage", change.stage);
      }
      if (change.type !== undefined) next.set("type", change.type);
      return `${pathname}?${next.toString()}`;
    },
    [params, pathname],
  );

  const select = useCallback(
    (change: Change) => router.push(href(change), { scroll: false }),
    [href, router],
  );

  /** Same table, another list: no server round trip and no extra Back step (guide §3.1). */
  const selectType = useCallback(
    (type: RankingType) => window.history.replaceState(null, "", href({ type })),
    [href],
  );

  return { ...state, uefa: state.league !== null && isUefa(state.league), select, selectType };
}
