"use client";

import { useQuery } from "@tanstack/react-query";
import { Fragment, useState, type ReactNode } from "react";
import { CompetitionFilter } from "@/components/common/CompetitionFilter";
import { MatchCard } from "@/components/common/MatchCard";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { chipClass } from "@/components/ui/chip";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { useFavorites } from "@/features/favorites/useFavorites";
import { isApiError } from "@/lib/api/errors";
import { useHydrated } from "@/lib/hooks/useHydrated";
import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { addDaysIso, formatKstTime, formatShortDate, parseIsoDate } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";
import { DateBar, type DateAvailability } from "./DateBar";
import { competitionsQuery, favoriteScheduleQuery, fixtureAvailabilityQuery, fixturesByDateQuery, teamScheduleQuery } from "./queries";
import { ScheduleNotice, failedNames } from "./ScheduleNotice";
import { SCHEDULE_BEFORE, SCHEDULE_DAYS, useScheduleParams } from "./useScheduleParams";

const PAGE_SIZE = 6;
const STALE_LIVE_MS = 3 * 60_000;

export function ListSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy>
      <Skeleton className="h-5 w-full" />
      <Skeleton className="h-5 w-4/5" />
      <Skeleton className="h-5 w-11/12" />
      <p className="text-label text-fg-secondary">정보를 불러오고 있습니다.</p>
    </div>
  );
}

/** The section's frame with a list placeholder: Suspense fallback and pre-hydration render. */
export function SectionSkeleton() {
  return (
    <div className="rounded-card border border-line bg-surface p-4 lg:p-6">
      <ListSkeleton />
    </div>
  );
}

/** "10/29" (no weekday) for compact ranges. */
function monthDay(iso: string) {
  const p = parseIsoDate(iso);
  return p ? `${p.month}/${p.day}` : iso;
}

/** "21:35 갱신"; flagged when the stored data was already old when this screen fetched it. */
function UpdatedAt({ value, checkedAt }: { value: string | null | undefined; checkedAt: number }) {
  if (!value) return null;
  const late = checkedAt - Date.parse(value) > STALE_LIVE_MS;
  return (
    <p className={cx("shrink-0 text-caption", late ? "text-warning" : "text-fg-muted")}>
      {formatKstTime(value)} 갱신{late && " · 갱신 지연"}
    </p>
  );
}

/**
 * Main schedule (SCH-002~006, UF-07·UF-20, schedule UX policy 2026-11-02; Figma
 * `KickTab/Schedule Explorer` 225:2013 and `Schedule Feedback` 225:2374).
 *
 * - Date view: one KST date of every supported competition, picked on the date bar.
 * - Team view (search pick or favourite button): that team's matches today−3 .. today+17,
 *   grouped by date. The date in the URL is left untouched, so clearing the team returns to
 *   the previous date and date-bar position; the competition condition carries over.
 * Competition filters are applied here to the loaded list, so an empty day, an empty filter
 * result, a failed lookup and an incomplete (partly failed) lookup each read differently.
 */
