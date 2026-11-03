"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef } from "react";
import { PlayerPhoto } from "@/components/common/TeamCrest";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import type {
  BlockStatus,
  MatchEvent,
  MatchInfo,
  MatchRecords as Records,
  PlayerRating,
  StatRow,
  TeamLineup,
} from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";
import { eventText, minuteText, positionText, statLabel, statShares, statValue } from "./model";
import { matchRecordsQuery } from "./queries";

export const RECORD_TABS = [
  { value: "timeline", label: "타임라인" },
  { value: "stats", label: "팀 통계" },
  { value: "lineups", label: "라인업" },
  { value: "ratings", label: "선수 평점" },
] as const;
export type RecordTab = (typeof RECORD_TABS)[number]["value"];

const BLOCK_OF: Record<RecordTab, keyof Records> = {
  timeline: "events",
  stats: "statistics",
  lineups: "lineups",
  ratings: "players",
};
const BLOCK_NAME: Record<RecordTab, string> = {
  timeline: "타임라인",
  stats: "팀 통계",
  lineups: "라인업",
  ratings: "선수 평점",
};

const CARD = "flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6";

interface Names {
  home: string;
  away: string;
}

function BlockMessage({ tab, status, onRetry }: { tab: RecordTab; status: BlockStatus; onRetry: () => void }) {
  if (status === "unavailable") {
    return (
      <StateMessage
        tone="error"
        title="기록을 불러오지 못했습니다"
        description="잠시 후 다시 확인해 주세요. 다른 영역은 계속 볼 수 있습니다."
        action={<Button onClick={onRetry}>다시 확인</Button>}
      />
    );
  }
  if (status === "not_yet") {
    return tab === "lineups" ? (
      <StateMessage title="라인업 발표 전" description="선발 명단이 발표되면 확인할 수 있습니다." />
    ) : (
      <StateMessage title="경기 시작 후 제공됩니다" />
    );
  }
  return (
    <StateMessage
      title="제공되지 않는 정보입니다"
      description={`이 경기는 데이터 제공사가 ${BLOCK_NAME[tab]} 정보를 제공하지 않습니다.`}
    />
  );
}

function Timeline({ events, names }: { events: MatchEvent[]; names: Names }) {
  if (events.length === 0) return <StateMessage title="아직 기록된 이벤트가 없습니다" />;
  // Latest first (Figma 52:257…).
  return (
    <div className="flex flex-col">
      <ol>
        {[...events].reverse().map((event, index) => (
          <li key={index} className="flex items-center gap-4 border-b border-line py-4 first:pt-0">
            <span className="w-13 shrink-0 text-center text-label font-bold text-action">{minuteText(event)}</span>
            <span className="min-w-0 text-body text-fg">{eventText(event, names)}</span>
          </li>
        ))}
      </ol>
      <p className="pt-3 text-small text-fg-muted">데이터 제공사가 전달한 이벤트만 표시합니다.</p>
    </div>
  );
}

function StatBar({ row }: { row: StatRow }) {
  const shares = statShares(row);
  if (!shares) return null;
  return (
    <div aria-hidden className="flex h-1 gap-1">
      <div className="rounded-full bg-action" style={{ flexGrow: shares.home, flexBasis: 0 }} />
      <div className="rounded-full bg-line-strong" style={{ flexGrow: shares.away, flexBasis: 0 }} />
    </div>
  );
}

function Statistics({ rows, names }: { rows: StatRow[]; names: Names }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between text-small font-bold">
        <span className="text-action">{names.home}</span>
        <span className="text-fg">{names.away}</span>
      </div>
      <dl className="flex flex-col gap-4">
        {rows.map((row) => (
          <div key={row.key} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <dd className="w-16 text-body font-bold text-action">{statValue(row.home, row.percent)}</dd>
              <dt className="min-w-0 flex-1 text-center text-small text-fg-secondary">{statLabel(row)}</dt>
              <dd className="w-16 text-right text-body font-bold text-fg">{statValue(row.away, row.percent)}</dd>
            </div>
            <StatBar row={row} />
          </div>
        ))}
      </dl>
    </div>
  );
}

