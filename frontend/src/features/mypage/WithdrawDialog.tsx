"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { signedOut } from "@/features/auth/session";
import { apiFetch } from "@/lib/api/client";

/**
 * 회원 탈퇴 (MY-004 rule 3, P-03, Figma 62:1800): what is deleted, then '계속 이용하기' or
 * '탈퇴 확인'. No extra password step (the valid session is the proof). After DELETE /me the
 * server has cleared the cookies: this browser becomes a guest at once (member data dropped,
 * the browser's own favourite teams come back) and the main page opens. A failure stays here.
 */
export function WithdrawDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [phase, setPhase] = useState<"idle" | "busy" | "failed">("idle");
  const busy = phase === "busy";

  const close = () => {
    if (busy) return;
    setPhase("idle");
    onClose();
  };

  const withdraw = async () => {
    setPhase("busy");
    try {
      await apiFetch<null>("/me", { method: "DELETE" });
    } catch {
      setPhase("failed");
      return;
    }
    // Done on the server: no session check that could fail and keep the old member.
    signedOut({ forget: true });
    setPhase("idle");
    onClose();
    router.push("/");
  };

  return (
    <Dialog open={open} onClose={close} title="회원 탈퇴" layout="responsive" width={375} closeDisabled={busy}>
      <div className="flex flex-col gap-4" aria-busy={busy || undefined}>
        <p className="text-lead font-bold text-fg">정말 탈퇴하시겠어요?</p>
        <p className="text-body text-fg-secondary">
          계정·관심 팀·경기 평가·반응이 삭제되고 복구되지 않습니다. 보낸 의견은 계정 연결을 해제한 뒤 보관합니다. 다시
          가입해도 이전 데이터는 복구되지 않습니다. 탈퇴 완료 후 경기 일정으로 이동합니다.
        </p>
        {/* Figma 62:1800: keep using (secondary) left, withdraw (danger) right, same width. */}
        <div className="grid grid-cols-2 gap-2">
          <Button variant="secondary" disabled={busy} onClick={close}>
            계속 이용하기
          </Button>
          <Button variant="danger" disabled={busy} aria-busy={busy || undefined} onClick={withdraw}>
            {busy ? "탈퇴 처리 중…" : "탈퇴 확인"}
          </Button>
        </div>
        {phase === "failed" && (
          <p role="alert" className="text-small text-error">
            탈퇴하지 못했습니다. 잠시 후 다시 시도해 주세요.
          </p>
        )}
      </div>
    </Dialog>
  );
}
