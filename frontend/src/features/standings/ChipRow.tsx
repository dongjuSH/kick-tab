"use client";

import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { ChipLabel, chipClass } from "@/components/ui/chip";
import { cx } from "@/components/ui/cx";

export interface ChipItem<T extends string> {
  value: T;
  label: string;
  /** Draw a divider before this chip (leagues | UEFA, Figma 53:1353). */
  groupStart?: boolean;
}

/**
 * One row of choice chips (competitions or UEFA stages: LEAG-001·002, Figma 53:1353 /
 * 234:8881). A row wider than its box scrolls sideways: PC (lg) shows ‹ › arrows that are
 * disabled at each end; phones have no arrows and swipe, with the row fading out at an edge
 * that has more chips behind it. The selected chip is brought into view when the page opens
 * or the choice changes (also by Back), without scrolling the page itself.
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
  const row = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ start: true, end: true });

  const update = useCallback(() => {
    const box = row.current;
    if (!box) return;
    setEdges({ start: box.scrollLeft <= 1, end: box.scrollLeft + box.clientWidth >= box.scrollWidth - 1 });
  }, []);

  useLayoutEffect(() => {
    const box = row.current;
    if (!box) return;
    update();
    const observer = new ResizeObserver(update);
    observer.observe(box);
    return () => observer.disconnect();
  }, [update]);

  useEffect(() => {
    const box = row.current;
    const chip = box?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (!box || !chip) return;
    // The row is the chip's offset parent (`relative`), so offsets are in its scroll space.
    const left = chip.offsetLeft;
    const right = left + chip.offsetWidth;
    if (left < box.scrollLeft) box.scrollLeft = left - 8;
    else if (right > box.scrollLeft + box.clientWidth) box.scrollLeft = right - box.clientWidth + 8;
    update();
  }, [value, update]);

  const page = (direction: 1 | -1) => {
    const box = row.current;
    if (!box) return;
    box.scrollBy({
      left: direction * Math.max(96, box.clientWidth - 96),
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
    });
  };
  const overflow = !(edges.start && edges.end);
  // A soft edge where more chips wait, so the cut chip reads as "more this way" (the only
  // hint on phones, which have no arrows).
  const fade =
    edges.start && edges.end
      ? undefined
      : `linear-gradient(to right, ${edges.start ? "#000" : "transparent"}, #000 24px, #000 calc(100% - 24px), ${edges.end ? "#000" : "transparent"})`;

  return (
    <div className="flex min-w-0 items-center gap-1">
      {overflow && (
        // PC only: the span hides it on phones (IconButton sets its own display).
        <span className="hidden shrink-0 lg:flex">
          <IconButton
            icon="chevron-left"
            label={`${label} 이전 항목 보기`}
            className="disabled:opacity-40"
            disabled={edges.start}
            onClick={() => page(-1)}
          />
        </span>
      )}
      <div
        ref={row}
        role="group"
        aria-label={label}
        onScroll={update}
        style={{ maskImage: fade, WebkitMaskImage: fade }}
        className={cx(
          "relative -mx-1 min-w-0 flex-1 overflow-x-auto px-1 py-0.5 [scrollbar-width:none]",
          overflow && "lg:mx-0",
        )}
      >
        <div className="flex w-max items-center gap-2">
          {items.map((item) => (
            <Fragment key={item.value}>
              {item.groupStart && <span aria-hidden className="mx-1 h-6 w-px shrink-0 bg-line" />}
              <button
                type="button"
                aria-pressed={item.value === value}
                className={chipClass(item.value === value)}
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
            className="disabled:opacity-40"
            disabled={edges.end}
            onClick={() => page(1)}
          />
        </span>
      )}
    </div>
  );
}