function LineupCard({ lineup, name }: { lineup: TeamLineup; name: string }) {
  const subs = lineup.substitutes.map((p) => (p.number === null ? p.name : `${p.number} ${p.name}`));
  return (
    <section className="flex flex-col gap-3 rounded-control bg-canvas p-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-body font-bold text-fg">{name}</h3>
        <p className="text-small font-medium text-action">
          {`선발 ${lineup.startXi.length}명 · ${lineup.formation ?? "포메이션 미제공"}`}
        </p>
      </div>
      <ol className="flex flex-col border-t border-line pt-2">
        {lineup.startXi.map((player, index) => (
          <li key={`${player.name}-${index}`} className="flex items-center gap-3 py-1.5 text-body">
            <span className="w-6 shrink-0 text-small text-fg-muted">{player.number ?? MISSING}</span>
            <span className="min-w-0 flex-1 text-fg">{player.name}</span>
            <span className="text-small text-fg-muted">{positionText(player.position)}</span>
          </li>
        ))}
      </ol>
      <div className="flex flex-col gap-1 border-t border-line pt-3 text-small text-fg-secondary">
        <p>
          <span className="text-fg-muted">교체 명단 </span>
          {subs.length ? subs.join(" · ") : MISSING}
        </p>
        <p>
          <span className="text-fg-muted">감독 </span>
          {lineup.coach ?? MISSING}
        </p>
      </div>
    </section>
  );
}

function Lineups({ lineups, names }: { lineups: TeamLineup[]; names: Names }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {lineups.map((lineup) => (
        <LineupCard key={lineup.side} lineup={lineup} name={names[lineup.side]} />
      ))}
    </div>
  );
}

function Ratings({ players, names }: { players: PlayerRating[]; names: Names }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h3 className="text-lead font-bold text-fg">선수 경기 평점</h3>
        <p className="text-small text-fg-secondary">
          데이터 제공사의 선수 평점입니다. 회원이 남기는 경기 평점과 별도로 표시됩니다.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[320px] text-left text-body">
          <thead className="bg-subtle text-small text-fg-muted">
            <tr>
              <th scope="col" className="px-2 py-2 font-normal">선수</th>
              <th scope="col" className="px-2 py-2 font-normal">팀</th>
              <th scope="col" className="px-2 py-2 text-right font-normal">평점</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player, index) => (
              <tr key={`${player.playerId}-${index}`} className="border-b border-line">
                <td className="px-2 py-3">
                  <span className="flex items-center gap-2">
                    <PlayerPhoto src={player.photoUrl} name={player.name} size={20} />
                    <span className="min-w-0 text-fg">{player.name}</span>
                  </span>
                </td>
                <td className="px-2 py-3 text-fg-secondary">{names[player.side]}</td>
                <td className="px-2 py-3 text-right font-bold text-action">
                  {player.rating === null ? MISSING : player.rating.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-small text-fg-muted">미제공 평점은 —로 표시합니다.</p>
    </div>
  );
}

function Panel({ tab, records, names, onRetry }: { tab: RecordTab; records: Records; names: Names; onRetry: () => void }) {
  const block = records[BLOCK_OF[tab]];
  if (block.status !== "available" || !block.data) {
    return <BlockMessage tab={tab} status={block.status} onRetry={onRetry} />;
  }
  switch (tab) {
    case "timeline":
      return <Timeline events={records.events.data ?? []} names={names} />;
    case "stats":
      return <Statistics rows={records.statistics.data ?? []} names={names} />;
    case "lineups":
      return <Lineups lineups={records.lineups.data ?? []} names={names} />;
    default:
      return <Ratings players={records.players.data ?? []} names={names} />;
  }
}

const loading = (
  <div className="flex flex-col gap-3">
    <Skeleton className="h-11 w-80" />
    <Skeleton className="h-5 w-full" />
    <Skeleton className="h-5 w-4/5" />
  </div>
);

/**
 * Match records (MAT-002·004, Figma 52:239 / 94:3748 / 94:4061 / 94:4418, mobile 59:*).
 * Live and finished matches: four tabs; abandoned matches: timeline only. Missing blocks
 * says so in its tab (domestic cups often have goals only). Before kickoff only the
 * lineup appears, as "라인업 발표 전" until it is announced (Figma 63:1909).
 */
