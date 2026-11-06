"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import type { StandingRow } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { dataStatus, formResults, numberText, signed, zoneLabel } from "./model";
import { standingsQuery } from "./queries";

const FORM_COLORS = { 승: "text-live", 무: "text-fg-secondary", 패: "text-error" } as const;
const HEAD = "h-10 px-2.5 text-left text-small font-medium text-fg-secondary";
const CELL = "h-[52px] px-2.5 text-body tabular-nums";

/**
 * League table of one season (LEAG-002; Figma 53:1353 / 61:1653, states 57:599). Values are
 * the provider's as stored (e.g. a 33-match row stays 33). Team links follow the current
 * allow set: a past team says "팀 상세 미제공", and the season's own relegation wording
 * ("당시 강등", "당시 승강 PO") is a separate mark. An unknown membership is never shown as
 * relegation; its link waits until it is confirmed.
 */
export function StandingsTable({ league, season }: { league: number; season: number | null }) {
  const table = useQuery(standingsQuery(league, season));
  const data = table.data?.data;
  const heading = data ? `${data.season.label} ${data.league.shortName}` : "팀 순위";
  const rows = data?.groups.flatMap((g) => g.rows) ?? [];
  const past = data ? !data.season.current : false;
  const marked = past && rows.some((r) => r.zone !== null || r.team.detailAvailable === false);
  // Partly shown: a later refresh failed (server or this browser), or some memberships are
  // unconfirmed. The stored table stays on screen in both cases.
  const unconfirmed = rows.some((r) => r.team.detailAvailable === null);
  const notices = [
    (table.data?.meta.refreshFailed || table.isError) &&
      "최신 순위로 갱신하지 못해 마지막으로 확인한 순위를 표시합니다.",
    unconfirmed &&
      "현재 소속을 확인하지 못한 팀은 강등으로 단정하지 않고 팀 링크를 잠시 보류합니다.",
  ].filter(Boolean);
  const emptyTitle = "순위 데이터가 아직 없습니다";
  const emptyDescription = "이 시즌의 리그 순위가 제공되면 표시합니다.";

  const body = (
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
      {rows.length === 0 ? (
        // The last confirmed table had no rows and a later refresh failed (partial).
        <StateMessage title={emptyTitle} description={emptyDescription} />
      ) : (
      <div className="flex flex-col gap-4">
        <p className="text-small text-fg-muted lg:hidden">↔ 좌우로 밀어 전체 기록 보기</p>
        {data?.groups.map((group) => (
          <div key={group.name} className="flex flex-col gap-2">
            {data.groups.length > 1 && <h3 className="text-label font-bold text-fg">{group.name}</h3>}
            <Table rows={group.rows} past={past} caption={`${heading} ${group.name}`} />
          </div>
        ))}
        {marked && (
          <p className="rounded-control bg-subtle px-3 py-2.5 text-small text-fg-secondary">
            당시 강등·승강 PO와 현재 팀 상세 제공 여부는 별개입니다. 현재 상세 미제공 팀도 과거 경기
            결과를 볼 수 있습니다.
          </p>
        )}
      </div>
      )}
    </DataState>
  );

  return (
    <section
      aria-labelledby="standings-table-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <h2 id="standings-table-title" className="text-subtitle font-bold">
        {heading}
      </h2>
      {body}
    </section>
  );
}

function Table({ rows, past, caption }: { rows: readonly StandingRow[]; past: boolean; caption: string }) {
  return (
    // Phones scroll the table sideways inside the card (guide §6.6); the page never scrolls.
    <div className="-mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0" tabIndex={0} aria-label={`${caption} 표`}>
      <table className="w-full min-w-[640px] border-collapse">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-subtle">
          <tr>
            <th scope="col" className={cx(HEAD, "w-10")}>#</th>
            <th scope="col" className={HEAD}>팀</th>
            <th scope="col" className={cx(HEAD, "w-[54px]")}>경기</th>
            <th scope="col" className={cx(HEAD, "w-11")}>승</th>
            <th scope="col" className={cx(HEAD, "w-11")}>무</th>
            <th scope="col" className={cx(HEAD, "w-11")}>패</th>
            <th scope="col" className={cx(HEAD, "w-16")}>득실</th>
            <th scope="col" className={cx(HEAD, "w-16")}>승점</th>
            <th scope="col" className={cx(HEAD, "w-[150px] lg:w-[223px]")}>최근 5경기</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.team.id} className="border-b border-line">
              <td className={CELL}>{row.rank}</td>
              <td className={cx(CELL, "py-2")}>
                <TeamCell row={row} past={past} />
              </td>
              <td className={CELL}>{numberText(row.played)}</td>
              <td className={CELL}>{numberText(row.win)}</td>
              <td className={CELL}>{numberText(row.draw)}</td>
              <td className={CELL}>{numberText(row.lose)}</td>
              <td className={CELL}>{signed(row.goalsDiff)}</td>
              <td className={cx(CELL, "font-bold")}>{numberText(row.points)}</td>
              <td className={CELL}>
                <Form form={row.form} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeamCell({ row, past }: { row: StandingRow; past: boolean }) {
  const name = teamName(row.team);
  const zone = past ? zoneLabel(row) : null;
  return (
    <div className="flex items-center gap-2">
      <TeamCrest src={row.team.crestUrl} name={name} size={24} />
      <div className="flex min-w-0 flex-col">
        {row.team.detailAvailable === true ? (
          <Link
            href={`/teams/${row.team.id}`}
            prefetch={false}
            className="truncate text-body text-fg hover:text-action hover:underline"
          >
            {name}
          </Link>
        ) : (
          <span className="truncate text-body text-fg">{name}</span>
        )}
        {row.team.detailAvailable === false && <span className="text-caption text-fg-muted">팀 상세 미제공</span>}
        {zone && <span className="text-caption font-medium text-warning">{zone}</span>}
      </div>
    </div>
  );
}

function Form({ form }: { form: string | null }) {
  const results = formResults(form);
  if (results.length === 0) return <span className="text-fg-muted">—</span>;
  return (
    <span className="flex gap-1.5 font-bold" aria-label={`최근 5경기 ${results.join(" ")}`}>
      {results.map((result, index) => (
        <span key={index} aria-hidden className={FORM_COLORS[result]}>
          {result}
        </span>
      ))}
    </span>
  );
}
