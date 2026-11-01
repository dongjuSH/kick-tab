/** Main menu (COM-003). Page menus live in the header only, never in the footer. */
export const MAIN_NAV = [
  { href: "/", label: "경기 일정" },
  { href: "/results", label: "지난 경기" },
  { href: "/standings", label: "리그 순위" },
  { href: "/teams", label: "팀 탐색" },
] as const;

/** "/" matches only itself; other items also match their sub-paths (/teams/42). */
export function isNavActive(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
