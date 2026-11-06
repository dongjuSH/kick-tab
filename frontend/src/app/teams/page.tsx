import type { Metadata } from "next";
import { Suspense } from "react";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { TeamsSection } from "@/features/teams/TeamsSection";

export const metadata: Metadata = { title: "팀 탐색" };

/**
 * `/teams?league=&q=&page=` team browse (chat 07, Figma 52:624 / 52:949). The conditions are
 * read from the URL inside Suspense, so the page shell is static.
 */
export default function TeamsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="text-heading font-bold">팀 탐색</h1>
      <p className="mt-1.5 text-body text-fg-secondary">좋아하는 팀을 등록하고 경기와 소식을 모아보세요.</p>
      <div className="mt-6">
        <Suspense fallback={<SectionSkeleton />}>
          <TeamsSection />
        </Suspense>
      </div>
    </div>
  );
}
