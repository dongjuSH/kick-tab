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

/**
 * Session generation: goes up whenever the viewer changes (sign-in, sign-out, another member)
 * and on `signedOut()` — but not when the first check of the page load settles: nothing was
 * signed in before it, so a refresh already on its way still counts (Codex N8). An answer to a request sent in an earlier generation is never applied
 * — a late refresh or session check must not bring back an ended session, and a late member
 * request must not land after a logout and a new login, even as the same member (Codex N1·N6).
 */
let epoch = 0;

export function authEpoch(): number {
  return epoch;
}

function set(next: AuthState) {
  const same =
    next.status === state.status &&
    (next.status !== "member" || (state.status === "member" && state.member.id === next.member.id));
  if (same && next.status !== "member") return;
  if (!same && state.status !== "loading") epoch += 1;
  state = next;
  listeners.forEach((listener) => listener());
}

/** What the current state says, for a check whose own answer came too late to apply. */
function settled(): "member" | "guest" | "unknown" {
  return state.status === "loading" ? "unknown" : state.status;
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
  const started = epoch;
  try {
    // 200 with null = not signed in (no failed request in the console for guests).
    const { data } = await apiFetch<Member | null>("/auth/me");
    if (epoch !== started) return settled();
    if (!data) {
      set(GUEST);
      return "guest";
    }
    set({ status: "member", member: data });
    return "member";
  } catch (error) {
    if (epoch !== started) return settled();
    if (isApiError(error) && error.status === 401) {
      set(GUEST);
      return "guest";
    }
    if (state.status === "loading") set(GUEST);
    return "unknown";
  }
}

/**
 * The server has already ended this session (withdrawal, 401 AUTH_REQUIRED): this browser is
 * a guest now, without asking /auth/me again (a failed check must not keep the old member).
 * `forget` also drops the unsent review texts (withdrawal; a lost session keeps them).
 */
export function signedOut({ forget }: { forget: boolean }): void {
  failedRefresh = null;
  epoch += 1;
  set(GUEST);
  if (forget) dropReviewDrafts();
}

/**
 * A member-only request (my page, account favourites). 401 means the session is gone (no
 * cookie, or the refresh failed), not that the area failed: this browser becomes a guest and
 * the page shows its login notice instead of personal data (MY-001, Codex N3·N5). A 401 from
 * an earlier generation becomes AbortError, so callers also skip navigation and notices.
 */
export async function memberRequest<T>(send: () => Promise<T>): Promise<T> {
  const started = epoch;
  try {
    return await send();
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      // A failed automatic refresh has already made this a guest. Its original mutation
      // still needs the login/return flow; an explicit logout or a new login does not.
      const ownFailedRefresh = error.code === "AUTH_EXPIRED" && state.status === "guest" &&
        failedRefresh?.started === started && failedRefresh.ended === epoch;
      if (logoutRequestPending || (epoch !== started && !ownFailedRefresh)) {
        if (logoutRequestPending && epoch === started) signedOut({ forget: false });
        throw new DOMException("The request belongs to an ended session.", "AbortError");
      }
      if (epoch === started) signedOut({ forget: false });
    }
    throw error;
  }
}

let refreshing: Promise<boolean> | null = null;
let failedRefresh: { started: number; ended: number } | null = null;
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
  const started = epoch;
  refreshing ??= apiFetch<Member>("/auth/refresh", { method: "POST" })
    .then(({ data }) => {
      // Signed out (withdrawal, lost session) while this was on its way: stays ended.
      if (epoch !== started) return false;
      set({ status: "member", member: data });
      return true;
    })
    .catch(() => {
      if (epoch === started) {
        set(GUEST);
        failedRefresh = { started, ended: epoch };
      }
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
  if (done) signedOut({ forget: true });
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
