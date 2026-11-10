import { useSyncExternalStore } from "react";

const TICK_MS = 30_000;
let now = 0;
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | undefined;

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (!timer) {
    timer = setInterval(() => {
      now = Date.now();
      listeners.forEach((notify) => notify());
    }, TICK_MS);
  }
  return () => {
    listeners.delete(listener);
    if (!listeners.size) {
      clearInterval(timer);
      timer = undefined;
    }
  };
}

function snapshot() {
  if (!now) now = Date.now();
  return now;
}

/**
 * Current time (ms) for render decisions such as "kickoff has passed", refreshed every 30 s
 * and shared by every subscriber. 0 during the server render, where no clock is read.
 */
export function useNow(): number {
  return useSyncExternalStore(subscribe, snapshot, () => 0);
}
