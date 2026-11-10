import type { ReactNode } from "react";
import { cx } from "./cx";

/** Filter chip (favourite teams, news badges; Figma 49:171 selected / 49:173 default). */
export function chipClass(selected: boolean) {
  return cx(
    "inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-control border px-4 text-label",
    selected
      ? "border-action bg-selected font-medium text-action"
      : "border-line bg-surface text-fg-secondary hover:bg-subtle",
  );
}

/**
 * Chip text whose width never changes on selection: the selected weight (medium) is wider
 * than the regular one, so an invisible medium copy holds the width and the row of chips
 * does not shift when one is pressed.
 */
export function ChipLabel({ children }: { children: ReactNode }) {
  return (
    <span className="grid">
      <span className="col-start-1 row-start-1">{children}</span>
      <span aria-hidden className="invisible col-start-1 row-start-1 font-medium">
        {children}
      </span>
    </span>
  );
}
