"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { logout, useAuth } from "@/features/auth/session";
import { isMemberOnlyPath } from "@/features/auth/returnTo";

/**
 * Header auth area (guest: Figma 133:4077 / 133:4134; member: 62:1475 desktop, 81:3209
 * mobile menu). Guest: 로그인 ghost + 회원가입 primary. Member: 마이페이지 ghost + 로그아웃
 * secondary. While the session is being checked the same space stays empty, so a member never
 * sees the guest buttons flash. The header and the mobile menu share this component.
 */
export function HeaderAuth({
  layout,
  onNavigate,
}: {
  layout: "desktop" | "menu";
  /** Mobile menu passes this to close the sheet after a link is chosen. */
  onNavigate?: () => void;
}) {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<"idle" | "busy" | "failed">("idle");
  // 96px items (Figma); "마이페이지" needs the tighter padding to stay on one line.
  const item = layout === "desktop" ? "w-24 px-2 whitespace-nowrap" : "flex-1 whitespace-nowrap";
  const box = cx("flex items-center gap-3", layout === "menu" && "w-full");

  if (auth.status === "loading") {
    return <div className={box} aria-hidden><span className={cx(item, "min-h-11")} /></div>;
  }

  if (auth.status === "guest") {
    return (
      <div className={box}>
        <ButtonLink href="/login" variant="ghost" className={item} onClick={onNavigate}>
          로그인
        </ButtonLink>
        <ButtonLink href="/signup" variant="primary" className={item} onClick={onNavigate}>
          회원가입
        </ButtonLink>
      </div>
    );
  }

  const signOut = async () => {
    setState("busy");
    const done = await logout();
    if (!done) {
      setState("failed");
      return;
    }
    setState("idle");
    onNavigate?.();
    // Public pages stay; member-only pages go to the main page (AUTH-004 rule 2).
    if (isMemberOnlyPath(pathname)) router.push("/");
  };

  return (
    <div className={cx("relative", layout === "menu" && "w-full")}>
      <div className={box}>
        <ButtonLink href="/mypage" variant="ghost" className={item} onClick={onNavigate}>
          마이페이지
        </ButtonLink>
        <Button variant="secondary" className={item} disabled={state === "busy"} onClick={signOut}>
          로그아웃
        </Button>
      </div>
      {state === "failed" && (
        <p
          role="alert"
          className={cx(
            "text-small text-error",
            layout === "desktop"
              ? "absolute top-full right-0 mt-1 w-max rounded-control border border-line bg-surface px-2 py-1 shadow-lg"
              : "mt-2",
          )}
        >
          로그아웃하지 못했습니다. 다시 시도해 주세요.
        </p>
      )}
    </div>
  );
}
