"use client";

import { Fragment, useEffect, useRef } from "react";
import { ChipLabel, chipClass } from "@/components/ui/chip";

export interface ChipItem<T extends string> {
  value: T;
  label: string;
  /** Draw a divider before this chip (leagues | UEFA, Figma 53:1353). */
  groupStart?: boolean;
}

/**
 * One row of choice chips (competitions or UEFA stages, LEAG-002 rule 6). On a narrow screen
 * the row scrolls sideways on its own line, and the selected chip is brought into view when
 * the page opens or the choice changes (also by Back), without scrolling the page itself.
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

  useEffect(() => {
    const box = row.current;
    const chip = box?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (!box || !chip) return;
    // The row is the chip's offset parent (`relative`), so offsets are in its scroll space.
    const left = chip.offsetLeft;
    const right = left + chip.offsetWidth;
    if (left < box.scrollLeft) box.scrollLeft = left - 8;
    else if (right > box.scrollLeft + box.clientWidth) box.scrollLeft = right - box.clientWidth + 8;
  }, [value]);

  return (
    <div
      ref={row}
      role="group"
      aria-label={label}
      className="relative -mx-1 overflow-x-auto px-1 py-0.5 [scrollbar-width:none]"
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
  );
}
