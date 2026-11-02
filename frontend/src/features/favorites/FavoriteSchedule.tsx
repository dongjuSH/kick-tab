"use client";

import { useQuery } from "@tanstack/react-query";
import { MatchCard } from "@/components/common/MatchCard";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { competitionsQuery, favoriteScheduleQuery } from "@/features/schedule/queries";
import { ScheduleNotice, failedNames } from "@/features/schedule/ScheduleNotice";
import { useFavorites } from "./useFavorites";

/**
 * "관심 팀 경기 일정" (FAV-001·004, SCH-005, Figma 49:320 / 49:800, empty 57:43).
 * Each favourite's live or nearest upcoming match, live first; a match between two
 * favourites appears once. Registering happens on team browse (/teams, chat 07).
 */
export function FavoriteSchedule() {
  const favorites = useFavorites();
  const ids = favorites.status === "ready" ? favorites.ids : [];
  const schedule = useQuery(favoriteScheduleQuery(ids));
  const competitions = useQuery(competitionsQuery);
  const matches = schedule.data?.data.matches ?? [];
  // Some competitions not collected: the nearest match may be missing, so an empty list is
  // never "no upcoming matches" and a shown list may be incomplete.
  const failed = failedNames(schedule.data?.meta.failedCompetitionIds ?? [], competitions.data);
  const retry = (
    <Button variant="ghost" onClick={() => schedule.refetch()}>
      다시 시도
    </Button>
  );
  const failedText = `${failed.join("·")} 조회 실패. 확인된 경기만 보여주며, 예정 경기가 없다고 단정하지 않습니다.`;

  let body;
  if (favorites.status === "loading") {
    body = <Skeleton className="h-20 w-full" />;
  } else if (favorites.status === "unavailable") {
    body = (
      <StateMessage
        tone="plain"
        title="이 브라우저에서는 관심 팀을 저장할 수 없습니다"
        description="브라우저 저장소를 사용할 수 없어 관심 팀을 불러오지 못했습니다. 경기 일정·뉴스 등 다른 기능은 그대로 이용할 수 있습니다."
      />
    );
  } else if (ids.length === 0) {
    body = (
      <StateMessage
        title="관심 등록된 팀이 없습니다."
        description="좋아하는 팀을 등록하고 일정을 빠르게 확인하세요."
        action={
          <ButtonLink href="/teams" className="w-[220px] max-w-full">
            팀 탐색에서 등록
          </ButtonLink>
        }
      />
    );
  } else if (schedule.isPending) {
    body = <Skeleton className="h-20 w-full" />;
  } else if (schedule.isError && matches.length === 0) {
    body = (
      <DataState
        status="error"
        errorTitle="관심 팀 일정을 불러오지 못했습니다"
        error={schedule.error}
        onRetry={() => schedule.refetch()}
      />
    );
  } else if (matches.length === 0 && failed.length) {
    body = <ScheduleNotice tone="warning" title="관심 팀 일정을 모두 확인하지 못했습니다" description={failedText} action={retry} />;
  } else if (matches.length === 0) {
    body = (
      <DataState
        status="empty"
        emptyTitle="관심 팀의 예정 경기가 없습니다"
        emptyDescription="앞으로 약 2주 안에 확인된 경기가 없습니다."
      />
    );
  } else {
    body = (
      <div className="flex flex-col gap-3">
        {schedule.isError && (
          <ScheduleNotice
            tone="warning"
            title="최신 일정으로 갱신하지 못했습니다"
            description="마지막으로 확인한 경기를 보여줍니다. 경기 상태가 바뀌었을 수 있습니다."
            action={retry}
          />
        )}
        {failed.length > 0 && (
          <ScheduleNotice tone="warning" title="일부 대회의 일정을 확인하지 못했습니다" description={failedText} action={retry} />
        )}
        <ul className="flex flex-col gap-2">
          {matches.map((match) => (
            <li key={match.id}>
              <MatchCard match={match} layout="stacked" withDate />
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <section
      aria-labelledby="favorite-schedule-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <h2 id="favorite-schedule-title" className="text-subtitle font-bold">
        관심 팀 경기 일정
      </h2>
      {favorites.status === "ready" && ids.length > 0 && (
        <div className="flex items-center gap-2">
          <p className="flex-1 text-small text-fg-muted">
            이 브라우저에 저장 · {ids.length}/{favorites.max}
          </p>
          <ButtonLink href="/teams" variant="ghost">
            관리
          </ButtonLink>
        </div>
      )}
      {body}
    </section>
  );
}
