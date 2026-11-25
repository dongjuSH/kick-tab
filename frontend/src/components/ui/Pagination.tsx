"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Icon, type IconName } from "./Icon";
import { cx } from "./cx";

/** Most page numbers shown at once (PC). */
export const MAX_NUMBERS = 7;
/** A 44px button plus the 4px gap after it (Figma 556:7312: arrows and numbers are 44px). */
const SLOT = 48;
const GAP = 4;

/**
 * How many page numbers fit a row `width` px wide next to `arrows` arrow buttons (4 with
 * « », 2 without): the width left after the arrows and gaps ÷ 48px, kept to 1–7.
 * The 375px card row (333px) fits 3 beside four arrows, the 320px one (278px) 1.
 */
export function numbersFor(width: number, arrows: 2 | 4 = 4): number {
  const fit = Math.floor((width + GAP) / SLOT) - arrows;
  return Math.min(MAX_NUMBERS, Math.max(1, fit));
}

/**
 * The consecutive page numbers shown: `numbers` of them with the current page in the middle
 * (a little left of it for an even count), pushed inward at either end so the count stays
 * the same. With fewer pages, every page.
 */
export function pageWindow(page: number, pages: number, numbers: number): number[] {
  const count = Math.min(numbers, pages);
  const start = Math.max(1, Math.min(page - Math.floor((count - 1) / 2), pages - count + 1));
  return Array.from({ length: count }, (_, i) => start + i);
}

/**
 * Page navigation (HIST-001 · Figma 'KickTab/Results Pagination' 556:7312, past results
 * 530:21586 / 530:21659, team browse 52:886 / 52:1197): `« ‹ 13 14 15 [16] 17 18 19 › »`.
 * ‹ › move one page, « » go to the first and last page and appear only when the numbers
 * cannot all be shown at once (team browse with 2 pages: `‹ 1 2 ›`). How many numbers fit
 * follows the row's measured width (PC 7, 375px 3, 320px 1). Arrows at an end are disabled;
 * the current page is filled and has `aria-current="page"`. Nothing is drawn for one page.
 */
export function Pagination({
  page,
  pages,
  onChange,
  label = "페이지",
}: {
  page: number;
  pages: number;
  onChange: (page: number) => void;
  label?: string;
}) {
  const navRef = useRef<HTMLElement>(null);
  const [width, setWidth] = useState(0);

  // The row follows the space it actually gets (card padding, zoom, phone width).
  useLayoutEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    const measure = () => setWidth(nav.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(nav);
    return () => observer.disconnect();
  }, [pages]);

  if (pages <= 1) return null;
  const ends = pages > numbersFor(width, 2);
  const numbers = pageWindow(page, pages, numbersFor(width, ends ? 4 : 2));
  const atStart = page <= 1;
  const atEnd = page >= pages;

  const arrow = (icon: IconName, name: string, target: number, disabled: boolean) => (
    <button
      type="button"
      aria-label={name}
      disabled={disabled}
      onClick={() => onChange(target)}
      className="inline-flex size-11 shrink-0 items-center justify-center rounded-control hover:bg-subtle disabled:cursor-not-allowed disabled:opacity-[0.38] disabled:hover:bg-transparent"
    >
      <Icon name={icon} />
    </button>
  );

  // The arrows have no frame, so the row may reach into the card's side padding (-mx-3):
  // that is what gives a 375px phone three numbers beside four arrows.
  return (
    <nav ref={navRef} aria-label={label} className="-mx-3 flex items-center justify-center gap-1 lg:gap-2">
      {ends && arrow("chevrons-left", "첫 페이지", 1, atStart)}
      {arrow("chevron-left", "이전 페이지", page - 1, atStart)}
      {numbers.map((n) => (
        <button
          key={n}
          type="button"
          aria-label={`${n}페이지`}
          aria-current={n === page ? "page" : undefined}
          onClick={() => n !== page && onChange(n)}
          className={cx(
            "inline-flex h-11 min-w-11 shrink-0 items-center justify-center rounded-control border px-2 text-body font-medium",
            n === page
              ? "border-action bg-action text-fg-inverse"
              : "border-line-strong bg-surface text-fg-secondary hover:bg-subtle",
          )}
        >
          {n}
        </button>
      ))}
      {arrow("chevron-right", "다음 페이지", page + 1, atEnd)}
      {ends && arrow("chevrons-right", "마지막 페이지", pages, atEnd)}
    </nav>
  );
}
