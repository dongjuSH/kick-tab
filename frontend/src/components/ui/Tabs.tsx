"use client";

import { useRef, type KeyboardEvent } from "react";
import { cx } from "./cx";

export interface TabItem<T extends string> {
  value: T;
  label: string;
}

/**
 * Figma "Tab navigation" (52:240, 52:302): 44px targets, 14px labels, the selected tab bold
 * blue with a 2px underline, a 1px divider under the row; scrolls sideways when narrow.
 * ARIA tabs pattern: arrow keys / Home / End move and select, only the selected tab is in
 * the Tab order. Panels use `tabPanelId(idBase, value)` and `aria-labelledby`.
 */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  label,
  idBase,
  className,
}: {
  items: readonly TabItem<T>[];
  /** null = nothing selected (e.g. an unsupported value in the URL). */
  value: T | null;
  onChange: (value: T) => void;
  label: string;
  idBase: string;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  // No tab selected (e.g. the URL named an unsupported league): keep the first one reachable.
  const focusIndex = Math.max(0, items.findIndex((item) => item.value === value));

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = items.length - 1;
    const next =
      event.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : event.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : null;
    if (next === null) return;
    event.preventDefault();
    onChange(items[next].value);
    refs.current[next]?.focus();
  };

  return (
    <div className={cx("border-b border-line", className)}>
      <div role="tablist" aria-label={label} className="-mb-px flex gap-2 overflow-x-auto [scrollbar-width:none]">
        {items.map((item, index) => {
          const selected = item.value === value;
          return (
            <button
              key={item.value}
              ref={(node) => {
                refs.current[index] = node;
              }}
              type="button"
              role="tab"
              id={tabId(idBase, item.value)}
              aria-selected={selected}
              aria-controls={tabPanelId(idBase, item.value)}
              tabIndex={index === focusIndex ? 0 : -1}
              onClick={() => onChange(item.value)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={cx(
                "flex h-11 shrink-0 items-center justify-center border-b-2 px-3 text-body whitespace-nowrap",
                selected
                  ? "border-action font-bold text-action"
                  : "border-transparent text-fg-secondary hover:text-fg",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function tabId(idBase: string, value: string) {
  return `${idBase}-tab-${value}`;
}

export function tabPanelId(idBase: string, value: string) {
  return `${idBase}-panel-${value}`;
}
