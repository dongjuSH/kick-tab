"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { checkSession, memberRequest, useAuth } from "@/features/auth/session";
import { ReviewRestrictionNotice, useRestrictionEnd } from "@/features/match/ReviewRestriction";
import { ReviewTextForm } from "@/features/match/ReviewTextForm";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type { MyReview } from "@/lib/api/types";
import { scoreText, teamName } from "@/lib/format/match";
import { reactionsText, reviewDatesText, reviewEditRefusal } from "./model";
import { AreaError, MyCard } from "./MyCard";
import { myReviewsQuery } from "./queries";

/**
 * 내 평가 (MY-003, Figma 639:8131 — List 639:8132 / Empty 639:8151 / Error 639:8154; mobile
 * 639:8161 / 639:8180 / 639:8183). Newest first: the match (link to its page), the text,
 * '작성 YYYY.MM.DD' (+ ' · 수정 YYYY.MM.DD' only for edited reviews) and the reaction counts.
 * No rating or average. Edit uses the match page's text rules; a closed match refuses it.
 * A restricted member (terms 제9조) sees the match page's notice and no edit, delete stays.
 */
export function MyReviews() {
  const query = useQuery(myReviewsQuery);
  const auth = useAuth();
  const restrictedUntil = auth.status === "member" ? (auth.member.reviewRestrictedUntil ?? null) : null;
  useRestrictionEnd(restrictedUntil);

  let body;
  if (query.isPending) body = <DataState status="loading" />;
  else if (!query.data)
    body = <AreaError text="경기 평가를 불러오지 못했습니다." onRetry={() => void query.refetch()} />;
  else if (query.data.length === 0) body = <p className="text-body text-fg-secondary">작성한 경기 평가가 없습니다</p>;
  else
    body = (
      <>
        {restrictedUntil && <ReviewRestrictionNotice until={restrictedUntil} />}
        <ul className="flex flex-col">
          {query.data.map((review) => (
            <ReviewRow key={review.id} review={review} restricted={Boolean(restrictedUntil)} />
          ))}
        </ul>
      </>
    );

  return (
    <MyCard title="내 평가" titleId="my-reviews-title">
      {body}
    </MyCard>
  );
}

