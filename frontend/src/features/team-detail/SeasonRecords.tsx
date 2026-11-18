"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import { dataStatus } from "@/features/standings/model";
import type { TransferHalf, TransferItem } from "@/lib/api/types";
import { MISSING, kstParts, kstTodayIso } from "@/lib/format/kst";
import { competitionName } from "@/lib/format/match";
import {
  HALF_TABS,
  SEASON_TABS,
  currentHalf,
  dotDate,
  pickHalf,
  seasonOf,
  seasonRows,
  seasonText,
  standingText,
  transferTypeText,
  type HalfChoice,
  type SeasonChoice,
} from "./model";
import { teamSeasonStatsQuery, teamTransfersQuery } from "./queries";
import { AREA } from "./TeamMatches";

/**
 * Right column (Figma 52:1254) / mobile "기록" tab (58:738): the season record (TEAM-005) and
 * transfers (TEAM-006, 471:6856), two cards with the same 이번 시즌 / 지난 시즌 switch. The
 * seasons and the transfer half live in the URL (`stats=last`, `transfers=last`, `half=`).
 */
export function SeasonRecords({
  teamId,
  teamName,
  currentSeason,
  statsSeason,
  transferSeason,
  half,
  onStatsSeason,
  onTransferSeason,
  onHalf,
}: {
  teamId: number;
  teamName: string;
  currentSeason: number;
  statsSeason: SeasonChoice;
  transferSeason: SeasonChoice;
  half: HalfChoice | null;
  onStatsSeason: (value: SeasonChoice) => void;
  onTransferSeason: (value: SeasonChoice) => void;
  onHalf: (value: HalfChoice) => void;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
      <section aria-labelledby="team-season" className={AREA}>
        <h2 id="team-season" className="text-title font-bold">시즌 기록</h2>
        <SeasonSwitch value={statsSeason} onChange={onStatsSeason} label="시즌 기록 시즌" />
        <SeasonStats teamId={teamId} season={seasonOf(statsSeason, currentSeason)} />
      </section>
      <Transfers
        teamId={teamId}
        teamName={teamName}
        season={seasonOf(transferSeason, currentSeason)}
        current={transferSeason === "this"}
        choice={transferSeason}
        onSeason={onTransferSeason}
        half={half}
        onHalf={onHalf}
      />
    </div>
  );
}

