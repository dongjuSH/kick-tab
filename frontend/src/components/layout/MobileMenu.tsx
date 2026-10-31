"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, useState } from "react";
import { IconButton, buttonClass } from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Dialog";
import { cx } from "@/components/ui/cx";
import { HeaderAuth } from "./HeaderAuth";
import { MAIN_NAV, isNavActive } from "./nav";

/** Mobile header menu button + sheet (Figma 62:1427). */
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
                <Fragment key={item.href}>
                  <li>
                    <Link
                      href={item.href}
                      onClick={close}
                      aria-current={active ? "page" : undefined}
                      className={cx(buttonClass("ghost", true), active && "font-bold text-action")}
                    >
                      {item.label}
                    </Link>
                  </li>
                  <li aria-hidden className="h-px bg-line" />
                </Fragment>
              );
            })}
          </ul>
        </nav>
        <HeaderAuth layout="menu" onNavigate={close} />
      </BottomSheet>
    </>
  );
}
