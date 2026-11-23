import type { Metadata } from "next";
import { MyPage } from "@/features/mypage/MyPage";

export const metadata: Metadata = { title: "마이페이지" };

/** `/mypage` (chat 09): member-only page; the session decides what is drawn (client). */
export default function MyPagePage() {
  return (
    <div className="kt-container flex flex-1 flex-col gap-6 py-6 lg:py-8">
      <MyPage />
    </div>
  );
}
