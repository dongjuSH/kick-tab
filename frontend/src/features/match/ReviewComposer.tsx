"use client";

import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { clearReviewIntent, hasReviewIntent, loginHref, rememberReviewIntent } from "@/features/auth/returnTo";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { ReviewItem } from "@/lib/api/types";
import { REVIEW_DRAFT_PREFIX, checkSession, memberRequest } from "@/features/auth/session";
import { ReviewGuidance } from "./ReviewGuidance";
import { ReviewRestrictionNotice, useRestrictionEnd } from "./ReviewRestriction";
import { ReviewTextForm } from "./ReviewTextForm";

/**
 * Text being written survives a lost session and the login round trip (AUTH-003, D-02) —
 * for the same member only: the key holds the member id, so another account signing in on
 * this tab never sees it (COM-005, Codex N1). An explicit logout removes the drafts
 * (`session.ts`).
 */
function draftKey(memberId: string, fixtureId: number) {
  return `${REVIEW_DRAFT_PREFIX}${memberId}:${fixtureId}`;
}
function readDraft(memberId: string, fixtureId: number): string | null {
  try {
    return sessionStorage.getItem(draftKey(memberId, fixtureId));
  } catch {
    return null;
  }
}
function writeDraft(memberId: string, fixtureId: number, text: string | null) {
  try {
    if (text === null) sessionStorage.removeItem(draftKey(memberId, fixtureId));
    else sessionStorage.setItem(draftKey(memberId, fixtureId), text);
  } catch {
    // No storage: the text simply is not kept across a reload.
  }
}

/**
 * Member review area (REV-002·003, Figma 63:1408 without the rating chips): a new review
 * (text, n / 300, 등록), or the member's own review with 수정 · 삭제. One per member and
 * match; empty or space-only text cannot be sent. If the session is lost while writing, the
 * text is kept and the login returns here (no automatic submit).
 */