function ReviewRow({ review, restricted }: { review: MyReview; restricted: boolean }) {
  const queryClient = useQueryClient();
  const [chosen, setMode] = useState<"view" | "edit" | "delete">("view");
  // Restricted while editing (found on save, or read again): the edit closes, delete stays.
  const mode = restricted && chosen === "edit" ? "view" : chosen;
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const deleteButton = useRef<HTMLButtonElement>(null);
  const keepButton = useRef<HTMLButtonElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  // The pressed button is replaced: the edit starts in the text, the delete check on '취소'.
  useEffect(() => {
    if (mode === "edit") field.current?.focus();
    if (mode === "delete") keepButton.current?.focus();
  }, [mode]);
  const { match } = review;
  const title = `${teamName(match.home)} ${scoreText(match)} ${teamName(match.away)}`;

  // The match page's count and list and this list both change.
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["matches", "reviews"] }),
      queryClient.invalidateQueries({ queryKey: queryKeys.me.reviews() }),
    ]);

  const fail = (caught: unknown, fallback: string) => {
    if (isApiError(caught) && caught.status === 401) {
      // The session ended (memberRequest made this a guest): the page shows its login notice.
      return;
    }
    // Restricted after this page loaded: read the member again so the notice replaces the
    // edit; focus moves to '삭제', which stays usable.
    if (isApiError(caught) && caught.code === "REVIEW_RESTRICTED") {
      void checkSession().then(() => {
        setMode("view");
        requestAnimationFrame(() => deleteButton.current?.focus());
      });
    }
    const closed = isApiError(caught) ? reviewEditRefusal(caught.status, caught.code) : null;
    if (closed) setError(closed);
    else if (isApiError(caught) && caught.status === 404) {
      // Already gone (deleted in another tab): show the list as stored.
      void refresh();
      setError(caught.message);
    } else setError(isApiError(caught) ? caught.message : fallback);
  };

  /** Back to the review; focus returns to the button that opened the edit or the check. */
  const back = () => {
    const target = mode === "delete" ? deleteButton : editButton;
    setMode("view");
    setError(null);
    requestAnimationFrame(() => target.current?.focus());
  };

  const save = async () => {
    setPending(true);
    setError(null);
    try {
      await memberRequest(() => apiFetch(`/reviews/${review.id}`, { method: "PATCH", body: { body: text } }));
      await refresh();
      back();
    } catch (caught) {
      fail(caught, "평가를 저장하지 못했습니다. 다시 시도해 주세요.");
    } finally {
      setPending(false);
    }
  };

  const remove = async () => {
    setPending(true);
    setError(null);
    try {
      await memberRequest(() => apiFetch(`/reviews/${review.id}`, { method: "DELETE" }));
      await refresh();
      // The row is gone: focus goes to the area title.
      document.getElementById("my-reviews-title")?.focus();
    } catch (caught) {
      fail(caught, "평가를 삭제하지 못했습니다. 다시 시도해 주세요.");
    } finally {
      setPending(false);
    }
  };

  const errorLine = error && (
    <p role="alert" className="text-small font-medium text-error">
      {error}
    </p>
  );

  return (
    <li className="flex flex-col gap-4 border-b border-line py-4 first:pt-0 last:border-b-0 last:pb-0">
      <Link href={`/matches/${match.id}`} prefetch={false} className="self-start text-body font-bold text-fg hover:underline">
        {title}
      </Link>
      {mode === "edit" ? (
        <ReviewTextForm
          label="평가 수정"
          text={text}
          onChange={setText}
          pending={pending}
          submitLabel="저장"
          onSubmit={save}
          onCancel={back}
          error={error}
          fieldRef={field}
        />
      ) : (
        <>
          <p className="text-body break-words whitespace-pre-line text-fg-secondary">{review.body}</p>
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
            <p className="text-small text-fg-muted lg:flex-1">
              <span className="block lg:inline">{reviewDatesText(review.createdAt, review.editedAt)}</span>
              <span className="hidden lg:inline">{` · ${reactionsText(review.likes, review.dislikes)}`}</span>
            </p>
            <div className="flex items-center gap-1">
              <p className="flex-1 text-small text-fg-muted lg:hidden">{reactionsText(review.likes, review.dislikes)}</p>
              {mode === "view" && (
                <>
                <Button
                  ref={editButton}
                  variant="text"
                  disabled={restricted}
                  aria-label={`${title} 평가 수정`}
                  onClick={() => {
                    setText(review.body);
                    setError(null);
                    setMode("edit");
                  }}
                >
                  수정
                </Button>
                <Button
                  ref={deleteButton}
                  variant="text"
                  aria-label={`${title} 평가 삭제`}
                  onClick={() => {
                    setError(null);
                    setMode("delete");
                  }}
                >
                  삭제
                </Button>
                </>
              )}
            </div>
          </div>
          {mode === "delete" && (
            // Its own row under the dates, so the dates never get squeezed.
            <div role="group" aria-label="평가 삭제 확인" className="flex flex-wrap items-center gap-2 rounded-control bg-subtle p-3">
              <p className="min-w-0 flex-1 text-small text-fg-secondary">이 평가를 삭제할까요? 삭제하면 되돌릴 수 없습니다.</p>
              <div className="flex gap-2">
                <Button ref={keepButton} variant="secondary" disabled={pending} onClick={back}>
                  취소
                </Button>
                <Button variant="danger" disabled={pending} onClick={remove} aria-busy={pending || undefined}>
                  {pending ? "삭제 중…" : "삭제"}
                </Button>
              </div>
            </div>
          )}
          {errorLine}
        </>
      )}
    </li>
  );
}
