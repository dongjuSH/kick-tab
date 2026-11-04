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
                  "group flex h-11 w-24 items-center justify-center rounded-control text-body font-medium",
                  active ? "text-action" : "text-fg-secondary hover:text-fg",
                )}
              >
                <span className="relative">
                  {item.label}
                  <span aria-hidden className={cx(
                    "absolute inset-x-0 -bottom-1.5 h-0.5 origin-center rounded-full",
                    active
                      ? "bg-action"
                      : "scale-x-0 bg-line-strong transition-transform duration-200 ease-out group-hover:scale-x-100 group-focus-visible:scale-x-100 group-focus-visible:bg-action motion-reduce:transition-none",
                  )} />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
