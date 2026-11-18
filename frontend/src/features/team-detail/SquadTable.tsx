"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import { useState } from "react";
import { PlayerPhoto } from "@/components/common/TeamCrest";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { dataStatus } from "@/features/standings/model";
import type { SquadPlayer } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { competitionName } from "@/lib/format/match";
import {
  DEFAULT_SORT,
  PLAYERS_SHOWN,
  nextSort,
  positionLabel,
  ratingText,
  seasonText,
  sortPlayers,
  statText,
  type SortKey,
  type SortState,
} from "./model";
import { teamSquadQuery } from "./queries";
import { AREA } from "./TeamMatches";

const COLUMNS: readonly { key: SortKey; label: string; className: string }[] = [
  { key: "name", label: "선수명", className: "min-w-36 text-left" },
  { key: "number", label: "등번호", className: "w-16 text-center" },
  { key: "position", label: "포지션", className: "w-16 text-center" },
  { key: "nationality", label: "국적", className: "min-w-32 text-left" },
  { key: "appearances", label: "출전", className: "w-14 text-right" },
  { key: "goals", label: "득점", className: "w-14 text-right" },
  { key: "assists", label: "도움", className: "w-14 text-right" },
];

/**
 * TEAM-002 (2026-11-18, Figma 52:1483 표 470:6667, 대회별 기록 469:6642, mobile 58:356): the
 * current squad, one row per player, with this season's total for this team in the supported
 * competitions (five leagues + Champions League · Europa League · Conference League). Every
 * column but the photo and the detail button sorts; position order by default. Ten rows,
 * then "선수 더 보기". A row's detail button opens its per-competition record; ratings exist
 * per competition only (no combined rating). Missing values are "—", never 0; a played
 * competition without collected records marks the totals "부분 집계".
 */
export function SquadTable({ teamId }: { teamId: number }) {
  const query = useQuery(teamSquadQuery(teamId));
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [expanded, setExpanded] = useState(false);
  // The dialog stays mounted and only opens/closes, so its own focus return brings focus back
  // to the row's detail button (Codex 1차 지적 2); the last player stays as its content.
  const [detail, setDetail] = useState<{ player: SquadPlayer; open: boolean } | null>(null);
  const squad = query.data?.data;
  const players = squad ? sortPlayers(squad.players, sort) : [];
  const shown = expanded ? players : players.slice(0, PLAYERS_SHOWN);
  const refreshFailed = Boolean(query.data?.meta.refreshFailed) || query.isError;
  const retry = () => void query.refetch();
  const season = squad ? seasonText(squad.season.label) : "";
  const missing = squad?.missingCompetitions ?? [];
  const partial =
    missing.length > 0 ||
    players.some((p) => p.totals && Object.values(p.totals).some((value) => value === null));
  const emptyTitle = "선수단 정보가 없습니다";
  const emptyDescription = "제공된 현재 선수단이 없습니다.";

  return (
    <section aria-labelledby="team-players" className={AREA}>
      <div className="flex flex-col gap-1">
        <h2 id="team-players" className="text-title font-bold">선수단</h2>
        <p className="flex flex-wrap items-center gap-2 text-small text-fg-secondary">
          <span>{season} 지원 대회 합계</span>
          {partial && <Badge tone="warning">부분 집계</Badge>}
        </p>
        <p className="text-caption text-action">상세 버튼을 누르면 대회별 기록을 볼 수 있습니다</p>
      </div>
      <DataState
        status={dataStatus(query, players.length === 0, refreshFailed)}
        error={query.error}
        onRetry={retry}
        retryLabel="다시 시도"
        errorTitle="선수단 정보를 불러오지 못했습니다"
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        partialNotice="선수단 또는 선수 기록을 다시 확인하지 못했습니다. 마지막으로 확인한 정보입니다."
        partialAction={<Button onClick={retry}>다시 시도</Button>}
        loadingFallback={
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} className="h-11" />
            ))}
          </div>
        }
      >
        {players.length === 0 ? (
          // A failed re-check of an empty squad: the empty wording inside the partial frame.
          <StateMessage title={emptyTitle} description={emptyDescription} />
        ) : (
          <div className="flex flex-col gap-3">
            {missing.length > 0 && (
              <p className="rounded-control bg-subtle px-3 py-2 text-small text-fg-secondary">
                {missing.map(competitionName).join(" · ")} 기록을 아직 확인하지 못해 합계에서 빠져 있습니다.
              </p>
            )}
            <p className="text-small text-fg-muted lg:hidden">↔ 좌우로 밀어 보기 · 열 제목을 눌러 정렬</p>
            {/* Only the table scrolls sideways on phones; the page itself never does. */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] border-collapse text-label">
                <caption className="sr-only">
                  현재 선수단과 {season} 지원 대회 합계, {sortCaption(sort)}
                </caption>
                <thead>
                  <tr className="bg-subtle text-small text-fg-secondary">
                    <th scope="col" className="w-12 min-w-12 px-2 py-2 text-left font-medium whitespace-nowrap">
                      사진
                    </th>
                    {COLUMNS.map((column) => (
                      <th
                        key={column.key}
                        scope="col"
                        aria-sort={sort.key === column.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                        className={cx("px-1 py-1 font-medium", column.className)}
                      >
                        <button
                          type="button"
                          onClick={() => setSort(nextSort(sort, column.key))}
                          className={cx(
                            "inline-flex min-h-11 items-center gap-1 rounded-control px-1 whitespace-nowrap hover:text-fg",
                            sort.key === column.key && "font-bold text-fg",
                          )}
                        >
                          {column.label}
                          <span aria-hidden className="w-2">
                            {sort.key === column.key ? (sort.dir === "asc" ? "↑" : "↓") : ""}
                          </span>
                        </button>
                      </th>
                    ))}
                    <th scope="col" className="w-12 px-1 py-2 text-center font-medium">
                      상세
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((row) => (
                    <tr key={row.player.id} className="border-b border-line">
                      <td className="min-w-12 px-2 py-2">
                        <PlayerPhoto src={row.player.photoUrl} name={row.player.name} size={28} />
                      </td>
                      <th scope="row" className="px-2 py-2 text-left font-medium text-fg">
                        {row.player.name}
                      </th>
                      <td className="px-1 py-2 text-center tabular-nums">{statText(row.number)}</td>
                      <td className="px-1 py-2 text-center">{positionLabel(row.position)}</td>
                      <td className="px-2 py-2">
                        <Nationality name={row.nationality} flagUrl={row.flagUrl} />
                      </td>
                      <td className="px-2 py-2 text-right tabular-nums">{statText(row.totals?.appearances)}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{statText(row.totals?.goals)}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{statText(row.totals?.assists)}</td>
                      <td className="px-1 py-1 text-center">
                        <button
                          type="button"
                          onClick={() => setDetail({ player: row, open: true })}
                          aria-label={`${row.player.name} 대회별 기록`}
                          className="inline-flex size-11 items-center justify-center rounded-control text-action hover:bg-subtle"
                        >
                          <DetailIcon />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!expanded && players.length > PLAYERS_SHOWN && (
              <Button fullWidth onClick={() => setExpanded(true)}>
                선수 더 보기 · {players.length - PLAYERS_SHOWN}명
              </Button>
            )}
          </div>
        )}
      </DataState>
      <p className="text-caption text-fg-muted">
        제공되지 않은 기록은 —로 표시합니다. 국내 컵·클럽 월드컵·친선 경기는 합계에 넣지 않습니다.
      </p>
      {detail && (
        <Dialog
          open={detail.open}
          onClose={() => setDetail({ ...detail, open: false })}
          title={`${detail.player.player.name} · 대회별 기록`}
          layout="center"
          width={352}
        >
          <CompetitionLines player={detail.player} season={season} />
        </Dialog>
      )}
    </section>
  );
}

