import type { Metadata } from "next";
import { Suspense } from "react";
import { ResultsSection } from "@/features/results/ResultsSection";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";

export const metadata: Metadata = { title: "지난 경기" };

/**
 * `/results` past results (chat 05, Figma 53:593 / 53:995). The filters are read from the URL
 * inside Suspense, so the page shell is static and the section renders per request.
 */
export default function ResultsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="text-heading font-bold">지난 경기</h1>
      <p className="mt-1.5 text-body text-fg-secondary">선택한 시즌의 경기 결과와 상세 기록을 확인하세요.</p>
      <div className="mt-6">
        <Suspense fallback={<SectionSkeleton />}>
          <ResultsSection />
        </Suspense>
      </div>
    </div>
  );
}
