import type { Metadata } from "next";
import { Suspense } from "react";
import { SignupForm } from "@/features/auth/SignupForm";

export const metadata: Metadata = { title: "회원가입" };

/** `/signup` (chat 02, AUTH-001). Keeps the login's returnTo/intent for after signup. */
export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
