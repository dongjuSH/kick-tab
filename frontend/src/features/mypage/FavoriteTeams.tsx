"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { MatchStatusBadge } from "@/components/common/MatchStatusBadge";
import { TeamCrest } from "@/components/common/TeamCrest";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { favoriteRefusal } from "@/features/favorites/FavoriteToggle";
import { favoriteMatches, teamNextMatch } from "@/features/favorites/nextMatches";
import type { FavoriteChange } from "@/features/favorites/store";
import { memberFavoritesQuery, useFavorites } from "@/features/favorites/useFavorites";
import { competitionsQuery, favoriteScheduleQuery } from "@/features/schedule/queries";
import { ScheduleNotice, failedNames } from "@/features/schedule/ScheduleNotice";
import type { MatchSummary, TeamRef } from "@/lib/api/types";
import { formatShortDate } from "@/lib/format/kst";
import { awaitingStatus, competitionName, kickoffTime, teamName } from "@/lib/format/match";
import { useNow } from "@/lib/hooks/useNow";
import { favoriteAddBlocked, favoriteCountText, favoriteLimitText, teamDetailNote } from "./model";
import { AreaError, MyCard } from "./MyCard";

/** What the second line of a team row shows. */
type NextState = { kind: "loading" } | { kind: "unknown" } | { kind: "match"; match: MatchSummary } | { kind: "none" };

/**
 * 관심 팀 (MY-002, Figma 52:2674 / 52:2912, states 797:20589, limit 656:27025). The account
 * list through `useFavorites()` — the same list and actions as the main panel, team browse and
 * team detail — in registration order, up to 10, all shown (no main-panel folding). The title
 * row is '★ 관심 팀 n / 10 … 팀 추가'; at 10 / 10 only adding stops. Each team shows its live
 * or nearest match from the schedule panel's lookup (`favoriteScheduleQuery`, one match per
 * team, a match between two favourites on both rows).
 */
export function FavoriteTeams() {
  const favorites = useFavorites();
  const ready = favorites.status === "ready";
  const ids = ready ? favorites.ids : [];
  // Names, crests and detail links come from the same cached account list.
  const list = useQuery({ ...memberFavoritesQuery, enabled: favorites.source === "member" });
  const teams = new Map((list.data?.teams ?? []).map((team) => [team.id, team]));
  // Keep the shown matches while a changed list is fetched (same lookup as the main panel).
  const schedule = useQuery({ ...favoriteScheduleQuery(ids), placeholderData: keepPreviousData });
  const competitions = useQuery(competitionsQuery);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const limitNotice = useRef<HTMLParagraphElement>(null);
  const count = favorites.ids.length;
  const blocked = favoriteAddBlocked(count, favorites.max);
  // After an add or a removal the pressed control is gone (search closed, row removed) or
  // disabled (10 / 10): focus goes to '팀 추가', or to the limit notice once it is off.
  const refocus = useRef(false);
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    (blocked ? limitNotice.current : addButton.current)?.focus();
  }, [count, blocked, adding]);

  const run = async (change: () => Promise<FavoriteChange>) => {
    setSaving(true);
    const result = await change();
    setSaving(false);
    setMessage(favoriteRefusal(result, favorites.max));
    return result;
  };
  const add = async (team: TeamRef) => {
    // Set before the change: the list (and the effect) updates before the promise resolves.
    refocus.current = true;
    const result = await run(() => favorites.add(team.id));
    if (result === "added" || result === "exists") setAdding(false);
    else refocus.current = false;
  };
  const remove = async (teamId: number) => {
    refocus.current = true;
    if ((await run(() => favorites.remove(teamId))) !== "removed") refocus.current = false;
  };

  // Second line of each row. Nothing is known yet (first load, or a team added while the
  // changed list is fetched): a skeleton. The lookup failed with nothing to show: empty.
  const data = schedule.data?.data;
  const matches = favoriteMatches(data?.matches ?? [], ids);
  const nextOf = (teamId: number): NextState => {
    if (schedule.isPending) return { kind: "loading" };
    if (!data) return { kind: "unknown" };
    const match = teamNextMatch(matches, teamId);
    if (match) return { kind: "match", match };
    if (schedule.isPlaceholderData && !data.teams.some((team) => team.id === teamId)) return { kind: "loading" };
    return { kind: "none" };
  };
  const failed = failedNames(schedule.data?.meta.failedCompetitionIds ?? [], competitions.data);
  const retry = (
    <Button className="self-start" disabled={schedule.isFetching} onClick={() => schedule.refetch()}>
      다시 확인
    </Button>
  );
  // Figma 797:20589: the warning sits under the guide line; the list and '해제' stay usable.
  let notice = null;
  if (schedule.isError && !data) {
    notice = (
      <ScheduleNotice
        tone="warning"
        title="관심 팀 일정을 확인하지 못했습니다"
        description="경기 정보를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요."
        action={retry}
        busy={schedule.isFetching}
      />
    );
  } else if (schedule.isError) {
    notice = (
      <ScheduleNotice
        tone="warning"
        title="최신 일정으로 갱신하지 못했습니다"
        description="마지막으로 확인한 경기를 보여줍니다. 경기 상태가 바뀌었을 수 있습니다."
        action={retry}
        busy={schedule.isFetching}
      />
    );
  } else if (failed.length > 0) {
    notice = (
      <ScheduleNotice
        tone="warning"
        title="일부 대회의 일정을 확인하지 못했습니다"
        description={`${failed.join("·")} 일정을 확인하지 못했습니다. 확인된 경기만 표시합니다.`}
        action={retry}
        busy={schedule.isFetching}
      />
    );
  }

  let body;
  if (favorites.status === "loading") {
    body = <DataState status="loading" />;
  } else if (!ready) {
    // The account list could not be read: never replaced by this browser's list (COM-005).
    body = <AreaError text="관심 팀을 불러오지 못했습니다." onRetry={favorites.retry} />;
  } else {
    body = (
      <>
        {blocked && (
          <p
            ref={limitNotice}
            tabIndex={-1}
            role="status"
            className="rounded-control bg-subtle p-4 text-body text-fg-secondary"
          >
            {favoriteLimitText(favorites.max)}
          </p>
        )}
        {adding && !blocked && (
          <TeamSearch
            label="관심 팀 검색"
            selected={null}
            onSelect={(team) => team && add(team)}
            candidates={(team) => team.detailAvailable === true && !favorites.ids.includes(team.id)}
          />
        )}
        {message && (
          <p role="status" className="text-small text-warning">
            {message}
          </p>
        )}
        {count === 0 ? (
          <p className="text-body text-fg-secondary">등록한 관심 팀이 없습니다.</p>
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-label text-fg-secondary">등록 팀별로 가장 가까운 경기만 표시합니다.</p>
            {notice}
            <ul aria-label="등록된 관심 팀" className="flex flex-col">
              {favorites.ids.map((id) => (
                <FavoriteRow
                  key={id}
                  team={teams.get(id)}
                  next={nextOf(id)}
                  saving={saving}
                  onRemove={() => remove(id)}
                />
              ))}
            </ul>
          </div>
        )}
      </>
    );
  }

  return (
    <MyCard
      title="관심 팀"
      titleId="my-favorites-title"
      icon={
        <svg aria-hidden width="18" height="18" viewBox="0 0 16 16" className="shrink-0 text-action">
          <path d="M8 1.6l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.2l-3.9 2.2.9-4.3-3.3-3 4.4-.5z" fill="currentColor" />
        </svg>
      }
      note={
        ready && (
          <span className="text-label text-fg-muted" aria-label={`${count}팀 등록, 최대 ${favorites.max}팀`}>
            {favoriteCountText(count, favorites.max)}
          </span>
        )
      }
      action={
        ready && (
          <Button
            ref={addButton}
            aria-label="관심 팀 추가"
            aria-expanded={adding && !blocked}
            disabled={blocked || saving}
            onClick={() => {
              setAdding((open) => !open);
              setMessage(null);
            }}
          >
            팀 추가
          </Button>
        )
      }
    >
      {body}
    </MyCard>
  );
}