export function ScheduleSection() {
  const hydrated = useHydrated();
  const params = useScheduleParams();
  const favorites = useFavorites();
  const [resetKey, setResetKey] = useState(0);
  const [picked, setPicked] = useState<TeamRef | null>(null);
  const teamMode = params.team !== null;

  const competitions = useQuery(competitionsQuery);
  const availability = useQuery({ ...fixtureAvailabilityQuery(params.today), enabled: !teamMode });
  const byDate = useQuery({ ...fixturesByDateQuery(params.date), enabled: !teamMode && params.dateInRange });
  const byTeam = useQuery({ ...teamScheduleQuery(params.team ?? 0, params.today), enabled: teamMode });
  const favoriteIds = favorites.status === "ready" ? favorites.ids : [];
  const favoriteTeams = useQuery(favoriteScheduleQuery(favoriteIds)).data?.data.teams ?? [];

  const selectedTeam = teamMode
    ? ((picked?.id === params.team ? picked : null) ??
      byTeam.data?.data.team ??
      favoriteTeams.find((t) => t.id === params.team) ??
      null)
    : null;

  const query = teamMode ? byTeam : byDate;
  const all = (teamMode ? byTeam.data?.data.matches : byDate.data?.data) ?? [];
  const filtered = all.filter(
    (m) => params.competitions.length === 0 || params.competitions.includes(m.competition.id),
  );
  const coveredDates = new Map(availability.data?.dates.map((item) => [item.date, item]));
  const dateState = (date: string, ids: readonly number[]): DateAvailability => {
    const row = coveredDates.get(date);
    if (!row || availability.isError) return availability.isPending ? "pending" : "unknown";
    const any = (values: readonly number[]) => values.some((id) => !ids.length || ids.includes(id));
    const exists = any(row.competitionIds);
    return any(row.unknownCompetitionIds) ? (exists ? "partial" : "unknown") : exists ? "ready" : "empty";
  };
  const dates = new Map(params.dates.map((date) => [date, dateState(date, params.competitions)]));
  const selectCompetitions = (ids: number[]) => {
    const change: { competitions: number[]; date?: string | null } = { competitions: ids };
    if (!teamMode && dateState(params.date, ids) === "empty") {
      for (const date of params.dates) {
        if (date < params.today) continue;
        const state = dateState(date, ids);
        if (state === "unknown" || state === "pending") break;
        if (state === "ready" || state === "partial") {
          change.date = date === params.today ? null : date;
          break;
        }
      }
    }
    params.update(change);
  };
  const teamCompetitions = new Set(byTeam.data?.data.matches.map((match) => match.competition.id));
  const teamUnknown = new Set(byTeam.data?.meta.failedCompetitionIds);
  const unavailable = teamMode && byTeam.isSuccess
    ? new Set(competitions.data?.filter((item) => item.currentSeason
      && !teamCompetitions.has(item.id) && !teamUnknown.has(item.id)).map((item) => item.id))
    : undefined;

  // "경기 더 보기" starts over whenever the list changes or the filters are reset, even when
  // the reset leaves the URL as it was (already today and every competition).
  const listKey = `${params.today}|${params.team ?? params.date}|${params.competitions.join(",")}|${resetKey}`;
  const [shown, setShown] = useState({ key: listKey, all: false });
  if (shown.key !== listKey) setShown({ key: listKey, all: false });
  const expanded = shown.key === listKey && shown.all;
  const visibleCount = expanded ? filtered.length : PAGE_SIZE;
  const visible = filtered.slice(0, visibleCount);
  const failed = failedNames(query.data?.meta.failedCompetitionIds ?? [], competitions.data, params.competitions);

  const reset = () => {
    params.reset();
    setPicked(null);
    setResetKey((k) => k + 1);
  };
  const selectTeam = (team: TeamRef | null) => {
    setPicked(team);
    params.update({ team: team?.id ?? null });
  };

  const rangeStart = byTeam.data?.data.start ?? addDaysIso(params.today, -SCHEDULE_BEFORE);
  const rangeEnd = byTeam.data?.data.end ?? addDaysIso(params.today, SCHEDULE_DAYS - SCHEDULE_BEFORE - 1);
  const retry = (
    <Button variant="ghost" onClick={() => query.refetch()}>
      다시 시도
    </Button>
  );
  const failedText = `${failed.join("·")}에 아직 확인되지 않은 일정이 있습니다. 확인된 일정은 그대로 표시합니다.`;

  let body: ReactNode;
  if (!teamMode && !params.dateInRange) {
    body = (
      <ScheduleNotice
        title="조회할 수 없는 날짜입니다"
        description="메인 일정은 지난 3일부터 향후 17일까지 제공합니다. 더 이전 결과는 지난 경기에서 확인해 주세요."
      />
    );
  } else if (query.isPending) {
    body = teamMode ? (
      <ScheduleNotice
        busy
        title="팀 경기 일정을 불러오고 있습니다"
        description="선택한 팀·대회와 21일 조회 범위를 유지합니다."
      />
    ) : (
      <ListSkeleton />
    );
  } else if (query.isError && filtered.length === 0) {
    // A failed refresh keeps a shown list (below), but never turns into "no matches".
    const notFound = isApiError(query.error) && query.error.status === 404;
    body = (
      <ScheduleNotice
        tone="error"
        title="경기 일정을 확인하지 못했습니다"
        description={
          notFound ? query.error.message : "조회에 실패했습니다. 선택한 조건을 유지하고 다시 시도해 주세요."
        }
        action={notFound ? undefined : retry}
      />
    );
  } else if (filtered.length === 0 && failed.length) {
    // Nothing to show while some competitions failed: never claim "no matches".
    body = <ScheduleNotice tone="warning" title="전체 일정을 확인하지 못했습니다" description={failedText} action={retry} />;
  } else if (filtered.length === 0 && teamMode && all.length > 0) {
    body = (
      <ScheduleNotice
        title="조회 기간에 해당 팀의 선택 대회 일정이 없습니다"
        description="현재 대회 조건만 해제해 다른 대회 일정도 확인할 수 있습니다."
        action={
          <Button fullWidth onClick={() => params.update({ competitions: [] })}>
            모든 대회 일정 보기
          </Button>
        }
      />
    );
  } else if (filtered.length === 0 && teamMode) {
    body = (
      <ScheduleNotice
        title="조회 기간에 등록된 경기 일정이 없습니다"
        description={`${selectedTeam ? teamName(selectedTeam) : "선택한 팀"} · ${monthDay(rangeStart)}–${monthDay(rangeEnd)} · 지원 14개 대회 기준`}
      />
    );
  } else if (filtered.length === 0) {
    body = (
      <ScheduleNotice
        title={`${formatShortDate(params.date)} 경기가 없습니다`}
        description={
          params.competitions.length
            ? "선택한 날짜에 대회 조건의 등록 일정이 없습니다."
            : "선택한 날짜에 등록된 경기 일정이 없습니다."
        }
      />
    );
  } else {
    body = (
      <div className="flex flex-col gap-3">
        {query.isError && (
          <ScheduleNotice
            tone="warning"
            title="최신 일정으로 갱신하지 못했습니다"
            description="마지막으로 확인한 일정을 보여줍니다. 경기 상태가 바뀌었을 수 있습니다."
            action={retry}
          />
        )}
        {failed.length > 0 && (
          <ScheduleNotice
            tone="warning"
            title="일부 대회의 일정을 확인하지 못했습니다"
            description={failedText}
            action={retry}
          />
        )}
        {teamMode ? <ByDate matches={visible} /> : <MatchList matches={visible} />}
        {filtered.length > PAGE_SIZE && (
          <Button fullWidth aria-expanded={expanded} onClick={() => setShown({ key: listKey, all: !expanded })}>
            {expanded ? "접기" : `경기 전체 보기 (${PAGE_SIZE}/${filtered.length})`}
          </Button>
        )}
      </div>
    );
  }

  const live = visible.some((m) => m.status === "live");

  // Competitions and favourite teams are shared caches (FavoriteSchedule may fetch them
  // before this boundary hydrates): keep the server's placeholder until hydration ends.
  if (!hydrated) return <SectionSkeleton />;

  return (
    <section
      aria-labelledby="schedule-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div className="flex items-center gap-2">
        <h2 id="schedule-title" className="flex-1 text-title font-bold">
          {teamMode ? "팀 경기 일정" : "전체 경기 일정"}
        </h2>
        <Button variant="ghost" onClick={reset}>
          초기화
        </Button>
      </div>

      {teamMode && (
        <div className="flex items-end gap-2">
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <p className="text-subtitle font-bold">
              {selectedTeam ? `${teamName(selectedTeam)} 경기 일정 · 21일 모아 보기` : "팀 경기 일정 · 21일 모아 보기"}
            </p>
            <p className="text-small text-fg-secondary">
              {formatShortDate(rangeStart)}–{formatShortDate(rangeEnd)} · 지난 3일부터 향후 17일까지
            </p>
          </div>
          {live && <UpdatedAt value={byTeam.data?.meta.updatedAt} checkedAt={byTeam.dataUpdatedAt} />}
        </div>
      )}

      {/* Kept mounted in the team view so its scroll position returns with the date view. */}
      <div hidden={teamMode}>
        <DateBar
          dates={params.dates}
          today={params.today}
          selected={params.date}
          onSelect={(date) => params.update({ date: date === params.today ? null : date })}
          resetKey={resetKey}
          availability={dates}
          visible={!teamMode}
        />
      </div>

      <div className="flex flex-col gap-2">
        {competitions.data ? (
          <CompetitionFilter
            competitions={competitions.data}
            selected={params.competitions}
            onChange={selectCompetitions}
            unavailable={unavailable}
          />
        ) : competitions.isError ? (
          <p className="flex items-center gap-2 text-small text-error">
            대회 목록을 불러오지 못했습니다.
            <Button className="min-h-9" onClick={() => competitions.refetch()}>
              다시 확인
            </Button>
          </p>
        ) : (
          <Skeleton className="h-11 w-full" />
        )}
        {/* Remounted by a reset: also clears a typed term that never selected a team. */}
        <TeamSearch key={resetKey} selected={selectedTeam} onSelect={selectTeam}
          description="팀을 선택하면 지난 3일부터 향후 17일까지의 경기를 모아봅니다. 대회별로 좁혀볼 수 있습니다."
        />
        {favoriteTeams.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto [scrollbar-width:none]" role="group" aria-label="관심 팀 일정">
            <span className="w-[54px] shrink-0 text-small text-fg-muted">관심 팀</span>
            {favoriteTeams.map((team) => {
              const active = params.team === team.id;
              return (
                <button
                  key={team.id}
                  type="button"
                  aria-pressed={active}
                  className={chipClass(active)}
                  onClick={() => selectTeam(active ? null : team)}
                >
                  {teamName(team)}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {!teamMode && (
        <div className="flex items-center gap-2">
          <h3 className="flex-1 text-body font-medium">{formatShortDate(params.date)} · 선택 날짜의 경기</h3>
          {live && <UpdatedAt value={byDate.data?.meta.updatedAt} checkedAt={byDate.dataUpdatedAt} />}
        </div>
      )}

      <div>{body}</div>

      {!teamMode && <p className="text-small text-fg-muted">지난 날짜의 결과도 같은 경기 상세에서 확인할 수 있습니다.</p>}
    </section>
  );
}

function MatchList({ matches }: { matches: readonly MatchSummary[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {matches.map((match) => (
        <li key={match.id}>
          <MatchCard match={match} layout="schedule" />
        </li>
      ))}
    </ul>
  );
}

/** Team view: date headings ("11/5(목)") over that day's matches, in kickoff order. */
function ByDate({ matches }: { matches: readonly MatchSummary[] }) {
  const days = [...new Set(matches.map((m) => m.kickoffDateKst))];
  return (
    <div className="flex flex-col gap-2">
      {days.map((day) => (
        <Fragment key={day}>
          <h3 className="text-body font-bold">{formatShortDate(day)}</h3>
          <MatchList matches={matches.filter((m) => m.kickoffDateKst === day)} />
        </Fragment>
      ))}
    </div>
  );
}
