"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { LegalLink } from "@/features/legal/LegalLink";
import type { LegalDocumentId } from "@/features/legal/documents";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { Member } from "@/lib/api/types";
import { AuthCard, Field, FormMessage, SocialButtons } from "./AuthForm";
import { EmailCodeStep, type Verified } from "./EmailCodeStep";
import { rememberReviewIntent, reviewIntent, safeReturnTo } from "./returnTo";
import {
  NICKNAME_HINT,
  PASSWORD_HINT,
  nicknameValid,
  passwordFieldErrors,
  signupStatus,
  type Confirmations,
} from "./rules";
import { checkSession, useAuth } from "./session";

const CONFIRMATIONS: { key: keyof Confirmations; label: string; document?: LegalDocumentId }[] = [
  { key: "termsOfService", label: "[필수] 서비스 이용약관 동의", document: "terms" },
  { key: "privacyCollection", label: "[필수] 개인정보 수집·이용 동의", document: "privacy-consent" },
  { key: "age14OrOlder", label: "[필수] 만 14세 이상입니다" },
];

type Phase = "form" | "checking" | "failed";

/**
 * Email signup (AUTH-001, Figma 52:2387 / 52:2545, confirmations 637:7298). Signup stays
 * disabled until the email is verified, the inputs follow P-04 and all three required
 * confirmations are ticked (none is ticked at first). Account created ≠ signed in: the
 * member state appears only after GET /auth/me confirms the session (Figma 62:1177 checking,
 * 62:1306 failed).
 */
export function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const auth = useAuth();
  const returnTo = safeReturnTo(params.get("returnTo"));
  const intent = reviewIntent(params.get("intent"));
  const [verified, setVerified] = useState<Verified | null>(null);
  // Figma 134:5398 · 134:5623: the social buttons belong to the first step only.
  const [codeSent, setCodeSent] = useState(false);
  // Remounts the email/code step so a later signup on this kept page starts empty.
  const [flow, setFlow] = useState(0);
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [confirmations, setConfirmations] = useState<Confirmations>({
    termsOfService: false,
    privacyCollection: false,
    age14OrOlder: false,
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [phase, setPhase] = useState<Phase>("form");
  const statusId = useId();

  // Signed in already (not by this form): signup is not needed.
  useEffect(() => {
    if (auth.status === "member" && phase === "form" && !pending) router.replace(returnTo);
  }, [auth.status, phase, pending, returnTo, router]);

  const status = signupStatus({ verified: verified !== null, nickname, password, passwordConfirm, confirmations });
  const local = passwordFieldErrors(password, passwordConfirm);
  const nicknameError = fieldErrors.nickname || (nickname && !nicknameValid(nickname) ? "닉네임은 2~12자 완성형 한글·영문·숫자로 입력해 주세요." : null);

  const confirmSession = async () => {
    setPhase("checking");
    if ((await checkSession()) === "member") {
      if (intent !== null) rememberReviewIntent(intent);
      // Next keeps visited pages alive: a later visit starts a new, empty signup.
      setPhase("form");
      setVerified(null);
      setCodeSent(false);
      setFlow((n) => n + 1);
      setNickname("");
      setPassword("");
      setPasswordConfirm("");
      setConfirmations({ termsOfService: false, privacyCollection: false, age14OrOlder: false });
      router.replace(returnTo);
    } else {
      setPhase("failed");
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!status.ready || !verified || pending) return;
    setPending(true);
    setError(null);
    setFieldErrors({});
    try {
      await apiFetch<Member>("/auth/signup", {
        method: "POST",
        body: {
          email: verified.email,
          verificationToken: verified.token,
          nickname,
          password,
          passwordConfirm,
          agreements: confirmations,
        },
      });
    } catch (caught) {
      if (isApiError(caught)) {
        setFieldErrors(caught.fieldErrors);
        setError(caught.message);
        // The verification expired or was used: the email must be verified again.
        if (caught.code === "VERIFICATION_INVALID") setVerified(null);
      } else {
        setError("가입하지 못했습니다. 다시 시도해 주세요.");
      }
      setPending(false);
      return;
    }
    setPending(false);
    await confirmSession();
  };

  if (phase !== "form") {
    return (
      <AuthCard title="회원가입 완료" description="계정이 생성되었습니다.">
        {phase === "checking" ? (
          <StateMessage
            title="자동 로그인 확인 중"
            description="로그인 상태를 확인하고 있습니다. 잠시만 기다려 주세요."
            action={
              <Button variant="primary" fullWidth disabled>
                자동 로그인 확인 중
              </Button>
            }
          />
        ) : (
          <StateMessage
            tone="error"
            title="자동 로그인을 완료하지 못했습니다"
            description="다시 가입하지 않고 생성된 계정으로 로그인해 주세요."
            action={
              <ButtonLink href={`/login?returnTo=${encodeURIComponent(returnTo)}`} variant="secondary" className="w-[200px]">
                로그인하기
              </ButtonLink>
            }
          />
        )}
        <ButtonLink href="/" variant="text">
          경기 일정 보기
        </ButtonLink>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="회원가입" description="이메일을 인증하고 KickTab을 시작하세요.">
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate aria-describedby={statusId}>
        <EmailCodeStep
          key={flow}
          purpose="signup"
          verified={verified}
          onVerified={setVerified}
          onSent={() => setCodeSent(true)}
        />
        <Field
          label="닉네임"
          hint={NICKNAME_HINT}
          placeholder="평가에 표시할 이름"
          autoComplete="nickname"
          maxLength={12}
          disabled={!verified}
          value={nickname}
          onChange={(event) => {
            setNickname(event.target.value);
            // A server answer (e.g. nickname taken) is for the old value only.
            if (fieldErrors.nickname) setFieldErrors({ ...fieldErrors, nickname: "" });
          }}
          error={nicknameError}
        />
        <Field
          label="비밀번호"
          hint={PASSWORD_HINT}
          type="password"
          placeholder="비밀번호 입력"
          autoComplete="new-password"
          maxLength={64}
          disabled={!verified}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password ?? local.password}
        />
        <Field
          label="비밀번호 확인"
          type="password"
          placeholder="비밀번호 다시 입력"
          autoComplete="new-password"
          maxLength={64}
          disabled={!verified}
          value={passwordConfirm}
          onChange={(event) => setPasswordConfirm(event.target.value)}
          error={fieldErrors.passwordConfirm ?? local.confirm}
        />
        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">필수 확인</legend>
          {CONFIRMATIONS.map(({ key, label, document }) => (
            <div key={key} className="flex flex-col">
              <label className="flex min-h-11 cursor-pointer items-center gap-2 text-body text-fg lg:min-h-6">
                <input
                  type="checkbox"
                  className="size-4 accent-[var(--kt-text-primary)]"
                  checked={confirmations[key]}
                  onChange={(event) => setConfirmations({ ...confirmations, [key]: event.target.checked })}
                />
                {label}
              </label>
              {document && <LegalLink document={document} className="pl-6 text-body text-fg-muted" />}
            </div>
          ))}
        </fieldset>
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <Button type="submit" variant="primary" fullWidth disabled={!status.ready || pending}>
          {pending ? "가입하는 중…" : "가입하기"}
        </Button>
        <p id={statusId} role="status" className="text-small text-fg-secondary">
          {status.message}
        </p>
      </form>
      {!verified && !codeSent && <SocialButtons />}
    </AuthCard>
  );
}
