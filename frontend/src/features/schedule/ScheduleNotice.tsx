import type { ReactNode } from "react";
import { cx } from "@/components/ui/cx";
import type { CompetitionItem } from "@/lib/api/types";
import { competitionName } from "@/lib/format/match";

/** Names of the failed competitions (`meta.failedCompetitionIds`) within the selection. */
export function failedNames(
  failedIds: readonly number[],
  competitions: readonly CompetitionItem[] | undefined,
  selected: readonly number[] = [],
): string[] {
  return failedIds
    .filter((id) => selected.length === 0 || selected.includes(id))
    .map((id) => {
      const competition = competitions?.find((c) => c.id === id);
      return competition ? competitionName(competition) : `대회 ${id}`;
    });
}

const TONES = {
  neutral: { box: "bg-canvas", title: "text-fg" },
  warning: { box: "bg-warning-bg", title: "text-fg" },
  error: { box: "bg-error-bg", title: "text-error" },
} as const;

/**
 * Schedule state box (Figma `KickTab/Schedule Feedback` 225:2374): empty results, loading,
 * lookup failure and partial failure, each with its own wording so "no matches" is never
 * shown for a failed or incomplete lookup.
 */
export function ScheduleNotice({
  tone = "neutral",
  title,
  description,
  action,
  busy = false,
}: {
  tone?: keyof typeof TONES;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  busy?: boolean;
}) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      aria-busy={busy || undefined}
      className={cx("flex flex-col gap-2 rounded-control p-3", TONES[tone].box)}
    >
      <p className={cx("text-body font-bold", TONES[tone].title)}>{title}</p>
      {description && <p className="text-small text-fg-secondary">{description}</p>}
      {action}
    </div>
  );
}
