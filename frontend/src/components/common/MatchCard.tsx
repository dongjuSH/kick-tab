"use client";

import Link from "next/link";
import { cx } from "@/components/ui/cx";
import { FavoriteStar } from "@/features/favorites/FavoriteStar";
import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { MISSING, formatShortDate } from "@/lib/format/kst";
import { useNow } from "@/lib/hooks/useNow";
import {
  awaitingStatus,
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
 * rows 49:320). A bordered card; the card body opens the match detail by id
 * (`/matches/[id]`, chat 04). Dates come from the surrounding date heading, except in
 * `withDate` lists (favourite schedule) that mix about two weeks.
 *
 * layout:
 * - "schedule": competition·time | home · score · away | status in one row from 1024px;
 *   below it competition + time, then the teams, then the status.
 * - "stacked": the narrow layout at every width (favourite column).
 *
 * `favorites` (main schedule, Figma 49:57 / 49:570): a star beside each team that can be
 * registered (`detailAvailable`) toggles it in place; the link sits underneath, so a star
 * press never navigates.
 */
export function MatchCard({
  match,
  layout,
  withDate = false,
  favorites = false,
}: {
  match: MatchSummary;
  layout: "schedule" | "stacked";
  withDate?: boolean;
  favorites?: boolean;
}) {
  const row = layout === "schedule";
  const penalty = penaltyText(match);
  const note = match.status === "abandoned" ? "중단 시점 스코어" : match.statusReason;
  const competition = competitionName(match.competition);
  const when = `${withDate ? `${formatShortDate(match.kickoffDateKst)} ` : ""}${kickoffTime(match)}`;
  // Kickoff has passed but the provider still says "not started": never shown as 예정.
  const awaiting = awaitingStatus(match, useNow());
  // Figma 308:4631: "상태 확인 중" with "—" until the provider confirms the start.
  const score = awaiting ? MISSING : scoreText(match);

  const status = (
    <span className={cx("flex flex-col items-start gap-0.5", row && "lg:items-end")}>
      <MatchStatusBadge match={match} awaiting={awaiting} />
      {note && <span className="text-2xs text-warning">{note}</span>}
    </span>
  );

  return (
    <div
      className={cx(
        "relative flex flex-col gap-2 rounded-control border border-line bg-surface p-3 hover:bg-subtle",
        row && "lg:flex-row lg:items-center lg:gap-3",
      )}
    >
      <Link
        href={`/matches/${match.id}`}
        prefetch={false}
        aria-label={`${competition} ${formatShortDate(match.kickoffDateKst)} ${kickoffTime(match)}, ${teamName(match.home)} ${score} ${teamName(match.away)}, ${awaiting ? "상태 확인 중" : statusWord(match)}`}
        className="absolute inset-0 rounded-control"
      />
      {/* Narrow: competition left, time right. Wide (schedule): a 164px column. */}
      <span className={cx("pointer-events-none flex items-center gap-2 text-small", row && "lg:hidden")}>
        <span className="min-w-0 flex-1 truncate text-fg-secondary">{competition}</span>
        <span className="shrink-0 font-medium text-fg">{when}</span>
      </span>
      {row && (
        <span className="pointer-events-none hidden w-[164px] shrink-0 flex-col gap-1 text-small lg:order-first lg:flex">
          <span className="truncate text-fg-secondary">{competition}</span>
          <span className="font-medium text-fg">{when}</span>
        </span>
      )}

      <span className={cx("pointer-events-none flex items-center gap-2", row && "lg:min-w-0 lg:flex-1")}>
        <Team team={match.home} side="home" star={favorites} />
        <span className="flex w-12 shrink-0 flex-col items-center">
          <span className="whitespace-nowrap text-lead font-bold text-fg">{score}</span>
          {penalty && <span className="whitespace-nowrap text-2xs text-fg-muted">{penalty}</span>}
        </span>
        <Team team={match.away} side="away" star={favorites} />
      </span>

      {/* Wide: a 164px status column mirrors the left one so the score sits at the card's centre. */}
      <span className={cx("pointer-events-none", row && "lg:flex lg:w-[164px] lg:shrink-0 lg:justify-end")}>{status}</span>
    </div>
  );
}

function Team({ team, side, star }: { team: TeamRef; side: "home" | "away"; star: boolean }) {
  const name = teamName(team);
  return (
    <span
      className={cx(
        "flex min-w-0 flex-1 items-center gap-2",
        side === "home" ? "justify-end text-right" : "flex-row-reverse justify-end",
      )}
    >
      {/* Only teams with a team detail can be registered (lower-division cup sides cannot). */}
      {star && team.detailAvailable === true && (
        <span className="pointer-events-auto relative z-10 inline-flex">
          <FavoriteStar teamId={team.id} teamName={name} />
        </span>
      )}
      <span className="min-w-0 break-keep text-body font-bold text-fg">{name}</span>
      <TeamCrest src={team.crestUrl} name={name} />
    </span>
  );
}
