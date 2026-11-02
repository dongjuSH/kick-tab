import Link from "next/link";
import { MatchStatusBadge } from "@/components/common/MatchStatusBadge";
import { Badge } from "@/components/ui/Badge";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import type { TopMatchItem, TopMatches } from "@/lib/api/types";
import { formatKstDateTime } from "@/lib/format/kst";
import { scoreText, teamName } from "@/lib/format/match";
import {
  NOTICES,
  POLICY_NOTICE,
  TOP5_MAX,
  changeText,
  kickoffText,
  noticeOf,
  weekText,
  type Top5Notice,
} from "./model";

type Top5Layout = "desktop" | "mobile";

/** One selected match (Figma TOP5 Row 126:141). The whole row opens the match detail. */
function Top5Row({ item, layout, onSelect }: { item: TopMatchItem; layout: Top5Layout; onSelect: () => void }) {
  const { match } = item;
  const change = changeText(match);
  const desktop = layout === "desktop";
  const teams = (
    <span className="flex min-w-0 flex-1 items-center gap-2 font-bold">
      <span className="min-w-0 flex-1 truncate text-body">{teamName(match.home)}</span>
      <span className="w-12 shrink-0 text-center text-lead">{scoreText(match)}</span>
      <span className="min-w-0 flex-1 truncate text-right text-body">{teamName(match.away)}</span>
    </span>
  );
  const kickoff = (
    <span className={cx("text-small text-fg-muted", desktop && "w-[216px] shrink-0")}>{kickoffText(match)}</span>
  );

  return (
    <li>
      <Link
        href={`/matches/${match.id}`}
        onClick={onSelect}
        className={cx(
          "flex flex-col rounded-control border border-line bg-surface hover:bg-subtle",
          desktop ? "gap-1 px-4 py-2" : "gap-2 p-3",
        )}
      >
        <span className="flex items-center gap-2">
          <Badge tone="accent">
            <span className="sr-only">순서 </span>
            {item.rank}
          </Badge>
          <span className="min-w-0 flex-1 truncate text-small text-fg-secondary">{match.competition.shortName}</span>
          <MatchStatusBadge match={match} size="small" />
        </span>
        {desktop ? (
          <span className="flex items-center gap-4">
            {kickoff}
            {teams}
          </span>
        ) : (
          <span className="flex flex-col gap-1">
            {kickoff}
            {teams}
          </span>
        )}
        <span className="text-small font-medium text-action">{item.reason}</span>
        {change && <span className="text-small font-medium text-warning">{change}</span>}
      </Link>
    </li>
  );
}

function NoticeBox({ notice }: { notice: Top5Notice }) {
  const copy = NOTICES[notice];
  const error = copy.tone === "error";
  return (
    <div
      role={error ? "alert" : "status"}
      className={cx("flex flex-col gap-2 rounded-control p-4", error ? "bg-error-bg" : "bg-canvas")}
    >
      <p className={cx("text-lead font-bold", error ? "text-error" : "text-fg")}>{copy.title}</p>
      <p className="text-label text-fg-secondary">{copy.description}</p>
      <p className="text-small text-fg-muted">{copy.note}</p>
    </div>
  );
}

function WeekLine({ data, layout }: { data: TopMatches; layout: Top5Layout }) {
  const selected = data.selectedAt && `선정 시각 ${formatKstDateTime(data.selectedAt)} KST`;
  return (
    <p className="whitespace-pre-wrap text-small text-fg-muted">
      {weekText(data)}
      {selected && (layout === "desktop" ? `  ·  ${selected}` : `\n${selected}`)}
    </p>
  );
}

interface Top5ListProps {
  data: TopMatches | undefined;
  isPending: boolean;
  error: unknown;
  onRetry: () => void;
  onSelect: () => void;
  layout: Top5Layout;
}

/**
 * Body of the expanded TOP 5 under its title (Figma 159:924, desktop panel / mobile sheet).
 * Only the match list scrolls; the week line, notes and the policy notice stay visible.
 */
export function Top5List({ data, isPending, error, onRetry, onSelect, layout }: Top5ListProps) {
  const notice = data && noticeOf(data);
  const count = data?.items.length ?? 0;

  return (
    <div className="flex min-h-0 flex-col gap-3">
      {!data ? (
        // Kept data stays on screen if a later refetch fails; only a first load shows these.
        <DataState
          status={isPending ? "loading" : "error"}
          error={error}
          onRetry={onRetry}
          errorTitle="주목 경기를 불러오지 못했습니다"
          loadingFallback={
            <div className="flex flex-col gap-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-[88px] w-full" />
              <Skeleton className="h-[88px] w-full" />
            </div>
          }
        />
      ) : (
        <>
          <WeekLine data={data} layout={layout} />
          {notice ? (
            <NoticeBox notice={notice} />
          ) : (
            <>
              <ol className="flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain">
                {data.items.map((item) => (
                  <Top5Row key={item.match.id} item={item} layout={layout} onSelect={onSelect} />
                ))}
              </ol>
              {count < TOP5_MAX && (
                <p className="text-small font-medium text-warning">
                  {`선정 당시 후보가 ${TOP5_MAX}개 미만이어서 실제 ${count}경기만 표시합니다.`}
                </p>
              )}
              <p className="text-small text-fg-muted">
                {layout === "desktop"
                  ? "경기 일시·상태·결과는 최신 정보로 표시합니다. 연기·취소되어도 선정 순서는 유지됩니다."
                  : "목록을 스크롤해 전체 경기를 확인하세요. 경기 정보는 최신으로 표시하고, 연기·취소되어도 선정 순서는 유지됩니다."}
              </p>
            </>
          )}
        </>
      )}
      <p className="rounded-control bg-canvas p-3 text-small text-fg-secondary">{POLICY_NOTICE}</p>
    </div>
  );
}
