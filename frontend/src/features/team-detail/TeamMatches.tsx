"use client";

import { useQuery } from "@tanstack/react-query";
import { MatchCard } from "@/components/common/MatchCard";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { dataStatus } from "@/features/standings/model";
import type { MatchSummary } from "@/lib/api/types";
import { teamFixturesQuery } from "./queries";

export const AREA = "flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6";

/**
 * TEAM-003 (Figma 52:1353): up to three upcoming matches (live first) and the last five
 * results of the current season, kept apart; every card opens the match detail and "경기 전체
 * 보기" opens the season's past results for this team (UF-09, `/results?team=`).
 */
export function TeamMatches({ teamId }: { teamId: number }) {
  const query = useQuery(teamFixturesQuery(teamId));
  const data = query.data?.data;
  const failed = query.data?.meta.failedCompetitionIds.length ?? 0;
  const retry = () => void query.refetch();

  return (
    <section aria-labelledby="team-matches" className={AREA}>
      <h2 id="team-matches" className="text-title font-bold">경기</h2>
      <DataState
        status={dataStatus(query, false, query.isError || failed > 0)}
        error={query.error}
        onRetry={retry}
        errorTitle="경기 정보를 불러오지 못했습니다"
        partialNotice={
          query.isError
            ? "경기 정보를 다시 확인하지 못했습니다. 마지막으로 확인한 경기입니다."
            : "일부 대회의 시즌 일정을 최신으로 확인하지 못해 빠진 경기가 있을 수 있습니다."
        }
        partialAction={query.isError ? <Button onClick={retry}>다시 확인</Button> : undefined}
        loadingFallback={
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        }
      >
        {data && (
          <div className="flex flex-col gap-4">
            <MatchList title="예정 경기" matches={data.upcoming} empty="예정된 경기가 없습니다." />
            <MatchList title="최근 결과" matches={data.recent} empty="이번 시즌 종료된 경기가 없습니다." />
          </div>
        )}
      </DataState>
      <ButtonLink href={`/results?team=${teamId}`} variant="secondary" fullWidth>
        경기 전체 보기
      </ButtonLink>
    </section>
  );
}

function MatchList({ title, matches, empty }: { title: string; matches: MatchSummary[]; empty: string }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-body font-bold text-fg">{title}</h3>
      {matches.length ? (
        <ul className="flex flex-col gap-2">
          {matches.map((match) => (
            <li key={match.id}>
              <MatchCard match={match} layout="schedule" withDate />
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-control bg-subtle px-3 py-3 text-label text-fg-secondary">{empty}</p>
      )}
    </div>
  );
}
