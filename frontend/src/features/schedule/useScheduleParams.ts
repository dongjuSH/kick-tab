"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";
import { addDaysIso, kstTodayIso, parseIsoDate } from "@/lib/format/kst";

/** Three calendar weeks in KST, including three past dates. */
export const SCHEDULE_BEFORE = 3;
export const SCHEDULE_DAYS = 21;

const DAY_MS = 86_400_000;
const KST_OFFSET_MS = 9 * 3_600_000; // KST has no daylight saving time

/**
 * Wakes the page at the next KST midnight (schedule UX policy: the base date changes while
 * the page stays open). Also checks when the tab becomes visible again, since timers may be
 * held back while a laptop sleeps.
 */
function subscribeKstMidnight(onChange: () => void) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const schedule = () => {
    const now = Date.now();
    const nextMidnight = (Math.floor((now + KST_OFFSET_MS) / DAY_MS) + 1) * DAY_MS - KST_OFFSET_MS;
    timer = setTimeout(() => {
      onChange();
      schedule();
    }, nextMidnight - now + 1_000);
  };
  const onVisible = () => document.visibilityState === "visible" && onChange();
  schedule();
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    clearTimeout(timer);
    document.removeEventListener("visibilitychange", onVisible);
  };
}

/** Today's KST date, re-rendering when it changes. */
function useKstToday(): string {
  return useSyncExternalStore(subscribeKstMidnight, kstTodayIso, kstTodayIso);
}

export interface ScheduleParams {
  today: string;
  dates: string[];
  /** Selected KST date; defaults to today. */
  date: string;
  /** false when ?date= is outside the date bar (shown as a range notice, never replaced). */
  dateInRange: boolean;
  /** Selected competition ids; empty = every competition. */
  competitions: number[];
  team: number | null;
}

function ids(value: string | null): number[] {
  if (!value) return [];
  return [...new Set(value.split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0))];
}

/**
 * Main schedule filters live in the URL (guide §6.6: back/forward and sharing work):
 * `?date=2026-11-03&competitions=39,2&team=50`. With `team` the view is the team's 21 days;
 * `date` stays as the date to return to when the team is cleared.
 */
export function useScheduleParams() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const today = useKstToday();
  const dates = Array.from({ length: SCHEDULE_DAYS }, (_, i) => addDaysIso(today, i - SCHEDULE_BEFORE));
  const rawDate = params.get("date");
  const date = rawDate && parseIsoDate(rawDate) ? rawDate : today;
  const team = Number(params.get("team"));

  const state: ScheduleParams = {
    today,
    dates,
    date,
    dateInRange: dates.includes(date),
    competitions: ids(params.get("competitions")),
    team: Number.isInteger(team) && team > 0 ? team : null,
  };

  const update = useCallback(
    (change: Partial<{ date: string | null; competitions: number[]; team: number | null }>) => {
      const next = new URLSearchParams(params.toString());
      const set = (key: string, value: string | null) => (value ? next.set(key, value) : next.delete(key));
      if ("date" in change) set("date", change.date ?? null);
      if ("competitions" in change) set("competitions", change.competitions?.length ? change.competitions.join(",") : null);
      if ("team" in change) set("team", change.team ? String(change.team) : null);
      const qs = next.toString();
      const url = qs ? `${pathname}?${qs}` : pathname;
      // Entering/leaving the team view and competition changes are history steps (Back
      // returns to them); moving along the date bar only replaces the current entry.
      if ("team" in change || "competitions" in change) router.push(url, { scroll: false });
      else router.replace(url, { scroll: false });
    },
    [params, pathname, router],
  );

  /** Filter reset (SCH-006): today, every competition, no team. Other areas keep their state. */
  const reset = useCallback(() => router.push(pathname, { scroll: false }), [pathname, router]);

  return { ...state, update, reset };
}
