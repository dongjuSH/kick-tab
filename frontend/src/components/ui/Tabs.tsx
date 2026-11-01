"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cx } from "./cx";

export interface TabItem<V extends string> {
  value: V;
  label: ReactNode;
}

interface TabsProps<V extends string> {
  items: readonly TabItem<V>[];
  value: V;
  onChange: (value: V) => void;
  ariaLabel: string;
  /** Prefix for tab/panel ids; pair with <TabPanel idBase value>. */
  idBase?: string;
  className?: string;
}

function tabId(idBase: string, value: string) {
  return `${idBase}-tab-${value}`;
}

function panelId(idBase: string, value: string) {
  return `${idBase}-panel-${value}`;
}

/** WAI-ARIA tabs with arrow/Home/End keys. Scrolls horizontally on narrow screens. */
export function Tabs<V extends string>({ items, value, onChange, ariaLabel, idBase, className }: TabsProps<V>) {
  const generated = useId();
  const base = idBase ?? generated;
  const list = useRef<HTMLDivElement>(null);

  const focusTab = (index: number) => {
    const next = items[(index + items.length) % items.length];
    onChange(next.value);
    list.current?.querySelector<HTMLButtonElement>(`#${CSS.escape(tabId(base, next.value))}`)?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = items.findIndex((item) => item.value === value);
    const keys: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: items.length - 1,
    };
    if (event.key in keys) {
      event.preventDefault();
      focusTab(keys[event.key]);
    }
  };

  return (
    <div
      ref={list}
      role="tablist"
      aria-label={ariaLabel}
      onKeyDown={onKeyDown}
      className={cx("flex gap-1 overflow-x-auto border-b border-line", className)}
    >
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            id={tabId(base, item.value)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={panelId(base, item.value)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.value)}
            className={cx(
              "-mb-px min-h-11 shrink-0 whitespace-nowrap border-b-2 px-4 text-body",
              selected
                ? "border-action font-bold text-action"
                : "border-transparent font-medium text-fg-secondary hover:text-fg",
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({
  idBase,
  value,
  active,
  children,
}: {
  idBase: string;
  value: string;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div role="tabpanel" id={panelId(idBase, value)} aria-labelledby={tabId(idBase, value)} hidden={!active}>
      {active && children}
    </div>
  );
}
