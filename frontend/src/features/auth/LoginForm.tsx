"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { Member } from "@/lib/api/types";
// SocialButtons: deferred, see the note in the form below.
import { AuthCard, Field, FormMessage } from "./AuthForm";
import { rememberReviewIntent, reviewIntent, safeReturnTo } from "./returnTo";
import { checkSession, useAuth } from "./session";

/**
 * Login (AUTH-002, Figma 52:2116 / 52:2265). Success is shown only after GET /auth/me
 * confirms the session; then the page returns to `returnTo` (internal paths only). A review
 * intent reopens that match's review area without submitting anything (AUTH-005).
 */
export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const auth = useAuth();
  const returnTo = safeReturnTo(params.get("returnTo"));
  const intent = reviewIntent(params.get("intent"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already signed in (e.g. back button): continue to where the login was going.
  useEffect(() => {
    if (auth.status === "member" && !pending) router.replace(returnTo);
  }, [auth.status, pending, returnTo, router]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    if (!email.trim() || !password) {
      setError("이메일과 비밀번호를 입력해 주세요.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await apiFetch<Member>("/auth/login", { method: "POST", body: { email, password } });
      if ((await checkSession()) !== "member") {
        setError("로그인 상태를 확인하지 못했습니다. 다시 시도해 주세요.");
        setPending(false);
        return;
      }
      if (intent !== null) rememberReviewIntent(intent);
      // Next keeps visited pages alive: leave the form clean for the next visit.
      setPending(false);
      setPassword("");
      router.replace(returnTo);
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : "로그인하지 못했습니다. 다시 시도해 주세요.");
      setPending(false);
    }
  };

  const signupHref = params.toString() ? `/signup?${params.toString()}` : "/signup";

  return (
    <AuthCard title="로그인" description="관심 팀과 나의 축구 기록을 이어가세요.">
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <Field
          label="이메일"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <Field
          label="비밀번호"
          type="password"
          autoComplete="current-password"
          placeholder="비밀번호 입력"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <Button type="submit" variant="primary" fullWidth disabled={pending}>
          {pending ? "로그인 중…" : "로그인"}
        </Button>
      </form>
      <div className="grid grid-cols-2">
        <ButtonLink href="/password-reset" variant="text">
          비밀번호 찾기
        </ButtonLink>
        <ButtonLink href={signupHref} variant="text">
          회원가입
        </ButtonLink>
      </div>
      {/* Social sign-in (Kakao/Google) is deferred until after launch (user decision 2026-11-26, guide P-02): the buttons are hidden until that work.
      <SocialButtons /> */}
    </AuthCard>
  );
}
