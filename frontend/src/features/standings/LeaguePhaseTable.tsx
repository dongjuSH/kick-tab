"use client";

import { useQuery } from "@tanstack/react-query";
import { RecentForm, formItem } from "@/components/common/RecentForm";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import { teamName } from "@/lib/format/match";
import { bandOf, dataStatus, numberText, tableBands } from "./model";
import { standingsQuery } from "./queries";
import { BandLegend, BasisNote, TeamCell, bandRowClass } from "./StandingsTable";
import { useCompetitionLabel } from "./useCompetitionLabel";

const GRID =
  "grid items-center grid-cols-[36px_minmax(120px,1fr)_40px_148px] lg:grid-cols-[44px_minmax(0,1fr)_64px_160px]";
const HEAD = "whitespace-nowrap px-1.5 py-2.5 text-small font-medium text-fg-secondary lg:px-2.5";
const CELL = "px-1.5 text-body tabular-nums lg:px-2.5";

/**
 * UEFA league phase (LEAG-002 rule 6; Figma 61:1653 PC / 61:2355 mobile): all 36 teams in the
 * provider's order, each row's band as a left border — 1–8 to the round of 16, 9–24 the
 * play-offs, 25–36 out — named once in the legend and in the row's accessible name. While
 * league-phase matches remain the bands are zones ("현재 순위 기준"); once every league-phase
 * match is over they are results ("확정 결과"). Recent matches are league-phase matches of the
 * season only (rule 4).
 */
export function LeaguePhaseTable({ league, season }: { league: number; season: number | null }) {
  const table = useQuery(standingsQuery(league, season));
  const label = useCompetitionLabel();
  const data = table.data?.data;
  const name = label(league);
  const rows = data?.groups.flatMap((g) => g.rows) ?? [];
  const unconfirmed = rows.some((r) => r.team.detailAvailable === null);
  const notices = [
    (table.data?.meta.refreshFailed || table.isError) &&
      "최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다.",
    unconfirmed && "현재 소속을 확인하지 못한 팀은 팀 링크를 잠시 보류합니다.",
  ].filter(Boolean);
  const emptyTitle = "리그 페이즈 순위가 아직 없습니다";
  const bands = tableBands(league, rows.length, data?.complete ?? false);

  return (
    <section aria-labelledby="league-phase-title" className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id="league-phase-title" className="text-subtitle font-bold">
          {name} 리그 페이즈 순위
        </h2>
        {data && rows.length > 0 && <BasisNote complete={data.complete} />}
      </div>
      <DataState
        status={dataStatus(table, rows.length === 0, notices.length > 0)}
        loadingFallback={<ListSkeleton />}
        error={table.error}
        onRetry={isApiError(table.error) && table.error.status === 404 ? undefined : () => table.refetch()}
        emptyTitle={emptyTitle}
        partialNotice={notices.join(" ")}
        partialAction={
          unconfirmed || table.isError ? (
            <Button className="min-h-9" onClick={() => table.refetch()}>
              다시 확인
            </Button>
          ) : undefined
        }
      >
        {rows.length === 0 ? (
          <StateMessage title={emptyTitle} />
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-small text-fg-muted sm:hidden">좌우로 밀어 전체 기록 보기</p>
            <div className="-mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0" tabIndex={0} aria-label={`${name} 리그 페이즈 순위 표`}>
              <div role="table" aria-label={`${name} 리그 페이즈 순위`} className="min-w-[347px] lg:min-w-0">
                <div role="rowgroup">
                  <div role="row" className={cx(GRID, bandRowClass(null), "rounded-control bg-subtle")}>
                    <span role="columnheader" className={HEAD}>순위</span>
                    <span role="columnheader" className={HEAD}>팀</span>
                    <span role="columnheader" className={HEAD}>승점</span>
                    <span role="columnheader" className={HEAD}>최근 5경기</span>
                  </div>
                </div>
                <div role="rowgroup">
                  {rows.map((row) => {
                    const band = bandOf(bands, row.rank);
                    return (
                      <div
                        key={row.team.id}
                        role="row"
                        className={cx(GRID, bandRowClass(band), "min-h-[46px] border-b border-b-line py-1.5")}
                      >
                        <span role="cell" className={CELL}>
                          {row.rank}
                          {band && <span className="sr-only">, {band.label}</span>}
                        </span>
                        <span role="rowheader" className={cx(CELL, "min-w-0")}>
                          <TeamCell row={row} />
                        </span>
                        <span role="cell" className={cx(CELL, "font-bold")}>{numberText(row.points)}</span>
                        <span role="cell" className={CELL}>
                          <RecentForm matches={row.recent.map(formItem)} teamName={teamName(row.team)} />
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <BandLegend bands={bands} />
          </div>
        )}
      </DataState>
    </section>
  );
}
