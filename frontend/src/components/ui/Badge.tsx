import type { ReactNode } from "react";
import { cx } from "./cx";

/**
 * Figma 55:27 status badges. Colour is never the only signal: always pass a text label
 * such as "진행 중 63분" or "경기 중단" (guide §6.6).
 */
export type BadgeTone = "info" | "live" | "neutral" | "warning" | "error";

const TONES: Record<BadgeTone, string> = {
  info: "bg-selected text-action",
  live: "bg-live-bg text-live",
  neutral: "bg-subtle text-fg-secondary",
  warning: "bg-warning-bg text-warning",
  error: "bg-error-bg text-error",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-badge px-2 py-1 text-caption font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
