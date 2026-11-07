"use client";

import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { dataStatus } from "@/features/standings/model";
import type { TransferHalf, TransferItem } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import {
  SEASON_TABS,
  notStartedText,
  seasonOf,
  seasonRows,
  standingText,
  transferTypeText,
  type SeasonChoice,
} from "./model";
import { teamSeasonStatsQuery, teamTransfersQuery } from "./queries";
import { AREA } from "./TeamMatches";

/**
 * Right column (Figma 52:1254) / mobile "기록" tab (58:738): the season record (TEAM-005) and
 * transfers (TEAM-006), each with its own 이번 시즌 / 지난 시즌 switch in the same format.
 */
export function SeasonRecords({
  teamId,
  currentSeason,
  statsSeason,
  transferSeason,
  onStatsSeason,
  onTransferSeason,
}: {
  teamId: number;
  currentSeason: number;
  statsSeason: SeasonChoice;
  transferSeason: SeasonChoice;
  onStatsSeason: (value: SeasonChoice) => void;
  onTransferSeason: (value: SeasonChoice) => void;
}) {
  return (
    <section aria-label="시즌 기록과 이적" className={AREA}>
      <div className="flex flex-col gap-3">
        <h2 id="team-season" className="text-title font-bold">시즌 기록</h2>
        <Tabs items={SEASON_TABS} value={statsSeason} onChange={onStatsSeason} label="시즌 기록 시즌" idBase="team-stats" />
        <div role="tabpanel" id={tabPanelId("team-stats", statsSeason)} aria-labelledby={tabId("team-stats", statsSeason)}>
          <SeasonStats teamId={teamId} season={seasonOf(statsSeason, currentSeason)} last={statsSeason === "last"} />
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <h2 id="team-transfers" className="text-title font-bold">이적</h2>
        <Tabs
          items={SEASON_TABS}
          value={transferSeason}
          onChange={onTransferSeason}
          label="이적 시즌"
          idBase="team-transfer"
        />
        <div
          role="tabpanel"
          id={tabPanelId("team-transfer", transferSeason)}
          aria-labelledby={tabId("team-transfer", transferSeason)}
        >
          <Transfers teamId={teamId} season={seasonOf(transferSeason, currentSeason)} />
        </div>
      </div>
    </section>
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

function SeasonStats({ teamId, season, last }: { teamId: number; season: number; last: boolean }) {
  const query = useQuery(teamSeasonStatsQuery(teamId, season));
  const data = query.data?.data;
  const retry = () => void query.refetch();
  const empty = data?.status === "not_provided";
  return (
    <DataState
        status={dataStatus(query, empty, Boolean(query.data?.meta.refreshFailed) || query.isError)}
        error={query.error}
        onRetry={retry}
        errorTitle="시즌 기록을 불러오지 못했습니다"
        // Figma 57:836 promoted: no league record that season (never another season's).
        emptyTitle={last ? "지난 시즌 리그 기록이 없습니다" : "이번 시즌 리그 기록이 아직 없습니다"}
        emptyDescription="다른 시즌의 기록으로 대신 표시하지 않습니다."
        partialNotice="시즌 기록을 다시 확인하지 못했습니다. 마지막으로 확인한 기록입니다."
        partialAction={<Button onClick={retry}>다시 확인</Button>}
        loadingFallback={<AreaSkeleton />}
      >
        {data?.record ? (
          <dl className="flex flex-col gap-3">
            {[{ label: "리그 순위", value: standingText(data.standing ?? null) }, ...seasonRows(data.record)].map((row) => (
              <div key={row.label} className="flex gap-4">
                <dt className="w-20 shrink-0 text-small text-fg-muted">{row.label}</dt>
                <dd className="text-label font-medium text-fg">{row.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          empty && (
            <StateMessage
              title={last ? "지난 시즌 리그 기록이 없습니다" : "이번 시즌 리그 기록이 아직 없습니다"}
              description="다른 시즌의 기록으로 대신 표시하지 않습니다."
            />
          )
        )}
    </DataState>
  );
}

function Transfers({ teamId, season }: { teamId: number; season: number }) {
  const query = useQuery(teamTransfersQuery(teamId, season));
  const data = query.data?.data;
  const retry = () => void query.refetch();
  return (
    <DataState
      status={dataStatus(query, false, Boolean(query.data?.meta.refreshFailed) || query.isError)}
      error={query.error}
      onRetry={retry}
      errorTitle="이적 정보를 불러오지 못했습니다"
      partialNotice="이적 기록을 다시 확인하지 못했습니다. 마지막으로 확인한 기록입니다."
      partialAction={<Button onClick={retry}>다시 확인</Button>}
      loadingFallback={<AreaSkeleton />}
    >
      {data && (
        <div className="flex flex-col gap-5">
          {data.halves.map((half) => (
            <Half key={half.half} half={half} />
          ))}
        </div>
      )}
    </DataState>
  );
}

/** One half: "26-27 전반기 · 2026년 6~12월", arrivals and departures by date. */
function Half({ half }: { half: TransferHalf }) {
  const title = `${half.label} · ${half.period}`;
  if (half.state === "not_started") {
    return (
      <p className="flex flex-col gap-1 rounded-control bg-subtle px-3 py-3 text-small text-fg-secondary">
        <span>{title}</span>
        <span>{notStartedText(half.start)}</span>
      </p>
    );
  }
  if (!half.arrivals.length && !half.departures.length) {
    return (
      <StateMessage className="py-4" title="이적 기록이 없습니다" description={title} />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-body font-bold text-fg">{title}</h3>
      <MoveList label="영입" items={half.arrivals} />
      <MoveList label="방출" items={half.departures} />
    </div>
  );
}

function MoveList({ label, items }: { label: string; items: TransferItem[] }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-label font-medium text-action">{label}</h4>
      {items.length ? (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={`${item.playerId}-${item.transferDate}-${item.counterpart.id}`} className="flex flex-col gap-0.5">
              <span className="text-label font-bold text-fg">
                {item.playerName} · {item.counterpart.name ?? MISSING}
              </span>
              <span className="text-caption text-fg-muted">
                {item.transferDate} · {transferTypeText(item.type)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-small text-fg-muted">{label} 기록 없음</p>
      )}
    </div>
  );
}
