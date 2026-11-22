/**
 * Login return (AUTH-005, guide §6.2): `/login?returnTo=<internal path>&intent=review:<id>`.
 * Only same-site paths are followed; anything else (other sites, `//host`, `/\host`,
 * schemes, the auth pages themselves) goes to the main page. The only intent is a review
 * (news saving was dropped 2026-11-21); it never submits anything by itself.
 */

const BASE = "http://kicktab.invalid";
const AUTH_PAGES = ["/login", "/signup", "/password-reset"];

export function safeReturnTo(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  // Control characters (tabs, line breaks) are dropped by URL parsing and could hide a host.
  if (/[\u0000-\u001f\u007f\\]/.test(value)) return "/";
  let url: URL;
  try {
    url = new URL(value, BASE);
  } catch {
    return "/";
  }
  if (url.origin !== BASE) return "/";
  if (AUTH_PAGES.some((page) => url.pathname === page || url.pathname.startsWith(`${page}/`))) return "/";
  return `${url.pathname}${url.search}${url.hash}`;
}

/** `review:123` → 123; anything else → null. */
export function reviewIntent(value: string | null | undefined): number | null {
  const match = /^review:([1-9][0-9]{0,9})$/.exec(value ?? "");
  return match ? Number(match[1]) : null;
}

export function loginHref(returnTo: string, intent?: string): string {
  const search = new URLSearchParams({ returnTo: safeReturnTo(returnTo) });
  if (intent) search.set("intent", intent);
  return `/login?${search.toString()}`;
}

/** Member-only pages: logging out there goes to the main page (AUTH-004 rule 2). */
export function isMemberOnlyPath(pathname: string): boolean {
  return pathname === "/mypage" || pathname.startsWith("/mypage/");
}

const INTENT_KEY = "kt-review-intent";

/** Remembers, for the page reached after login, which match's review area to open. */
export function rememberReviewIntent(fixtureId: number) {
  try {
    sessionStorage.setItem(INTENT_KEY, String(fixtureId));
  } catch {
    // Without storage the page still opens; only the focus on the review area is lost.
  }
}

/** Whether the login was started from this match's review area (read only). */
export function hasReviewIntent(fixtureId: number): boolean {
  try {
    return sessionStorage.getItem(INTENT_KEY) === String(fixtureId);
  } catch {
    return false;
  }
}

/** Forgets the intent once the review area has been opened for it. */
export function clearReviewIntent() {
  try {
    sessionStorage.removeItem(INTENT_KEY);
  } catch {
    // Nothing kept.
  }
}
