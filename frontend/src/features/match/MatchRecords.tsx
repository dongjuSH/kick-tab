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
import { MISSING, formatKstTime } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";
import { EventIcon } from "./icons";
import { eventKind, eventText, minuteText, positionText, statLabel, statShares, statValue } from "./model";
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
  // Latest first, each record with its icon and text (MAT-002, Figma 52:151).
  return (
    <ol>
      {[...events].reverse().map((event, index) => (
        <li key={index} className="flex items-center gap-3 border-b border-line py-3 first:pt-0 lg:gap-4">
          <span className="w-13 shrink-0 text-center text-label font-bold text-action">{minuteText(event)}</span>
          <span className="grid size-4 shrink-0 place-items-center">
            <EventIcon kind={eventKind(event)} />
          </span>
          <span className="min-w-0 text-body text-fg">{eventText(event, names)}</span>
        </li>
      ))}
    </ol>
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

function RatingCard({ name, players }: { name: string; players: PlayerRating[] }) {
  return (
    <section className="flex min-w-0 flex-col rounded-control bg-canvas p-3">
      <div className="flex items-baseline justify-between gap-2 pb-2">
        <h3 className="min-w-0 text-body font-bold text-fg">{name}</h3>
        <span className="text-caption text-fg-muted" aria-hidden>평점</span>
      </div>
      {players.length ? (
        <ol aria-label={`${name} 선수 평점, 높은 순`}>
          {players.map((player, index) => (
            <li
              key={`${player.playerId}-${index}`}
              className="flex items-center gap-2 border-b border-line py-1.5 text-body last:border-b-0"
            >
              <PlayerPhoto src={player.photoUrl} name={player.name} size={20} />
              <span className="min-w-0 flex-1 text-fg">{player.name}</span>
              <span className="font-bold text-action">
                <span className="sr-only">평점 </span>
                {player.rating === null ? MISSING : player.rating.toFixed(1)}
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="py-1.5 text-small text-fg-muted">제공된 선수 평점이 없습니다.</p>
      )}
    </section>
  );
}

/** Provider player ratings by team, home left and away right on PC (Figma 94:4418). */
function Ratings({ players, names }: { players: PlayerRating[]; names: Names }) {
  const sides = ["home", "away"] as const;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 lg:grid-cols-2 lg:items-start">
        {sides.map((side) => (
          <RatingCard key={side} name={names[side]} players={players.filter((p) => p.side === side)} />
        ))}
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
 * Match records (MAT-002·004, Figma 52:151 / 161:4161, mobile 52:404 / 161:5190).
 * Live and finished matches: four tabs; abandoned matches: timeline only. A missing block
 * says so in its tab (domestic cups often have goals only). Shown from kickoff on only:
 * before kickoff there is no lineup area and no request (MAT-004 rule 4). While live the
 * header shows when the records were last updated.
 *
 * Refresh follows the match query only (`infoUpdatedAt` = its last successful update):
 * one read per update while live, one read when the status changes (kickoff, finish,
 * stop, resume). There is no second timer, so a finish never reads the record twice.
 */
export function MatchRecords({
  info,
  infoUpdatedAt,
  tab,
  onTab,
}: {
  info: MatchInfo;
  infoUpdatedAt: number;
  tab: RecordTab;
  onTab: (tab: RecordTab) => void;
}) {
  const query = useQuery(matchRecordsQuery(info.match));
  const status = info.match.status;
  const seen = useRef({ status, infoUpdatedAt });
  const { refetch } = query;
  useEffect(() => {
    const before = seen.current;
    if (before.status === status && before.infoUpdatedAt === infoUpdatedAt) return;
    seen.current = { status, infoUpdatedAt };
    if (before.status !== status) {
      // Keep the cached blocks visible; a read already running may predate the change.
      void refetch();
    } else if (status === "live") {
      void refetch({ cancelRefetch: false });
    }
  }, [status, infoUpdatedAt, refetch]);
  const idBase = useId();
  const names = { home: teamName(info.match.home), away: teamName(info.match.away) };
  const retry = () => void query.refetch();

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
  const updatedAt = query.data.meta.updatedAt;

  return (
    <section className={cx(CARD, "gap-0")} aria-labelledby={`${idBase}-title`}>
      <div className="flex items-baseline justify-between gap-3 pb-3">
        <h2 id={`${idBase}-title`} className="text-subtitle font-bold">경기 기록</h2>
        {info.match.status === "live" && updatedAt && (
          <p className="text-small text-fg-muted">{`마지막 갱신 ${formatKstTime(updatedAt)}`}</p>
        )}
      </div>
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
