"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Dialog";
import { cx } from "@/components/ui/cx";
import { HeaderAuth } from "./HeaderAuth";
import { MAIN_NAV, isNavActive } from "./nav";

/** Mobile header menu button + sheet (Figma 62:1427): menu items split by 1px lines. */
export function MobileMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const close = () => setOpen(false);

  return (
    <>
      <IconButton
        icon="menu"
        label="메뉴 열기"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      />
      <BottomSheet open={open} onClose={close} title="메뉴" closeLabel="메뉴 닫기">
        <nav aria-label="주요 메뉴">
          <ul className="flex flex-col gap-4">
            {MAIN_NAV.map((item) => {
              const active = isNavActive(item.href, pathname);
              return (
                <li key={item.href} className="border-b border-line pb-4">
                  <Link
                    href={item.href}
                    onClick={close}
                    aria-current={active ? "page" : undefined}
                    className={cx(
                      "flex min-h-11 items-center justify-center rounded-control text-body hover:bg-subtle",
                      active ? "font-bold text-action" : "font-medium text-fg",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <HeaderAuth layout="menu" onNavigate={close} />
      </BottomSheet>
    </>
  );
}
