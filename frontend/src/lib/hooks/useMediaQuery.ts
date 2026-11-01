"use client";

import { useSyncExternalStore } from "react";

/** Matches a CSS media query. Returns `serverValue` during SSR and hydration. */
export function useMediaQuery(query: string, serverValue = false): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => serverValue,
  );
}

/** Desktop layout starts at 1024px (menus collapse and columns stack below it). */
export const DESKTOP_QUERY = "(min-width: 1024px)";
