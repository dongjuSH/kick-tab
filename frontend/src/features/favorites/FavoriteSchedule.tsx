"use client";

import { keepPreviousData, useQuery, type UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { MatchStatusBadge } from "@/components/common/MatchStatusBadge";
import { TeamCrest } from "@/components/common/TeamCrest";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { competitionsQuery, favoriteScheduleQuery, type ScheduleData } from "@/features/schedule/queries";
import { ScheduleNotice, failedNames } from "@/features/schedule/ScheduleNotice";
import type { FavoriteSchedule as FavoriteScheduleData, MatchSummary, TeamRef } from "@/lib/api/types";
import { formatShortDate } from "@/lib/format/kst";
import { awaitingStatus, competitionName, kickoffTime, teamName } from "@/lib/format/match";
import { useNow } from "@/lib/hooks/useNow";
import type { FavoriteChange } from "./store";
import { useFavorites } from "./useFavorites";

/**
 * "관심 팀" panel (FAV-001~004, SCH-005; Figma `KickTab/Guest Favorites` 306:6220 —
 * Registered · Empty · Search · Limit · SaveError). The registered teams with remove, "팀
 * 추가" search right here (registrable teams only, from zero teams too), and each team's live
 * or nearest upcoming match, live first (a match between two favourites appears once).
 * Changes land in the shared browser store (max 5), so match-card stars and the schedule's
 * favourite buttons follow; a failed save keeps the previous list.
 */
export function FavoriteSchedule() {
  const favorites = useFavorites();
  const ids = favorites.status === "ready" ? favorites.ids : [];
  // Keep the shown names and matches while a changed list is fetched.
  const schedule = useQuery({ ...favoriteScheduleQuery(ids), placeholderData: keepPreviousData });
  const competitions = useQuery(competitionsQuery);
  const [adding, setAdding] = useState(false);
  // The change that could not be saved, kept so "다시 시도" repeats it.
  const [failedChange, setFailedChange] = useState<(() => FavoriteChange) | null>(null);
  const [picked, setPicked] = useState<TeamRef[]>([]);

  const known = new Map([...picked, ...(schedule.data?.data.teams ?? [])].map((t) => [t.id, t]));
  const matches = (schedule.data?.data.matches ?? []).filter(
    (m) => ids.includes(m.home.id) || ids.includes(m.away.id),
  );
  // Some competitions not collected: the nearest match may be missing, so an empty list is
  // never "no upcoming matches" and a shown list may be incomplete.
  const failed = failedNames(schedule.data?.meta.failedCompetitionIds ?? [], competitions.data);
  const retry = (
    <Button variant="ghost" onClick={() => schedule.refetch()}>
      다시 시도
    </Button>
  );
  const failedText = `${failed.join("·")} 조회 실패. 확인된 경기만 보여주며, 예정 경기가 없다고 단정하지 않습니다.`;
  const full = favorites.status === "ready" && ids.length >= favorites.max;

  const run = (change: () => FavoriteChange) => {
    const result = change();
    const saveFailed = result === "failed" || result === "unavailable";
    setFailedChange(saveFailed ? () => change : null);
    return result;
  };
  const add = (team: TeamRef) => {
    const result = run(() => favorites.add(team.id));
    if (result === "added" || result === "exists") {
      setPicked((list) => [team, ...list.filter((t) => t.id !== team.id)]);
      setAdding(false);
    }
  };

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
  } else {
    body = (
      <>
        {full && <p className="text-small text-fg-secondary">최대 5팀까지 등록할 수 있습니다.</p>}
        {adding && !full && <AddTeam registered={ids} onAdd={add} />}
        {failedChange && (
          // Figma 306:6183 SaveError: the previous list stays; retry repeats the change.
          <div role="alert" className="flex flex-col gap-2 rounded-control bg-error-bg p-4">
            <p className="text-body font-bold text-error">관심 팀을 저장하지 못했습니다</p>
            <p className="text-small text-fg-secondary">기존 목록을 유지했습니다. 다시 시도해 주세요.</p>
            <Button variant="ghost" onClick={() => run(failedChange)}>
              다시 시도
            </Button>
          </div>
        )}
        {ids.length === 0 ? (
          // Figma 306:6061 Empty.
          <div className="flex flex-col gap-2 rounded-control bg-canvas p-4">
            <p className="text-body font-bold text-fg">등록한 관심 팀이 없습니다</p>
            <p className="text-small text-fg-secondary">팀을 추가하면 가까운 경기 일정을 볼 수 있습니다.</p>
          </div>
        ) : (
          <>
            <ul aria-label="등록된 관심 팀" className="flex flex-col divide-y divide-line">
              {ids.map((id) => {
                const team = known.get(id);
                const name = team ? teamName(team) : "팀 정보 확인 중";
                return (
                  <li key={id} className="flex min-h-11 items-center gap-2">
                    <TeamCrest src={team?.crestUrl ?? null} name={name} size={20} />
                    <span className="min-w-0 flex-1 truncate text-body font-medium text-fg">{name}</span>
                    <Button variant="ghost" aria-label={`${name} 관심 팀 해제`} onClick={() => run(() => favorites.remove(id))}>
                      해제
                    </Button>
                  </li>
                );
              })}
            </ul>
            <div className="flex flex-col gap-2">
              <p className="text-caption text-fg-secondary">등록 팀별로 가장 가까운 경기만 표시합니다.</p>
              <Summary
                schedule={schedule}
                matches={matches}
                failed={failed.length > 0}
                failedText={failedText}
                retry={retry}
              />
            </div>
          </>
        )}
      </>
    );
  }

  return (
    <section
      aria-labelledby="favorite-schedule-title"
      className="flex min-w-0 flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <div className="flex items-center gap-2">
        <svg aria-hidden width="18" height="18" viewBox="0 0 16 16" className="shrink-0 text-action">
          <path d="M8 1.6l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.2l-3.9 2.2.9-4.3-3.3-3 4.4-.5z" fill="currentColor" />
        </svg>
        <h2 id="favorite-schedule-title" className="flex-1 text-subtitle font-bold">
          관심 팀
        </h2>
        {favorites.status === "ready" && (
          <>
            <span className="text-small font-medium text-fg-secondary" aria-label={`${ids.length}팀 등록, 최대 ${favorites.max}팀`}>
              {ids.length}/{favorites.max}
            </span>
            <Button
              aria-expanded={adding && !full}
              disabled={full}
              onClick={() => {
                setAdding((open) => !open);
                setFailedChange(null);
              }}
            >
              팀 추가
            </Button>
          </>
        )}
      </div>
      {body}
    </section>
  );
}

