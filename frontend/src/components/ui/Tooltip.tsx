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
 * Desktop shows on hover/focus; touch devices toggle on tap (REV-004 rules pattern).
 * Escape or a tap elsewhere closes it.
 */
export function Tooltip({ label, trigger, children, align = "start", className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLSpanElement>(null);

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
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        className="inline-flex size-11 items-center justify-center rounded-control hover:bg-subtle"
        onClick={() => setOpen((value) => !value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
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
