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

function TeamIdentity({ team, name, linked }: { team: TeamRef; name: string; linked: boolean }) {
  return (
    <>
      <span className="lg:hidden">
        <TeamCrest src={team.crestUrl} name={name} size={44} />
      </span>
      <span className="hidden lg:block">
        <TeamCrest src={team.crestUrl} name={name} size={64} />
      </span>
      <span className={cx("text-body font-bold break-keep lg:text-title", linked && "group-hover:underline")}>
        {name}
      </span>
    </>
  );
}

const IDENTITY = "flex flex-col items-center gap-2 lg:gap-3";

function TeamSide({ team, side }: { team: TeamRef; side: "home" | "away" }) {
  const name = teamName(team);
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center lg:gap-3">
      {/* Crest and name are one link to the team detail, only for team-browse teams (D-15,
          Figma 52:151 · 63:1909 · 161:4161); other teams are plain text. */}
      {team.detailAvailable ? (
        <Link
          href={`/teams/${team.id}`}
          aria-label={`${name} 팀 상세`}
          className={cx(IDENTITY, "group rounded-control text-action")}
        >
          <TeamIdentity team={team} name={name} linked />
        </Link>
      ) : (
        <div className={cx(IDENTITY, "text-fg")}>
          <TeamIdentity team={team} name={name} linked={false} />
        </div>
      )}
      <span className="text-small text-fg-muted">{side === "home" ? "홈" : "원정"}</span>
    </div>
  );
}

/**
 * Match header (Figma 52:218 / 52:404): competition and status badges, both teams, the
 * provided score ("VS" before kickoff, "—" when missing, never 0:0), season and kickoff.
 * A live score whose last confirmation is old is flagged here.
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
      {/* The regular update time sits in the records header (Figma 161:4161); the score
          line appears here only when its update is late (LIVE-004). */}
      {match.status === "live" && updatedAt && stale && (
        <p role="status" className="text-center text-small text-warning">
          {`스코어 마지막 확인 ${formatKstTime(updatedAt)} · 갱신이 지연되고 있어 현재 스코어와 다를 수 있습니다.`}
        </p>
      )}
    </section>
  );
}
