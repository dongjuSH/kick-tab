"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cx } from "./cx";

export interface TabItem<T extends string> {
  value: T;
  label: string;
  /** Shown dimmed; not clickable and skipped by the arrow keys (aria-disabled). */
  disabled?: boolean;
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
  trailing,
}: {
  items: readonly TabItem<T>[];
  /** null = nothing selected (e.g. an unsupported value in the URL). */
  value: T | null;
  onChange: (value: T) => void;
  label: string;
  idBase: string;
  className?: string;
  /** Small note at the right end of the tab row (e.g. "후반기는 1월부터"). */
  trailing?: ReactNode;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = items.flatMap((item, index) => (item.disabled ? [] : [index]));
  // No tab selected (e.g. the URL named an unsupported league): keep the first one reachable.
  const selectedIndex = items.findIndex((item) => item.value === value && !item.disabled);
  const focusIndex = selectedIndex >= 0 ? selectedIndex : (enabled[0] ?? 0);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const at = enabled.indexOf(index);
    const last = enabled.length - 1;
    const step =
      event.key === "ArrowRight" ? (at === last ? 0 : at + 1)
      : event.key === "ArrowLeft" ? (at <= 0 ? last : at - 1)
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : null;
    if (step === null || last < 0) return;
    event.preventDefault();
    const next = enabled[step];
    onChange(items[next].value);
    refs.current[next]?.focus();
  };

  return (
    <div className={cx("flex items-center gap-2 border-b border-line", className)}>
      <div role="tablist" aria-label={label} className="-mb-px flex min-w-0 flex-1 gap-2 overflow-x-auto [scrollbar-width:none]">
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
              aria-selected={selected && !item.disabled}
              aria-controls={item.disabled ? undefined : tabPanelId(idBase, item.value)}
              aria-disabled={item.disabled || undefined}
              tabIndex={index === focusIndex && !item.disabled ? 0 : -1}
              onClick={() => !item.disabled && onChange(item.value)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={cx(
                "flex h-11 shrink-0 items-center justify-center border-b-2 px-3 text-body whitespace-nowrap",
                item.disabled
                  ? "cursor-not-allowed border-transparent text-fg-muted opacity-50"
                  : selected
                    ? "border-action font-bold text-action"
                    : "border-transparent text-fg-secondary hover:text-fg",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {trailing && <span className="shrink-0 text-caption whitespace-nowrap text-fg-muted">{trailing}</span>}
    </div>
  );
}

export function tabId(idBase: string, value: string) {
  return `${idBase}-tab-${value}`;
}

export function tabPanelId(idBase: string, value: string) {
  return `${idBase}-panel-${value}`;
}