/**
 * "팀 추가" search: the same team search field and candidate list as the schedule's team
 * search (user decision 2026-11-10 — one UI for one function, instead of Figma 306:6075's
 * register buttons). Only registrable teams that are not registered yet are offered.
 */
function AddTeam({ registered, onAdd }: { registered: readonly number[]; onAdd: (team: TeamRef) => void }) {
  return (
    <TeamSearch
      selected={null}
      onSelect={(team) => team && onAdd(team)}
      candidates={(team) => team.detailAvailable === true && !registered.includes(team.id)}
    />
  );
}

function Summary({
  schedule,
  matches,
  failed,
  failedText,
  retry,
}: {
  schedule: UseQueryResult<ScheduleData<FavoriteScheduleData>>;
  matches: readonly MatchSummary[];
  failed: boolean;
  failedText: string;
  retry: ReactNode;
}) {
  if (schedule.isPending) return <Skeleton className="h-16 w-full" />;
  if (schedule.isError && matches.length === 0) {
    return (
      <DataState status="error" errorTitle="관심 팀 일정을 불러오지 못했습니다" error={schedule.error} onRetry={() => schedule.refetch()} />
    );
  }
  if (matches.length === 0 && failed) {
    return <ScheduleNotice tone="warning" title="관심 팀 일정을 모두 확인하지 못했습니다" description={failedText} action={retry} />;
  }
  if (matches.length === 0) {
    return <p className="rounded-control bg-canvas p-3 text-small text-fg-secondary">관심 팀의 예정 경기가 없습니다.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {schedule.isError && (
        <ScheduleNotice
          tone="warning"
          title="최신 일정으로 갱신하지 못했습니다"
          description="마지막으로 확인한 경기를 보여줍니다. 경기 상태가 바뀌었을 수 있습니다."
          action={retry}
        />
      )}
      {failed && <ScheduleNotice tone="warning" title="일부 대회의 일정을 확인하지 못했습니다" description={failedText} action={retry} />}
      <ul className="flex flex-col gap-2">
        {matches.map((match) => (
          <li key={match.id}>
            <SummaryMatch match={match} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Compact nearest-match row (Figma 49:57 right panel): teams, competition · date time, status. */
function SummaryMatch({ match }: { match: MatchSummary }) {
  const now = useNow();
  const title = `${teamName(match.home)} vs ${teamName(match.away)}`;
  const when = `${formatShortDate(match.kickoffDateKst)} ${kickoffTime(match)}`;
  return (
    <Link
      href={`/matches/${match.id}`}
      prefetch={false}
      className="flex flex-col gap-1 rounded-control bg-subtle p-3 hover:bg-selected"
    >
      <span className="text-small font-bold text-fg">{title}</span>
      <span className="flex items-center gap-2 text-caption text-fg-secondary">
        <span className="min-w-0 flex-1 truncate">
          {competitionName(match.competition)} · {when}
        </span>
        <MatchStatusBadge match={match} size="caption" awaiting={awaitingStatus(match, now)} />
      </span>
    </Link>
  );
}
