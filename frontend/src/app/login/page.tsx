import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/auth/LoginForm";

export const metadata: Metadata = { title: "로그인" };

/** `/login?returnTo=&intent=` (chat 02, AUTH-002·005). The form reads the URL in Suspense. */
export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
