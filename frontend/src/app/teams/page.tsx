import type { Metadata } from "next";
import { Suspense } from "react";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { TeamsSection } from "@/features/teams/TeamsSection";

export const metadata: Metadata = { title: "팀 탐색" };

/**
 * `/teams?league=&q=&team=&page=` team browse (chat 07, Figma 52:624 / 52:949). Like the other
 * pages, the visible page starts with the filters (no title or intro, LEAG-003 rule 1); the
 * page heading stays for screen readers. The conditions are read from the URL inside
 * Suspense, so the page shell is static.
 */
export default function TeamsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="sr-only">팀 탐색</h1>
      <Suspense fallback={<SectionSkeleton />}>
        <TeamsSection />
      </Suspense>
    </div>
  );
}
