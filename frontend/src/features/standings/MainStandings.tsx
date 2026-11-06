"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { chipClass } from "@/components/ui/chip";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { teamName } from "@/lib/format/match";
import { DEFAULT_LEAGUE, LEAGUES, dataStatus, numberText } from "./model";
import { standingsSummaryQuery } from "./queries";

/**
 * Main page compact tables (LEAG-001, SCH-005; Figma 49:368 / 49:848): five league chips, the
 * top six of the current season, and "전체 순위 보기" to the same league's current-season
 * table (a past season chosen on the standings page is never carried over). A failure here
 * leaves the other main sections untouched.
 */
export function MainStandings() {
  const [league, setLeague] = useState<number>(DEFAULT_LEAGUE);
  const summary = useQuery(standingsSummaryQuery);
  const item = summary.data?.leagues.find((l) => l.league.id === league);

  // One league never collected is a failure of that league only (the others still show).
  const notCollected = summary.isSuccess && item?.status !== "available";
  const rows = item?.rows ?? [];

  const body = (
    <DataState
      status={
        notCollected
          ? "error"
          : dataStatus(summary, rows.length === 0, Boolean(item?.refreshFailed || summary.isError))
      }
      loadingFallback={<ListSkeleton />}
      error={notCollected ? undefined : summary.error}
      errorTitle={notCollected ? "이 리그 순위를 아직 불러오지 못했습니다" : "리그 순위를 불러오지 못했습니다"}
      onRetry={() => summary.refetch()}
      emptyTitle="순위 데이터가 아직 없습니다"
      partialNotice="최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다."
    >
      {rows.length === 0 ? (
        // The last confirmed table was empty and a later refresh failed (partial).
        <StateMessage title="순위 데이터가 아직 없습니다" />
      ) : (
      <ol aria-label={`${item?.league.shortName ?? ""} 상위 ${rows.length}팀`}>
        {rows.map((row) => (
          <li key={row.team.id} className="flex h-[55px] items-center gap-3 border-b border-line text-body">
            <span className="w-5 shrink-0 text-small text-fg-muted tabular-nums">{row.rank}</span>
            <TeamCrest src={row.team.crestUrl} name={teamName(row.team)} size={20} />
            <span className="min-w-0 flex-1 truncate font-medium">{teamName(row.team)}</span>
            <span className="shrink-0 font-bold tabular-nums">
              <span className="sr-only">승점 </span>
              {numberText(row.points)}
            </span>
          </li>
        ))}
      </ol>
      )}
    </DataState>
  );

  return (
    <section
      aria-labelledby="main-standings-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <h2 id="main-standings-title" className="text-subtitle font-bold">
        5대 리그 순위
      </h2>
      <div className="-mx-1 overflow-x-auto px-1 py-1 [scrollbar-width:none]" role="group" aria-label="리그 선택">
        <div className="flex gap-2">
          {LEAGUES.map((l) => (
            <button
              key={l.id}
              type="button"
              aria-pressed={league === l.id}
              className={chipClass(league === l.id)}
              onClick={() => setLeague(l.id)}
            >
              {l.chip}
            </button>
          ))}
        </div>
      </div>
      {body}
      <ButtonLink href={`/standings?league=${league}`} fullWidth>
        전체 순위 보기
      </ButtonLink>
    </section>
  );
}
