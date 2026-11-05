"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * false on the server and during hydration, true afterwards. Sections that read shared
 * TanStack Query caches render their placeholder until then, so data another component
 * fetched first never makes the hydrating HTML differ from the server's (§3.1, chat 04
 * report on `CompetitionFilter`).
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
