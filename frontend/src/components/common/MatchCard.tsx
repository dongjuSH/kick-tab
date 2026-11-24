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
  statusNotes,
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
 *   below it the phone card (Figma 306:3969, 2026-11-24): competition over time with the
 *   status at the top right, then the teams — a 24px star slot at each outer edge, 12px names
 *   that wrap between words onto a second line, 16px crests and a 38px score.
 * - "stacked": the phone card at every width.
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
  const competition = competitionName(match.competition);
  const when = `${withDate ? `${formatShortDate(match.kickoffDateKst)} ` : ""}${kickoffTime(match)}`;
  const { awaiting, score } = useMatchScore(match);

  return (
    <div
      className={cx(
        "relative flex flex-col gap-1.5 rounded-control border border-line bg-surface px-2 py-3 hover:bg-subtle",
        row && "lg:flex-row lg:items-center lg:gap-3 lg:p-3",
      )}
    >
      <Link
        href={`/matches/${match.id}`}
        prefetch={false}
        aria-label={`${competition} ${formatShortDate(match.kickoffDateKst)} ${kickoffTime(match)}, ${teamName(match.home)} ${score} ${teamName(match.away)}, ${awaiting ? "상태 확인 중" : statusWord(match)}`}
        className="absolute inset-0 rounded-control"
      />
      {/* Narrow: competition over time, status at the right. Wide (schedule): a 164px column. */}
      <span className={cx("pointer-events-none flex items-start gap-2", row && "lg:hidden")}>
        <span className="flex min-w-0 flex-1 flex-col text-small leading-[18px]">
          <span className="truncate text-fg-secondary">{competition}</span>
          <span className="font-medium text-fg">{when}</span>
        </span>
        <MatchStatus match={match} awaiting={awaiting} end />
      </span>
      {row && (
        <span className="pointer-events-none hidden w-[164px] shrink-0 flex-col gap-1 text-small lg:order-first lg:flex">
          <span className="truncate text-fg-secondary">{competition}</span>
          <span className="font-medium text-fg">{when}</span>
        </span>
      )}

      <MatchTeams match={match} favorites={favorites} card className={cx("pointer-events-none", row && "lg:min-w-0 lg:flex-1")} />

      {/* Wide: a 164px status column mirrors the left one so the score sits at the card's centre. */}
      {row && (
        <span className="pointer-events-none hidden lg:flex lg:w-[164px] lg:shrink-0 lg:justify-end">
          <MatchStatus match={match} awaiting={awaiting} className="lg:items-end" />
        </span>
      )}
    </div>
  );
}

/**
 * Score shown for a match: kickoff passed but the provider still says "not started" is never
 * shown as 예정 — "상태 확인 중" with "—" until the start is confirmed (Figma 308:4631).
 */
export function useMatchScore(match: MatchSummary): { awaiting: boolean; score: string } {
  const awaiting = awaitingStatus(match, useNow());
  return { awaiting, score: awaiting ? MISSING : scoreText(match) };
}

/** Status badge with its notes under it — abandoned score notice and provider reason (match cards, TOP 5). */
export function MatchStatus({
  match,
  awaiting,
  end = false,
  className,
}: {
  match: MatchSummary;
  awaiting: boolean;
  /** Right-aligned at every width (TOP 5 rows). */
  end?: boolean;
  className?: string;
}) {
  return (
    <span className={cx("flex flex-col gap-0.5", end ? "items-end text-right" : "items-start", className)}>
      <MatchStatusBadge match={match} awaiting={awaiting} />
      {statusNotes(match).map((note) => (
        <span key={note} className="text-2xs text-warning">{note}</span>
      ))}
    </span>
  );
}

/**
 * Home name · crest · score (PK under it) · crest · away name (match cards, TOP 5 rows).
 * `card`: a match card, which below 1024px uses the phone layout (Figma 306:3969).
 */
export function MatchTeams({
  match,
  favorites = false,
  card = false,
  className,
}: {
  match: MatchSummary;
  favorites?: boolean;
  card?: boolean;
  className?: string;
}) {
  const { score } = useMatchScore(match);
  const penalty = penaltyText(match);
  return (
    <span className={cx("flex items-center", card ? "gap-1 lg:gap-2" : "gap-2", className)}>
      <Team team={match.home} side="home" star={favorites} card={card} />
      <span className={cx("flex shrink-0 flex-col items-center", card ? "w-[38px] lg:w-12" : "w-12")}>
        <span className="whitespace-nowrap text-lead font-bold text-fg">{score}</span>
        {penalty && <span className="whitespace-nowrap text-2xs text-fg-muted">{penalty}</span>}
      </span>
      <Team team={match.away} side="away" star={favorites} card={card} />
    </span>
  );
}

function Team({ team, side, star, card }: { team: TeamRef; side: "home" | "away"; star: boolean; card: boolean }) {
  const name = teamName(team);
  // Only teams with a team detail can be registered (lower-division cup sides cannot).
  const registrable = star && team.detailAvailable === true;
  return (
    <span
      className={cx(
        "flex min-w-0 flex-1 items-center",
        card ? "gap-1 lg:gap-2" : "gap-2",
        side === "home" ? "justify-end text-right" : "flex-row-reverse justify-end",
      )}
    >
      {/* Phone card: the star keeps its 24px slot at the outer edge even when hidden, so the
          names and the score stay put (Figma 306:3969). */}
      {(registrable || (star && card)) && (
        <span
          className={cx(
            "pointer-events-auto relative z-10 inline-flex shrink-0",
            card && "w-6 justify-center",
            !registrable && "lg:hidden",
          )}
        >
          {registrable && <FavoriteStar teamId={team.id} teamName={name} />}
        </span>
      )}
      {/* Words stay whole and a long name goes on to a second line between words; only a
          single word longer than the column breaks inside it. */}
      <span
        className={cx(
          "min-w-0 break-keep font-bold text-fg [overflow-wrap:anywhere]",
          card ? "flex-1 text-small leading-[18px] lg:flex-none lg:text-body lg:leading-[22px]" : "text-body",
        )}
      >
        {name}
      </span>
      <TeamCrest src={team.crestUrl} name={name} className={card ? "max-lg:size-4!" : undefined} />
    </span>
  );
}
