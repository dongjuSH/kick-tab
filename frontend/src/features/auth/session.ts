"use client";

import { useSyncExternalStore } from "react";
import { apiFetch, setUnauthorizedHandler } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { Member } from "@/lib/api/types";

/**
 * Member session (AUTH-002·003·004, guide §6.2). Tokens live in httpOnly cookies, so the
 * browser only knows who is signed in by asking GET /auth/me. Until that answer the state
 * is "loading": member-only data is never guessed from the guest state (COM-005).
 */
export type AuthState =
  | { status: "loading" }
  | { status: "guest" }
  | { status: "member"; member: Member };

const LOADING: AuthState = { status: "loading" };
const GUEST: AuthState = { status: "guest" };
let state: AuthState = LOADING;
const listeners = new Set<() => void>();

function set(next: AuthState) {
  const same =
    next.status === state.status &&
    (next.status !== "member" || (state.status === "member" && state.member.id === next.member.id));
  if (same && next.status !== "member") return;
  state = next;
  listeners.forEach((listener) => listener());
}

export function subscribeAuth(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function readAuth(): AuthState {
  return state;
}

export function useAuth(): AuthState {
  return useSyncExternalStore(subscribeAuth, readAuth, () => LOADING);
}

/**
 * Asks the server who is signed in (an expired access token is refreshed once first; a
 * failed refresh ends as a guest).
 * "unknown" = the server could not answer (network, 5xx): on the first check the page goes
 * on as a guest without member data; afterwards the current state is kept.
 */
export async function checkSession(): Promise<"member" | "guest" | "unknown"> {
  try {
    // 200 with null = not signed in (no failed request in the console for guests).
    const { data } = await apiFetch<Member | null>("/auth/me");
    if (!data) {
      set(GUEST);
      return "guest";
    }
    set({ status: "member", member: data });
    return "member";
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      set(GUEST);
      return "guest";
    }
    if (state.status === "loading") set(GUEST);
    return "unknown";
  }
}

let refreshing: Promise<boolean> | null = null;
let loggingOut: Promise<boolean> | null = null;
let logoutRequestPending = false;

/**
 * One shared POST /auth/refresh for every request that got 401 AUTH_EXPIRED at the same
 * time. Failure (the server also clears the cookies) turns this browser into a guest.
 */
export function refreshSession(): Promise<boolean> {
  // Finish an already-sent refresh before logout clears its cookies. Do not start another
  // one while that logout is pending: a late reply could restore the member and cookies.
  if (logoutRequestPending && !refreshing) return Promise.resolve(false);
  refreshing ??= apiFetch<Member>("/auth/refresh", { method: "POST" })
    .then(({ data }) => {
      set({ status: "member", member: data });
      return true;
    })
    .catch(() => {
      set(GUEST);
      return false;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/**
 * AUTH-004: end the session on the server, then confirm with /auth/me that it really
 * ended. Resolves true when this browser is a guest again.
 */
export function logout(): Promise<boolean> {
  loggingOut ??= performLogout().finally(() => { loggingOut = null; });
  return loggingOut;
}

async function performLogout(): Promise<boolean> {
  logoutRequestPending = true;
  try {
    await refreshing;
    await apiFetch<null>("/auth/logout", { method: "POST" });
  } catch {
    // Checked below: a failed request must not be mistaken for a logout.
  } finally {
    // A failed logout may need to refresh while checking whether the session still exists.
    logoutRequestPending = false;
  }
  const done = (await checkSession()) === "guest";
  if (done) dropReviewDrafts();
  return done;
}

/** sessionStorage prefix of unsent review texts (`ReviewComposer`, per member and match). */
export const REVIEW_DRAFT_PREFIX = "kt-review-draft:";

/** A deliberate logout leaves no private text behind on this tab (a lost session keeps it). */
function dropReviewDrafts() {
  try {
    for (const key of Object.keys(sessionStorage)) {
      if (key.startsWith(REVIEW_DRAFT_PREFIX)) sessionStorage.removeItem(key);
    }
  } catch {
    // No storage: nothing was kept.
  }
}

if (typeof window !== "undefined") {
  setUnauthorizedHandler(() => refreshSession());
}
