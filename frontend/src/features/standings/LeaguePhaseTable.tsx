"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import { teamName } from "@/lib/format/match";
import { UEFA, dataStatus, numberText, phaseBands } from "./model";
import { standingsQuery } from "./queries";
import { RecentForm } from "./RecentForm";
import { TeamCell } from "./StandingsTable";

const GRID =
  "grid items-center grid-cols-[36px_minmax(120px,1fr)_40px_164px] lg:grid-cols-[44px_minmax(0,1fr)_64px_200px]";
const HEAD = "whitespace-nowrap px-1.5 py-2.5 text-small font-medium text-fg-secondary lg:px-2.5";
const CELL = "px-1.5 text-body tabular-nums lg:px-2.5";

/**
 * UEFA league phase (LEAG-002 rule 6; Figma 61:1653 PC / 61:2355 mobile): all 36 teams in the
 * provider's order under three bands — 1–8 to the round of 16, 9–24 the play-offs, 25–36 out.
 * While league-phase matches remain the bands are zones and the table says "현재 순위 기준";
 * once every league-phase match is over they are results ("확정 결과"). Recent matches are
 * league-phase matches of the season only (rule 4).
 */
export function LeaguePhaseTable({ league, season }: { league: number; season: number | null }) {
  const table = useQuery(standingsQuery(league, season));
  const data = table.data?.data;
  const short = UEFA.find((c) => c.id === league)?.short ?? "";
  const rows = data?.groups.flatMap((g) => g.rows) ?? [];
  const unconfirmed = rows.some((r) => r.team.detailAvailable === null);
  const notices = [
    (table.data?.meta.refreshFailed || table.isError) &&
      "최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다.",
    unconfirmed && "현재 소속을 확인하지 못한 팀은 팀 링크를 잠시 보류합니다.",
  ].filter(Boolean);
  const emptyTitle = "리그 페이즈 순위가 아직 없습니다";
  const bands = phaseBands(data?.complete ?? false);

  return (
    <section aria-labelledby="league-phase-title" className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id="league-phase-title" className="text-subtitle font-bold">
          {short} 리그 페이즈 순위
        </h2>
        {data && rows.length > 0 && (
          <p className="text-small text-fg-secondary">{data.complete ? "확정 결과" : "현재 순위 기준"}</p>
        )}
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
          <div className="-mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0" tabIndex={0} aria-label={`${short} 리그 페이즈 순위 표`}>
            <div role="table" aria-label={`${short} 리그 페이즈 순위`} className="min-w-[360px] lg:min-w-0">
              <div role="rowgroup">
                <div role="row" className={cx(GRID, "rounded-control bg-subtle")}>
                  <span role="columnheader" className={HEAD}>순위</span>
                  <span role="columnheader" className={HEAD}>팀</span>
                  <span role="columnheader" className={HEAD}>승점</span>
                  <span role="columnheader" className={HEAD}>최근 5경기</span>
                </div>
              </div>
              {bands.map((band) => {
                const inBand = rows.filter((r) => r.rank >= band.from && r.rank <= band.to);
                if (inBand.length === 0) return null;
                return (
                  <div key={band.key} role="rowgroup" aria-label={`${band.label} ${band.range}`}>
                    <p aria-hidden className="flex items-center gap-2 px-1.5 pt-3 pb-1 lg:px-2.5">
                      <Badge tone={band.tone} size="caption" className="px-1.5 py-0.5">
                        {band.label}
                      </Badge>
                      <span className="text-caption text-fg-muted">{band.range}</span>
                    </p>
                    {inBand.map((row, index) => (
                        <div
                          key={row.team.id}
                          role="row"
                          className={cx(GRID, "min-h-[46px] py-1.5", index < inBand.length - 1 && "border-b border-line")}
                        >
                          <span role="cell" className={CELL}>{row.rank}</span>
                          <span role="rowheader" className={cx(CELL, "min-w-0")}>
                            <TeamCell row={row} zone={null} />
                          </span>
                          <span role="cell" className={cx(CELL, "font-bold")}>{numberText(row.points)}</span>
                          <span role="cell" className={CELL}>
                            <RecentForm matches={row.recent} teamName={teamName(row.team)} />
                          </span>
                        </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
          </div>
        )}
      </DataState>
    </section>
  );
}
