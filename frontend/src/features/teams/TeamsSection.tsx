"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Button, IconButton } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Pagination } from "@/components/ui/Pagination";
import { ChipLabel, chipClass } from "@/components/ui/chip";
import { cx } from "@/components/ui/cx";
import { FavoriteToggle } from "@/features/favorites/FavoriteToggle";
import { useFavorites } from "@/features/favorites/useFavorites";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { LEAGUES, dataStatus } from "@/features/standings/model";
import type { BrowseTeam } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { teamsQuery } from "./queries";
import { SEARCH_MAX, useTeamsParams, type InvalidCondition } from "./useTeamsParams";

const INVALID_LABELS: Record<InvalidCondition, string> = { league: "리그", q: "검색어", page: "페이지" };
const SEARCH_DELAY_MS = 300;

/**
 * Team browse (LEAG-003, FAV-001~003 guest part, UF-05·UF-10; Figma 52:624 / 52:949, states
 * 57:766). Current-season five-league teams with a league filter and an alias name search
 * (both combinable, both in the URL with the page), 12 per page. Each card links to the team
 * detail and registers / unregisters the team as a guest favourite, which the main page's
 * favourite schedule and buttons read from the same store.
 */
export function TeamsSection() {
  const params = useTeamsParams();
  const listTop = useRef<HTMLParagraphElement>(null);
  const readable = params.invalid.length === 0;
  const teams = useQuery({
    ...teamsQuery({ league: params.league, q: params.q, page: params.page }),
    enabled: readable,
  });

  const goToPage = (page: number) => {
    params.update({ page });
    listTop.current?.scrollIntoView({ block: "start" });
  };
  const clearSearch = () => params.update({ q: null });

  const total = teams.data?.meta.total ?? 0;
  const size = teams.data?.meta.size ?? 12;
  const pages = Math.max(1, Math.ceil(total / size));
  const items = teams.data?.data ?? [];
  const leagueLabel = LEAGUES.find((l) => l.id === params.league)?.label ?? "5대 리그";

  let body: ReactNode;
  if (!readable) {
    body = (
      <StateMessage
        tone="error"
        title="조회 조건을 확인할 수 없습니다"
        description={`주소의 ${params.invalid.map((key) => INVALID_LABELS[key]).join("·")} 조건이 올바르지 않습니다. 전체 팀으로 바꿔 보여주지 않습니다.`}
        action={<Button onClick={params.reset}>필터 초기화</Button>}
      />
    );
  } else {
    const emptyTitle = params.q ? "일치하는 팀이 없습니다" : "표시할 팀이 없습니다";
    const emptyDescription = `현재 시즌 ${leagueLabel} 팀만 찾을 수 있습니다.`;
    const emptyAction = params.q ? <Button onClick={clearSearch}>검색어 지우기</Button> : undefined;
    const retry = () => teams.refetch();
    body = (
      // A failed re-check keeps the list already confirmed (partial), never an error or empty.
      <DataState
        status={dataStatus(teams, total === 0, teams.isError)}
        loadingFallback={<ListSkeleton />}
        error={teams.error}
        onRetry={retry}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        emptyAction={emptyAction}
        partialNotice="팀 목록을 다시 확인하지 못했습니다. 마지막으로 확인한 목록입니다."
        partialAction={<Button onClick={retry}>다시 확인</Button>}
      >
        {total === 0 ? (
          <StateMessage title={emptyTitle} description={emptyDescription} action={emptyAction} />
        ) : items.length === 0 ? (
          // Past the last page: also inside the failed-refresh frame (Codex 1차 지적 3).
          <StateMessage
            title="이 페이지에는 팀이 없습니다"
            description={`${params.q ? "검색 결과는" : "팀 목록은"} ${pages}페이지까지입니다.`}
            action={<Button onClick={() => goToPage(pages)}>마지막 페이지로</Button>}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <TeamCard key={item.team.id} item={item} />
              ))}
            </ul>
            <Pagination page={params.page} pages={pages} onChange={goToPage} label="팀 목록 페이지" />
          </div>
        )}
      </DataState>
    );
  }

  return (
    <section
      aria-label="팀 목록"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div
        role="group"
        aria-label="리그 필터"
        className="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] lg:mx-0 lg:px-0"
      >
        <LeagueChip
          label="전체"
          selected={params.league === null && !params.invalid.includes("league")}
          onSelect={() => params.update({ league: null })}
        />
        {LEAGUES.map((league) => (
          <LeagueChip
            key={league.id}
            label={league.label}
            selected={params.league === league.id}
            onSelect={() => params.update({ league: league.id })}
          />
        ))}
      </div>
      <SearchField
        value={params.q}
        urlKey={params.urlKey}
        onCommit={(q, replace) => params.update({ q }, { replace })}
      />
      <FavoritesNotice />
      <p ref={listTop} className="scroll-mt-40 text-label text-fg-secondary">
        {readable && teams.data
          ? params.q
            ? `현재 시즌 ${leagueLabel} · '${params.q}' 검색 결과 ${total}개 팀`
            : `현재 시즌 ${leagueLabel} · ${total}개 팀`
          : `현재 시즌 ${leagueLabel}`}
      </p>
      {body}
    </section>
  );
}

function LeagueChip({ label, selected, onSelect }: { label: string; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" aria-pressed={selected} className={chipClass(selected)} onClick={() => !selected && onSelect()}>
      <ChipLabel>{label}</ChipLabel>
    </button>
  );
}

