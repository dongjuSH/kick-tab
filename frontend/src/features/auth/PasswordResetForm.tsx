"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import { AuthCard, Field, FormMessage } from "./AuthForm";
import { EmailCodeStep, type Verified } from "./EmailCodeStep";
import { PASSWORD_HINT, passwordFieldErrors, passwordValid } from "./rules";

/**
 * Forgot password (AUTH-001 rule 4, Figma 134:4077~134:5037, 4 steps): 1 email → 2 code
 * (same rules as signup) → 3 new password → 4 done. Every session of the account ends; the
 * member signs in again with the new password.
 */
export function PasswordResetForm() {
  const [verified, setVerified] = useState<Verified | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);
  const [codeSent, setCodeSent] = useState(false);
  // Remounts the email/code step so a new search starts empty.
  const [flow, setFlow] = useState(0);
  const local = passwordFieldErrors(password, confirm);

  // Next keeps this page alive after leaving it (Codex N4): a later visit must start at
  // step 1, not on the finished or half-done search.
  const restart = () => {
    setVerified(null);
    setPassword("");
    setConfirm("");
    setPending(false);
    setError(null);
    setFieldErrors({});
    setDone(false);
    setCodeSent(false);
    setFlow((n) => n + 1);
  };
  // Leaving the finished screen any way (e.g. the header) starts over: the cleanup runs when
  // Next hides the kept page, so the next visit begins at step 1.
  useEffect(() => {
    if (!done) return;
    return restart;
  }, [done]);

  if (done) {
    return (
      <AuthCard title="비밀번호를 변경했어요" step="4 / 4 단계">
        <FormMessage tone="success">새 비밀번호로 다시 로그인해 주세요.</FormMessage>
        <ButtonLink href="/login" variant="primary" fullWidth onClick={restart}>
          로그인하기
        </ButtonLink>
      </AuthCard>
    );
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!verified || pending || !passwordValid(password) || password !== confirm) return;
    setPending(true);
    setError(null);
    setFieldErrors({});
    try {
      await apiFetch("/auth/password-reset", {
        method: "POST",
        body: { email: verified.email, verificationToken: verified.token, newPassword: password, newPasswordConfirm: confirm },
      });
      setDone(true);
    } catch (caught) {
      if (isApiError(caught)) {
        setFieldErrors(caught.fieldErrors);
        setError(caught.message);
        if (caught.code === "VERIFICATION_INVALID") setVerified(null);
      } else {
        setError("비밀번호를 변경하지 못했습니다. 다시 시도해 주세요.");
      }
    } finally {
      setPending(false);
    }
  };

  if (!verified) {
    return (
      <AuthCard
        title="비밀번호 찾기"
        step={codeSent ? "2 / 4 단계" : "1 / 4 단계"}
        description={codeSent ? "메일로 받은 인증번호 6자리를 입력해 주세요." : "가입한 이메일로 인증번호를 보내드릴게요."}
      >
        <EmailCodeStep
          key={flow}
          purpose="password_reset"
          verified={null}
          onVerified={setVerified}
          onSent={() => setCodeSent(true)}
        />
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <Link href="/login" onClick={restart} className="inline-flex min-h-11 items-center justify-center rounded-control text-body text-fg hover:bg-subtle">
          로그인으로 돌아가기
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="새 비밀번호 설정" step="3 / 4 단계" description="새로 사용할 비밀번호를 입력해 주세요.">
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <Field label="이메일" value={verified.email} readOnly hint="인증 완료" />
        <Field
          label="새 비밀번호"
          hint={PASSWORD_HINT}
          type="password"
          autoComplete="new-password"
          maxLength={64}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.newPassword ?? local.password}
        />
        <Field
          label="새 비밀번호 확인"
          type="password"
          autoComplete="new-password"
          maxLength={64}
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          error={fieldErrors.newPasswordConfirm ?? local.confirm}
        />
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <Button
          type="submit"
          variant="primary"
          fullWidth
          disabled={pending || !passwordValid(password) || password !== confirm}
        >
          {pending ? "변경하는 중…" : "비밀번호 변경"}
        </Button>
      </form>
    </AuthCard>
  );
}
