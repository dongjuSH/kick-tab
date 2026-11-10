"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { ChipLabel, chipClass } from "@/components/ui/chip";
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
  const chips = useRef<HTMLDivElement>(null);

  // Figma 306:6221: the five leagues scroll sideways to Ligue 1. Touch scrolls natively; with
  // a mouse the row is dragged (press and move), and the wheel moves it too until an end. A
  // drag never selects the chip it started on.
  useEffect(() => {
    const row = chips.current;
    if (!row) return;
    const onWheel = (event: WheelEvent) => {
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      const max = row.scrollWidth - row.clientWidth;
      if (max <= 0) return;
      const next = Math.min(max, Math.max(0, row.scrollLeft + event.deltaY));
      if (next === row.scrollLeft) return;
      event.preventDefault();
      row.scrollLeft = next;
    };
    let drag: { x: number; left: number; moved: boolean } | null = null;
    let suppressClick = false;
    const onDown = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || event.button !== 0) return;
      drag = { x: event.clientX, left: row.scrollLeft, moved: false };
    };
    const onMove = (event: PointerEvent) => {
      if (!drag) return;
      const dx = event.clientX - drag.x;
      if (!drag.moved && Math.abs(dx) < 5) return;
      drag.moved = true;
      row.scrollLeft = drag.left - dx;
    };
    const onUp = () => {
      suppressClick = Boolean(drag?.moved);
      drag = null;
    };
    const onClick = (event: MouseEvent) => {
      if (!suppressClick) return;
      suppressClick = false;
      event.preventDefault();
      event.stopPropagation();
    };
    row.addEventListener("wheel", onWheel, { passive: false });
    row.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    row.addEventListener("click", onClick, true);
    return () => {
      row.removeEventListener("wheel", onWheel);
      row.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      row.removeEventListener("click", onClick, true);
    };
  }, []);
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
          // Figma 306:6221: name over "경기 10 · 8승 2무 0패", points on the right.
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
        5대 리그 순위
      </h2>
      <div ref={chips} className="-mx-1 overflow-x-auto px-1 py-1 select-none [scrollbar-width:none]" role="group" aria-label="리그 선택">
        <div className="flex w-max gap-[9px]">
          {LEAGUES.map((l) => (
            <button
              key={l.id}
              type="button"
              aria-pressed={league === l.id}
              className={chipClass(league === l.id)}
              onClick={(event) => {
                setLeague(l.id);
                event.currentTarget.scrollIntoView({ block: "nearest", inline: "nearest" });
              }}
            >
              <ChipLabel>{l.chip}</ChipLabel>
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
