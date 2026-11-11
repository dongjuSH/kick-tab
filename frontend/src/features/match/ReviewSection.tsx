"use client";

import { useQuery } from "@tanstack/react-query";
import { useId } from "react";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import type { ReviewItem, ReviewSort } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { ThumbIcon } from "./icons";
import { reviewsQuery } from "./queries";
import { ReviewGuidance } from "./ReviewGuidance";

const SORTS = [
  { value: "popular", label: "인기순" },
  { value: "latest", label: "최신순" },
] as const satisfies readonly { value: ReviewSort; label: string }[];

function Reactions({ review }: { review: ReviewItem }) {
  // Counts only: reacting is a member action added by chat 02 (REV-004 rule 4).
  return (
    <p className="flex items-center gap-2 text-body font-medium text-fg-secondary">
      <span className="flex h-11 items-center gap-1.5 px-3">
        <ThumbIcon />
        {`좋아요 ${review.likes}`}
      </span>
      <span className="flex h-11 items-center gap-1.5 px-3">
        <ThumbIcon down />
        {`싫어요 ${review.dislikes}`}
      </span>
    </p>
  );
}

/**
 * Match reviews: public text reviews of a live or normally finished match (REV-001·004,
 * Figma 52:151 · 161:4161). The valid review count, popular/latest order, reactions and
 * the review rules; no star rating or average. Writing, editing, reacting and the login
 * box above the list (Figma 52:294) are chat 02's: nothing to write with is placed here.
 */
export function ReviewSection({
  fixtureId,
  sort,
  onSort,
}: {
  fixtureId: number;
  sort: ReviewSort;
  onSort: (sort: ReviewSort) => void;
}) {
  const query = useQuery(reviewsQuery(fixtureId, sort));
  const idBase = useId();
  const summary = query.data?.summary;

  return (
    <section
      aria-labelledby={`${idBase}-title`}
      className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div className="flex items-center gap-1">
        <h2 id={`${idBase}-title`} className="text-subtitle font-bold">경기 평가</h2>
        <ReviewGuidance />
        <span className="ml-auto text-small text-fg-muted">
          {summary ? (
            <>
              <span className="sr-only">평가 </span>
              {`${summary.count}건`}
            </>
          ) : (
            query.isPending && <Skeleton className="h-4 w-8" />
          )}
        </span>
      </div>
      <div>
        <Tabs items={SORTS} value={sort} onChange={onSort} label="평가 정렬" idBase={idBase} />
        <div role="tabpanel" id={tabPanelId(idBase, sort)} aria-labelledby={tabId(idBase, sort)} className="pt-4">
          {!query.data ? (
            <DataState
              status={query.isPending ? "loading" : "error"}
              error={query.error}
              onRetry={() => void query.refetch()}
              errorTitle="경기 평가를 불러오지 못했습니다"
            />
          ) : query.data.items.length === 0 ? (
            <StateMessage title="아직 평가가 없습니다" description="평가 0건" />
          ) : (
            <ol className="flex flex-col">
              {query.data.items.map((review) => (
                <li key={review.id} className="flex flex-col gap-2.5 border-b border-line py-4 first:pt-0">
                  <p className="text-body font-bold text-fg">{review.authorNickname ?? MISSING}</p>
                  <p className="text-body break-words whitespace-pre-line text-fg">{review.body}</p>
                  <Reactions review={review} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}
