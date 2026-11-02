import Link from "next/link";
import { cx } from "@/components/ui/cx";
import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { formatShortDate } from "@/lib/format/kst";
import {
  competitionName,
  kickoffTime,
  penaltyText,
  scoreText,
  statusWord,
  teamName,
} from "@/lib/format/match";
import { MatchStatusBadge } from "./MatchStatusBadge";
import { TeamCrest } from "./TeamCrest";

/**
 * One match (Figma `KickTab/Schedule Match Row` 187:591 desktop / 225:1918 mobile, favourite
 * rows 49:320). A bordered card; the whole card opens the match detail by id
 * (`/matches/[id]`, chat 04). Dates come from the surrounding date heading, except in
 * `withDate` lists (favourite schedule) that mix about two weeks.
 *
 * layout:
 * - "schedule": competition·time | home · score · away | status in one row from 1024px;
 *   below it competition + time, then the teams, then the status.
 * - "stacked": the narrow layout at every width (favourite column).
 */
export function MatchCard({
  match,
  layout,
  withDate = false,
}: {
  match: MatchSummary;
  layout: "schedule" | "stacked";
  withDate?: boolean;
}) {
  const row = layout === "schedule";
  const penalty = penaltyText(match);
  const note = match.status === "abandoned" ? "중단 시점 스코어" : match.statusReason;
  const competition = competitionName(match.competition);
  const when = `${withDate ? `${formatShortDate(match.kickoffDateKst)} ` : ""}${kickoffTime(match)}`;

  const status = (
    <span className={cx("flex flex-col items-start gap-0.5", row && "lg:shrink-0")}>
      <MatchStatusBadge match={match} />
      {note && <span className="text-2xs text-warning">{note}</span>}
    </span>
  );

  return (
    <Link
      href={`/matches/${match.id}`}
      prefetch={false}
      aria-label={`${competition} ${formatShortDate(match.kickoffDateKst)} ${kickoffTime(match)}, ${teamName(match.home)} ${scoreText(match)} ${teamName(match.away)}, ${statusWord(match)}`}
      className={cx(
        "flex flex-col gap-2 rounded-control border border-line bg-surface p-3 hover:bg-subtle",
        row && "lg:flex-row lg:items-center lg:gap-3",
      )}
    >
      {/* Narrow: competition left, time right. Wide (schedule): a 164px column. */}
      <span className={cx("flex items-center gap-2 text-small", row && "lg:hidden")}>
        <span className="min-w-0 flex-1 truncate text-fg-secondary">{competition}</span>
        <span className="shrink-0 font-medium text-fg">{when}</span>
      </span>
      {row && (
        <span className="hidden w-[164px] shrink-0 flex-col gap-1 text-small lg:order-first lg:flex">
          <span className="truncate text-fg-secondary">{competition}</span>
          <span className="font-medium text-fg">{when}</span>
        </span>
      )}

      <span className={cx("flex items-center gap-2", row && "lg:min-w-0 lg:flex-1")}>
        <Team team={match.home} side="home" />
        <span className="flex w-12 shrink-0 flex-col items-center">
          <span className="whitespace-nowrap text-lead font-bold text-fg">{scoreText(match)}</span>
          {penalty && <span className="whitespace-nowrap text-2xs text-fg-muted">{penalty}</span>}
        </span>
        <Team team={match.away} side="away" />
      </span>

      {status}
    </Link>
  );
}

function Team({ team, side }: { team: TeamRef; side: "home" | "away" }) {
  const name = teamName(team);
  return (
    <span
      className={cx(
        "flex min-w-0 flex-1 items-center gap-2",
        side === "away" && "flex-row-reverse text-right",
      )}
    >
      <TeamCrest src={team.crestUrl} name={name} />
      <span className="min-w-0 break-keep text-body font-bold text-fg">{name}</span>
    </span>
  );
}
