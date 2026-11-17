"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import type { TableRow } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { competitionLabel, dataStatus, leagueZone, numberText, signed, type Zone } from "./model";
import { standingsQuery } from "./queries";
import { RecentForm } from "./RecentForm";

/**
 * Column orders (Figma 53:1353 PC / 53:2047 mobile): PC 순위·팀·경기·승·무·패·득실·승점·
 * 최근 5경기; mobile 순위·팀·승점·최근 5경기·경기·승·무·패·득실 in a sideways-scrolling table.
 * Cells stay in the PC order in the DOM (read order) and `order-*` moves them on phones.
 */
const GRID =
  "grid items-center grid-cols-[36px_108px_40px_164px_40px_32px_32px_32px_48px] " +
  "lg:grid-cols-[44px_minmax(0,1fr)_54px_44px_44px_44px_64px_64px_200px]";
const ORDER = {
  played: "order-5 lg:order-none",
  win: "order-6 lg:order-none",
  draw: "order-7 lg:order-none",
  lose: "order-8 lg:order-none",
  diff: "order-9 lg:order-none",
  points: "order-3 lg:order-none",
  recent: "order-4 lg:order-none",
};
const HEAD = "whitespace-nowrap px-1.5 py-2.5 text-small font-medium text-fg-secondary lg:px-2.5";
const CELL = "px-1.5 text-body tabular-nums lg:px-2.5";

/**
 * League table of one season (LEAG-002; Figma 53:1353 / 53:2047, states 57:599). Rows are the
 * provider's order and values. Relegation marks come from the row's position
 * (`leagueZone`, rule 5) — a zone while the season runs, the result once it is over — and are
 * separate from "팀 상세 미제공" (the current allow set). An unknown membership is never shown
 * as relegation; its link waits until it is confirmed.
 */
export function StandingsTable({ league, season }: { league: number; season: number | null }) {
  const table = useQuery(standingsQuery(league, season));
  const data = table.data?.data;
  const heading = `${competitionLabel(league)} 순위`;
  const rows = data?.groups.flatMap((g) => g.rows) ?? [];
  const unconfirmed = rows.some((r) => r.team.detailAvailable === null);
  const notices = [
    (table.data?.meta.refreshFailed || table.isError) &&
      "최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다.",
    unconfirmed &&
      "현재 소속을 확인하지 못한 팀은 강등으로 단정하지 않고 팀 링크를 잠시 보류합니다.",
  ].filter(Boolean);
  const emptyTitle = "순위 데이터가 아직 없습니다";
  const emptyDescription = "이 시즌의 리그 순위가 제공되면 표시합니다.";
  const pastTeams = rows.some((r) => r.team.detailAvailable === false);

  return (
    <section aria-labelledby="standings-table-title" className="flex min-w-0 flex-col gap-4">
      <h2 id="standings-table-title" className="text-subtitle font-bold">
        {heading}
      </h2>
      <DataState
        status={dataStatus(table, rows.length === 0, notices.length > 0)}
        loadingFallback={<ListSkeleton />}
        error={table.error}
        // 404 = an unsupported league or season: asking again cannot help.
        onRetry={isApiError(table.error) && table.error.status === 404 ? undefined : () => table.refetch()}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        partialNotice={notices.join(" ")}
        // Figma 57:599 membership-error: the stored table stays; asking again re-reads the
        // current allow set with it. A server-side refresh failure is not helped by a click.
        partialAction={
          unconfirmed || table.isError ? (
            <Button className="min-h-9" onClick={() => table.refetch()}>
              다시 확인
            </Button>
          ) : undefined
        }
      >
        {rows.length === 0 || !data ? (
          // The last confirmed table had no rows and a later refresh failed (partial).
          <StateMessage title={emptyTitle} description={emptyDescription} />
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-small text-fg-muted lg:hidden">좌우로 밀어 전체 기록 보기</p>
            {data.groups.map((group) => (
              <div key={group.name} className="flex flex-col gap-2">
                {data.groups.length > 1 && <h3 className="text-label font-bold text-fg">{group.name}</h3>}
                <Table rows={group.rows} league={league} complete={data.complete} caption={`${heading} ${group.name}`} />
              </div>
            ))}
            {pastTeams && (
              <p className="rounded-control bg-subtle px-3 py-2.5 text-small text-fg-secondary">
                강등·승강 플레이오프 표시와 현재 팀 상세 제공 여부는 별개입니다. 현재 상세 미제공 팀도 과거
                경기 결과를 볼 수 있습니다.
              </p>
            )}
          </div>
        )}
      </DataState>
    </section>
  );
}

