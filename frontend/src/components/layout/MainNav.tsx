"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cx } from "@/components/ui/cx";
import { MAIN_NAV, isNavActive } from "./nav";

/** Desktop menu: 32px from the logo, 32px between items, 2px underline on the current page. */
export function MainNav() {
  return <NavList pathname={usePathname()} />;
}

/**
 * The same menu before the current path is known: on a page with a runtime param
 * (`/matches/[id]`) the prerendered shell shows it without a current item (guide §3.1).
 */
export function MainNavFallback() {
  return <NavList pathname={null} />;
}

function NavList({ pathname }: { pathname: string | null }) {
  return (
    <nav aria-label="주요 메뉴" className="pl-8">
      <ul className="flex items-center gap-8">
        {MAIN_NAV.map((item) => {
          const active = pathname !== null && isNavActive(item.href, pathname);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "flex w-24 flex-col items-center gap-1.5 text-center text-body",
                  active ? "font-bold text-action" : "font-medium text-fg-secondary hover:text-fg",
                )}
              >
                {item.label}
                {active && <span aria-hidden className="h-0.5 w-full bg-action" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
