"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import { FavoriteToggle } from "@/features/favorites/FavoriteToggle";
import { useFavorites } from "@/features/favorites/useFavorites";
import { RecentForm, formItem } from "@/components/common/RecentForm";
import { isApiError } from "@/lib/api/errors";
import type { TeamOverview } from "@/lib/api/types";
import { competitionName, teamName } from "@/lib/format/match";
import { SeasonRecords } from "./SeasonRecords";
import { SquadTable } from "./SquadTable";
import { TeamMatches } from "./TeamMatches";
import { TeamNews } from "./TeamNews";
import { TEAM_TABS, isHalf, isTeamTab, standingText, venueText, type SeasonChoice, type TeamTab } from "./model";
import { teamOverviewQuery } from "./queries";

const TABS_ID = "team-areas";

/**
 * Team detail (TEAM-001~006, FAV-002·003 guest part, UF-11; Figma 52:1254 / 52:1866, mobile
 * tabs 58:356 · 58:738 · 58:924, states 57:766 · 57:836). The overview is one request; the
 * areas load on their own so one failing area never hides another. PC: team info · matches ·
 * squad · news on the left, season record · transfers on the right. Mobile shows the areas
 * under the team info as tabs (경기 · 선수단 · 기록 · 뉴스, 기록 = season record + transfers).
 * The tab, the two season switches and the transfer half live in the URL
 * (`?tab=records&stats=last&transfers=last&half=second`), so going back restores them.
 */
export function TeamDetail({ id }: { id: number }) {
  const query = useQuery(teamOverviewQuery(id));
  const params = useSearchParams();
  const pathname = usePathname();

  const tabParam = params.get("tab");
  const tab: TeamTab = isTeamTab(tabParam) ? tabParam : "matches";
  const statsSeason: SeasonChoice = params.get("stats") === "last" ? "last" : "this";
  const transferSeason: SeasonChoice = params.get("transfers") === "last" ? "last" : "this";
  const halfParam = params.get("half");
  const half = isHalf(halfParam) ? halfParam : null;
  const setParams = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    const qs = next.toString();
    // Native history entry: synced with useSearchParams, no server round trip (guide §3.1);
    // pushed so the browser's back button returns to the previous choice.
    window.history.pushState(null, "", qs ? `${pathname}?${qs}` : pathname);
  };
  const setParam = (key: string, value: string, fallback: string) =>
    setParams({ [key]: value === fallback ? null : value });

  if (!query.data) {
    return <OverviewFailure pending={query.isPending} error={query.error} onRetry={() => void query.refetch()} />;
  }

  const overview = query.data.data;
  const name = teamName(overview.team);
  // Desktop shows every area; below 1024px only the selected tab's panel.
  const panel = (value: TeamTab, children: ReactNode) => (
    <div
      role="tabpanel"
      id={tabPanelId(TABS_ID, value)}
      aria-labelledby={tabId(TABS_ID, value)}
      className={cx(tab === value ? "flex" : "hidden", "min-w-0 flex-col gap-4 lg:flex lg:gap-6")}
    >
      {children}
    </div>
  );

  return (
    <>
      <Link href="/teams" className="self-start rounded-control text-label font-medium text-fg-secondary hover:text-fg">
        ‹ 팀 탐색
      </Link>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-6">
        <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
          <TeamHeader overview={overview} name={name} refreshFailed={query.isError} onRetry={() => void query.refetch()} />
          <Tabs
            items={TEAM_TABS}
            value={tab}
            onChange={(value) => setParam("tab", value, "matches")}
            label={`${name} 정보`}
            idBase={TABS_ID}
            className="lg:hidden"
          />
          {panel("matches", <TeamMatches teamId={id} />)}
          {panel("players", <SquadTable teamId={id} />)}
          {panel("news", <TeamNews teamId={id} />)}
        </div>
        {panel(
          "records",
          <SeasonRecords
            teamId={id}
            teamName={name}
            currentSeason={overview.season.season}
            statsSeason={statsSeason}
            transferSeason={transferSeason}
            half={half}
            onStatsSeason={(value) => setParam("stats", value, "this")}
            // Another season starts again on its default half.
            onTransferSeason={(value) => setParams({ transfers: value === "this" ? null : value, half: null })}
            onHalf={(value) => setParams({ half: value })}
          />,
        )}
      </div>
    </>
  );
}

