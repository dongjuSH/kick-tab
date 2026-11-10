import { Suspense } from "react";
import { StickyPanel } from "@/components/layout/StickyPanel";
import { FavoriteSchedule } from "@/features/favorites/FavoriteSchedule";
import { MainNews } from "@/features/news/MainNews";
import { ScheduleSection, SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { MainStandings } from "@/features/standings/MainStandings";

/**
 * Main page (SCH-001·005, Figma 49:57 / 49:570, 2026-11-09). The page title is for assistive
 * technology only; the visible page starts at "전체 경기 일정". Desktop: two bands —
 * schedule | favourites, news | five-league standings. Mobile order: schedule, favourites,
 * news, standings. Each section loads and fails on its own.
 */
export default function Home() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="sr-only">경기 일정</h1>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          {/* The schedule reads its filters from the URL, so it renders per request. */}
          <Suspense fallback={<SectionSkeleton />}>
            <ScheduleSection />
          </Suspense>
        </div>
        <div className="min-w-0">
          <StickyPanel>
            <FavoriteSchedule />
          </StickyPanel>
        </div>
        <div className="min-w-0">
          <MainNews />
        </div>
        <div className="min-w-0">
          <StickyPanel>
            <MainStandings />
          </StickyPanel>
        </div>
      </div>
    </div>
  );
}
