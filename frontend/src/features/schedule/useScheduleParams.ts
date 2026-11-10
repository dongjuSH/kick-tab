"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";
import { addDaysIso, kstTodayIso, parseIsoDate } from "@/lib/format/kst";
import type { DateAvailability } from "./DateBar";

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
 * Date to move to after applying competitions in the date view (SCH-004): only when the
 * current date is confirmed to have no match, the nearest confirmed match day from today.
 * Unconfirmed dates are skipped, never taken as match days (Figma 308:4631); before the
 * availability arrives nothing moves. `undefined` = stay.
 */
export function nearestMatchDate(
  dates: readonly string[],
  today: string,
  current: string,
  stateOf: (date: string) => DateAvailability,
): string | undefined {
  if (stateOf(current) !== "empty") return undefined;
  for (const date of dates) {
    if (date < today) continue;
    const state = stateOf(date);
    if (state === "pending") return undefined;
    if (state === "ready" || state === "partial") return date;
  }
  return undefined;
}

/** URL value of `from` when the competitions before the team view were "every competition". */
const ALL = "all";

/** Query after picking team `id`: "전체 대회", return point saved only from the date view. */
export function withTeam(query: string, id: number): string {
  const next = new URLSearchParams(query);
  if (!next.get("team")) next.set("from", next.get("competitions") ?? ALL);
  next.delete("competitions");
  next.set("team", String(id));
  return next.toString();
}

/** Query after clearing the team: the saved date stays, the saved competitions come back. */
export function withoutTeam(query: string): string {
  const next = new URLSearchParams(query);
  const from = next.get("from");
  next.delete("team");
  next.delete("from");
  // A team link without a saved return point (shared URL) returns to every competition.
  if (from && from !== ALL) next.set("competitions", from);
  else next.delete("competitions");
  return next.toString();
}

/**
 * Main schedule filters live in the URL (guide §6.6: back/forward and sharing work):
 * `?date=2026-11-03&competitions=39,2&team=50&from=135`. With `team` the view is the team's
 * 21 days (SCH-006, 2026-11-10): `competitions` narrows that team view, while `date` and
 * `from` keep the date and competitions from just before the first team was picked, which
 * clearing the team restores (the date bar stays mounted, so its position returns too).
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

  /**
   * Pick a team (search candidate or favourite button): every new team starts at "전체 대회".
   * The return point is saved only when leaving the date view, so switching teams or
   * narrowing the team view never overwrites it.
   */
  const selectTeam = useCallback(
    (id: number) => router.push(`${pathname}?${withTeam(params.toString(), id)}`, { scroll: false }),
    [params, pathname, router],
  );

  /** Clear the team (X, emptied search, same favourite again): restore date and competitions. */
  const clearTeam = useCallback(() => {
    const qs = withoutTeam(params.toString());
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [params, pathname, router]);

  const update = useCallback(
    (change: Partial<{ date: string | null; competitions: number[] }>) => {
      const next = new URLSearchParams(params.toString());
      const set = (key: string, value: string | null) => (value ? next.set(key, value) : next.delete(key));
      if ("date" in change) set("date", change.date ?? null);
      if ("competitions" in change) set("competitions", change.competitions?.length ? change.competitions.join(",") : null);
      const qs = next.toString();
      const url = qs ? `${pathname}?${qs}` : pathname;
      // Competition changes are history steps (Back returns to them, like entering/leaving
      // the team view); moving along the date bar only replaces the current entry.
      if ("competitions" in change) router.push(url, { scroll: false });
      else router.replace(url, { scroll: false });
    },
    [params, pathname, router],
  );

  /** Filter reset (SCH-006): today, every competition, no team. Other areas keep their state. */
  const reset = useCallback(() => router.push(pathname, { scroll: false }), [pathname, router]);

  return { ...state, update, selectTeam, clearTeam, reset };
}
