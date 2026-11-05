"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Icon } from "@/components/ui/Icon";
import { cx } from "@/components/ui/cx";
import type { SeasonItem } from "@/lib/api/types";

/** "2026-27 · 현재 시즌", "2025-26 · 이전 시즌" (Figma 65:1616 / 65:1633). */
function optionLabel(season: SeasonItem, seasons: readonly SeasonItem[]): string {
  if (season.current) return `${season.label} · 현재 시즌`;
  const current = seasons.find((s) => s.current);
  return current && season.season === current.season - 1 ? `${season.label} · 이전 시즌` : season.label;
}

/**
 * Season dropdown (HIST-002, CMP-003; Figma trigger 93:3198 220×44, list 65:1616): past
 * results and standings (chat 06). `value` null = the URL named a season the service does
 * not offer: the trigger asks for a choice instead of showing another season.
 * A listbox popover: arrows/Home/End move, Enter/Space picks, Escape or an outside press
 * closes and focus returns to the trigger.
 */
export function SeasonSelect({
  seasons,
  value,
  onChange,
  className,
}: {
  seasons: readonly SeasonItem[];
  value: number | null;
  onChange: (season: number) => void;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const id = useId();
  const selected = seasons.find((s) => s.season === value) ?? null;

  useEffect(() => {
    if (!open) return;
    listRef.current?.focus();
    const close = (event: PointerEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const show = () => {
    setActive(Math.max(0, seasons.findIndex((s) => s.season === value)));
    setOpen(true);
  };
  const close = () => {
    setOpen(false);
    buttonRef.current?.focus();
  };
  const pick = (season: SeasonItem) => {
    close();
    if (season.season !== value) onChange(season.season);
  };

  const onListKey = (event: KeyboardEvent) => {
    const last = seasons.length - 1;
    const moves: Record<string, number> = {
      ArrowDown: Math.min(active + 1, last),
      ArrowUp: Math.max(active - 1, 0),
      Home: 0,
      End: last,
    };
    if (event.key in moves) {
      event.preventDefault();
      setActive(moves[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (seasons[active]) pick(seasons[active]);
    } else if (event.key === "Escape" || event.key === "Tab") {
      if (event.key === "Escape") event.preventDefault();
      close();
    }
  };

  return (
    <div ref={boxRef} className={cx("relative w-full sm:w-[220px]", className)}>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? `${id}-list` : undefined}
        aria-label={`시즌 선택: ${selected ? `${selected.label} 시즌` : "선택 필요"}`}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            show();
          }
        }}
        className="flex min-h-11 w-full items-center gap-2 rounded-control border border-line-strong bg-surface px-3 text-body text-fg hover:bg-subtle"
      >
        <span className={cx("min-w-0 flex-1 truncate text-center", !selected && "text-fg-muted")}>
          {selected ? `${selected.label} 시즌` : "시즌 선택"}
        </span>
        <Icon name="chevron-down" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-30 mt-1 w-[260px] max-w-[calc(100vw-2rem)] rounded-card border border-line bg-surface p-4 shadow-lg">
          <p id={`${id}-label`} className="mb-2 text-label text-fg-secondary">
            시즌 선택
          </p>
          <ul
            ref={listRef}
            id={`${id}-list`}
            role="listbox"
            tabIndex={-1}
            aria-labelledby={`${id}-label`}
            aria-activedescendant={`${id}-option-${active}`}
            onKeyDown={onListKey}
            className="flex flex-col gap-2 outline-none"
          >
            {seasons.map((season, index) => (
              <li
                key={season.season}
                id={`${id}-option-${index}`}
                role="option"
                aria-selected={season.season === value}
                onClick={() => pick(season)}
                onMouseEnter={() => setActive(index)}
                className={cx(
                  "flex min-h-11 cursor-pointer items-center justify-center rounded-control px-3 text-lead",
                  season.season === value ? "bg-selected font-medium text-action" : "text-fg",
                  index === active && season.season !== value && "bg-subtle",
                  index === active && "ring-2 ring-focus ring-inset",
                )}
              >
                {optionLabel(season, seasons)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
