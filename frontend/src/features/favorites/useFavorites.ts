"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { authEpoch, memberRequest, useAuth } from "@/features/auth/session";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type { MemberFavorites } from "@/lib/api/types";
import {
  FAVORITES_MAX,
  addFavorite,
  readFavorites,
  removeFavorite,
  serverFavorites,
  subscribeFavorites,
  type FavoriteChange,
} from "./store";

/** Member list size (2026-11-21: members 10, guests 5). The server enforces it too. */
export const MEMBER_FAVORITES_MAX = 10;

export type FavoritesStatus = "loading" | "ready" | "unavailable" | "failed";

export interface Favorites {
  /** loading: not known yet · unavailable: guest storage blocked · failed: member list
   *  could not be read (never replaced by the guest list, COM-005). */
  status: FavoritesStatus;
  source: "guest" | "member";
  ids: readonly number[];
  max: number;
  has: (teamId: number) => boolean;
  add: (teamId: number) => Promise<FavoriteChange>;
  remove: (teamId: number) => Promise<FavoriteChange>;
  retry: () => void;
}

/** The account list (`teams` in registration order); my page reads the names from it. */
export const memberFavoritesQuery = {
  queryKey: queryKeys.me.favorites(),
  queryFn: ({ signal }: { signal: AbortSignal }) =>
    memberRequest(async () => (await apiFetch<MemberFavorites>("/me/favorites", { signal })).data),
};

/**
 * Current favourite teams and actions (guide §2: main, team browse, team detail and my
 * page). The source follows the session (COM-005): guests use this browser's list (max 5),
 * members their account list (max 10). The two are never merged or copied, and logging out
 * shows the browser list again unchanged.
 */
export function useFavorites(): Favorites {
  const auth = useAuth();
  const guest = useSyncExternalStore(subscribeFavorites, readFavorites, serverFavorites);
  const queryClient = useQueryClient();
  const member = auth.status === "member";
  const list = useQuery({ ...memberFavoritesQuery, enabled: member });

  if (!member) {
    const ids = auth.status === "loading" ? [] : guest.ids;
    return {
      status: auth.status === "loading" ? "loading" : guest.status,
      source: "guest",
      ids,
      max: FAVORITES_MAX,
      has: (teamId) => ids.includes(teamId),
      add: async (teamId) => addFavorite(teamId),
      remove: async (teamId) => removeFavorite(teamId),
      retry: () => undefined,
    };
  }

  const ids = list.data?.teams.map((team) => team.id) ?? [];
  const change = async (request: () => Promise<MemberFavorites>, done: FavoriteChange): Promise<FavoriteChange> => {
    // A late answer from before a logout (even if the same member signed in again) never
    // lands in the list read since (`authEpoch`, Codex N1).
    const started = authEpoch();
    const stillSame = () => authEpoch() === started;
    try {
      const saved = await memberRequest(request);
      if (stillSame()) queryClient.setQueryData(queryKeys.me.favorites(), saved);
      return done;
    } catch (error) {
      // Refused or failed: the saved list is read again so the screen shows what is stored.
      if (stillSame()) void queryClient.invalidateQueries({ queryKey: queryKeys.me.favorites() });
      return isApiError(error) && error.code === "FAVORITE_LIMIT" ? "limit" : "failed";
    }
  };
  return {
    status: list.isPending ? "loading" : list.isError && !list.data ? "failed" : "ready",
    source: "member",
    ids,
    max: MEMBER_FAVORITES_MAX,
    has: (teamId) => ids.includes(teamId),
    add: (teamId) =>
      change(
        async () => (await apiFetch<MemberFavorites>("/me/favorites", { method: "POST", body: { teamId } })).data,
        ids.includes(teamId) ? "exists" : "added",
      ),
    remove: (teamId) =>
      change(
        async () => (await apiFetch<MemberFavorites>(`/me/favorites/${teamId}`, { method: "DELETE" })).data,
        "removed",
      ),
    retry: () => void list.refetch(),
  };
}
