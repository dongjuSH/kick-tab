import type { Metadata } from "next";
import { Suspense } from "react";
import { ResultsSection } from "@/features/results/ResultsSection";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";

export const metadata: Metadata = { title: "지난 경기" };

/**
 * `/results` past results (chat 05, Figma 61:883 / 53:995). Like the main page, the visible
 * page starts with the season and filters (no intro text, HIST-001 rule 4); the page heading
 * stays for screen readers. The filters are read from the URL inside Suspense, so the page
 * shell is static and the section renders per request.
 */
export default function ResultsPage() {
  return (
    <div className="kt-container flex-1 py-6 lg:py-8">
      <h1 className="sr-only">지난 경기</h1>
      <Suspense fallback={<SectionSkeleton />}>
        <ResultsSection />
      </Suspense>
    </div>
  );
}
