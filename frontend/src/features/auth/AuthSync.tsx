"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { queryKeys } from "@/lib/api/query-keys";
import { checkSession, readAuth, subscribeAuth } from "./session";

/**
 * Checks the session once per page load (AUTH-003) and keeps cached data in line with it:
 * when the signed-in member changes (login, logout, expired session, withdrawal) every
 * member-only query is dropped (COM-005, AUTH-004 rule 4) and review lists are fetched again
 * for their "mine" / reaction marks.
 */
export function AuthSync() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const viewer = () => {
      const current = readAuth();
      return current.status === "member" ? current.member.id : current.status;
    };
    let last = viewer();
    const unsubscribe = subscribeAuth(() => {
      const next = viewer();
      if (next === last) return;
      const wasKnown = last !== "loading";
      last = next;
      if (next !== "loading" && wasKnown) {
        queryClient.removeQueries({ queryKey: queryKeys.me.all });
        void queryClient.invalidateQueries({ queryKey: ["matches", "reviews"] });
      }
    });
    void checkSession();
    return unsubscribe;
  }, [queryClient]);

  return null;
}
