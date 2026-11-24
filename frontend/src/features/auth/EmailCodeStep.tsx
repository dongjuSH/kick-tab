"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { EmailCodeSent, EmailCodeVerified, VerificationPurpose } from "@/lib/api/types";
import { Field } from "./AuthForm";
import { emailValid } from "./rules";

export interface Verified {
  email: string;
  token: string;
}

/** Seconds ticking while a code is live (countdown and the 1-minute resend wait). Starts at
 *  0 (no clock is read while prerendering); callers take the larger of this and the moment
 *  the code was sent. */
function useSecondClock(active: boolean): number {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);
  return now;
}

function mmss(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * Email + 6-digit code (AUTH-001 rule 1). 10 minutes valid, resend after 1 minute (the new
 * code replaces the old one), five wrong codes make it unusable. '인증번호 받기' is primary on
 * both screens (user decision 2026-11-24; Figma 52:2387 still draws it secondary).
 * - signup: both on the same screen (Figma 52:2387 → 134:5398 → 134:5623); changing the
 *   address after a send starts over, and once confirmed the address is locked.
 * - password_reset: separate steps (Figma 134:4077 → 134:4344). After the send the address
 *   is no longer editable; '이메일 다시 입력' goes back to step 1.
 */
export function EmailCodeStep({
  purpose,
  verified,
  onVerified,
  onSent,
  onEditEmail,
}: {
  purpose: VerificationPurpose;
  verified: Verified | null;
  onVerified: (verified: Verified) => void;
  /** Called with the address after a code was sent (password reset moves to step 2). */
  onSent?: (email: string) => void;
  /** Password reset: '이메일 다시 입력' was pressed (back to step 1). */
  onEditEmail?: () => void;
}) {
  const steps = purpose === "password_reset";
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState<{ email: string; sentAt: number; expiresAt: number; resendAt: number } | null>(null);
  const [pending, setPending] = useState<"send" | "verify" | null>(null);
  const [error, setError] = useState<{ field: "email" | "code"; text: string } | null>(null);
  const clock = useSecondClock(sent !== null && verified === null);
  const now = Math.max(clock, sent?.sentAt ?? 0);

  if (verified) {
    return (
      <Field
        label="이메일"
        hint="인증 완료 · 이메일은 변경할 수 없습니다."
        type="email"
        value={verified.email}
        readOnly
      />
    );
  }

  const send = async () => {
    if (!emailValid(email)) {
      setError({ field: "email", text: "이메일 주소 형식을 확인해 주세요." });
      return;
    }
    setPending("send");
    setError(null);
    try {
      const { data } = await apiFetch<EmailCodeSent>("/auth/email-codes", {
        method: "POST",
        body: { email: email.trim(), purpose },
      });
      setSent({
        email: email.trim(),
        sentAt: Date.now(),
        expiresAt: Date.parse(data.expiresAt),
        resendAt: Date.parse(data.resendAt),
      });
      setCode("");
      onSent?.(email.trim());
    } catch (caught) {
      const text = isApiError(caught) ? caught.message : "인증번호를 보내지 못했습니다. 다시 시도해 주세요.";
      setError({ field: sent ? "code" : "email", text });
    } finally {
      setPending(null);
    }
  };

  const verify = async () => {
    if (!sent) return;
    if (!/^[0-9]{6}$/.test(code.trim())) {
      setError({ field: "code", text: "인증번호 6자리 숫자를 입력해 주세요." });
      return;
    }
    setPending("verify");
    setError(null);
    try {
      const { data } = await apiFetch<EmailCodeVerified>("/auth/email-codes/verify", {
        method: "POST",
        body: { email: sent.email, purpose, code: code.trim() },
      });
      onVerified({ email: sent.email, token: data.verificationToken });
    } catch (caught) {
      setError({ field: "code", text: isApiError(caught) ? caught.message : "인증번호를 확인하지 못했습니다." });
    } finally {
      setPending(null);
    }
  };

  const expired = sent !== null && now >= sent.expiresAt;
  const canResend = sent !== null && now >= sent.resendAt;
  const timing = sent
    ? expired
      ? "인증번호가 만료되었습니다 · 다시 받아 주세요"
      : `남은 시간 ${mmss(sent.expiresAt - now)} · ${canResend ? "재발송 가능" : `${Math.ceil((sent.resendAt - now) / 1000)}초 뒤 재발송 가능`}`
    : null;

  const editEmail = () => {
    setSent(null);
    setCode("");
    setError(null);
    onEditEmail?.();
  };

  return (
    <div className="flex flex-col gap-3">
      {!(steps && sent) && (
        <Field
          label="이메일"
          type="email"
          autoComplete="email"
          placeholder={steps ? "you@example.com" : "이메일 주소 입력"}
          value={email}
          // Signup: changing the address after a send starts over.
          onChange={(event) => {
            setEmail(event.target.value);
            if (sent && event.target.value.trim() !== sent.email) setSent(null);
          }}
          error={error?.field === "email" ? error.text : null}
        />
      )}
      {!sent ? (
        <Button variant="primary" fullWidth disabled={pending !== null} onClick={send}>
          {pending === "send" ? "보내는 중…" : "인증번호 받기"}
        </Button>
      ) : (
        <>
          <Field
            label="인증번호 6자리"
            hint={<span aria-live="off">{timing}</span>}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="6자리 인증번호"
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/[^0-9]/g, ""))}
            error={error?.field === "code" ? error.text : null}
          />
          <Button variant="primary" fullWidth disabled={pending !== null || expired} onClick={verify}>
            {pending === "verify" ? "확인 중…" : "인증번호 확인"}
          </Button>
          <Button variant="secondary" fullWidth disabled={pending !== null || !canResend} onClick={send}>
            {pending === "send" ? "보내는 중…" : "인증번호 다시 받기"}
          </Button>
          {steps && (
            <Button variant="secondary" fullWidth disabled={pending !== null} onClick={editEmail}>
              이메일 다시 입력
            </Button>
          )}
          <p role="status" className="sr-only">
            {pending === null && !error ? `${sent.email}로 인증번호를 보냈습니다.` : ""}
          </p>
        </>
      )}
    </div>
  );
}
