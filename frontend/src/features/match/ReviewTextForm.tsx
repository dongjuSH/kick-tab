"use client";

import { useId, type FormEvent, type ReactNode, type Ref } from "react";
import { Button } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";

/** Review text limit (REV-002·003): 1–300 characters, not only spaces. The server checks it too. */
export const REVIEW_MAX = 300;

/** Whether the text can be sent: not empty or only spaces, at most 300 characters. */
export function reviewSendable(text: string): boolean {
  return Boolean(text.trim()) && text.length <= REVIEW_MAX;
}

/**
 * Review text input (Figma 63:1408 without the rating chips): label row, 300-character field,
 * `n / 300` counter, optional 취소 and the submit button. Shared by the match page's writing
 * area (04·02) and my page's review edit (09), so both follow the same rules.
 */
export function ReviewTextForm({
  label,
  aside,
  text,
  onChange,
  pending,
  submitLabel,
  onSubmit,
  onCancel,
  error,
  fieldRef,
}: {
  label: string;
  /** Right side of the label row (review guidance, '경기당 1개'). */
  aside?: ReactNode;
  text: string;
  onChange: (value: string) => void;
  pending: boolean;
  submitLabel: string;
  onSubmit: () => void;
  /** Shows 취소 next to the submit button. */
  onCancel?: () => void;
  error?: string | null;
  fieldRef?: Ref<HTMLTextAreaElement>;
}) {
  const ids = useId();
  const tooLong = text.length > REVIEW_MAX;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (pending || !reviewSendable(text)) return;
    onSubmit();
  };
  return (
    <form onSubmit={submit} className="flex flex-col gap-2" noValidate>
      <div className="flex items-center gap-1">
        <label htmlFor={`${ids}-text`} className="text-label font-bold text-fg">
          {label}
        </label>
        {aside}
      </div>
      <textarea
        id={`${ids}-text`}
        ref={fieldRef}
        value={text}
        readOnly={pending}
        onChange={(event) => onChange(event.target.value)}
        placeholder="경기에 대한 평가를 남겨 주세요."
        aria-describedby={`${ids}-count`}
        aria-invalid={tooLong || undefined}
        className={cx(
          "h-20 resize-none rounded-control border bg-surface p-3 text-body text-fg placeholder:text-fg-muted",
          tooLong ? "border-error" : "border-line-strong",
        )}
      />
      <div className="flex items-center gap-2">
        <span id={`${ids}-count`} className={cx("flex-1 text-small", tooLong ? "text-error" : "text-fg-muted")}>
          {text.length} / {REVIEW_MAX}
        </span>
        {onCancel && (
          <Button variant="secondary" disabled={pending} onClick={onCancel}>
            취소
          </Button>
        )}
        <Button type="submit" variant="primary" className="w-16" disabled={pending || !reviewSendable(text)}>
          {submitLabel}
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-small font-medium text-error">
          {error}
        </p>
      )}
    </form>
  );
}
