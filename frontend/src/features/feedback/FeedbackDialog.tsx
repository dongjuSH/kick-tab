"use client";

import { useMutation } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useId, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { Dialog } from "@/components/ui/Dialog";
import { cx } from "@/components/ui/cx";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { FeedbackCreate, FeedbackReceipt, FeedbackType } from "@/lib/api/types";
import { EMPTY_DRAFT, clearDraft, loadDraft, saveDraft, type FeedbackDraft } from "./draft";

export const FEEDBACK_MAX_LENGTH = 1000;

const TYPES: { value: FeedbackType; label: string }[] = [
  { value: "bug", label: "버그" },
  { value: "suggestion", label: "제안" },
  { value: "other", label: "기타" },
];

const FAIL_MESSAGE = "전송하지 못했습니다. 입력한 내용은 유지되었으니 다시 시도해 주세요.";

function submitFeedback(payload: FeedbackCreate) {
  return apiFetch<FeedbackReceipt>("/feedback", { method: "POST", body: payload });
}

/**
 * Feedback modal (FEED-002; Figma 62:1822·1851·1882, mobile sheet 62:1593·1622·1653·1672).
 * Body (1~1,000 chars, whitespace-only rejected) and type are both required; the type is
 * required by user decision (2026-10-31), so the Figma label "선택" reads "필수" here.
 * On failure the input stays; the draft also survives closing the dialog.
 */
export function FeedbackDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const [draft, setDraftState] = useState<FeedbackDraft>(() =>
    typeof window === "undefined" ? EMPTY_DRAFT : loadDraft(),
  );
  const [touched, setTouched] = useState(false);
  // Honeypot (hidden from people): bots that fill every field get refused by the API.
  const honeypot = useRef<HTMLInputElement>(null);
  const [sent, setSent] = useState(false);
  const bodyId = useId();
  const hintId = useId();
  const errorId = useId();
  const typeErrorId = useId();

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      clearDraft();
      setDraftState(EMPTY_DRAFT);
      setTouched(false);
      setSent(true);
    },
  });

  const setDraft = (next: FeedbackDraft) => {
    setDraftState(next);
    saveDraft(next);
    if (mutation.isError) mutation.reset();
  };

  const close = () => {
    onClose();
    // Next open starts from the form again; an unsent draft is kept.
    setSent(false);
    setTouched(false);
    mutation.reset();
  };

  const trimmed = draft.body.trim();
  const serverErrors = isApiError(mutation.error) ? mutation.error.fieldErrors : {};
  const emptyError = touched && !trimmed ? "공백 외 내용을 입력해 주세요." : undefined;
  const fieldError = emptyError ?? serverErrors.body;
  const typeError =
    (touched && !draft.type ? "의견 유형을 선택해 주세요." : undefined) ?? serverErrors.type;
  const failed = mutation.isError && !serverErrors.body && !serverErrors.type;
  const apiError = isApiError(mutation.error) ? mutation.error : null;
  const failMessage =
    apiError?.code === "RATE_LIMITED"
      ? `${apiError.message} 입력한 내용은 유지되었습니다.`
      : apiError?.code === "FEEDBACK_DUPLICATE"
        ? apiError.message
        : FAIL_MESSAGE;

  const submit = () => {
    setTouched(true);
    if (!trimmed || !draft.type || mutation.isPending) return;
    mutation.mutate({
      body: draft.body,
      type: draft.type,
      pagePath: pathname,
      website: honeypot.current?.value || undefined,
    });
  };

  return (
    <Dialog open={open} onClose={close} title={sent ? "의견을 전달했습니다" : "의견 보내기"}>
      {sent ? (
        <StateMessage
          title="의견을 전달했습니다"
          description="보내주신 의견은 서비스 개선에 참고하겠습니다."
          action={
            <Button variant="secondary" className="w-full max-w-[220px]" onClick={close}>
              닫기
            </Button>
          }
        />
      ) : (
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <p className="text-body text-fg-secondary">불편했던 점이나 바라는 점을 알려주세요.</p>

          {/* Honeypot: off-screen, unfocusable and hidden from assistive tech. */}
          <div aria-hidden className="absolute -left-[10000px] top-auto h-px w-px overflow-hidden">
            <label>
              웹사이트
              <input ref={honeypot} type="text" name="kt_website" tabIndex={-1} autoComplete="off" />
            </label>
          </div>

          <fieldset className="flex flex-col gap-4" aria-describedby={typeError ? typeErrorId : undefined}>
            <legend className="mb-4 text-label font-medium">의견 유형 · 필수</legend>
            <div className="flex gap-2 overflow-x-auto">
              {TYPES.map((type) => {
                const selected = draft.type === type.value;
                return (
                  <button
                    key={type.value}
                    type="button"
                    aria-pressed={selected}
                    // Required: choosing again keeps the selection instead of clearing it.
                    onClick={() => !selected && setDraft({ ...draft, type: type.value })}
                    className={cx(
                      "min-h-11 w-[76px] shrink-0 rounded-control border p-3 text-label",
                      selected
                        ? "border-action bg-selected font-medium text-action"
                        : "border-line bg-surface text-fg-secondary hover:bg-subtle",
                    )}
                  >
                    {type.label}
                  </button>
                );
              })}
            </div>
            {typeError && (
              <p id={typeErrorId} role="alert" className="text-label font-medium text-error">
                {typeError}
              </p>
            )}
          </fieldset>

          <div className="flex flex-col gap-4">
            <label htmlFor={bodyId} className="text-body font-medium">
              내용 · 필수
            </label>
            <textarea
              id={bodyId}
              value={draft.body}
              maxLength={FEEDBACK_MAX_LENGTH}
              required
              placeholder="서비스를 사용하며 느낀 점을 적어주세요."
              aria-invalid={fieldError ? true : undefined}
              aria-describedby={cx(hintId, fieldError && errorId)}
              onChange={(event) => setDraft({ ...draft, body: event.target.value })}
              onBlur={() => setTouched(true)}
              className={cx(
                "h-36 resize-none rounded-control border bg-surface p-3 text-body text-fg placeholder:text-fg-muted",
                fieldError ? "border-error" : "border-line-strong",
              )}
            />
            <p id={hintId} className="text-right text-small text-fg-muted">
              {draft.body.length.toLocaleString("ko-KR")} / {FEEDBACK_MAX_LENGTH.toLocaleString("ko-KR")}
            </p>
            {fieldError && (
              <p id={errorId} role="alert" className="text-label font-medium text-error">
                {fieldError}
              </p>
            )}
          </div>

          {failed && (
            <p role="alert" className="rounded-control bg-error-bg p-3 text-label text-error">
              {failMessage}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            fullWidth
            disabled={!trimmed || !draft.type || mutation.isPending}
          >
            {mutation.isPending ? "보내는 중…" : failed ? "다시 보내기" : "의견 보내기"}
          </Button>
          <p className="text-small text-fg-muted">로그인하지 않아도 익명으로 보낼 수 있습니다.</p>
        </form>
      )}
    </Dialog>
  );
}
