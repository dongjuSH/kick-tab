"use client";

import { useQuery } from "@tanstack/react-query";
import { competitionsQuery } from "@/features/schedule/queries";
import { competitionName } from "@/lib/format/match";
import { competitionLabel } from "./model";

/**
 * Competition names of the standings screens: the DB `name_ko` from `/competitions` (the same
 * list the schedule already caches, guide §3.1 — 06 개선 2026-11-20), and the seeded value of
 * `model.ts` while it loads or when the list cannot be read.
 */
export function useCompetitionLabel(): (id: number) => string {
  const competitions = useQuery(competitionsQuery);
  return (id) => {
    const found = competitions.data?.find((c) => c.id === id);
    return found ? competitionName(found) : competitionLabel(id);
  };
}
