import type { Metadata } from "next";
import { Suspense } from "react";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { StandingsSection } from "@/features/standings/StandingsSection";

export const metadata: Metadata = { title: "리그 순위" };

/**
 * `/standings?league=&season=&type=` league standings (chat 06, Figma 53:1353 / 53:2047). The
 * state is read from the URL inside Suspense, so the page shell is static.
 */
export default function StandingsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="text-heading font-bold">리그 순위</h1>
      <p className="mt-1.5 text-body text-fg-secondary">같은 시즌의 팀 순위와 선수 순위를 함께 확인하세요.</p>
      <div className="mt-6">
        <Suspense fallback={<SectionSkeleton />}>
          <StandingsSection />
        </Suspense>
      </div>
    </div>
  );
}
