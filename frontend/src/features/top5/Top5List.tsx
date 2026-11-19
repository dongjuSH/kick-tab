import Link from "next/link";
import { MatchStatus, MatchTeams, useMatchScore } from "@/components/common/MatchCard";
import { Badge } from "@/components/ui/Badge";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import type { TopMatchItem, TopMatches } from "@/lib/api/types";
import { competitionName } from "@/lib/format/match";
import {
  LIST_FOOTNOTE,
  SHORT_LIST_NOTICE,
  TOP5_MAX,
  changeText,
  isPlainClick,
  kickoffText,
  noticeCopy,
  noticeOf,
  type Top5Notice,
} from "./model";

type Top5Layout = "desktop" | "mobile";

/*
 * Mobile sheet: only the list scrolls (Figma 128:4408). On a very short screen (under 420px,
 * e.g. 200% zoom) a list squeezed between the heading and the footnote would shrink to a
 * sliver, so there the list is not a scroll box and the sheet body scrolls as a whole.
 */
const SHEET_BODY = "shrink-0 [@media(min-height:420px)]:min-h-0 [@media(min-height:420px)]:shrink";
const SHEET_LIST =
  "[@media(min-height:420px)]:min-h-0 [@media(min-height:420px)]:overflow-y-auto [@media(min-height:420px)]:overscroll-contain";

function Rank({ item }: { item: TopMatchItem }) {
  return (
    <Badge tone="accent" className="w-8 justify-center">
      <span className="sr-only">순서 </span>
      {item.rank}
    </Badge>
  );
}

/**
 * One selected match (Figma TOP5 Row in 128:3700 / 128:4408). The whole row opens the match
 * detail. Teams, crests, score (VS / — / PK), status badge and its note come from the common
 * match card parts (`MatchTeams`, `MatchStatus`); rank, the selected kickoff, its change line
 * and the reason are TOP 5's own. Desktop: rank · teams over competition and kickoff · reason ·
 * status. Mobile: rank, competition, status / kickoff / teams / reason.
 */
function Top5Row({ item, layout, onSelect }: { item: TopMatchItem; layout: Top5Layout; onSelect: () => void }) {
  const { match } = item;
  const { awaiting } = useMatchScore(match);
  const change = changeText(item);
  const competition = <span className="text-fg-secondary">{competitionName(match.competition)}</span>;
  const kickoff = <span className="text-fg-muted">{kickoffText(item)}</span>;
  const reason = (
    <span className="flex min-w-0 flex-col text-small font-medium text-fg-secondary">
      <span>{item.reason}</span>
      {change && <span className="text-warning">{change}</span>}
    </span>
  );

  if (layout === "desktop") {
    return (
      <li>
        <Link
          href={`/matches/${match.id}`}
          onClick={(event) => isPlainClick(event) && onSelect()}
          className="flex items-center gap-5 rounded-control border border-line bg-surface px-4 py-[11px] hover:bg-subtle"
        >
          <Rank item={item} />
          <span className="flex w-[420px] shrink-0 flex-col gap-1">
            <MatchTeams match={match} />
            <span className="flex justify-center gap-3 whitespace-nowrap text-small">
              {competition}
              {kickoff}
            </span>
          </span>
          <span className="min-w-0 flex-1">{reason}</span>
          <span className="flex w-[108px] shrink-0 justify-end">
            <MatchStatus match={match} awaiting={awaiting} end />
          </span>
        </Link>
      </li>
    );
  }

  return (
    <li>
      <Link
        href={`/matches/${match.id}`}
        onClick={(event) => isPlainClick(event) && onSelect()}
        className="flex flex-col gap-2 rounded-control border border-line bg-surface p-3 hover:bg-subtle"
      >
        <span className="flex items-start gap-2 text-small">
          <Rank item={item} />
          <span className="min-w-0 flex-1 truncate py-1">{competition}</span>
          <MatchStatus match={match} awaiting={awaiting} end className="shrink-0" />
        </span>
        <span className="flex flex-col gap-1">
          <span className="text-small">{kickoff}</span>
          <MatchTeams match={match} />
        </span>
        {reason}
      </Link>
    </li>
  );
}

/** "No supported matches" / delay notice (Figma 159:322 / 159:406). */
function NoticeBox({ notice, data }: { notice: Top5Notice; data: TopMatches }) {
  const copy = noticeCopy(notice, data);
  return (
    <div role="status" className="flex flex-col gap-1 rounded-control bg-subtle p-4">
      <p className="text-body font-bold text-fg">{copy.title}</p>
      <p className="text-small text-fg-secondary">{copy.description}</p>
    </div>
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
 * Body of the expanded TOP 5 under its heading (week, selection time and close live in the
 * heading): the list or a notice. Only the match list scrolls on a short window.
 */
export function Top5List({ data, isPending, error, onRetry, onSelect, layout }: Top5ListProps) {
  if (!data) {
    // Kept data stays on screen if a later refetch fails; only a first load shows these.
    return (
      <DataState
        status={isPending ? "loading" : "error"}
        error={error}
        onRetry={onRetry}
        errorTitle="주목 경기를 불러오지 못했습니다"
        loadingFallback={
          <div className="flex flex-col gap-2">
            <Skeleton className="h-[68px] w-full" />
            <Skeleton className="h-[68px] w-full" />
          </div>
        }
      />
    );
  }
  const notice = noticeOf(data);
  if (notice) return <NoticeBox notice={notice} data={data} />;
  return (
    <div className={cx("flex flex-col gap-3", layout === "mobile" ? SHEET_BODY : "min-h-0")}>
      <ol className={cx("flex flex-col gap-2", layout === "mobile" ? SHEET_LIST : "min-h-0 overflow-y-auto overscroll-contain")}>
        {data.items.map((item) => (
          <Top5Row key={item.match.id} item={item} layout={layout} onSelect={onSelect} />
        ))}
      </ol>
      {data.items.length < TOP5_MAX && <p className="text-small text-fg-secondary">{SHORT_LIST_NOTICE}</p>}
      <p className="text-small text-fg-secondary">{LIST_FOOTNOTE}</p>
    </div>
  );
}