/** Figma 이번 시즌 / 지난 시즌: two equal buttons, the selected one filled. */
function SeasonSwitch({
  value,
  onChange,
  label,
}: {
  value: SeasonChoice;
  onChange: (value: SeasonChoice) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} className="grid grid-cols-2 gap-2">
      {SEASON_TABS.map((tab) => {
        const selected = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(tab.value)}
            className={cx(
              "h-11 rounded-control border text-body",
              selected
                ? "border-action bg-action font-bold text-fg-inverse hover:bg-action-hover"
                : "border-line bg-surface text-fg hover:bg-subtle",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

function AreaSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-5 w-full" />
      <Skeleton className="h-5 w-2/3" />
      <Skeleton className="h-5 w-3/4" />
    </div>
  );
}

function SeasonStats({ teamId, season }: { teamId: number; season: number }) {
  const query = useQuery(teamSeasonStatsQuery(teamId, season));
  const data = query.data?.data;
  const retry = () => void query.refetch();
  const empty = data !== undefined && data.status !== "available";
  // Figma 57:836 promoted: no league record that season (never another season's).
  const emptyTitle =
    data?.status === "not_participated"
      ? `${seasonText(data.season.label)} 시즌에는 이 리그에 참가하지 않았습니다.`
      : "선택한 시즌의 기록이 없습니다.";
  return (
    <div className="flex flex-col gap-3">
      {data && (
        <p className="text-small text-fg-muted">
          {seasonText(data.season.label)} · {competitionName(data.league)} 정규 리그
        </p>
      )}
      <DataState
        status={dataStatus(query, empty, Boolean(query.data?.meta.refreshFailed) || query.isError)}
        error={query.error}
        onRetry={retry}
        retryLabel="다시 시도"
        errorTitle="시즌 기록을 불러오지 못했습니다"
        emptyTitle={emptyTitle}
        partialNotice="시즌 기록을 다시 확인하지 못했습니다. 마지막으로 확인한 기록입니다."
        partialAction={<Button onClick={retry}>다시 시도</Button>}
        loadingFallback={<AreaSkeleton />}
      >
        {data?.record ? (
          <dl className="flex flex-col">
            {[{ label: "리그 순위", value: standingText(data.standing ?? null) }, ...seasonRows(data.record)].map(
              (row) => (
                <div key={row.label} className="flex items-center justify-between gap-4 border-b border-line py-3 last:border-b-0">
                  <dt className="text-small text-fg-muted">{row.label}</dt>
                  <dd className="text-label font-medium text-fg">{row.value}</dd>
                </div>
              ),
            )}
          </dl>
        ) : (
          empty && <StateMessage title={emptyTitle} />
        )}
      </DataState>
    </div>
  );
}

function Transfers({
  teamId,
  teamName,
  season,
  current,
  choice,
  onSeason,
  half,
  onHalf,
}: {
  teamId: number;
  teamName: string;
  season: number;
  current: boolean;
  choice: SeasonChoice;
  onSeason: (value: SeasonChoice) => void;
  half: HalfChoice | null;
  onHalf: (value: HalfChoice) => void;
}) {
  const query = useQuery(teamTransfersQuery(teamId, season));
  const data = query.data?.data;
  const retry = () => void query.refetch();
  const updated = current && query.data?.meta.updatedAt ? kstParts(query.data.meta.updatedAt) : null;
  // Today's half is read only once the data is here (never in the server prerender).
  const selected = data ? pickHalf(half, data.halves, currentHalf(kstTodayIso())) : null;
  const shown = data?.halves.find((h) => h.half === selected) ?? null;
  const tabs = HALF_TABS.map((tab) => ({
    ...tab,
    disabled: data?.halves.find((h) => h.half === tab.value)?.state !== "open",
  }));

  return (
    <section aria-labelledby="team-transfers" className={AREA}>
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="team-transfers" className="text-title font-bold">이적</h2>
        {updated && (
          <span className="text-caption text-fg-muted">
            최근 갱신 {updated.year}.{String(updated.month).padStart(2, "0")}.{String(updated.day).padStart(2, "0")}
          </span>
        )}
      </div>
      <SeasonSwitch value={choice} onChange={onSeason} label="이적 시즌" />
      <DataState
        status={dataStatus(query, false, Boolean(query.data?.meta.refreshFailed) || query.isError)}
        error={query.error}
        onRetry={retry}
        retryLabel="다시 시도"
        errorTitle="이적 정보를 불러오지 못했습니다"
        partialNotice="이적 기록을 다시 확인하지 못했습니다. 마지막으로 확인한 기록입니다."
        partialAction={<Button onClick={retry}>다시 시도</Button>}
        loadingFallback={<AreaSkeleton />}
      >
        {data && selected && (
          <div className="flex flex-col gap-3">
            <Tabs
              items={tabs}
              value={selected}
              onChange={onHalf}
              label="이적 기간"
              idBase="team-half"
              trailing="후반기는 1월부터"
            />
            <div role="tabpanel" id={tabPanelId("team-half", selected)} aria-labelledby={tabId("team-half", selected)}>
              {shown && <Half key={`${season}-${shown.half}`} half={shown} teamName={teamName} />}
            </div>
          </div>
        )}
      </DataState>
    </section>
  );
}

/** One half: "26-27 전반기 · 2026년 6~12월", the moves shown first, then "기타 이동 N건". */
function Half({ half, teamName }: { half: TransferHalf; teamName: string }) {
  const [othersOpen, setOthersOpen] = useState(false);
  const others = half.otherArrivals.length + half.otherDepartures.length;
  const main = half.arrivals.length + half.departures.length;
  return (
    <div className="flex flex-col gap-4">
      <p className="text-caption text-fg-muted">
        {half.label} · {half.period}
      </p>
      {main + others === 0 ? (
        <StateMessage className="py-4" tone="plain" title="아직 확인된 이적이 없습니다" />
      ) : (
        <>
          {main > 0 ? (
            <>
              <MoveList label="영입" items={half.arrivals} teamName={teamName} direction="in" />
              <MoveList label="방출" items={half.departures} teamName={teamName} direction="out" />
            </>
          ) : (
            <p className="text-small text-fg-muted">주요 이적은 아직 없습니다.</p>
          )}
          {others > 0 && (
            <div className="flex flex-col gap-3 border-t border-line pt-3">
              <button
                type="button"
                aria-expanded={othersOpen}
                onClick={() => setOthersOpen((open) => !open)}
                className="flex min-h-11 items-center justify-between rounded-control text-label font-medium text-fg-secondary hover:text-fg"
              >
                기타 이동 {others}건
                <span aria-hidden>{othersOpen ? "▲" : "▼"}</span>
              </button>
              {othersOpen && (
                <>
                  <MoveList label="영입" items={half.otherArrivals} teamName={teamName} direction="in" />
                  <MoveList label="방출" items={half.otherDepartures} teamName={teamName} direction="out" />
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MoveList({
  label,
  items,
  teamName,
  direction,
}: {
  label: string;
  items: TransferItem[];
  teamName: string;
  direction: "in" | "out";
}) {
  if (!items.length) return null;
  return (
    <div className="flex flex-col">
      <h3 className="text-label font-medium text-action">{label}</h3>
      <ul className="flex flex-col">
        {items.map((item) => {
          const other = item.counterpart.name ?? MISSING;
          const route = direction === "in" ? `${other} → ${teamName}` : `${teamName} → ${other}`;
          return (
            <li
              key={`${item.playerId}-${item.transferDate}-${item.counterpart.id ?? item.counterpart.name}`}
              className="flex items-start justify-between gap-3 border-b border-line py-3 last:border-b-0"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <span className="text-body font-bold text-fg">{item.playerName}</span>
                <span className="text-caption text-fg-muted">
                  {dotDate(item.transferDate)} · {route}
                </span>
              </div>
              <span className="shrink-0 text-label font-medium text-action">{transferTypeText(item.type)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