function Table({
  rows,
  league,
  complete,
  caption,
}: {
  rows: readonly TableRow[];
  league: number;
  complete: boolean;
  caption: string;
}) {
  return (
    // Phones scroll the table sideways inside the area (guide §6.6); the page never scrolls.
    <div className="-mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0" tabIndex={0} aria-label={`${caption} 표`}>
      <div role="table" aria-label={caption} className="min-w-[532px] lg:min-w-0">
        <div role="rowgroup">
          <div role="row" className={cx(GRID, "rounded-control bg-subtle")}>
            <span role="columnheader" className={HEAD}>순위</span>
            <span role="columnheader" className={HEAD}>팀</span>
            <span role="columnheader" className={cx(HEAD, ORDER.played)}>경기</span>
            <span role="columnheader" className={cx(HEAD, ORDER.win)}>승</span>
            <span role="columnheader" className={cx(HEAD, ORDER.draw)}>무</span>
            <span role="columnheader" className={cx(HEAD, ORDER.lose)}>패</span>
            <span role="columnheader" className={cx(HEAD, ORDER.diff)}>득실</span>
            <span role="columnheader" className={cx(HEAD, ORDER.points)}>승점</span>
            <span role="columnheader" className={cx(HEAD, ORDER.recent)}>최근 5경기</span>
          </div>
        </div>
        <div role="rowgroup">
          {rows.map((row) => (
            <div key={row.team.id} role="row" className={cx(GRID, "min-h-[46px] border-b border-line py-1.5")}>
              <span role="cell" className={CELL}>{row.rank}</span>
              <span role="rowheader" className={cx(CELL, "min-w-0")}>
                <TeamCell row={row} zone={leagueZone(league, row.rank, rows.length, complete)} />
              </span>
              <span role="cell" className={cx(CELL, ORDER.played)}>{numberText(row.played)}</span>
              <span role="cell" className={cx(CELL, ORDER.win)}>{numberText(row.win)}</span>
              <span role="cell" className={cx(CELL, ORDER.draw)}>{numberText(row.draw)}</span>
              <span role="cell" className={cx(CELL, ORDER.lose)}>{numberText(row.lose)}</span>
              <span role="cell" className={cx(CELL, ORDER.diff)}>{signed(row.goalsDiff)}</span>
              <span role="cell" className={cx(CELL, ORDER.points, "font-bold")}>{numberText(row.points)}</span>
              <span role="cell" className={cx(CELL, ORDER.recent)}>
                <RecentForm matches={row.recent} teamName={teamName(row.team)} />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Crest, name (a link only for a current team) and the row's marks (Figma 449:6462). */
export function TeamCell({ row, zone }: { row: TableRow; zone: Zone | null }) {
  const name = teamName(row.team);
  return (
    <span className="flex min-w-0 items-center gap-2">
      <TeamCrest src={row.team.crestUrl} name={name} size={20} />
      <span className="flex min-w-0 flex-col items-start gap-0.5">
        {row.team.detailAvailable === true ? (
          <Link
            href={`/teams/${row.team.id}`}
            prefetch={false}
            className="line-clamp-2 font-bold text-fg hover:text-action hover:underline lg:truncate"
          >
            {name}
          </Link>
        ) : (
          <span className="line-clamp-2 font-bold text-fg lg:truncate">{name}</span>
        )}
        {zone && (
          <Badge tone={zone.tone} size="caption" className="px-1.5 py-0.5">
            {zone.label}
          </Badge>
        )}
        {row.team.detailAvailable === false && <span className="text-caption text-fg-muted">팀 상세 미제공</span>}
      </span>
    </span>
  );
}
