"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { MatchStatusBadge } from "@/components/common/MatchStatusBadge";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Badge } from "@/components/ui/Badge";
import { cx } from "@/components/ui/cx";
import type { MatchInfo, TeamRef } from "@/lib/api/types";
import { formatKstDateTime, formatKstTime } from "@/lib/format/kst";
import { competitionName, penaltyText, scoreText, teamName } from "@/lib/format/match";

// Flag a live score when its age passes this threshold, even while refetches fail.
const STALE_LIVE_MS = 3 * 60_000;

/** "Regular Season - 11" -> "11라운드", "League Stage - 4" -> "리그 페이즈 4차전"; other
 * stages (cup rounds) keep the provider wording. */
function roundText(round: string | null): string | null {
  if (!round) return null;
  const regular = /^Regular Season - (\d+)$/.exec(round);
  if (regular) return `${regular[1]}라운드`;
  const league = /^League Stage - (\d+)$/.exec(round);
  return league ? `리그 페이즈 ${league[1]}차전` : round;
}

function TeamSide({ team, side }: { team: TeamRef; side: "home" | "away" }) {
  const name = teamName(team);
  const label = side === "home" ? "홈" : "원정";
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center lg:gap-3">
      <span className="lg:hidden">
        <TeamCrest src={team.crestUrl} name={name} size={44} />
      </span>
      <span className="hidden lg:block">
        <TeamCrest src={team.crestUrl} name={name} size={64} />
      </span>
      {/* Team links follow the shared allow set (D-15): only current five-league teams. */}
      {team.detailAvailable ? (
        <Link
          href={`/teams/${team.id}`}
          className="rounded-control text-body font-bold break-keep text-fg hover:text-action hover:underline lg:text-title"
        >
          {name}
        </Link>
      ) : (
        <span className="text-body font-bold break-keep text-fg lg:text-title">{name}</span>
      )}
      <span className="text-small text-fg-muted">
        {label}
        {team.detailAvailable === false && " · 팀 상세 미제공"}
      </span>
    </div>
  );
}

/**
 * Match header (Figma 52:218 / 52:404): competition and status badges, both teams, the
 * provided score ("VS" before kickoff, "—" when missing, never 0:0), season and kickoff.
 * Live matches show when the score was last confirmed, flagged when it is old.
 */
export function Scoreboard({
  info,
  updatedAt,
  checkedAt,
  heading,
}: {
  info: MatchInfo;
  updatedAt: string | null;
  checkedAt: number;
  heading: ReactNode;
}) {
  const { match } = info;
  const [clock, setClock] = useState(checkedAt);
  const live = match.status === "live";
  useEffect(() => {
    if (!live) return;
    const tick = () => {
      if (document.visibilityState === "visible") setClock(Date.now());
    };
    const timer = window.setInterval(tick, 1_000);
    document.addEventListener("visibilitychange", tick);
    window.addEventListener("focus", tick);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
      window.removeEventListener("focus", tick);
    };
  }, [live]);
  const penalty = penaltyText(match);
  const kickoff = match.timeConfirmed
    ? formatKstDateTime(match.kickoffAt)
    : `${match.kickoffDateKst} 시간 미정`;
  const meta = [info.seasonLabel, roundText(info.round), kickoff].filter(Boolean).join("  ·  ");
  const stale = updatedAt !== null && Math.max(clock, checkedAt) - Date.parse(updatedAt) > STALE_LIVE_MS;

  return (
    <section className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6">
      {heading}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Badge size="caption">{competitionName(match.competition)}</Badge>
        <MatchStatusBadge match={match} size="caption" />
      </div>
      <div className="flex items-center gap-3">
        <TeamSide team={match.home} side="home" />
        <div className="flex w-24 shrink-0 flex-col items-center lg:w-[217px]">
          <span className="text-heading font-bold whitespace-nowrap text-fg lg:text-[40px] lg:leading-[54px]">
            {scoreText(match)}
          </span>
          {penalty && <span className="text-small text-fg-muted">{penalty}</span>}
        </div>
        <TeamSide team={match.away} side="away" />
      </div>
      <p className="text-center text-small whitespace-pre-wrap text-fg-muted">{meta}</p>
      {match.status === "live" && updatedAt && (
        <p className={cx("text-center text-small", stale ? "text-warning" : "text-fg-muted")}>
          {`마지막 확인 ${formatKstTime(updatedAt)}`}
          {stale && " · 갱신이 지연되고 있어 현재 스코어와 다를 수 있습니다."}
        </p>
      )}
    </section>
  );
}
