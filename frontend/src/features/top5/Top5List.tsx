import Link from "next/link";
import { TeamCrest } from "@/components/common/TeamCrest";
import { DataState } from "@/components/ui/DataState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import type { TeamRef, TopMatchItem, TopMatches } from "@/lib/api/types";
import { MISSING, formatKstMonthDayTime, formatPeriod } from "@/lib/format/kst";

export type Top5Layout = "desktop" | "mobile";

export function teamName(team: TeamRef): string {
  return team.nameKo ?? team.nameEn;
}

export function scoreText(home: number | null, away: number | null): string {
  return home === null || away === null ? MISSING : `${home} : ${away}`;
}

/** No ratings → "—", never "0" (rating aggregate rule). */
function averageText(item: TopMatchItem): string {
  return `평균 ${item.averageRating === null ? MISSING : item.averageRating.toFixed(1)} / 5`;
}

/** "10/26(월)~11/1(일) · 종료 경기 3개" or "… · 이번 주 선정 결과 없음" (Figma 128:3145·128:3674). */
export function periodSummary(data: TopMatches): string {
  const parts = data.period ? [formatPeriod(data.period.start, data.period.end)] : [];
  parts.push(data.items.length ? `종료 경기 ${data.items.length}개` : "이번 주 선정 결과 없음");
  return parts.join(" · ");
}

function footnote(count: number, layout: Top5Layout): string {
  if (layout === "mobile" && count > 3) return `목록을 스크롤해 전체 ${count}개 경기를 확인하세요.`;
  if (count >= 5) return "종료된 경기 중 최대 5개를 보여드립니다.";
  return `선정된 ${count}개 경기만 표시합니다.`;
}

function Score({ item, layout }: { item: TopMatchItem; layout: Top5Layout }) {
  const { score } = item.match;
  const hasPenalties = score.penaltyHome !== null && score.penaltyAway !== null;
  return (
    <span className={cx("flex shrink-0 flex-col items-center text-center", layout === "desktop" ? "w-20" : "w-16")}>
      <span
        className={cx(
          "whitespace-nowrap font-bold",
          layout === "desktop" ? "text-title" : "text-subtitle leading-[27px]",
        )}
      >
        {scoreText(score.home, score.away)}
      </span>
      {hasPenalties && (
        <span className="whitespace-nowrap text-2xs text-fg-muted">
          PK {score.penaltyHome}:{score.penaltyAway}
        </span>
      )}
    </span>
  );
}

function Teams({ item, layout }: { item: TopMatchItem; layout: Top5Layout }) {
  const { home, away } = item.match;
  const crest = layout === "desktop" ? 28 : 20;
  const name = cx("truncate font-bold", layout === "desktop" ? "text-body" : "text-label");
  return (
    <span className={cx("flex min-w-0 flex-1 items-center", layout === "desktop" ? "gap-3" : "gap-2")}>
      <span className="flex min-w-0 flex-1 items-center justify-end gap-1.5">
        <span className={cx(name, "text-right")}>{teamName(home)}</span>
        <TeamCrest src={home.crestUrl} name={teamName(home)} size={crest} />
      </span>
      <Score item={item} layout={layout} />
      <span className="flex min-w-0 flex-1 items-center gap-1.5">
        <TeamCrest src={away.crestUrl} name={teamName(away)} size={crest} />
        <span className={name}>{teamName(away)}</span>
      </span>
    </span>
  );
}

/** One ranked match (Figma component 126:111 desktop / 126:140 mobile). */
function Top5Row({ item, layout, onSelect }: { item: TopMatchItem; layout: Top5Layout; onSelect?: () => void }) {
  const { match } = item;
  const competition = (
    <span className="flex min-w-0 flex-col gap-0.5">
      <span className="truncate text-small text-fg-secondary">{match.competition.shortName}</span>
      <span className="text-caption text-fg-muted">{formatKstMonthDayTime(match.kickoffAt)}</span>
    </span>
  );

  if (layout === "desktop") {
    return (
      <li>
        <Link
          href={`/matches/${match.id}`}
          onClick={onSelect}
          className="flex items-center gap-4 rounded-control bg-surface p-4 hover:bg-subtle"
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-control bg-selected text-title font-bold text-action">
            {item.rank}
          </span>
          <span className="w-[180px] shrink-0">{competition}</span>
          <Teams item={item} layout="desktop" />
          <span className="flex w-36 shrink-0 flex-col gap-0.5">
            <span className="text-body font-bold text-action">{averageText(item)}</span>
            <span className="text-small text-fg-muted">평가 {item.ratingCount.toLocaleString("ko-KR")}</span>
          </span>
          <Icon name="chevron-right" className="shrink-0" />
        </Link>
      </li>
    );
  }

  return (
    <li>
      <Link
        href={`/matches/${match.id}`}
        onClick={onSelect}
        className="flex flex-col gap-2 rounded-control bg-surface p-3 hover:bg-subtle"
      >
        <span className="flex items-center gap-2">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-control bg-selected text-lead font-bold text-action">
            {item.rank}
          </span>
          {competition}
        </span>
        <Teams item={item} layout="mobile" />
        <span className="flex items-center justify-between gap-3">
          <span className="text-body font-bold text-action">{averageText(item)}</span>
          <span className="text-small text-fg-muted">평가 {item.ratingCount.toLocaleString("ko-KR")}</span>
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
  layout: Top5Layout;
}

/** Body of the expanded TOP 5 (desktop panel 128:3145 / mobile sheet 128:3574). */
export function Top5List({ data, isPending, error, onRetry, onSelect, layout }: Top5ListProps) {
  if (isPending || error || !data) {
    return (
      <DataState
        status={isPending ? "loading" : "error"}
        error={error}
        onRetry={onRetry}
        errorTitle="인기 경기를 불러오지 못했습니다"
        loadingFallback={
          <div className="flex flex-col gap-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-[72px] w-full" />
            <Skeleton className="h-[72px] w-full" />
          </div>
        }
      />
    );
  }

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <p className="text-small text-fg-muted">{periodSummary(data)}</p>
      {data.items.length === 0 ? (
        // Never fall back to last week's ranking (TOP-003).
        <div role="status" className="flex flex-col gap-2 rounded-control bg-canvas p-6 text-center">
          <p className="text-lead font-bold">아직 선정된 경기가 없어요</p>
          <p className="text-label text-fg-secondary">이번 주 인기 경기가 선정되면 여기에 표시됩니다.</p>
        </div>
      ) : (
        <>
          <ol className={cx("flex flex-col gap-2", layout === "mobile" && "max-h-[424px] overflow-y-auto")}>
            {data.items.map((item) => (
              <Top5Row key={item.match.id} item={item} layout={layout} onSelect={onSelect} />
            ))}
          </ol>
          <hr className="border-line" />
          <p className="text-small text-fg-muted">{footnote(data.items.length, layout)}</p>
        </>
      )}
    </div>
  );
}