export function MatchRecords({ info, tab, onTab }: { info: MatchInfo; tab: RecordTab; onTab: (tab: RecordTab) => void }) {
  const query = useQuery(matchRecordsQuery(info.match));
  const previousStatus = useRef(info.match.status);
  const { refetch } = query;
  useEffect(() => {
    if (previousStatus.current !== info.match.status) {
      previousStatus.current = info.match.status;
      // Keep the cached blocks visible, but fetch once on kickoff, finish, stop or resume.
      void refetch();
    }
  }, [info.match.status, refetch]);
  const idBase = useId();
  const names = { home: teamName(info.match.home), away: teamName(info.match.away) };
  const retry = () => void query.refetch();
  const beforeKickoff = info.match.status === "scheduled" || info.match.status === "postponed";

  if (!query.data) {
    return (
      <section className={CARD}>
        <DataState
          status={query.isPending ? "loading" : "error"}
          error={query.error}
          onRetry={retry}
          errorTitle="경기 기록을 불러오지 못했습니다"
          loadingFallback={loading}
        />
      </section>
    );
  }
  const records = query.data.data;

  // MAT-001: a stopped match exposes its provided timeline, not the other record tabs.
  if (info.match.status === "abandoned") {
    return (
      <section className={CARD} aria-label="경기 기록">
        <h2 className="text-subtitle font-bold">타임라인</h2>
        {query.isError && <RefreshFailure onRetry={retry} />}
        <Panel tab="timeline" records={records} names={names} onRetry={retry} />
      </section>
    );
  }

  if (beforeKickoff) {
    const lineups = records.lineups;
    return lineups.status === "available" && lineups.data ? (
      <section className={CARD} aria-labelledby={`${idBase}-lineup`}>
        <h2 id={`${idBase}-lineup`} className="text-subtitle font-bold">라인업</h2>
        {query.isError && <RefreshFailure onRetry={retry} />}
        <Lineups lineups={lineups.data} names={names} />
      </section>
    ) : (
      <section className="rounded-card bg-surface">
        {query.isError && <RefreshFailure onRetry={retry} />}
        <BlockMessage tab="lineups" status={lineups.status} onRetry={retry} />
      </section>
    );
  }

  const statuses = RECORD_TABS.map((t) => records[BLOCK_OF[t.value]].status);
  if (statuses.every((s) => s === "not_provided")) {
    return (
      <section className="flex flex-col gap-2 rounded-card bg-surface p-4 lg:p-6">
        {query.isError && <RefreshFailure onRetry={retry} />}
        <h2 className="text-lead font-bold">경기 기록 미제공</h2>
        <p className="text-body text-fg-secondary">제공되지 않은 타임라인·통계·라인업·선수 평점은 표시하지 않습니다.</p>
      </section>
    );
  }
  const partial = statuses.some((s) => s === "not_provided");

  return (
    <section className={cx(CARD, "gap-0")} aria-label="경기 기록">
      <Tabs items={RECORD_TABS} value={tab} onChange={onTab} label="경기 기록" idBase={idBase} />
      {query.isError && <RefreshFailure onRetry={retry} />}
      {partial && (
        <p className="mt-4 rounded-control bg-subtle px-3 py-2 text-small text-fg-secondary">
          일부 기록이 제공되지 않습니다. 확인된 정보는 계속 볼 수 있습니다.
        </p>
      )}
      <div
        role="tabpanel"
        id={tabPanelId(idBase, tab)}
        aria-labelledby={tabId(idBase, tab)}
        tabIndex={0}
        className="pt-4"
      >
        <Panel tab={tab} records={records} names={names} onRetry={retry} />
      </div>
    </section>
  );
}

function RefreshFailure({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="mt-3 rounded-control bg-warning-bg p-3 text-small text-warning">
      최신 기록으로 갱신하지 못했습니다. 마지막으로 확인한 기록을 보여줍니다.
      <Button variant="ghost" onClick={onRetry}>다시 확인</Button>
    </div>
  );
}
