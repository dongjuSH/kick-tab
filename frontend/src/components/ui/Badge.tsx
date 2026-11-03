import type { ReactNode } from "react";
import { cx } from "./cx";

/**
 * Figma 55:27 status badges. Colour is never the only signal: always pass a text label
 * such as "진행 중 63′" or "경기 중단" (guide §6.6).
 * Tone "accent" is the action-soft badge of the TOP 5 strip/panel ("AI 선정", rank); "error" is
 * a loss in the recent-form row of the match detail (Figma 63:1909 승·무·패).
 * Size "small" = 12px (status badges, Figma 159:924·187:591); "caption" = 11px (news, 49:457).
 */
export type BadgeTone = "accent" | "live" | "neutral" | "warning" | "error";
export type BadgeSize = "small" | "caption";

const TONES: Record<BadgeTone, string> = {
  accent: "bg-action-soft text-action",
  live: "bg-live-bg text-live",
  neutral: "bg-subtle text-fg-secondary",
  warning: "bg-warning-bg text-warning",
  error: "bg-error-bg text-error",
};

const SIZES: Record<BadgeSize, string> = {
  small: "text-small",
  caption: "text-caption",
};

export function Badge({
  tone = "neutral",
  size = "small",
  className,
  children,
}: {
  tone?: BadgeTone;
  size?: BadgeSize;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-badge px-2 py-1 font-medium",
        SIZES[size],
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
