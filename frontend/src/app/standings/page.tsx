import type { Metadata } from "next";
import { Suspense } from "react";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { StandingsSection } from "@/features/standings/StandingsSection";

export const metadata: Metadata = { title: "리그 순위" };

/**
 * `/standings?league=&season=&stage=&type=` league standings and UEFA stages (chat 06, Figma
 * 53:1353 / 53:2047). The page title is for assistive technology only (LEAG-002 rule 1); the
 * visible page starts at the white area. The state is read from the URL inside Suspense, so
 * the page shell is static.
 */
export default function StandingsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="sr-only">리그 순위</h1>
      <Suspense fallback={<SectionSkeleton />}>
        <StandingsSection />
      </Suspense>
    </div>
  );
}
