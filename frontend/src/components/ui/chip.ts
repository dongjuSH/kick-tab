import { cx } from "./cx";

/** Filter chip (favourite teams, news badges; Figma 49:171 selected / 49:173 default). */
export function chipClass(selected: boolean) {
  return cx(
    "inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-control border px-3 text-label",
    selected
      ? "border-action bg-selected font-medium text-action"
      : "border-line bg-surface text-fg-secondary hover:bg-subtle",
  );
}
