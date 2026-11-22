import type { Metadata } from "next";
import { PasswordResetForm } from "@/features/auth/PasswordResetForm";

export const metadata: Metadata = { title: "비밀번호 찾기" };

/** `/password-reset` (chat 02, AUTH-001 rule 4): email code → new password. */
export default function PasswordResetPage() {
  return <PasswordResetForm />;
}