/**
 * Name search (Figma 52:705, 40px field inside a 44px target as in D-03-8). The URL follows
 * the text after a short pause; the first change of one typing session is a history step and
 * the following keystrokes replace it, so Back returns to the list before the search.
 * A typing session ends on blur, on Enter / ×, and on any URL change this field did not make
 * (Back, Forward, league, page, reset), so the next search is a new history step and never
 * overwrites another entry (Codex 1차 지적 1).
 * - Any URL change this field did not make wins: the field shows that URL's search and text not
 *   sent yet is dropped, so a pending search never re-applies after Back (Codex 2차 지적 1).
 * - Enter and blur (Tab) first finish the session's last text in the same history step, then
 *   end it (Codex 2차 지적 2).
 */
function SearchField({
  value,
  urlKey,
  onCommit,
}: {
  value: string | null;
  /** The whole query string: tells this field's own commits from other URL changes. */
  urlKey: string;
  onCommit: (q: string | null, replace: boolean) => void;
}) {
  const [text, setText] = useState(value ?? "");
  const [synced, setSynced] = useState({ value, urlKey });
  // Searches this field sent that the URL has not shown yet, oldest first.
  const [sent, setSent] = useState<(string | null)[]>([]);
  const [typing, setTyping] = useState(false);
  // Blurred with text not sent yet: the pending send still joins the session, then ends it.
  const [closing, setClosing] = useState(false);
  const commit = useRef(onCommit);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    commit.current = onCommit;
  });

  if (synced.value !== value || synced.urlKey !== urlKey) {
    setSynced({ value, urlKey });
    const own = sent.indexOf(value);
    if (own >= 0) {
      // The URL caught up with one of this field's commits: keep what is being typed.
      setSent(sent.slice(own + 1));
    } else {
      setSent([]);
      setTyping(false);
      setClosing(false);
      // Also when the search is the same: drops text not sent yet (and so its timer).
      setText(value ?? "");
    }
  }

  const lastSent = sent.length ? sent[sent.length - 1] : undefined;
  const shown = lastSent === undefined ? value : lastSent;
  const unsent = (text.trim() || null) !== shown;
  useEffect(() => {
    const next = text.trim() || null;
    if (next === shown) return;
    const timer = setTimeout(() => {
      setSent((list) => [...list, next]);
      setTyping(!closing);
      setClosing(false);
      commit.current(next, typing);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [text, shown, typing, closing]);

  /** Sends `next` now: in the current history step while a session is open, then ends it. */
  const commitNow = (next: string | null, keepStep: boolean) => {
    setTyping(false);
    setClosing(false);
    if (next === shown) return;
    setSent((list) => [...list, next]);
    commit.current(next, keepStep && typing);
  };

  return (
    <form
      role="search"
      className="relative flex items-center"
      onSubmit={(event) => {
        event.preventDefault();
        commitNow(text.trim() || null, true);
      }}
    >
      <label className="flex min-h-11 min-w-0 flex-1 items-center">
        <span className="sr-only">팀 이름 검색</span>
        <input
          ref={inputRef}
          type="search"
          autoComplete="off"
          maxLength={SEARCH_MAX}
          placeholder="팀 이름 검색 · 한국어, 영문, 별칭"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onFocus={() => setClosing(false)}
          onBlur={() => (unsent ? setClosing(true) : setTyping(false))}
          className="h-10 w-full rounded-control border border-line-strong bg-surface pl-3 pr-11 text-body text-fg placeholder:text-fg-muted [&::-webkit-search-cancel-button]:hidden"
        />
      </label>
      {text && (
        <IconButton
          className="absolute right-0"
          icon="x"
          label="검색어 지우기"
          onClick={() => {
            setText("");
            commitNow(null, false);
            inputRef.current?.focus();
          }}
        />
      )}
    </form>
  );
}

/** Figma 52:711 / 57:766: count of this browser's favourites, the full state, or no storage. */
function FavoritesNotice() {
  const favorites = useFavorites();
  if (favorites.status === "unavailable") {
    return (
      <p role="status" className="rounded-control bg-warning-bg px-3 py-3 text-label text-warning">
        이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 목록은 계속 볼 수 있습니다.
      </p>
    );
  }
  const count = favorites.ids.length;
  return (
    <p role="status" className="min-h-[45px] rounded-control bg-subtle px-3 py-3 text-label text-fg-secondary">
      {favorites.status === "loading"
        ? null
        : count >= favorites.max
          ? `관심 팀 ${count} / ${favorites.max} · 다른 팀을 해제한 뒤 추가하세요.`
          : `관심 팀 ${count} / ${favorites.max} · 이 브라우저에 저장`}
    </p>
  );
}

function TeamCard({ item }: { item: BrowseTeam }) {
  const favorites = useFavorites();
  const { team, league } = item;
  const name = teamName(team);
  const info = (
    <>
      <TeamCrest src={team.crestUrl} name={name} size={40} />
      <span className="flex min-w-0 flex-col">
        <span className="truncate text-lead font-bold text-fg group-hover:underline">{name}</span>
        <span className="truncate text-small text-fg-muted">
          {team.nameKo ? `${team.nameEn} · ${league.shortName}` : league.shortName}
        </span>
      </span>
    </>
  );
  return (
    <li
      className={cx(
        "flex min-w-0 flex-col gap-3.5 rounded-card border bg-surface p-4",
        favorites.has(team.id) ? "border-action" : "border-line",
      )}
    >
      {team.detailAvailable === true ? (
        <Link href={`/teams/${team.id}`} prefetch={false} className="group flex min-h-12 items-center gap-3 rounded-control">
          {info}
        </Link>
      ) : (
        <div className="flex min-h-12 items-center gap-3">{info}</div>
      )}
      <FavoriteToggle teamId={team.id} teamName={name} />
    </li>
  );
}
