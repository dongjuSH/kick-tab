"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cx } from "./cx";

interface TooltipProps {
  /** Accessible name of the trigger button, e.g. "후기 작성 주의사항". */
  label: string;
  /** Trigger content (usually an icon). */
  trigger: ReactNode;
  children: ReactNode;
  align?: "start" | "end";
  className?: string;
}

/**
 * Mouse: shows on hover and stays open on click. Touch/pen: each tap toggles.
 * Keyboard: shows on focus; Enter/Space toggles. Escape or a tap elsewhere closes it.
 *
 * Focus from a pointer press is ignored so "focus opens, then click toggles" can't close
 * it on the first click or tap (cross-review #9). The press is forgotten on click,
 * pointercancel, release outside the button, or blur, so it never blocks keyboard focus.
 */
export function Tooltip({ label, trigger, children, align = "start", className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLSpanElement>(null);
  // Pointer type of the press in progress; null for keyboard-originated focus/clicks.
  const pressedBy = useRef<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <span
      ref={root}
      className={cx("relative inline-flex", className)}
      onPointerEnter={(event) => event.pointerType === "mouse" && setOpen(true)}
      onPointerLeave={(event) => event.pointerType === "mouse" && setOpen(false)}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        className="inline-flex size-11 items-center justify-center rounded-control hover:bg-subtle"
        onPointerDown={(event) => {
          pressedBy.current = event.pointerType;
          // A press released outside the button produces no click: forget it then, so a
          // later keyboard focus still opens the tooltip (re-review B). A release on the
          // button keeps it for the click that follows.
          const button = event.currentTarget;
          const onRelease = (up: PointerEvent) => {
            if (!button.contains(up.target as Node)) pressedBy.current = null;
          };
          window.addEventListener("pointerup", onRelease, { capture: true, once: true });
        }}
        onPointerCancel={() => {
          pressedBy.current = null;
        }}
        onClick={() => {
          const by = pressedBy.current;
          pressedBy.current = null;
          setOpen((value) => (by === "mouse" ? true : !value));
        }}
        onFocus={() => {
          if (pressedBy.current === null) setOpen(true);
        }}
        onBlur={() => {
          pressedBy.current = null;
          setOpen(false);
        }}
      >
        {trigger}
      </button>
      <span
        id={id}
        role="tooltip"
        hidden={!open}
        className={cx(
          "absolute top-full z-50 mt-1 w-72 max-w-[calc(100vw-32px)] rounded-control border border-line",
          "bg-surface p-3 text-small text-fg-secondary shadow-lg",
          align === "start" ? "left-0" : "right-0",
        )}
      >
        {children}
      </span>
    </span>
  );
}
