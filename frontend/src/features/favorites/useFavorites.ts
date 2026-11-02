"use client";

import { useSyncExternalStore } from "react";
import {
  FAVORITES_MAX,
  addFavorite,
  readFavorites,
  removeFavorite,
  serverFavorites,
  subscribeFavorites,
} from "./store";

/**
 * Current favourite teams and actions (guide §2: shared by main, team browse, team detail
 * and my page). Guests read localStorage; chat 02 switches the source for members.
 */
export function useFavorites() {
  const snapshot = useSyncExternalStore(subscribeFavorites, readFavorites, serverFavorites);
  return {
    status: snapshot.status,
    ids: snapshot.ids,
    max: FAVORITES_MAX,
    has: (teamId: number) => snapshot.ids.includes(teamId),
    add: addFavorite,
    remove: removeFavorite,
  };
}
