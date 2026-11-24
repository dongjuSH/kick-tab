"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import { loginHref } from "@/features/auth/returnTo";
import { memberRequest, useAuth } from "@/features/auth/session";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { ReviewItem, ReviewSort } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { ThumbIcon } from "./icons";
import { reviewsQuery } from "./queries";
import { ReviewComposer } from "./ReviewComposer";
import { ReviewGuidance } from "./ReviewGuidance";
import { ReviewLoginNotice } from "./ReviewLoginNotice";

const SORTS = [
  { value: "popular", label: "인기순" },
  { value: "latest", label: "최신순" },
] as const satisfies readonly { value: ReviewSort; label: string }[];

/**
 * Like / dislike (REV-004 rule 4): 44px buttons, one reaction per member and review; pressing
 * the chosen one again clears it, the other one switches. Own reviews cannot be reacted to.
 * Guests get the login dialog (Figma 62:1939) and nothing is saved.
 */
function Reactions({
  review,
  member,
  onGuest,
  onSessionLost,
}: {
  review: ReviewItem;
  member: boolean;
  onGuest: () => void;
  onSessionLost: () => void;
}) {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const own = member && review.mine;

  const react = async (value: 1 | -1) => {
    if (!member) {
      onGuest();
      return;
    }
    setPending(true);
    setError(null);
    try {
      const clear = review.myReaction === value;
      // 401: memberRequest makes this a guest first, so the login page shows its form.
      await memberRequest(() =>
        apiFetch(`/reviews/${review.id}/reaction`, clear ? { method: "DELETE" } : { method: "PUT", body: { value } }),
      );
      await queryClient.invalidateQueries({ queryKey: ["matches", "reviews"] });
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      if (isApiError(caught) && caught.status === 401) onSessionLost();
      else setError(isApiError(caught) ? caught.message : "반응을 저장하지 못했습니다.");
    } finally {
      setPending(false);
    }
  };

  const button = (value: 1 | -1, label: string, count: number) => {
    const chosen = review.myReaction === value;
    return (
      <button
        type="button"
        aria-pressed={member && !own ? chosen : undefined}
        aria-label={own ? `${label} ${count}, 내 평가에는 반응할 수 없습니다` : `${label} ${count}`}
        disabled={own || pending}
        onClick={() => react(value)}
        className={cx(
          "flex h-11 items-center gap-1.5 rounded-control px-3 text-body font-medium",
          chosen ? "bg-selected text-action" : "text-fg-secondary",
          !own && "hover:bg-subtle",
          own && "cursor-default",
        )}
      >
        <ThumbIcon down={value === -1} />
        {`${label} ${count}`}
      </button>
    );
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {button(1, "좋아요", review.likes)}
        {button(-1, "싫어요", review.dislikes)}
      </div>
      {error && (
        <p role="alert" className="px-3 text-small text-error">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * Match reviews: public text reviews of a live or normally finished match (REV-001·004,
 * Figma 52:151 · 161:4161). The valid review count, popular/latest order, reactions and
 * the review rules; no star rating or average. Guests see the login notice (408:16478);
 * members see the writing area (63:1408) or their own review with edit/delete (chat 02).
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
  const auth = useAuth();
  const router = useRouter();
  const idBase = useId();
  const summary = query.data?.summary;
  const [loginPrompt, setLoginPrompt] = useState(false);
  const member = auth.status === "member";
  const mine = query.data?.items.find((item) => item.mine);
  const loginTarget = loginHref(`/matches/${fixtureId}`, `review:${fixtureId}`);

  return (
    <section
      aria-labelledby={`${idBase}-title`}
      className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4"
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
      {auth.status === "guest" && <ReviewLoginNotice fixtureId={fixtureId} />}
      {member && query.data && (
        <ReviewComposer
          key={`${auth.member.id}:${mine?.id ?? "new"}`}
          memberId={auth.member.id}
          restrictedUntil={auth.member.reviewRestrictedUntil ?? null}
          fixtureId={fixtureId}
          mine={mine}
        />
      )}
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
                  <p className="text-body font-bold text-fg">
                    {review.authorNickname ?? MISSING}
                    {member && review.mine && <span className="ml-2 text-small font-medium text-action">내 평가</span>}
                  </p>
                  <p className="text-body break-words whitespace-pre-line text-fg">{review.body}</p>
                  <Reactions
                    review={review}
                    member={member}
                    onGuest={() => setLoginPrompt(true)}
                    onSessionLost={() => router.push(loginTarget)}
                  />
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
      {/* Never left open behind a login: closed on the way out, and members do not get it. */}
      <Dialog open={loginPrompt && !member} onClose={() => setLoginPrompt(false)} title="로그인이 필요합니다" layout="responsive" width={375}>
        <div className="flex flex-col gap-4">
          <p className="text-body text-fg-secondary">로그인 후 현재 화면으로 돌아와 이용할 수 있어요.</p>
          {/* Cancel left (secondary), action right (primary), same width (Figma 62:1939 / 62:1702). */}
          <div className="grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => setLoginPrompt(false)}>
              계속 둘러보기
            </Button>
            <ButtonLink href={loginTarget} variant="primary" onClick={() => setLoginPrompt(false)}>
              로그인하기
            </ButtonLink>
          </div>
        </div>
      </Dialog>
    </section>
  );
}