/** Flag before the API's nationality; no flag → text only; no nationality → "—". */
function Nationality({ name, flagUrl }: { name: string | null; flagUrl: string | null }) {
  const [failed, setFailed] = useState(false);
  if (!name) return <span className="text-fg-muted">{MISSING}</span>;
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      {flagUrl && !failed && (
        <Image
          src={flagUrl}
          alt=""
          width={20}
          height={14}
          unoptimized
          onError={() => setFailed(true)}
          style={{ width: 20, height: 14 }}
          className="shrink-0 object-cover"
        />
      )}
      {name}
    </span>
  );
}

/** Figma 469:6642: one row per supported competition the player has a record in. */
function CompetitionLines({ player, season }: { player: SquadPlayer; season: string }) {
  const lines = player.competitions;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-small text-fg-secondary">{season} · 현재 소속 팀 기록</p>
      {lines.length === 0 ? (
        <p className="py-4 text-center text-body text-fg-secondary">이번 시즌 지원 대회 기록이 없습니다.</p>
      ) : (
        <table className="w-full border-collapse text-label">
          <caption className="sr-only">{player.player.name} 대회별 기록</caption>
          <thead>
            <tr className="text-small text-fg-secondary">
              <th scope="col" className="py-2 text-left font-medium">대회</th>
              <th scope="col" className="w-12 py-2 text-right font-medium">출전</th>
              <th scope="col" className="w-12 py-2 text-right font-medium">득점</th>
              <th scope="col" className="w-12 py-2 text-right font-medium">도움</th>
              <th scope="col" className="w-12 py-2 text-right font-medium">평점</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.competition.id} className="border-t border-line">
                <th scope="row" className="py-3 text-left font-normal text-fg">
                  {competitionName(line.competition)}
                </th>
                <td className="py-3 text-right tabular-nums">{statText(line.appearances)}</td>
                <td className="py-3 text-right tabular-nums">{statText(line.goals)}</td>
                <td className="py-3 text-right tabular-nums">{statText(line.assists)}</td>
                <td className="py-3 text-right tabular-nums">{ratingText(line.rating)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="text-caption text-fg-muted">평점은 대회별 제공값입니다.</p>
    </div>
  );
}

function DetailIcon() {
  return (
    <svg aria-hidden width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z" strokeLinejoin="round" />
      <path d="M5 6h6M5 8.25h4" strokeLinecap="round" />
    </svg>
  );
}

function sortCaption(sort: SortState): string {
  const label = COLUMNS.find((column) => column.key === sort.key)?.label ?? "";
  return `${label} ${sort.dir === "asc" ? "오름차순" : "내림차순"} 정렬`;
}
