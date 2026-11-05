"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Fragment, useRef, useState, type ReactNode } from "react";
import { CompetitionFilter } from "@/components/common/CompetitionFilter";
import { MatchCard } from "@/components/common/MatchCard";
import { SeasonSelect } from "@/components/common/SeasonSelect";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { Pagination } from "@/components/ui/Pagination";
import { Skeleton } from "@/components/ui/Skeleton";
import { chipClass } from "@/components/ui/chip";
import { useFavorites } from "@/features/favorites/useFavorites";
import { ListSkeleton, SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { ScheduleNotice, failedNames } from "@/features/schedule/ScheduleNotice";
import { competitionsQuery, favoriteScheduleQuery } from "@/features/schedule/queries";
import { isApiError } from "@/lib/api/errors";
import type { CompetitionItem, MatchSummary, TeamRef } from "@/lib/api/types";
import { useHydrated } from "@/lib/hooks/useHydrated";
import { teamName } from "@/lib/format/match";
import { resultsQuery, seasonsQuery } from "./queries";
import { useResultsParams, type InvalidCondition } from "./useResultsParams";

const INVALID_LABELS: Record<InvalidCondition, string> = { team: "팀", competitions: "대회", page: "페이지" };

/** Competitions offered for a season: provider data exists (CMP-004 — a season without
 * data is left out of that season only), plus any the URL already selected. */
function seasonCompetitions(all: readonly CompetitionItem[], season: number, selected: readonly number[]) {
  return all.filter(
    (c) =>
      selected.includes(c.id) ||
      c.seasons.some((s) => s.season === season && s.availability === "available"),
  );
}

/**
 * Past results (HIST-001~003, UF-09·UF-20; Figma 53:593/53:995, 61:883/61:1290, states
 * 57:477). Every finished match of the selected season — no date filter — combined with
 * competition, team search and favourite-team conditions, 10 per page, newest first.
 *
 * Rules: season change keeps team and competitions and goes to page 1; clearing the team keeps
 * season and competitions; reset keeps the season and clears team, text, competitions and
 * page. An unsupported season is reported, never replaced by another season.
 */
export function ResultsSection() {
  const hydrated = useHydrated();
  const params = useResultsParams();
  const favorites = useFavorites();
  const [resetKey, setResetKey] = useState(0);
  const [picked, setPicked] = useState<TeamRef | null>(null);
  const listTop = useRef<HTMLParagraphElement>(null);

  const seasons = useQuery(seasonsQuery);
  const competitions = useQuery(competitionsQuery);
  const favoriteIds = favorites.status === "ready" ? favorites.ids : [];
  const favoriteTeams = useQuery(favoriteScheduleQuery(favoriteIds)).data?.data.teams ?? [];

  const current = seasons.data?.find((s) => s.current)?.season ?? null;
  const unsupported =
    params.seasonInvalid ||
    (params.season !== null && seasons.isSuccess && !seasons.data.some((s) => s.season === params.season));
  // An unreadable condition is reported, never queried as "every team / competition". Its
  // parsed key equals the unfiltered one, so cached results must not be shown for it either.
  const readable = !unsupported && params.invalid.length === 0;
  const results = useQuery({
    ...resultsQuery({
      season: params.season,
      competitions: params.competitions,
      team: params.team,
      page: params.page,
    }),
    enabled: readable,
  });
  const season = unsupported ? null : (results.data?.data.season.season ?? params.season ?? current);
  const seasonInfo = seasons.data?.find((s) => s.season === season) ?? results.data?.data.season ?? null;

  // Keep the last resolved team, so a later failed page or season still names the filter.
  const resolvedTeam = results.data?.data.team ?? null;
  if (resolvedTeam && resolvedTeam.id === params.team && picked?.id !== resolvedTeam.id) setPicked(resolvedTeam);

  const selectedTeam =
    params.team === null
      ? null
      : ((picked?.id === params.team ? picked : null) ??
        (results.data?.data.team?.id === params.team ? results.data.data.team : null) ??
        favoriteTeams.find((t) => t.id === params.team) ??
        null);

  const selectTeam = (team: TeamRef | null) => {
    setPicked(team);
    params.update({ team: team?.id ?? null });
  };
  const reset = () => {
    params.reset();
    setPicked(null);
    setResetKey((k) => k + 1);
  };
  const goToPage = (page: number) => {
    params.update({ page });
    listTop.current?.scrollIntoView({ block: "start" });
  };

  if (!hydrated) return <SectionSkeleton />;

  const total = results.data?.meta.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / (results.data?.meta.size ?? 10)));
  const matches = results.data?.data.matches ?? [];
  const failed = failedNames(results.data?.meta.failedCompetitionIds ?? [], competitions.data, params.competitions);
  const retry = <Button onClick={() => results.refetch()}>다시 확인</Button>;
  const resetButton = <Button onClick={reset}>필터 초기화</Button>;

  let body: ReactNode;
  if (!unsupported && params.invalid.length > 0) {
    body = (
      <StateMessage
        tone="error"
        title="조회 조건을 확인할 수 없습니다"
        description={`주소의 ${params.invalid.map((key) => INVALID_LABELS[key]).join("·")} 조건이 올바르지 않습니다. 전체 조건으로 바꿔 보여주지 않습니다.`}
        action={resetButton}
      />
    );
  } else if (unsupported) {
    body = (
      <StateMessage
        tone="error"
        title="지원하지 않는 시즌입니다"
        description="시즌 선택에서 조회할 시즌을 골라 주세요. 다른 시즌으로 바꿔 보여주지 않습니다."
      />
    );
  } else if (results.isPending) {
    body = <ListSkeleton />;
  } else if (results.isError) {
    // Server messages for 404 (unknown team/season), 422 (bad URL condition) and 503 (never
    // collected), never "no results". Retrying only helps a failure; a bad condition is
    // cleared instead (reset keeps the season, so it is offered only when it changes things).
    const status = isApiError(results.error) ? results.error.status : 0;
    const known = status === 404 || status === 422 || status === 503;
    const clearable = params.team !== null || params.competitions.length > 0;
    body = (
      <StateMessage
        tone="error"
        title="정보를 불러오지 못했습니다"
        description={known && isApiError(results.error) ? results.error.message : "잠시 후 다시 시도해 주세요."}
        action={status === 404 || status === 422 ? (clearable ? resetButton : undefined) : retry}
      />
    );
  } else if (matches.length === 0 && total > 0) {
    body = (
      <StateMessage
        title="이 페이지에는 경기가 없습니다"
        description={`검색 결과는 ${pages}페이지까지입니다.`}
        action={<Button onClick={() => goToPage(pages)}>마지막 페이지로</Button>}
      />
    );
  } else if (matches.length === 0 && failed.length) {
    body = (
      <ScheduleNotice
        tone="warning"
        title="지난 경기를 모두 확인하지 못했습니다"
        description={`${failed.join("·")}의 시즌 경기를 아직 불러오지 못했습니다. 결과가 없다고 단정하지 않습니다.`}
        action={retry}
      />
    );
  } else if (matches.length === 0) {
    body = (
      <StateMessage
        title="선택한 조건의 종료 경기가 없습니다"
        description="시즌·팀·대회 조건을 바꿔보세요."
        action={resetButton}
      />
    );
  } else {
    body = (
      <div className="flex flex-col gap-4">
        {failed.length > 0 && (
          <ScheduleNotice
            tone="warning"
            title="일부 대회의 지난 경기를 확인하지 못했습니다"
            description={`${failed.join("·")}의 경기가 빠져 있을 수 있습니다. 확인된 경기만 표시합니다.`}
            action={retry}
          />
        )}
        <ByDate matches={matches} />
        <Pagination page={params.page} pages={pages} onChange={goToPage} label="지난 경기 페이지" />
      </div>
    );
  }

  const competitionList =
    competitions.data && season !== null
      ? seasonCompetitions(competitions.data, season, params.competitions)
      : null;

  return (
    <section
      aria-label="지난 경기 필터와 결과"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div className="flex items-center gap-3">
        {seasons.data ? (
          <SeasonSelect
            className="min-w-0 max-w-[220px]"
            seasons={seasons.data}
            value={unsupported ? null : season}
            onChange={(next) => params.update({ season: next })}
          />
        ) : seasons.isError ? (
          <p className="flex items-center gap-2 text-small text-error">
            시즌 목록을 불러오지 못했습니다.
            <Button className="min-h-9" onClick={() => seasons.refetch()}>
              다시 확인
            </Button>
          </p>
        ) : (
          <Skeleton className="h-11 w-full max-w-[220px]" />
        )}
        <span className="flex-1" />
        <Button variant="ghost" className="shrink-0 whitespace-nowrap" onClick={reset}>
          초기화
        </Button>
      </div>

      {!unsupported && (
        <div className="flex flex-col gap-3">
          {competitionList ? (
            <CompetitionFilter
              competitions={competitionList}
              selected={params.competitions}
              onChange={(ids) => params.update({ competitions: ids })}
              season={season ?? undefined}
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
          <TeamSearch
            key={resetKey}
            selected={selectedTeam}
            onSelect={selectTeam}
            season={season}
            placeholder="팀 검색 · 맨시티, Man City"
          />
          {favoriteTeams.length > 0 && (
            <div
              className="flex items-center gap-2 overflow-x-auto [scrollbar-width:none]"
              role="group"
              aria-label="관심 팀 지난 경기"
            >
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
          {selectedTeam && <TeamLine team={selectedTeam} />}
        </div>
      )}

      {readable && seasonInfo && results.isSuccess && (
        <p ref={listTop} className="text-label text-fg">
          {seasonInfo.label} 시즌 전체 · 검색 결과 {total.toLocaleString("ko-KR")}경기
        </p>
      )}

      <div>{body}</div>
    </section>
  );
}

/**
 * Selected team (HIST-002, Figma 57:477 historic-team): a team link only when the current
 * allow set includes it; `false` = "팀 상세 미제공" while past results and match details stay
 * available; `null` (membership not confirmed) is never shown as relegation.
 */
function TeamLine({ team }: { team: TeamRef }) {
  const name = teamName(team);
  if (team.detailAvailable === true) {
    return (
      <p className="text-label text-fg-secondary">
        <Link href={`/teams/${team.id}`} prefetch={false} className="font-bold text-action hover:underline">
          {name} 팀 상세 보기
        </Link>
      </p>
    );
  }
  if (team.detailAvailable === false) {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-body font-bold text-fg">{name} · 팀 상세 미제공</p>
        <p className="text-small text-fg-secondary">과거 경기 검색과 경기 상세는 계속 이용할 수 있습니다.</p>
      </div>
    );
  }
  return <p className="text-body font-bold text-fg">{name}</p>;
}

/** KST date headings ("2026-10-29", Figma 73:2718) over that day's matches, newest first. */
function ByDate({ matches }: { matches: readonly MatchSummary[] }) {
  const days = [...new Set(matches.map((m) => m.kickoffDateKst))];
  return (
    <div className="flex flex-col gap-2">
      {days.map((day) => (
        <Fragment key={day}>
          <h3 className="pt-2 text-label font-medium text-fg-secondary">{day}</h3>
          <ul className="flex flex-col gap-2">
            {matches
              .filter((m) => m.kickoffDateKst === day)
              .map((match) => (
                <li key={match.id}>
                  <MatchCard match={match} layout="schedule" />
                </li>
              ))}
          </ul>
        </Fragment>
      ))}
    </div>
  );
}
