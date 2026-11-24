"use client";

import { Fragment, useEffect } from "react";
import { IconButton } from "@/components/ui/Button";
import { ChipLabel, chipClass } from "@/components/ui/chip";
import { cx } from "@/components/ui/cx";
import { useScrollRow } from "@/lib/hooks/useScrollRow";

export interface ChipItem<T extends string> {
  value: T;
  label: string;
  /** Draw a divider before this chip (leagues | UEFA, Figma 53:1353). */
  groupStart?: boolean;
}

/**
 * One row of choice chips (competitions or UEFA stages: LEAG-001·002, Figma 53:1353 /
 * 234:8881). A row wider than its box scrolls sideways: PC (lg) shows 24×44 ‹ › arrows, as the
 * favourite-team chips do, disabled at each end; phones have no arrows and swipe. No fade at
 * the edges (2026-11-24).
 * The selected chip is brought into view when the page opens or the choice changes (also by
 * Back), without scrolling the page itself.
 */
export function ChipRow<T extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: readonly ChipItem<T>[];
  value: T | null;
  onChange: (value: T) => void;
  label: string;
}) {
  const { ref: row, edges, overflow, update, page, reveal } = useScrollRow<HTMLDivElement>();

  useEffect(() => {
    reveal(row.current?.querySelector<HTMLElement>('[aria-pressed="true"]'), 8);
  }, [value, row, reveal]);

  return (
    <div className="flex min-w-0 items-center gap-1">
      {overflow && (
        // PC only: the span hides it on phones (IconButton sets its own display).
        <span className="hidden shrink-0 lg:flex">
          <IconButton
            icon="chevron-left"
            label={`${label} 이전 항목 보기`}
            className="w-6 disabled:opacity-40"
            disabled={edges.start}
            onClick={() => page(-1, 96)}
          />
        </span>
      )}
      <div
        ref={row}
        role="group"
        aria-label={label}
        onScroll={update}
        // The row (with ‹ ›) is exactly as wide as the content below it (2026-11-24); the
        // chips' focus outline is drawn inside them so the row's edge never clips it.
        className="relative min-w-0 flex-1 overflow-x-auto py-0.5 [scrollbar-width:none]"
      >
        <div className="flex w-max items-center gap-2">
          {items.map((item) => (
            <Fragment key={item.value}>
              {item.groupStart && <span aria-hidden className="mx-1 h-6 w-px shrink-0 bg-line" />}
              <button
                type="button"
                aria-pressed={item.value === value}
                className={cx(chipClass(item.value === value), "focus-visible:-outline-offset-3")}
                onClick={() => onChange(item.value)}
              >
                <ChipLabel>{item.label}</ChipLabel>
              </button>
            </Fragment>
          ))}
        </div>
      </div>
      {overflow && (
        // PC only: the span hides it on phones (IconButton sets its own display).
        <span className="hidden shrink-0 lg:flex">
          <IconButton
            icon="chevron-right"
            label={`${label} 다음 항목 보기`}
            className="w-6 disabled:opacity-40"
            disabled={edges.end}
            onClick={() => page(1, 96)}
          />
        </span>
      )}
    </div>
  );
}
