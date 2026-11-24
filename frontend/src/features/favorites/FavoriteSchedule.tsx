"use client";

import { keepPreviousData, useQuery, type UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { MatchStatusBadge } from "@/components/common/MatchStatusBadge";
import { TeamCrest } from "@/components/common/TeamCrest";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button, IconButton } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { competitionsQuery, favoriteScheduleQuery, type ScheduleData } from "@/features/schedule/queries";
import { ScheduleNotice, failedNames } from "@/features/schedule/ScheduleNotice";
import type { FavoriteSchedule as FavoriteScheduleData, MatchSummary, TeamRef } from "@/lib/api/types";
import { formatShortDate } from "@/lib/format/kst";
import { awaitingStatus, competitionName, kickoffTime, teamName } from "@/lib/format/match";
import { useNow } from "@/lib/hooks/useNow";
import { useScrollRow } from "@/lib/hooks/useScrollRow";
import type { FavoriteChange } from "./store";
import { useFavorites } from "./useFavorites";

// Nearest matches shown before "더 보기" (2026-11-24, Figma 669:7801): three rows and the
// button make the panel as tall as the schedule card on a one-match day.
const FOLDED_MATCHES = 3;

/**
 * "관심 팀" panel (FAV-001~004, SCH-005; Figma `KickTab/Guest Favorites` 306:6220 —
 * Registered · Empty · Search · Limit · SaveError). The registered teams with remove, "팀
 * 추가" search right here (registrable teams only, from zero teams too), and each team's live
 * or nearest upcoming match, live first (a match between two favourites appears once).
 * The registered teams are one row of chips (emblem, name, 해제; 2026-11-24, Figma 306:6025)
 * that scrolls sideways: PC shows ‹ › only when it overflows, phones swipe.
 * Changes land in the current user's list (guest: this browser, max 5; member: the account,
 * max 10), so match-card stars and the schedule's favourite buttons follow; a failed save
 * keeps the previous list.
 *
 * More than three nearest matches (guests and members alike): the first three are shown,
 * '더 보기 (3/n)' opens all and '접기 (n/n)' folds back. The team chips always list every
 * registered team (they scroll sideways); only the match list folds.
 */
