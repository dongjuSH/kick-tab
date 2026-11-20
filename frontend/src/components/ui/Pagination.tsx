"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Icon } from "./Icon";
import { cx } from "./cx";

/** Most page numbers shown at once (PC). */
export const MAX_NUMBERS = 9;
/** Fewest: the first page, the current one and the last. */
const MIN_NUMBERS = 3;
/** Row parts (Figma 530:21586 · 530:21659): 44px arrows and numbers, 14px "…", 4px gaps. */
const ITEM = 44;
const GAP = 4;
const ELLIPSIS = 14;

/**
 * How many page numbers fit a row `width` px wide: both arrows, two "…" and the gaps
 * between every part, so the row never scrolls sideways (320px phone: 3, 375px: 4).
 */
export function numbersFor(width: number): number {
  const fixed = 2 * ITEM + 2 * ELLIPSIS + 3 * GAP;
  const fit = Math.floor((width - fixed) / (ITEM + GAP));
  return Math.min(MAX_NUMBERS, Math.max(MIN_NUMBERS, fit));
}

export type PageItem = number | "gap";

/**
 * `1 2 3 … 420` style items: every page when they fit, otherwise the first and last page
 * always, a run around `page` filling the remaining `numbers - 2` places (pushed inward at
 * either end), and "gap" where pages are left out.
 */
export function pageItems(page: number, pages: number, numbers: number): PageItem[] {
  if (pages <= numbers) return Array.from({ length: pages }, (_, i) => i + 1);
  const middle = numbers - 2;
  const start = Math.max(2, Math.min(page - Math.floor((middle - 1) / 2), pages - middle));
  const end = start + middle - 1;
  return [
    1,
    ...(start > 2 ? (["gap"] as const) : []),
    ...Array.from({ length: middle }, (_, i) => start + i),
    ...(end < pages - 1 ? (["gap"] as const) : []),
    pages,
  ];
}

/**
 * Page navigation (HIST-001 · Figma `지난 경기 페이지네이션 · 공통` 530:21586 PC / 530:21659
 * mobile), shared by past results and team browse (07): `< 1 2 3 … 420 >` in one centred row.
 * The first and last page stay fixed; as many numbers as the row's width allows (up to 9)
 * sit around the current page, which is filled and has `aria-current="page"`. The arrows are
 * icon buttons, dimmed and disabled at either end. Nothing is drawn for a single page.
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
  const [width, setWidth] = useState<number | null>(null);

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
  const items = pageItems(page, pages, width === null ? MIN_NUMBERS : numbersFor(width));

  const arrow = (direction: "left" | "right", name: string, target: number, disabled: boolean) => (
    <button
      type="button"
      aria-label={name}
      disabled={disabled}
      onClick={() => onChange(target)}
      className="inline-flex size-11 shrink-0 items-center justify-center rounded-control hover:bg-subtle disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent"
    >
      <Icon name={`chevron-${direction}`} />
    </button>
  );

  // The arrows have no frame, so the row may reach into the card's side padding (-mx-3):
  // that is what lets 320px phones keep `< 1 … 210 … 420 >` on one line.
  return (
    <nav ref={navRef} aria-label={label} className="-mx-3 flex items-center justify-center gap-1">
      {arrow("left", "이전 페이지", page - 1, page <= 1)}
      {items.map((item, index) =>
        item === "gap" ? (
          <span
            key={`gap-${index}`}
            aria-hidden
            className="w-3.5 shrink-0 text-center text-body font-medium text-fg-secondary"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            aria-label={`${item}페이지`}
            aria-current={item === page ? "page" : undefined}
            onClick={() => item !== page && onChange(item)}
            className={cx(
              "inline-flex h-11 min-w-11 shrink-0 items-center justify-center rounded-control border px-2 text-body font-medium",
              item === page
                ? "border-action bg-action text-fg-inverse"
                : "border-line-strong bg-surface text-fg hover:bg-subtle",
            )}
          >
            {item}
          </button>
        ),
      )}
      {arrow("right", "다음 페이지", page + 1, page >= pages)}
    </nav>
  );
}
