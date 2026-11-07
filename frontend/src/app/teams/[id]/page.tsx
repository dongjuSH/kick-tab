import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { TeamDetail } from "@/features/team-detail/TeamDetail";

export const metadata: Metadata = { title: "팀 상세" };

function Fallback() {
  return (
    <div className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6" aria-busy>
      <div className="flex items-center gap-4">
        <Skeleton className="size-[72px] rounded-full" />
        <Skeleton className="h-8 w-48" />
      </div>
      <Skeleton className="h-11 w-48" />
      <span className="sr-only">불러오는 중</span>
    </div>
  );
}

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Positive integer ids only; anything else is no team (never another team instead).
  if (!/^[1-9]\d{0,8}$/.test(id)) notFound();
  return <TeamDetail id={Number(id)} />;
}

/**
 * `/teams/[id]` (chat 08). The id is only known per request, so the page renders a static
 * shell and resolves the team inside Suspense (cacheComponents, like `/matches/[id]`).
 */
export default function TeamPage({ params }: PageProps<"/teams/[id]">) {
  return (
    <div className="kt-container flex flex-1 flex-col gap-4 py-6 lg:gap-6 lg:pt-8 lg:pb-12">
      <Suspense fallback={<Fallback />}>
        <Detail params={params} />
      </Suspense>
    </div>
  );
}
