"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { cx } from "./cx";
import { Icon } from "./Icon";

export interface DropdownOption<V extends string> {
  value: V;
  label: string;
  disabled?: boolean;
}

interface DropdownProps<V extends string> {
  options: readonly DropdownOption<V>[];
  value: V | null;
  onChange: (value: V) => void;
  /** Accessible name, e.g. "시즌 선택". */
  label: string;
  placeholder?: string;
  className?: string;
}

/** Single-select listbox button (season/league selects). 16px chevron, 8px gap (§6.6). */
export function Dropdown<V extends string>({
  options,
  value,
  onChange,
  label,
  placeholder = "선택",
  className,
}: DropdownProps<V>) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const listId = useId();
  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    // Move focus into the listbox so aria-activedescendant is announced.
    list.current?.focus();
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  const close = () => {
    setOpen(false);
    button.current?.focus();
  };

  const openList = () => {
    setActive(Math.max(0, options.findIndex((option) => option.value === value)));
    setOpen(true);
  };

  const choose = (index: number) => {
    const option = options[index];
    if (!option || option.disabled) return;
    onChange(option.value);
    close();
  };

  const move = (delta: number) => {
    if (!options.length) return;
    let next = active;
    for (let step = 0; step < options.length; step += 1) {
      next = (next + delta + options.length) % options.length;
      if (!options[next].disabled) break;
    }
    setActive(next);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (!open && ["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      openList();
      return;
    }
    if (!open) return;
    const handlers: Record<string, () => void> = {
      ArrowDown: () => move(1),
      ArrowUp: () => move(-1),
      Home: () => setActive(0),
      End: () => setActive(options.length - 1),
      Enter: () => choose(active),
      " ": () => choose(active),
      Escape: close,
      Tab: () => setOpen(false),
    };
    if (handlers[event.key]) {
      if (event.key !== "Tab") event.preventDefault();
      handlers[event.key]();
    }
  };

  return (
    <div ref={root} className={cx("relative inline-block", className)}>
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onKeyDown}
        className="inline-flex min-h-11 w-full items-center justify-between gap-2 rounded-control border border-line-strong bg-surface px-3 text-body hover:bg-subtle"
      >
        <span className={cx("truncate", !selected && "text-fg-muted")}>{selected?.label ?? placeholder}</span>
        <Icon name="chevron-down" className={cx("transition-transform", open && "rotate-180")} />
      </button>
      <ul
        ref={list}
        id={listId}
        role="listbox"
        tabIndex={-1}
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        onKeyDown={onKeyDown}
        aria-label={label}
        hidden={!open}
        className="absolute left-0 top-full z-50 mt-1 max-h-72 min-w-full overflow-y-auto rounded-control border border-line bg-surface py-1 shadow-lg"
      >
        {options.map((option, index) => (
          <li
            key={option.value}
            id={`${listId}-${index}`}
            role="option"
            aria-selected={option.value === value}
            aria-disabled={option.disabled || undefined}
            onPointerDown={(event) => event.preventDefault()}
            onClick={() => choose(index)}
            onMouseEnter={() => setActive(index)}
            className={cx(
              "flex min-h-11 cursor-pointer items-center whitespace-nowrap px-3 text-body",
              index === active && "bg-subtle",
              option.value === value && "font-bold text-action",
              option.disabled && "cursor-not-allowed text-fg-muted",
            )}
          >
            {option.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
