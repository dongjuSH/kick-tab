import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { MatchDetail } from "@/features/match/MatchDetail";

export const metadata: Metadata = { title: "경기 상세" };

function Fallback() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-card border border-line bg-surface p-6" aria-busy>
      <Skeleton className="h-6 w-40" />
      <Skeleton className="h-12 w-72" />
      <Skeleton className="h-4 w-48" />
      <span className="sr-only">불러오는 중</span>
    </div>
  );
}

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Positive integer ids only; anything else is not a match (never another match instead).
  if (!/^[1-9]\d{0,17}$/.test(id)) notFound();
  return <MatchDetail id={Number(id)} />;
}

/**
 * `/matches/[id]` (chat 04). The id is only known per request, so the page renders a static
 * shell and resolves the match inside Suspense (cacheComponents); data is read in the
 * browser so live matches can refresh.
 */
export default function MatchPage({ params }: PageProps<"/matches/[id]">) {
  return (
    <div className="kt-container flex flex-1 flex-col gap-4 py-6 lg:gap-6 lg:pt-8 lg:pb-12">
      <Suspense fallback={<Fallback />}>
        <Detail params={params} />
      </Suspense>
    </div>
  );
}
