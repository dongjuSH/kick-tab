import Link from "next/link";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Badge } from "@/components/ui/Badge";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { TeamRef, TopMatchItem, TopMatches } from "@/lib/api/types";
import { MISSING, formatKstTime, formatPeriod } from "@/lib/format/kst";

export function teamName(team: TeamRef): string {
  return team.nameKo ?? team.nameEn;
}

export function scoreText(home: number | null, away: number | null): string {
  return home === null || away === null ? MISSING : `${home} : ${away}`;
}

/** "10/26(월)~11/1(일) · 종료 경기 3개" (Figma 62:1523). */
export function periodSummary(data: TopMatches): string | null {
  if (!data.period) return null;
  return `${formatPeriod(data.period.start, data.period.end)} · 종료 경기 ${data.items.length}개`;
}

function Top5Row({ item, onSelect }: { item: TopMatchItem; onSelect?: () => void }) {
  const { match } = item;
  const { score } = match;
  const hasPenalties = score.penaltyHome !== null && score.penaltyAway !== null;
  return (
    <li className="flex flex-col gap-4">
      <p className="text-lead font-bold text-action">{String(item.rank).padStart(2, "0")}</p>
      <Link
        href={`/matches/${match.id}`}
        onClick={onSelect}
        className="flex flex-col gap-2 rounded-control bg-surface p-3 hover:bg-subtle"
      >
        <span className="flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-caption text-fg-muted">
            {match.competition.shortName} · {formatKstTime(match.kickoffAt)}
          </span>
          {/* TOP 5 only ranks finished matches (TOP-001). */}
          <Badge tone="neutral">종료</Badge>
        </span>
        <span className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <span className="flex min-w-0 items-center justify-end gap-1.5">
            <span className="truncate text-right text-body font-medium">{teamName(match.home)}</span>
            <TeamCrest src={match.home.crestUrl} name={teamName(match.home)} />
          </span>
          <span className="flex w-10 flex-col items-center text-center">
            <span className="whitespace-nowrap text-lead font-bold">{scoreText(score.home, score.away)}</span>
            {hasPenalties && (
              <span className="whitespace-nowrap text-2xs text-fg-muted">
                PK {score.penaltyHome}:{score.penaltyAway}
              </span>
            )}
          </span>
          <span className="flex min-w-0 items-center gap-1.5">
            <TeamCrest src={match.away.crestUrl} name={teamName(match.away)} />
            <span className="truncate text-body font-medium">{teamName(match.away)}</span>
          </span>
        </span>
      </Link>
    </li>
  );
}

interface Top5ListProps {
  data: TopMatches | undefined;
  isPending: boolean;
  error: unknown;
  onRetry: () => void;
  onSelect?: () => void;
}

/** Expanded TOP 5 list shared by the desktop panel and the mobile sheet. */
export function Top5List({ data, isPending, error, onRetry, onSelect }: Top5ListProps) {
  const status = isPending ? "loading" : error ? "error" : !data?.items.length ? "empty" : "ready";
  const summary = data ? periodSummary(data) : null;
  return (
    <DataState
      status={status}
      error={error}
      onRetry={onRetry}
      errorTitle="인기 경기를 불러오지 못했습니다"
      emptyTitle="이번 주 인기 경기를 준비 중입니다"
      emptyDescription="지난주 순위를 이번 주 TOP 5로 보여주지 않습니다."
      loadingFallback={
        <div className="flex flex-col gap-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {summary && <p className="text-label text-fg-muted">{summary}</p>}
        <ol className="flex flex-col gap-4">
          {data?.items.map((item) => (
            <Top5Row key={item.match.id} item={item} onSelect={onSelect} />
          ))}
        </ol>
      </div>
    </DataState>
  );
}
