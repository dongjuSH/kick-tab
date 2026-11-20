"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { teamName } from "@/lib/format/match";
import { ChipRow } from "./ChipRow";
import { COMPETITIONS, DEFAULT_LEAGUE, UEFA, dataStatus, isUefa, numberText } from "./model";
import { standingsSummaryQuery } from "./queries";
import { useCompetitionLabel } from "./useCompetitionLabel";

/**
 * Main page compact tables (LEAG-001, SCH-005; Figma 49:57 / 49:570, 234:8881 / 234:9750):
 * chips for the five leagues and the three UEFA competitions (DB names; PC arrows, phones
 * swipe), the top six of the current season — a UEFA competition's league phase, kept as last
 * stored once its knockouts begin — and a link to the same competition's current-season page
 * ("전체 순위 보기"; UEFA "전체 순위·대진 보기", opening on the league phase). A past season
 * chosen on the standings page is never carried over. A competition not provided or failing
 * is reported here only; the other main sections are untouched.
 */
export function MainStandings() {
  const [league, setLeague] = useState<number>(DEFAULT_LEAGUE);
  const label = useCompetitionLabel();
  const summary = useQuery(standingsSummaryQuery);
  const item = summary.data?.leagues.find((l) => l.league.id === league);

  // One competition never collected is a failure of that one only (the others still show).
  const notCollected = summary.isSuccess && item?.status !== "available";
  const rows = item?.rows ?? [];
  const name = label(league);

  const body = (
    <DataState
      status={
        notCollected
          ? "error"
          : dataStatus(summary, rows.length === 0, Boolean(item?.refreshFailed || summary.isError))
      }
      loadingFallback={<ListSkeleton />}
      error={notCollected ? undefined : summary.error}
      errorTitle={notCollected ? `${name} 순위를 아직 불러오지 못했습니다` : "리그 순위를 불러오지 못했습니다"}
      onRetry={() => summary.refetch()}
      emptyTitle="순위 데이터가 아직 없습니다"
      partialNotice="최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다."
    >
      {rows.length === 0 ? (
        // The last confirmed table was empty and a later refresh failed (partial).
        <StateMessage title="순위 데이터가 아직 없습니다" />
      ) : (
        <ol aria-label={`${name}${isUefa(league) ? " 리그 페이즈" : ""} 상위 ${rows.length}팀`}>
          {rows.map((row) => (
            // Figma 234:8881: name over "경기 4 · 3승 1무 0패", points on the right.
            <li key={row.team.id} className="flex min-h-[58px] items-center gap-3 border-b border-line py-2 text-body">
              <span className="w-5 shrink-0 text-small text-fg-muted tabular-nums">{row.rank}</span>
              <TeamCrest src={row.team.crestUrl} name={teamName(row.team)} size={20} />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate font-medium">{teamName(row.team)}</span>
                <span className="text-caption text-fg-muted tabular-nums">
                  경기 {numberText(row.played)} · {numberText(row.win)}승 {numberText(row.draw)}무 {numberText(row.lose)}패
                </span>
              </span>
              <span className="shrink-0 font-bold tabular-nums">
                <span className="sr-only">승점 </span>
                {row.points === null ? numberText(null) : `${row.points}점`}
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
        리그 순위
      </h2>
      <ChipRow
        items={COMPETITIONS.map((c) => ({
          value: String(c.id),
          label: label(c.id),
          groupStart: c.id === UEFA[0].id,
        }))}
        value={String(league)}
        onChange={(value) => setLeague(Number(value))}
        label="대회 선택"
      />
      {body}
      <ButtonLink href={`/standings?league=${league}`} fullWidth>
        {isUefa(league) ? "전체 순위·대진 보기" : "전체 순위 보기"}
      </ButtonLink>
    </section>
  );
}