function OverviewFailure({ pending, error, onRetry }: { pending: boolean; error: unknown; onRetry: () => void }) {
  if (isApiError(error) && error.status === 404) {
    const unavailable = error.code === "TEAM_DETAIL_UNAVAILABLE";
    return (
      <StateMessage
        tone="error"
        className="rounded-card border border-line bg-surface"
        title={unavailable ? "팀 상세를 제공하지 않는 팀입니다" : "팀을 찾을 수 없습니다"}
        description={error.message}
        action={<ButtonLink href="/teams">팀 탐색으로 이동</ButtonLink>}
      />
    );
  }
  if (isApiError(error) && error.code === "MEMBERSHIP_UNKNOWN") {
    // Figma 57:836 membership-error: never shown as "relegated".
    return (
      <StateMessage
        tone="error"
        className="rounded-card border border-line bg-surface"
        title="현재 소속을 확인하지 못했습니다"
        description="강등으로 단정하지 않고 팀 상세를 잠시 보류합니다."
        action={<Button onClick={onRetry}>다시 확인</Button>}
      />
    );
  }
  return (
    <div className="rounded-card border border-line bg-surface p-4 lg:p-6">
      <DataState
        status={pending ? "loading" : "error"}
        error={error}
        onRetry={onRetry}
        errorTitle="팀 정보를 불러오지 못했습니다"
        loadingFallback={
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <Skeleton className="size-[72px] rounded-full" />
              <Skeleton className="h-8 w-48" />
            </div>
            <Skeleton className="h-11 w-48" />
            <Skeleton className="h-12 w-full" />
          </div>
        }
      />
    </div>
  );
}

/** Figma 472:18198: crest, name, English name · league, favourite button, facts, last five. */
function TeamHeader({
  overview,
  name,
  refreshFailed,
  onRetry,
}: {
  overview: TeamOverview;
  name: string;
  refreshFailed: boolean;
  onRetry: () => void;
}) {
  const favorites = useFavorites();
  const { team, league, standing, coach, venue, recent } = overview;
  const missing = (status: string) => (status === "unavailable" ? "확인하지 못했습니다" : "미제공");
  const facts = [
    {
      label: "리그",
      value: standing.status === "available" ? standingText(standing.data ?? null) : missing(standing.status),
    },
    { label: "감독", value: coach.status === "available" && coach.data ? coach.data.name : missing(coach.status) },
    { label: "홈구장", value: venue.status === "available" ? venueText(venue.data ?? null) : missing(venue.status) },
  ];

  return (
    // Figma 472:18198: 16px top/bottom, 12px between rows, 56px emblem on PC.
    <section aria-labelledby="team-name" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4 lg:px-6">
      {refreshFailed && (
        <div role="alert" className="flex flex-wrap items-center gap-2 rounded-control bg-warning-bg px-3 py-2 text-small text-warning">
          <span className="min-w-0 flex-1">팀 정보를 다시 확인하지 못했습니다. 마지막으로 확인한 정보입니다.</span>
          <Button variant="secondary" onClick={onRetry}>다시 시도</Button>
        </div>
      )}
      <div className="flex items-center gap-3 lg:gap-4">
        <TeamCrest src={team.crestUrl} name={name} size={56} className="max-lg:!size-12" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 id="team-name" className="text-title font-bold break-keep text-fg lg:text-heading lg:leading-[34px]">{name}</h1>
          <p className="text-label leading-5 text-fg-muted">
            {team.nameEn}
            <span className="hidden lg:inline"> · {competitionName(league)}</span>
          </p>
        </div>
        <FavoriteToggle teamId={team.id} teamName={name} className="shrink-0 lg:min-w-48" />
      </div>
      {favorites.status === "unavailable" && (
        <p role="status" className="rounded-control bg-warning-bg px-3 py-2 text-small text-warning">
          이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 정보는 계속 볼 수 있습니다.
        </p>
      )}
      <dl className="flex flex-wrap gap-x-6 gap-y-2 text-label">
        {facts.map((fact) => (
          <div key={fact.label} className="flex gap-1.5">
            <dt className="text-fg-muted">{fact.label}</dt>
            <dd className="font-medium text-fg">{fact.value}</dd>
          </div>
        ))}
      </dl>
      {/* Shared chips are inline-flex: flex list items keep the row at the chip height. */}
      <div className="flex flex-wrap items-center gap-3 [&_li]:flex">
        <span className="text-small text-fg-muted">최근 5경기</span>
        {recent.length ? (
          <RecentForm matches={recent.map(formItem)} teamName={name} />
        ) : (
          <span className="text-small text-fg-muted">최근 공식 경기 기록이 없습니다.</span>
        )}
      </div>
    </section>
  );
}
