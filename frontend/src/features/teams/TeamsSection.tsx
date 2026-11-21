"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Pagination } from "@/components/ui/Pagination";
import { cx } from "@/components/ui/cx";
import { FavoriteToggle } from "@/features/favorites/FavoriteToggle";
import { useFavorites } from "@/features/favorites/useFavorites";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { ChipRow, type ChipItem } from "@/features/standings/ChipRow";
import { LEAGUES, dataStatus } from "@/features/standings/model";
import { isApiError } from "@/lib/api/errors";
import type { BrowseTeam, TeamRef } from "@/lib/api/types";
import { competitionName, teamName } from "@/lib/format/match";
import { teamsQuery } from "./queries";
import { useTeamsParams, type InvalidCondition } from "./useTeamsParams";

const INVALID_LABELS: Record<InvalidCondition, string> = { league: "리그", q: "검색어", team: "팀", page: "페이지" };
const ALL = "all";
const LEAGUE_CHIPS: ChipItem<string>[] = [
  { value: ALL, label: "전체" },
  ...LEAGUES.map((league) => ({ value: String(league.id), label: league.label })),
];

/**
 * Team browse (LEAG-003, FAV-001~003 guest part, UF-05·UF-10; Figma 52:624 / 52:949, states
 * 57:766, membership error 57:836). Current-season five-league teams with a league filter and
 * the common team search, 12 per page. The search is the same field as the other pages
 * (label, magnifier, small ×, autocomplete): picking a candidate shows that team's card, and
 * Enter without a candidate lists the teams matching the typed words (aliases included).
 * Each card links to the team detail and registers / unregisters the team as a guest
 * favourite, which the main page's favourite schedule and buttons read from the same store.
 */
export function TeamsSection() {
  const params = useTeamsParams();
  const listTop = useRef<HTMLParagraphElement>(null);
  const [picked, setPicked] = useState<TeamRef | null>(null);
  const readable = params.invalid.length === 0;
  const teams = useQuery({
    ...teamsQuery({ league: params.league, q: params.q, team: params.team, page: params.page }),
    enabled: readable,
  });

  const goToPage = (page: number) => {
    params.update({ page });
    listTop.current?.scrollIntoView({ block: "start" });
  };
  const clearSearch = () => params.update({ q: null, team: null });

  const total = teams.data?.meta.total ?? 0;
  const size = teams.data?.meta.size ?? 12;
  const pages = Math.max(1, Math.ceil(total / size));
  const items = teams.data?.data ?? [];
  const leagueLabel = LEAGUES.find((l) => l.id === params.league)?.label ?? "5대 리그";
  const selectedTeam =
    params.team === null
      ? null
      : ((picked?.id === params.team ? picked : null) ??
        items.find((item) => item.team.id === params.team)?.team ??
        null);
  const searchWords = params.team !== null ? (selectedTeam ? teamName(selectedTeam) : null) : params.q;
  const searching = params.team !== null || params.q !== null;

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
  } else if (teams.data === undefined && isApiError(teams.error) && teams.error.code === "MEMBERSHIP_UNKNOWN") {
    // Figma 57:836 membership-error: never shown as "relegated" or as an empty list.
    body = (
      <StateMessage
        tone="error"
        title="현재 소속을 확인하지 못했습니다"
        description="강등으로 단정하지 않고 팀 링크를 잠시 보류합니다."
        action={<Button onClick={() => teams.refetch()}>다시 확인</Button>}
      />
    );
  } else {
    // Figma 57:766 search-none (the league's name when one is chosen).
    const emptyTitle = searching ? "일치하는 팀이 없습니다" : "표시할 팀이 없습니다";
    const emptyDescription = `현재 시즌 ${leagueLabel} 팀만 찾을 수 있습니다.`;
    const emptyAction = searching ? <Button onClick={clearSearch}>검색어 지우기</Button> : undefined;
    const retry = () => teams.refetch();
    body = (
      // A failed re-check keeps the list already confirmed (partial), never an error or empty.
      // A first failure is Figma 57:766 error: '정보를 불러오지 못했습니다 · 잠시 후 다시 시도해
      // 주세요.' (no server wording).
      <DataState
        status={dataStatus(teams, total === 0, teams.isError)}
        loadingFallback={<ListSkeleton />}
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
            description={`${searching ? "검색 결과는" : "팀 목록은"} ${pages}페이지까지입니다.`}
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
      {/* One row that scrolls sideways on a narrow screen (no wrap, no page scroll). */}
      <ChipRow
        label="리그 필터"
        items={LEAGUE_CHIPS}
        value={params.invalid.includes("league") ? null : params.league === null ? ALL : String(params.league)}
        onChange={(value) => {
          const league = value === ALL ? null : Number(value);
          // A league change ends a picked team (it may play elsewhere) and keeps typed words.
          if (league !== params.league) params.update({ league, team: null });
        }}
      />
      <TeamSearch
        label="팀 검색"
        description="한글·영문·별칭으로 팀을 찾습니다."
        selected={selectedTeam}
        defaultText={params.team === null ? (params.q ?? undefined) : undefined}
        // Only current five-league members: the teams this page lists.
        candidates={(team) => team.detailAvailable === true}
        onSelect={(team) => {
          setPicked(team);
          // A picked team is shown wherever it plays: the league filter returns to '전체'.
          params.update(team ? { team: team.id, league: null, q: null } : { team: null, q: null });
        }}
        onSubmitText={(text) => {
          // Enter on the search already shown adds no history step.
          if ((text || null) === params.q && params.team === null) return;
          params.update({ q: text || null, team: null });
        }}
      />
      <FavoritesNotice />
      <p ref={listTop} className="scroll-mt-40 text-label text-fg-secondary">
        {readable && teams.data
          ? searchWords
            ? `현재 시즌 ${leagueLabel} · '${searchWords}' 검색 결과 ${total}개 팀`
            : `현재 시즌 ${leagueLabel} · ${total}개 팀`
          : `현재 시즌 ${leagueLabel}`}
      </p>
      {body}
    </section>
  );
}

/**
 * Shown only when it matters (LEAG-003 rule 2: no standing 'n / 5' count): five teams saved
 * (Figma 57:766 fav-full) or no storage in this browser. Each team's button shows its state.
 */
function FavoritesNotice() {
  const favorites = useFavorites();
  if (favorites.status === "unavailable") {
    return (
      <p role="status" className="rounded-control bg-warning-bg px-3 py-3 text-label text-warning">
        이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 목록은 계속 볼 수 있습니다.
      </p>
    );
  }
  if (favorites.status !== "ready" || favorites.ids.length < favorites.max) return null;
  return (
    <p role="status" className="rounded-control bg-subtle px-3 py-3 text-label text-fg-secondary">
      관심 팀은 최대 {favorites.max}팀까지 등록할 수 있습니다.
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
          {team.nameKo ? `${team.nameEn} · ${competitionName(league)}` : competitionName(league)}
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
