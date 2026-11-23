"use client";

import { useEffect } from "react";
import { checkSession } from "@/features/auth/session";

/** "2026.12.01 18:30" in KST, the time the restriction ends. */
function formatRestriction(iso: string): string {
  const kst = new Date(Date.parse(iso) + 9 * 3600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${kst.getUTCFullYear()}.${pad(kst.getUTCMonth() + 1)}.${pad(kst.getUTCDate())} ${pad(kst.getUTCHours())}:${pad(kst.getUTCMinutes())}`;
}

/**
 * Review restriction (terms 제9조, `Member.reviewRestrictedUntil`): the notice shown where a
 * review would be written or edited — match page and my page.
 */
export function ReviewRestrictionNotice({ until }: { until: string }) {
  return (
    <p role="status" className="rounded-control bg-warning-bg p-3 text-small text-warning">
      운영 정책에 따라 {formatRestriction(until)}까지 경기 평가를 작성·수정할 수 없습니다.
      문의는 kicktab2026@gmail.com으로 보내 주세요.
    </p>
  );
}

/**
 * The restriction ends while the page is open: ask the server again at that moment, so the
 * form comes back without a reload (Codex N2). Checked each minute (long timeouts are capped
 * by the browser).
 */
export function useRestrictionEnd(until: string | null) {
  useEffect(() => {
    if (!until) return;
    const end = Date.parse(until);
    const timer = setInterval(() => {
      if (Date.now() >= end) void checkSession();
    }, 60_000);
    return () => clearInterval(timer);
  }, [until]);
}