export function FavoriteSchedule() {
  const favorites = useFavorites();
  const ids = favorites.status === "ready" ? favorites.ids : [];
  // Keep the shown names and matches while a changed list is fetched.
  const schedule = useQuery({ ...favoriteScheduleQuery(ids), placeholderData: keepPreviousData });
  const competitions = useQuery(competitionsQuery);
  const [adding, setAdding] = useState(false);
  // The change that could not be saved, kept so "다시 시도" repeats it.
  const [failedChange, setFailedChange] = useState<(() => Promise<FavoriteChange>) | null>(null);
  const [picked, setPicked] = useState<TeamRef[]>([]);
  const [expanded, setExpanded] = useState(false);
  const known = new Map([...picked, ...(schedule.data?.data.teams ?? [])].map((t) => [t.id, t]));
  // Live first, then the existing order; a match between two favourites appears once.
  // A released team's match leaves at once, before the changed list is fetched again.
  const allMatches = (schedule.data?.data.matches ?? []).filter(
    (m) => ids.includes(m.home.id) || ids.includes(m.away.id),
  );
  const foldable = allMatches.length > FOLDED_MATCHES;
  // Back to three or fewer matches: the fold is gone, and a later fourth starts folded.
  if (!foldable && expanded) setExpanded(false);
  const matches = foldable && !expanded ? allMatches.slice(0, FOLDED_MATCHES) : allMatches;
  const listId = useId();
  const addButton = useRef<HTMLButtonElement>(null);
  const toggleFocused = useRef(false);
  // The fold button disappeared while focused: focus moves to '팀 추가'.
  useEffect(() => {
    if (foldable) return;
    if (toggleFocused.current) {
      toggleFocused.current = false;
      addButton.current?.focus();
    }
  }, [foldable]);

  // Some competitions not collected: the nearest match may be missing, so an empty list is
  // never "no upcoming matches" and a shown list may be incomplete.
  const failed = failedNames(schedule.data?.meta.failedCompetitionIds ?? [], competitions.data);
  const retry = (
    <Button variant="secondary" onClick={() => schedule.refetch()}>
      다시 시도
    </Button>
  );
  const failedText = `${failed.join("·")} 조회 실패. 확인된 경기만 보여주며, 예정 경기가 없다고 단정하지 않습니다.`;
  const full = favorites.status === "ready" && ids.length >= favorites.max;

  const [saving, setSaving] = useState(false);
  const [limitHit, setLimitHit] = useState(false);
  const run = async (change: () => Promise<FavoriteChange>) => {
    setSaving(true);
    const result = await change();
    setSaving(false);
    const saveFailed = result === "failed" || result === "unavailable";
    setFailedChange(saveFailed ? () => change : null);
    setLimitHit(result === "limit");
    return result;
  };
  const add = async (team: TeamRef) => {
    const result = await run(() => favorites.add(team.id));
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
  } else if (favorites.status === "failed") {
    // The account list could not be read: never replaced by this browser's list (COM-005).
    body = (
      <DataState
        status="error"
        errorTitle="관심 팀을 불러오지 못했습니다"
        error={null}
        onRetry={favorites.retry}
        retryLabel="다시 시도"
      />
    );
  } else {
    body = (
      <>
        {/* The limit has no standing notice (the count shows it); a refused add still says so. */}
        {limitHit && (
          <p role="status" className="text-small text-warning">
            관심 팀은 최대 {favorites.max}개까지 등록할 수 있습니다.
          </p>
        )}
        {adding && !full && <AddTeam registered={ids} onAdd={add} />}
        {failedChange && (
          // Figma 306:6183 SaveError: the previous list stays; retry repeats the change.
          <div role="alert" className="flex flex-col gap-2 rounded-control bg-error-bg p-4">
            <p className="text-body font-bold text-error">관심 팀을 저장하지 못했습니다</p>
            <p className="text-small text-fg-secondary">기존 목록을 유지했습니다. 다시 시도해 주세요.</p>
            <Button variant="secondary" onClick={() => run(failedChange)}>
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
          <div className="flex flex-col gap-3">
            <TeamChips
              teams={ids.map((id) => ({ id, team: known.get(id) }))}
              disabled={saving}
              onRemove={(id) => run(() => favorites.remove(id))}
            />
            <div id={listId} className="flex flex-col gap-2">
              <p className="text-small text-fg-secondary">등록 팀별로 가장 가까운 경기만 표시합니다.</p>
              <Summary
                schedule={schedule}
                matches={matches}
                failed={failed.length > 0}
                failedText={failedText}
                retry={retry}
              />
            </div>
          </div>
        )}
        {foldable && (
          // '표시 경기 수 / 전체 경기 수'; the whole list opens at once.
          <Button
            fullWidth
            aria-expanded={expanded}
            aria-controls={listId}
            onFocus={() => (toggleFocused.current = true)}
            onBlur={() => (toggleFocused.current = false)}
            onClick={() => setExpanded((open) => !open)}
          >
            {expanded ? `접기 (${allMatches.length}/${allMatches.length})` : `더 보기 (${FOLDED_MATCHES}/${allMatches.length})`}
          </Button>
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
        <h2 id="favorite-schedule-title" className="text-subtitle font-bold">
          관심 팀
        </h2>
        {favorites.status === "ready" && (
          <span className="text-small font-medium text-fg-secondary" aria-label={`${ids.length}팀 등록, 최대 ${favorites.max}팀`}>
            {ids.length}/{favorites.max}
          </span>
        )}
        <span className="flex-1" />
        {favorites.status === "ready" && (
          <>
            <Button
              ref={addButton}
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
 * Registered teams as one sideways row of chips (Figma 306:6025 / 306:6220, 2026-11-24):
 * f8fafc chip, border, 8px radius, 44px tall, emblem 20px + name 14px Medium + '해제'. PC shows
 * 24×44 ‹ › at both ends only when the chips overflow, each moving one view and disabled at
 * its end; phones have no arrows and swipe. Every '해제' is reachable by Tab (the row
 * follows the focus).
 */
function TeamChips({
  teams,
  disabled,
  onRemove,
}: {
  teams: readonly { id: number; team: TeamRef | undefined }[];
  disabled: boolean;
  onRemove: (id: number) => void;
}) {
  const { ref, edges, overflow, update, page, reveal } = useScrollRow<HTMLUListElement>();
  const arrow = (direction: 1 | -1) =>
    overflow && (
      // PC only: the span hides it on phones (IconButton sets its own display).
      <span className="hidden shrink-0 lg:flex">
        <IconButton
          icon={direction < 0 ? "chevron-left" : "chevron-right"}
          label={direction < 0 ? "이전 관심 팀 보기" : "다음 관심 팀 보기"}
          className="w-6 disabled:opacity-40"
          disabled={direction < 0 ? edges.start : edges.end}
          onClick={() => page(direction)}
        />
      </span>
    );
  return (
    <div className="flex min-w-0 items-center gap-1">
      {arrow(-1)}
      <ul
        ref={ref}
        aria-label="등록된 관심 팀"
        onScroll={update}
        onFocus={(event) => reveal(event.target.closest("li"))}
        className="relative flex min-w-0 flex-1 gap-2 overflow-x-auto [scrollbar-width:none]"
      >
        {teams.map(({ id, team }) => {
          const name = team ? teamName(team) : "팀 정보 확인 중";
          return (
            <li
              key={id}
              className="flex h-11 shrink-0 items-center gap-1 overflow-hidden rounded-control border border-line bg-canvas pl-2"
            >
              <TeamCrest src={team?.crestUrl ?? null} name={name} size={20} />
              <span className="whitespace-nowrap text-body font-medium text-fg">{name}</span>
              {/* The chip's right end is the button: hover/pressed fill and the focus outline
                  stay inside the chip, darker than its f8fafc so the state reads. */}
              <button
                type="button"
                className="inline-flex self-stretch items-center px-3 text-body font-medium text-fg-secondary transition-colors not-disabled:hover:bg-line not-disabled:hover:text-fg not-disabled:active:bg-line-strong disabled:cursor-not-allowed disabled:text-fg-disabled focus-visible:-outline-offset-3"
                aria-label={`${name} 관심 팀 해제`}
                disabled={disabled}
                onClick={() => onRemove(id)}
              >
                해제
              </button>
            </li>
          );
        })}
      </ul>
      {arrow(1)}
    </div>
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
      <ul className="flex flex-col gap-3">
        {matches.map((match) => (
          <li key={match.id}>
            <SummaryMatch match={match} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Nearest-match row (Figma 306:6025 / 669:7794, 2026-11-24): teams over "competition · date
 * time" and the status, 76px (15/12 padding, 5px between the lines) so three rows and the
 * '더 보기' button match the schedule card of a one-match day.
 */
function SummaryMatch({ match }: { match: MatchSummary }) {
  const now = useNow();
  const title = `${teamName(match.home)} vs ${teamName(match.away)}`;
  const when = `${formatShortDate(match.kickoffDateKst)} ${kickoffTime(match)}`;
  return (
    <Link
      href={`/matches/${match.id}`}
      prefetch={false}
      className="flex flex-col gap-[5px] rounded-control bg-subtle px-3 py-[15px] hover:bg-selected"
    >
      <span className="text-label leading-5 font-bold text-fg">{title}</span>
      <span className="flex min-h-[21px] items-center gap-2 text-small text-fg-secondary">
        <span className="min-w-0 flex-1 truncate">
          {competitionName(match.competition)} · {when}
        </span>
        <MatchStatusBadge match={match} size="compact" raised awaiting={awaitingStatus(match, now)} />
      </span>
    </Link>
  );
}
