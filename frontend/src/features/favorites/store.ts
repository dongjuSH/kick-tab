/**
 * Guest favourite teams in localStorage (FAV-001~003, PRD 9장): this browser only, at most
 * five team ids, no duplicates. Every storage access is guarded: a blocked or broken
 * storage reports "unavailable" and the public screens keep working (guide §6.6).
 * Chat 02 adds the member list (DB) as a second source; the two are never merged.
 */

const FAVORITES_KEY = "kt-fav-guest";
export const FAVORITES_MAX = 5;

export type FavoritesSnapshot =
  | { status: "loading"; ids: readonly number[] } // server render, before the browser reads
  | { status: "ready"; ids: readonly number[] }
  | { status: "unavailable"; ids: readonly number[] };

export type FavoriteChange = "added" | "removed" | "exists" | "limit" | "unavailable" | "failed";

const SERVER: FavoritesSnapshot = { status: "loading", ids: [] };
const UNAVAILABLE: FavoritesSnapshot = { status: "unavailable", ids: [] };
const listeners = new Set<() => void>();
let cache: { raw: string | null; snapshot: FavoritesSnapshot } | null = null;

function parse(raw: string | null): number[] {
  if (!raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    const ids = value.filter((v): v is number => Number.isInteger(v) && v > 0);
    return [...new Set(ids)].slice(0, FAVORITES_MAX);
  } catch {
    return [];
  }
}

export function readFavorites(): FavoritesSnapshot {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(FAVORITES_KEY);
  } catch {
    cache = null;
    return UNAVAILABLE;
  }
  // Same stored value -> same object, as useSyncExternalStore requires.
  if (cache?.raw !== raw) cache = { raw, snapshot: { status: "ready", ids: parse(raw) } };
  return cache!.snapshot;
}

export function serverFavorites(): FavoritesSnapshot {
  return SERVER;
}

function notify() {
  listeners.forEach((listener) => listener());
}

export function subscribeFavorites(listener: () => void): () => void {
  listeners.add(listener);
  // Other tabs of this browser change the same list.
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === FAVORITES_KEY) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

function write(ids: number[]): boolean {
  try {
    window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(ids));
    return true;
  } catch {
    return false;
  } finally {
    notify();
  }
}

/**
 * The stored list right before a change. When it differs from what the screens last read
 * (another tab saved first and its storage event has not arrived), every subscriber is told,
 * so a refusal is shown next to the list it was refused for (07: 5 / 5 notice).
 */
function latest(): FavoritesSnapshot {
  const shown = cache?.snapshot;
  const current = readFavorites();
  if (shown && current !== shown) notify();
  return current;
}

export function addFavorite(teamId: number): FavoriteChange {
  const current = latest();
  if (current.status !== "ready") return "unavailable";
  if (current.ids.includes(teamId)) return "exists";
  if (current.ids.length >= FAVORITES_MAX) return "limit";
  return write([...current.ids, teamId]) ? "added" : "failed";
}

export function removeFavorite(teamId: number): FavoriteChange {
  const current = latest();
  if (current.status !== "ready") return "unavailable";
  if (!current.ids.includes(teamId)) return "removed"; // nothing to change (FAV-003)
  return write(current.ids.filter((id) => id !== teamId)) ? "removed" : "failed";
}
