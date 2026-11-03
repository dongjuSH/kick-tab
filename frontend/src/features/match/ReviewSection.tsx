"use client";

import { useQuery } from "@tanstack/react-query";
import { useId } from "react";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import type { ReviewItem, ReviewSort } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { reviewsQuery } from "./queries";

const SORTS = [
  { value: "popular", label: "인기순" },
  { value: "latest", label: "최신순" },
] as const satisfies readonly { value: ReviewSort; label: string }[];

/** Always visible review rules (REV-004, Figma 100:2619; user decision 2026-11-01: no tooltip). */
export function ReviewGuidelines() {
  return (
    <section
      aria-label="후기 작성 주의사항"
      className="flex flex-col gap-2.5 rounded-control border border-l-3 border-warning bg-warning-bg p-4 text-warning"
    >
      <ul className="text-body">
        <li>• 이용자를 겨냥한 시비·반복 도발·싸움 유도·집단 괴롭힘은 제한합니다.</li>
        <li>• 도 넘은 인신공격·가족 비난·혐오·성희롱·협박·폭력 조장은 금지합니다.</li>
        <li>• 개인정보 노출, 확인되지 않은 범죄·사생활 의혹의 단정은 제한합니다.</li>
        <li>• 광고·도배·불법 베팅 홍보 등 경기와 무관한 내용은 제한합니다.</li>
      </ul>
      <p className="text-label font-bold">
        농담이어도 대상과 맥락·수위·반복성을 함께 판단하며, 기준을 넘은 후기는 삭제될 수 있습니다.
      </p>
    </section>
  );
}

function Reactions({ review }: { review: ReviewItem }) {
  // Counts only: reacting is a member action added by chat 02 (REV-004 rule 4).
  return (
    <p className="flex items-center gap-2 text-body font-medium text-fg-secondary">
      <span className="flex h-11 items-center gap-1.5 px-3">
        <Icon name="thumbs" />
        {`좋아요 ${review.likes}`}
      </span>
      <span className="flex h-11 items-center gap-1.5 px-3">
        <Icon name="thumbs" className="rotate-180" />
        {`싫어요 ${review.dislikes}`}
      </span>
    </p>
  );
}

/**
 * Member ratings and reviews, public to everyone (REV-004, Figma 52:289). Average and count
 * ("—" with no review, never 0 points), popular/latest order, review rules. Writing,
 * editing and reactions are chat 02's: no input or login button is placed here.
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
      <h2 id={`${idBase}-title`} className="text-subtitle font-bold">회원 평점·후기</h2>
      {summary ? (
        <p className="flex items-center gap-4">
          <span className="text-[32px] leading-[43px] font-bold text-fg">
            {summary.average === null ? MISSING : summary.average.toFixed(1)}
          </span>
          <span className="text-label text-fg-secondary">{`평균 평점 · 평가 ${summary.count}건`}</span>
        </p>
      ) : (
        query.isPending && <Skeleton className="h-11 w-48" />
      )}
      <p className="bg-subtle p-4 text-body font-medium text-fg">평점과 후기는 누구나 볼 수 있어요.</p>
      <ReviewGuidelines />
      <div>
        <Tabs items={SORTS} value={sort} onChange={onSort} label="후기 정렬" idBase={idBase} />
        <div role="tabpanel" id={tabPanelId(idBase, sort)} aria-labelledby={tabId(idBase, sort)} className="pt-4">
          {!query.data ? (
            <DataState
              status={query.isPending ? "loading" : "error"}
              error={query.error}
              onRetry={() => void query.refetch()}
              errorTitle="평점과 후기를 불러오지 못했습니다"
            />
          ) : query.data.items.length === 0 ? (
            <StateMessage title="아직 평가가 없습니다" description="평균 평점 — · 평가 0건" />
          ) : (
            <ol className="flex flex-col">
              {query.data.items.map((review) => (
                <li key={review.id} className="flex flex-col gap-2.5 border-b border-line py-4 first:pt-0">
                  <p className="text-body font-bold whitespace-pre-wrap text-fg">
                    {`${review.authorNickname ?? MISSING}  ·  ${review.rating}점`}
                  </p>
                  {review.body && <p className="text-body break-words whitespace-pre-line text-fg">{review.body}</p>}
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
