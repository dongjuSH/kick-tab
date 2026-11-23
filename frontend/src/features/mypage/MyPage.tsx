"use client";

import { ButtonLink } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { loginHref } from "@/features/auth/returnTo";
import { useAuth } from "@/features/auth/session";
import { AccountPanel } from "./AccountPanel";
import { FavoriteTeams } from "./FavoriteTeams";
import { MyReviews } from "./MyReviews";

/**
 * `/mypage` (MY-001~004, Figma 52:2674 / 52:2912). Members only: while the session is checked
 * nothing personal is drawn, guests and expired sessions get the login notice (Figma 62:1939 /
 * 62:1702) that comes back here after login. Each area loads and fails on its own.
 * PC: records (896) left, account (360) right; below 1024px one column.
 */
export function MyPage() {
  const auth = useAuth();
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <h1 className="text-heading font-bold text-fg">마이페이지</h1>
        {auth.status === "member" && (
          <p className="text-body text-fg-secondary">{auth.member.nickname} 님, 관심 팀과 나의 기록을 관리하세요.</p>
        )}
      </div>
      <MyPageBody />
    </>
  );
}

function MyPageBody() {
  const auth = useAuth();

  if (auth.status === "loading") {
    return <DataState status="loading" className="rounded-card border border-line bg-surface" />;
  }

  if (auth.status === "guest") {
    return (
      <section
        aria-labelledby="mypage-login-title"
        className="mx-auto flex w-full max-w-[375px] flex-col gap-4 rounded-card border border-line bg-surface p-6"
      >
        <h2 id="mypage-login-title" className="text-title font-bold text-fg">
          로그인이 필요합니다
        </h2>
        <p className="text-body text-fg-secondary">로그인 후 현재 화면으로 돌아와 이용할 수 있어요.</p>
        <ButtonLink href={loginHref("/mypage")} variant="primary" fullWidth>
          로그인하기
        </ButtonLink>
        <ButtonLink href="/" variant="ghost" fullWidth>
          계속 둘러보기
        </ButtonLink>
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start lg:gap-6">
      <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
        <FavoriteTeams />
        <MyReviews />
      </div>
      <AccountPanel key={auth.member.id} member={auth.member} />
    </div>
  );
}
