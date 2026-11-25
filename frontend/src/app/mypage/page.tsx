import type { Metadata } from "next";
import { MyPage } from "@/features/mypage/MyPage";

export const metadata: Metadata = { title: "마이페이지" };

/**
 * `/mypage` (chat 09): member-only page; the session decides what is drawn (client). Like the
 * other pages the visible page starts with its content (no title or intro, 2026-11-25); the
 * page heading stays for screen readers.
 */
export default function MyPagePage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="sr-only">마이페이지</h1>
      <MyPage />
    </div>
  );
}