/**
 * One team (Figma 52:2674 / 797:20589): emblem 32, name (team page link when available), '해제'
 * at the right end; under it the team's next match, '예정된 경기가 없습니다.' or a skeleton.
 */
function FavoriteRow({
  team,
  next,
  saving,
  onRemove,
}: {
  team: TeamRef | undefined;
  next: NextState;
  saving: boolean;
  onRemove: () => void;
}) {
  const name = team ? teamName(team) : "팀 정보 확인 중";
  const note = team ? teamDetailNote(team.detailAvailable) : null;
  return (
    <li className="flex flex-col gap-1 border-b border-line py-3">
      <div className="flex items-center gap-3">
        <TeamCrest src={team?.crestUrl ?? null} name={name} size={32} />
        <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2">
          {team?.detailAvailable === true ? (
            <Link
              href={`/teams/${team.id}`}
              prefetch={false}
              className="min-w-0 text-body font-medium break-words text-fg hover:underline"
            >
              {name}
            </Link>
          ) : (
            <span className="min-w-0 text-body font-medium break-words text-fg">{name}</span>
          )}
          {note && <span className="text-label text-fg-muted">{note}</span>}
        </span>
        <Button variant="text" aria-label={`${name} 관심 팀 해제`} disabled={saving} onClick={onRemove}>
          해제
        </Button>
      </div>
      {next.kind === "loading" && <Skeleton className="h-5 w-64 max-w-full" />}
      {next.kind === "none" && <p className="text-label text-fg-secondary">예정된 경기가 없습니다.</p>}
      {next.kind === "match" && <NextMatch match={next.match} />}
    </li>
  );
}

/**
 * The team's next match: PC one line [home · emblem · vs · emblem · away] [competition ·
 * date time] [status]; phones the pairing, then competition, date and status below. The
 * pairing links to the match page.
 */
function NextMatch({ match }: { match: MatchSummary }) {
  const now = useNow();
  const home = teamName(match.home);
  const away = teamName(match.away);
  return (
    <div className="flex flex-col gap-1 lg:flex-row lg:flex-wrap lg:items-center lg:gap-x-3">
      <Link
        href={`/matches/${match.id}`}
        prefetch={false}
        aria-label={`${home} 대 ${away} 경기 상세`}
        className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 self-start text-body font-medium text-fg hover:underline"
      >
        <span className="break-words">{home}</span>
        <TeamCrest src={match.home.crestUrl} name={home} size={20} />
        <span className="text-label font-normal text-fg-muted">vs</span>
        <TeamCrest src={match.away.crestUrl} name={away} size={20} />
        <span className="break-words">{away}</span>
      </Link>
      <span className="flex flex-wrap items-center gap-2 text-label text-fg-secondary">
        <span>
          {competitionName(match.competition)} · {formatShortDate(match.kickoffDateKst)} {kickoffTime(match)}
        </span>
        <MatchStatusBadge match={match} awaiting={awaitingStatus(match, now)} />
      </span>
    </div>
  );
}
