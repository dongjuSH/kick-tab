"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { Member } from "@/lib/api/types";
import { canChangePassword, formatDotDate, loginMethodLabel } from "./model";
import { MyCard } from "./MyCard";
import { PasswordDialog } from "./PasswordDialog";
import { WithdrawDialog } from "./WithdrawDialog";

/**
 * 계정 관리 (MY-004, Figma 639:8206 — Email 639:8207 / Success 639:8225 / SocialReference
 * 639:8244). Nickname, email, login method and join date are shown only (no nickname change).
 * '비밀번호 변경' for email accounts only; '회원 탈퇴' for everyone. No logout here (header).
 */
export function AccountPanel({ member }: { member: Member }) {
  const [dialog, setDialog] = useState<"password" | "withdraw" | null>(null);
  const [changed, setChanged] = useState(false);
  const rows: [string, string][] = [
    ["닉네임", member.nickname],
    ["이메일", member.email],
    ["로그인 방식", loginMethodLabel(member.loginMethod)],
    ["가입일", formatDotDate(member.createdAt)],
  ];

  return (
    <div className="flex flex-col gap-3">
      <MyCard title="계정 관리" titleId="my-account-title">
        <dl className="flex flex-col gap-4">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-center gap-3">
              <dt className="w-24 shrink-0 text-label text-fg-muted">{label}</dt>
              <dd className="min-w-0 flex-1 text-body font-medium break-all text-fg">{value}</dd>
            </div>
          ))}
        </dl>
        {canChangePassword(member.loginMethod) && (
          <Button
            fullWidth
            onClick={() => {
              setChanged(false);
              setDialog("password");
            }}
          >
            비밀번호 변경
          </Button>
        )}
        <div className="border-t border-line pt-4">
          <Button variant="text" fullWidth onClick={() => setDialog("withdraw")}>
            회원 탈퇴
          </Button>
        </div>
      </MyCard>
      {/* Figma 639:8225: the notice under the card once the dialog has closed. */}
      <p role="status" className="text-small text-live">
        {changed ? "비밀번호를 변경했습니다." : ""}
      </p>
      {canChangePassword(member.loginMethod) && (
        <PasswordDialog
          open={dialog === "password"}
          onClose={() => setDialog(null)}
          onDone={() => {
            setDialog(null);
            setChanged(true);
          }}
        />
      )}
      <WithdrawDialog open={dialog === "withdraw"} onClose={() => setDialog(null)} />
    </div>
  );
}
