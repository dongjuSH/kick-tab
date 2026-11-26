"use client";

import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";

/**
 * Login / signup / password-reset card (Figma 52:2116 · 52:2387 · 134:4077): 440px card with
 * a 28px title and a one-line description, centred under the header; full width on mobile.
 */
export function AuthCard({
  title,
  description,
  step,
  children,
}: {
  title: string;
  description?: ReactNode;
  /** "1 / 4 단계" line of the password-reset flow. */
  step?: string;
  children: ReactNode;
}) {
  return (
    <div className="kt-container flex justify-center py-6 lg:py-10">
      <section
        aria-labelledby="auth-title"
        className="flex w-full max-w-[440px] flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
      >
        <h1 id="auth-title" className="text-heading font-bold text-fg">
          {title}
        </h1>
        {step && <p className="text-small text-fg-secondary">{step}</p>}
        {description && <p className="text-body text-fg-secondary">{description}</p>}
        {children}
      </section>
    </div>
  );
}

const INPUT =
  "min-h-11 w-full rounded-control border bg-surface px-3 text-body text-fg placeholder:text-fg-muted " +
  "disabled:bg-subtle disabled:text-fg-secondary read-only:bg-subtle";

/** Labelled input with an optional rule hint above it and an error under it. */
export function Field({
  label,
  hint,
  error,
  className,
  ...input
}: {
  label: string;
  hint?: ReactNode;
  error?: string | null;
} & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className={cx("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-label font-bold text-fg">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-small text-fg-secondary">
          {hint}
        </p>
      )}
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={cx(hint ? `${id}-hint` : null, error ? `${id}-error` : null) || undefined}
        className={cx(INPUT, error ? "border-error" : "border-line-strong")}
        {...input}
      />
      {error && (
        <p id={`${id}-error`} role="alert" className="text-small font-medium text-error">
          {error}
        </p>
      )}
    </div>
  );
}

/** Form-level message: failure (alert) or plain notice (status). */
export function FormMessage({ tone, children }: { tone: "error" | "info" | "success"; children: ReactNode }) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cx(
        "rounded-control p-3 text-label",
        tone === "error" && "bg-error-bg text-error",
        tone === "info" && "bg-subtle text-fg-secondary",
        tone === "success" && "bg-live-bg font-medium text-live",
      )}
    >
      {children}
    </p>
  );
}

export const SOCIAL_NOTICE = "카카오·구글 로그인은 준비 중입니다. 이메일로 이용해 주세요.";

/**
 * Not shown for now: social sign-in is deferred until after launch (2026-11-26, guide P-02);
 * the login and signup forms keep their usage commented out.
 * Kakao / Google buttons kept as designed (P-02, Figma 637:7272 Default → Notice). Pressing
 * one shows the notice under the group on the same screen: no page move, popup or toast,
 * no social sign-in.
 */
export function SocialButtons() {
  const [notice, setNotice] = useState(false);
  return (
    <div className="flex flex-col gap-3 border-t border-line pt-4">
      <p className="text-center text-small text-fg-secondary">다른 방법으로 계속하기</p>
      <Button variant="secondary" fullWidth onClick={() => setNotice(true)}>
        <svg aria-hidden width="16" height="16" viewBox="0 0 16 16">
          <path
            fill="currentColor"
            d="M8 2C4.13 2 1 4.46 1 7.5c0 1.97 1.31 3.7 3.29 4.67l-.67 2.45c-.06.22.19.4.38.27L6.9 13c.36.04.72.06 1.1.06 3.87 0 7-2.46 7-5.5S11.87 2 8 2Z"
          />
        </svg>
        카카오로 계속하기
      </Button>
      <Button variant="secondary" fullWidth onClick={() => setNotice(true)}>
        <svg aria-hidden width="16" height="16" viewBox="0 0 16 16">
          <path fill="#4285F4" d="M15.68 8.18c0-.57-.05-1.11-.15-1.64H8v3.1h4.3a3.68 3.68 0 0 1-1.6 2.41v2h2.58c1.51-1.39 2.4-3.44 2.4-5.87Z" />
          <path fill="#34A853" d="M8 16c2.16 0 3.97-.72 5.29-1.94l-2.58-2c-.72.48-1.63.76-2.71.76-2.09 0-3.85-1.41-4.48-3.3H.86v2.07A8 8 0 0 0 8 16Z" />
          <path fill="#FBBC05" d="M3.52 9.52a4.8 4.8 0 0 1 0-3.04V4.41H.86a8 8 0 0 0 0 7.18l2.66-2.07Z" />
          <path fill="#EA4335" d="M8 3.18c1.18 0 2.23.4 3.06 1.2l2.29-2.29A8 8 0 0 0 .86 4.41l2.66 2.07C4.15 4.59 5.91 3.18 8 3.18Z" />
        </svg>
        Google로 계속하기
      </Button>
      {/* Always in the page (live region); out of the layout until there is a notice. */}
      <p role="status" className={notice ? "text-small text-fg-secondary" : "sr-only"}>
        {notice ? SOCIAL_NOTICE : null}
      </p>
    </div>
  );
}