export function ReviewComposer({
  memberId,
  fixtureId,
  mine,
  restrictedUntil,
}: {
  /** The signed-in member (drafts are kept per member). */
  memberId: string;
  /** Terms 제9조: writing and editing are blocked until this moment (null = free). */
  restrictedUntil: string | null;
  fixtureId: number;
  /** The member's own review of this match, when the list has it. */
  mine: ReviewItem | undefined;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [mode, setMode] = useState<"write" | "edit" | null>(null);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const area = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  // Restricted (terms 제9조): an own review is shown read-only with 삭제 still available —
  // even when an edit was open or a kept edit draft was restored (Codex N1).
  const current = restrictedUntil && mine ? null : (mode ?? (mine ? null : "write"));

  useRestrictionEnd(restrictedUntil);

  // Restore a kept draft once (new review, or the edit that was interrupted).
  const restored = useRef(false);
  const restoringEdit = useRef(false);
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    const draft = readDraft(memberId, fixtureId);
    if (draft === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time restore from storage
    setText(draft);
    if (mine) {
      restoringEdit.current = true;
      setMode("edit");
    }
  }, [memberId, fixtureId, mine]);

  // Opened by the login return for this match (review intent): bring the text, or the own
  // review, into view and focus it once. Mounted only for members, so this runs after login.
  useEffect(() => {
    // The draft effect has requested edit mode, but its textarea mounts on the next render.
    if (restoringEdit.current && !restrictedUntil && current !== "edit") return;
    restoringEdit.current = false;
    if (!hasReviewIntent(fixtureId)) return;
    clearReviewIntent();
    area.current?.scrollIntoView({ block: "center" });
    (field.current ?? area.current?.querySelector<HTMLElement>("button:not(:disabled)"))?.focus({ preventScroll: true });
  }, [fixtureId, current, restrictedUntil]);

  const change = (value: string) => {
    setText(value);
    writeDraft(memberId, fixtureId, value);
  };

  // The match's list and the member's own list on the my page (written, edited or deleted
  // here — desktop review 2026-11-24: 내 평가 stayed stale until it refetched by itself).
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["matches", "reviews"] }),
      queryClient.invalidateQueries({ queryKey: queryKeys.me.reviews() }),
    ]);

  const fail = (caught: unknown, fallback: string) => {
    if (caught instanceof DOMException && caught.name === "AbortError") return;
    if (isApiError(caught) && caught.status === 401) {
      // Session ended and could not be renewed (memberRequest made this a guest, so the login
      // page shows its form — Codex N9): keep the text, sign in, come back here.
      rememberReviewIntent(fixtureId);
      router.push(loginHref(`/matches/${fixtureId}`, `review:${fixtureId}`));
      return;
    }
    if (isApiError(caught) && caught.code === "REVIEW_EXISTS") void refresh();
    // Restricted after this page loaded: read the member again so the notice replaces the form.
    if (isApiError(caught) && caught.code === "REVIEW_RESTRICTED") void checkSession();
    setError(isApiError(caught) ? caught.message : fallback);
  };

  const submit = async () => {
    setPending(true);
    setError(null);
    try {
      if (current === "edit" && mine) {
        await memberRequest(() => apiFetch(`/reviews/${mine.id}`, { method: "PATCH", body: { body: text } }));
      } else {
        await memberRequest(() => apiFetch(`/fixtures/${fixtureId}/reviews`, { method: "POST", body: { body: text } }));
      }
      writeDraft(memberId, fixtureId, null);
      setText("");
      setMode(null);
      await refresh();
    } catch (caught) {
      fail(caught, "평가를 저장하지 못했습니다. 다시 시도해 주세요.");
    } finally {
      setPending(false);
    }
  };

  const remove = async () => {
    if (!mine || pending) return;
    setPending(true);
    setError(null);
    try {
      await memberRequest(() => apiFetch(`/reviews/${mine.id}`, { method: "DELETE" }));
      writeDraft(memberId, fixtureId, null);
      setConfirmDelete(false);
      setMode(null);
      setText("");
      await refresh();
    } catch (caught) {
      fail(caught, "평가를 삭제하지 못했습니다. 다시 시도해 주세요.");
    } finally {
      setPending(false);
    }
  };

  const restriction = restrictedUntil && <ReviewRestrictionNotice until={restrictedUntil} />;

  const errorLine = error && (
    <p role="alert" className="text-small font-medium text-error">
      {error}
    </p>
  );

  if (current === null && mine) {
    return (
      <div ref={area} className="flex flex-col gap-2 rounded-control bg-subtle p-4">
        <p className="text-label font-bold text-fg">내 평가</p>
        <p className="text-body break-words whitespace-pre-line text-fg">{mine.body}</p>
        {confirmDelete ? (
          <div role="group" aria-label="평가 삭제 확인" className="flex flex-wrap items-center gap-2">
            <p className="flex-1 text-small text-fg-secondary">이 평가를 삭제할까요? 삭제하면 되돌릴 수 없습니다.</p>
            <Button variant="secondary" disabled={pending} onClick={() => setConfirmDelete(false)}>
              취소
            </Button>
            <Button variant="danger" disabled={pending} onClick={remove}>
              {pending ? "삭제 중…" : "삭제"}
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <Button
              variant="text"
              disabled={Boolean(restrictedUntil)}
              onClick={() => {
                setText(mine.body);
                setMode("edit");
                setError(null);
              }}
            >
              수정
            </Button>
            <Button variant="text" onClick={() => setConfirmDelete(true)}>
              삭제
            </Button>
          </div>
        )}
        {restriction}
        {errorLine}
      </div>
    );
  }

  if (restriction) {
    return (
      <div ref={area} className="flex flex-col gap-2">
        <p className="text-label font-bold text-fg">평가 작성</p>
        {restriction}
      </div>
    );
  }

  return (
    <div ref={area}>
      <ReviewTextForm
        label={current === "edit" ? "평가 수정" : "평가 작성"}
        aside={
          <>
            <ReviewGuidance />
            <span className="ml-auto text-small text-fg-muted">경기당 1개</span>
          </>
        }
        text={text}
        onChange={change}
        pending={pending}
        submitLabel={current === "edit" ? "저장" : "등록"}
        onSubmit={submit}
        onCancel={
          current === "edit"
            ? () => {
                writeDraft(memberId, fixtureId, null);
                setMode(null);
                setText("");
                setError(null);
              }
            : undefined
        }
        error={error}
        fieldRef={field}
      />
    </div>
  );
}
