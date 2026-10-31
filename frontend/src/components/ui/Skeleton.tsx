import { cx } from "./cx";

/** Loading placeholder block. Size it with className (e.g. "h-5 w-40"). */
export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden className={cx("block animate-pulse rounded-control bg-subtle", className)} />;
}
