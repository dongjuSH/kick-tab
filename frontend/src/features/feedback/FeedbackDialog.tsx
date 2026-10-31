"use client";

import { useMutation } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useId, useState } from "react";
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
 * Body is required (1~1,000 chars, whitespace-only rejected); type is optional.
 * On failure the input stays; the draft also survives closing the dialog.
 */
export function FeedbackDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const [draft, setDraftState] = useState<FeedbackDraft>(() =>
    typeof window === "undefined" ? EMPTY_DRAFT : loadDraft(),
  );
  const [touched, setTouched] = useState(false);
  const [sent, setSent] = useState(false);
  const bodyId = useId();
  const hintId = useId();
  const errorId = useId();

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
  const serverFieldError = isApiError(mutation.error) ? mutation.error.fieldErrors.body : undefined;
  const emptyError = touched && !trimmed ? "공백 외 내용을 입력해 주세요." : undefined;
  const fieldError = emptyError ?? serverFieldError;
  const failed = mutation.isError && !serverFieldError;
  const failMessage =
    failed && isApiError(mutation.error) && mutation.error.code === "RATE_LIMITED"
      ? `${mutation.error.message} 입력한 내용은 유지되었습니다.`
      : FAIL_MESSAGE;

  const submit = () => {
    setTouched(true);
    if (!trimmed || mutation.isPending) return;
    mutation.mutate({ body: draft.body, type: draft.type, pagePath: pathname });
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

          <fieldset className="flex flex-col gap-4">
            <legend className="mb-4 text-label font-medium">의견 유형 · 선택</legend>
            <div className="flex gap-2 overflow-x-auto">
              {TYPES.map((type) => {
                const selected = draft.type === type.value;
                return (
                  <button
                    key={type.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setDraft({ ...draft, type: selected ? null : type.value })}
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

          <Button type="submit" variant="primary" fullWidth disabled={!trimmed || mutation.isPending}>
            {mutation.isPending ? "보내는 중…" : failed ? "다시 보내기" : "의견 보내기"}
          </Button>
          <p className="text-small text-fg-muted">로그인하지 않아도 익명으로 보낼 수 있습니다.</p>
        </form>
      )}
    </Dialog>
  );
}
