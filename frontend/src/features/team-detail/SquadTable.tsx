"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PlayerPhoto } from "@/components/common/TeamCrest";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { dataStatus } from "@/features/standings/model";
import { MISSING } from "@/lib/format/kst";
import { competitionName } from "@/lib/format/match";
import {
  DEFAULT_SORT,
  PLAYERS_SHOWN,
  nextSort,
  positionLabel,
  ratingText,
  sortPlayers,
  statText,
  type SortKey,
  type SortState,
} from "./model";
import { teamSquadQuery } from "./queries";
import { AREA } from "./TeamMatches";

const COLUMNS: readonly { key: SortKey; label: string; className: string }[] = [
  { key: "number", label: "번호", className: "w-14 text-center" },
  { key: "name", label: "이름", className: "min-w-36 text-left" },
  { key: "position", label: "포지션", className: "w-16 text-center" },
  { key: "nationality", label: "국적", className: "min-w-24 text-center" },
  { key: "appearances", label: "출전", className: "w-14 text-center" },
  { key: "goals", label: "득점", className: "w-14 text-center" },
  { key: "assists", label: "도움", className: "w-14 text-center" },
  { key: "rating", label: "평점", className: "w-14 text-center" },
];

/**
 * TEAM-002 (Figma 52:1483, mobile 58:356): the current squad joined with this season's league
 * record, one row per player (a player's line at another club is never added). Every column but
 * the photo sorts; position order by default. Ten rows, then "선수 더 보기" shows everyone.
 * A missing number, nationality or record is "—", never 0.
 */
export function SquadTable({ teamId }: { teamId: number }) {
  const query = useQuery(teamSquadQuery(teamId));
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [expanded, setExpanded] = useState(false);
  const squad = query.data?.data;
  const players = squad ? sortPlayers(squad.players, sort) : [];
  const shown = expanded ? players : players.slice(0, PLAYERS_SHOWN);
  const refreshFailed = Boolean(query.data?.meta.refreshFailed) || query.isError;
  const retry = () => void query.refetch();
  const league = squad ? competitionName(squad.league) : "리그";
  const emptyTitle = "선수단 정보가 없습니다";
  const emptyDescription = "제공된 현재 선수단이 없습니다.";

  return (
    <section aria-labelledby="team-players" className={AREA}>
      <div className="flex flex-col gap-1">
        <h2 id="team-players" className="text-title font-bold">선수</h2>
        <p className="text-small text-fg-secondary">현재 선수단 + 이번 시즌 기록</p>
      </div>
      <DataState
        status={dataStatus(query, players.length === 0, refreshFailed)}
        error={query.error}
        onRetry={retry}
        errorTitle="선수 정보를 불러오지 못했습니다"
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        partialNotice="선수단을 다시 확인하지 못했습니다. 마지막으로 확인한 선수단입니다."
        partialAction={<Button onClick={retry}>다시 확인</Button>}
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
            <p className="text-small text-fg-muted lg:hidden">↔ 좌우로 밀어 기록 보기 · 열 제목을 눌러 정렬</p>
            <div className="-mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0">
              <table className="w-full min-w-[640px] border-collapse text-label">
                <caption className="sr-only">
                  현재 선수단과 이번 시즌 {league} 기록, {sortCaption(sort)}
                </caption>
                <thead>
                  <tr className="bg-subtle text-small text-fg-secondary">
                    <th scope="col" className="w-11 px-2 py-2 font-medium">
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
                            "inline-flex min-h-11 items-center gap-1 rounded-control px-1 hover:text-fg",
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
                  </tr>
                </thead>
                <tbody>
                  {shown.map((row) => (
                    <tr key={row.player.id} className="border-b border-line">
                      <td className="px-2 py-2">
                        <PlayerPhoto src={row.player.photoUrl} name={row.player.name} size={28} />
                      </td>
                      <td className="px-1 py-2 text-center">{statText(row.number)}</td>
                      <th scope="row" className="px-1 py-2 text-left font-medium text-fg">
                        {row.player.name}
                      </th>
                      <td className="px-1 py-2 text-center">{positionLabel(row.position)}</td>
                      <td className="px-1 py-2 text-center">{row.nationality ?? MISSING}</td>
                      <td className="px-1 py-2 text-center">{statText(row.stats?.appearances)}</td>
                      <td className="px-1 py-2 text-center">{statText(row.stats?.goals)}</td>
                      <td className="px-1 py-2 text-center">{statText(row.stats?.assists)}</td>
                      <td className={cx("px-1 py-2 text-center", row.stats?.rating != null && "font-medium text-action")}>
                        {ratingText(row.stats?.rating)}
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
        제공되지 않은 기록은 —로 표시합니다. 시즌 기록은 {league} 경기 기준입니다.
      </p>
    </section>
  );
}

function sortCaption(sort: SortState): string {
  const label = COLUMNS.find((column) => column.key === sort.key)?.label ?? "";
  return `${label} ${sort.dir === "asc" ? "오름차순" : "내림차순"} 정렬`;
}
