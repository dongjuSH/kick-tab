"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { PlayerPhoto } from "@/components/common/TeamCrest";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import type { PlayerRankItem, RankingType } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { RANKING_TYPES, dataStatus, numberText, rankText } from "./model";
import { playerRankingsQuery } from "./queries";

const SHOWN = 10;
const ID_BASE = "player-ranking";
const HEAD = "h-10 px-2.5 text-left text-small font-medium text-fg-secondary";

/**
 * Player rankings of the selected league season (LEAG-004; Figma 53:1353 right card, states
 * 57:599). Goals / assists / yellow / red are the provider's top 20 in its order — not a full
 * ranking; red counts direct reds only. Saves are aggregated from every player record:
 * goalkeepers with a missing value are excluded and counted, equal totals share a rank.
 * Ten rows first, "더 보기" shows the rest; a new league, season or type starts at ten
 * (the parent remounts this per league and season).
 */
export function PlayerRankings({
  league,
  season,
  type,
  typeInvalid,
  onTypeChange,
}: {
  league: number;
  season: number | null;
  type: RankingType;
  typeInvalid: boolean;
  onTypeChange: (type: RankingType) => void;
}) {
  const [expandedType, setExpandedType] = useState<RankingType | null>(null);
  const ranking = useQuery({ ...playerRankingsQuery(league, season, type), enabled: !typeInvalid });
  const label = RANKING_TYPES.find((t) => t.value === type)?.label ?? "";
  const data = ranking.data?.data;
  const items = data?.items ?? [];
  const expanded = expandedType === type;
  const excluded = type === "saves" && data?.excluded ? data.excluded : 0;
  const emptyTitle = `${label} 순위 데이터가 없습니다`;
  const emptyDescription =
    type === "saves"
      ? `선방 값이 확인된 골키퍼가 없습니다.${excluded ? ` 기록이 누락된 골키퍼 ${excluded}명 제외.` : ""}`
      : "제공된 선수 순위가 없습니다.";

  const body = typeInvalid ? (
    // A condition the service does not offer: nothing is requested and nothing replaced.
    <StateMessage
      tone="error"
      title="조회 조건을 확인할 수 없습니다"
      description="주소의 선수 순위 유형이 올바르지 않습니다. 위에서 유형을 골라 주세요."
    />
  ) : (
    <DataState
      status={dataStatus(ranking, items.length === 0, Boolean(ranking.data?.meta.refreshFailed || ranking.isError))}
      loadingFallback={<ListSkeleton />}
      error={ranking.error}
      // 404 = an unsupported league or season: asking again cannot help.
      onRetry={isApiError(ranking.error) && ranking.error.status === 404 ? undefined : () => ranking.refetch()}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
      partialNotice="최신 순위로 갱신하지 못해 마지막으로 확인한 선수 순위를 표시합니다."
    >
      {items.length === 0 ? (
        // The last confirmed list was empty and a later refresh failed (partial).
        <StateMessage title={emptyTitle} description={emptyDescription} />
      ) : (
      <div className="flex flex-col gap-3">
        <table className="w-full border-collapse">
          <caption className="sr-only">{`${label} 순위`}</caption>
          <thead className="bg-subtle">
            <tr>
              <th scope="col" className={cx(HEAD, "w-[60px]")}>순위</th>
              <th scope="col" className={HEAD}>{type === "saves" ? "골키퍼 / 팀" : "선수 / 팀"}</th>
              <th scope="col" className={cx(HEAD, "w-14 text-right")}>{label}</th>
            </tr>
          </thead>
          <tbody>
            {(expanded ? items : items.slice(0, SHOWN)).map((item) => (
              <Row key={`${item.player.id}-${item.rank}`} item={item} />
            ))}
          </tbody>
        </table>
        {excluded > 0 && (
          <p className="rounded-control bg-subtle px-3 py-2.5 text-small text-fg-secondary">
            기록이 누락된 골키퍼 {excluded}명 제외 · 선방 값이 없는 선수를 0으로 넣지 않습니다.
          </p>
        )}
        {!expanded && items.length > SHOWN && (
          <Button fullWidth onClick={() => setExpandedType(type)}>
            더 보기 · {items.length}명
          </Button>
        )}
      </div>
      )}
    </DataState>
  );

  return (
    <section
      aria-labelledby="player-ranking-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <h2 id="player-ranking-title" className="text-subtitle font-bold">
        선수 순위
      </h2>
      <Tabs
        items={RANKING_TYPES}
        value={typeInvalid ? null : type}
        onChange={(next) => {
          setExpandedType(null);
          onTypeChange(next);
        }}
        label="선수 순위 유형"
        idBase={ID_BASE}
      />
      <div role="tabpanel" id={tabPanelId(ID_BASE, type)} aria-labelledby={tabId(ID_BASE, type)} className="flex flex-col gap-3">
        <p className="text-small text-fg-muted">
          {type === "saves"
            ? "리그 전체 선수 기록으로 집계한 골키퍼 선방 순위입니다."
            : "리그별 제공 상위 20명 · 전체 선수 순위가 아닙니다."}
          {type === "red" && " 직접 퇴장만 집계하며 경고 누적 퇴장은 합산하지 않습니다."}
        </p>
        {body}
      </div>
    </section>
  );
}

function Row({ item }: { item: PlayerRankItem }) {
  const team = item.team;
  return (
    <tr className="border-b border-line">
      <td className="h-[60px] px-2.5 text-body tabular-nums whitespace-nowrap">{rankText(item.rank, item.tied)}</td>
      <td className="px-2.5 py-2">
        <div className="flex items-center gap-2">
          <PlayerPhoto src={item.player.photoUrl} name={item.player.name} size={24} />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-body text-fg">{item.player.name}</span>
            {team === null ? (
              <span className="text-small text-fg-muted">—</span>
            ) : team.detailAvailable === true ? (
              <Link
                href={`/teams/${team.id}`}
                prefetch={false}
                className="truncate text-small text-fg-muted hover:text-action hover:underline"
              >
                {teamName(team)}
              </Link>
            ) : (
              <span className="truncate text-small text-fg-muted">{teamName(team)}</span>
            )}
          </div>
        </div>
      </td>
      <td className="px-2.5 text-right text-body font-bold text-action tabular-nums">{numberText(item.value)}</td>
    </tr>
  );
}
