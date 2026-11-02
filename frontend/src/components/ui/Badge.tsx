import type { ReactNode } from "react";
import { cx } from "./cx";

/**
 * Figma 55:27 status badges. Colour is never the only signal: always pass a text label
 * such as "진행 중 63분" or "경기 중단" (guide §6.6).
 * 12px text (TOP 5 badges, Figma 159:924). Tone "accent" is the action-soft badge of the
 * TOP 5 strip/panel ("AI 선정", rank).
 */
export type BadgeTone = "accent" | "live" | "neutral" | "warning";

const TONES: Record<BadgeTone, string> = {
  accent: "bg-action-soft text-action",
  live: "bg-live-bg text-live",
  neutral: "bg-subtle text-fg-secondary",
  warning: "bg-warning-bg text-warning",
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
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-badge px-2 py-1 text-small font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
