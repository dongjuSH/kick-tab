import { Suspense } from "react";
import { FavoriteSchedule } from "@/features/favorites/FavoriteSchedule";
import { MainNews } from "@/features/news/MainNews";
import { ScheduleSection, SectionSkeleton } from "@/features/schedule/ScheduleSection";

/**
 * Main page (SCH-001, Figma 49:57 / 49:570). Desktop: schedule then news on the left,
 * favourite schedule on the right; mobile: schedule, favourites, news. The compact league
 * table belongs to chat 06 and is not placed yet. Each section loads and fails on its own.
 */
export default function Home() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="text-heading font-bold">경기 일정</h1>
      <p className="mt-1.5 text-body text-fg-secondary">
        날짜와 대회를 선택하고, 관심 팀 경기를 빠르게 확인하세요.
      </p>
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="min-w-0 lg:col-start-1 lg:row-start-1">
          {/* The schedule reads its filters from the URL, so it renders per request. */}
          <Suspense fallback={<SectionSkeleton />}>
            <ScheduleSection />
          </Suspense>
        </div>
        <div className="min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <FavoriteSchedule />
        </div>
        <div className="min-w-0 lg:col-start-1 lg:row-start-2">
          <MainNews />
        </div>
      </div>
    </div>
  );
}
