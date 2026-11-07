"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { cx } from "@/components/ui/cx";
import { FavoriteToggle } from "@/features/favorites/FavoriteToggle";
import { useFavorites } from "@/features/favorites/useFavorites";
import { RESULT_LABEL } from "@/features/match/model";
import { isApiError } from "@/lib/api/errors";
import type { TeamOverview } from "@/lib/api/types";
import { formatShortDate } from "@/lib/format/kst";
import { competitionName, teamName } from "@/lib/format/match";
import { SeasonRecords } from "./SeasonRecords";
import { SquadTable } from "./SquadTable";
import { TeamMatches } from "./TeamMatches";
import { TeamNews } from "./TeamNews";
import { TEAM_TABS, isTeamTab, standingText, venueText, type SeasonChoice, type TeamTab } from "./model";
import { teamOverviewQuery } from "./queries";

const TABS_ID = "team-areas";

/**
 * Team detail (TEAM-001~006, FAV-002·003 guest part, UF-11; Figma 52:1254 / 52:1866, mobile
 * tabs 58:356 · 58:738 · 58:924, states 57:836). The overview is one request; the six areas
 * below load on their own so one failing area never hides another. Mobile shows the areas
 * under the overview as tabs (경기 · 선수 · 기록 · 뉴스, 기록 = season record + transfers).
 * The tab and the two season switches live in the URL (`?tab=players&stats=last`).
 */
export function TeamDetail({ id }: { id: number }) {
  const query = useQuery(teamOverviewQuery(id));
  const params = useSearchParams();
  const pathname = usePathname();

  const tabParam = params.get("tab");
  const tab: TeamTab = isTeamTab(tabParam) ? tabParam : "matches";
  const statsSeason: SeasonChoice = params.get("stats") === "last" ? "last" : "this";
  const transferSeason: SeasonChoice = params.get("transfers") === "last" ? "last" : "this";
  const setParam = (key: string, value: string, fallback: string) => {
    const next = new URLSearchParams(params);
    if (value === fallback) next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    // Native history update: synced with useSearchParams, no server round trip (guide §3.1).
    window.history.replaceState(null, "", qs ? `${pathname}?${qs}` : pathname);
  };

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
      <TeamHeader overview={overview} name={name} refreshFailed={query.isError} onRetry={() => void query.refetch()} />
      <Tabs
        items={TEAM_TABS}
        value={tab}
        onChange={(value) => setParam("tab", value, "matches")}
        label={`${name} 정보`}
        idBase={TABS_ID}
        className="lg:hidden"
      />
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-6">
        <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
          {panel("matches", <TeamMatches teamId={id} />)}
          {panel("players", <SquadTable teamId={id} />)}
          {panel("news", <TeamNews teamId={id} />)}
        </div>
        {panel(
          "records",
          <SeasonRecords
            teamId={id}
            currentSeason={overview.season.season}
            statsSeason={statsSeason}
            transferSeason={transferSeason}
            onStatsSeason={(value) => setParam("stats", value, "this")}
            onTransferSeason={(value) => setParam("transfers", value, "this")}
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

/** Figma 52:1317: identity, favourite button, league standing · coach · venue, last five. */
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
  const { team, league, standing, coach, venue, form } = overview;
  const missing = (status: string) => (status === "unavailable" ? "확인하지 못했습니다" : "미제공");
  const facts = [
    {
      label: "리그 순위",
      value: standing.status === "available" ? standingText(standing.data ?? null) : missing(standing.status),
    },
    { label: "감독", value: coach.status === "available" && coach.data ? coach.data.name : missing(coach.status) },
    { label: "경기장", value: venue.status === "available" ? venueText(venue.data ?? null) : missing(venue.status) },
  ];

  return (
    <section aria-labelledby="team-name" className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6">
      {refreshFailed && (
        <div role="alert" className="flex flex-wrap items-center gap-2 rounded-control bg-warning-bg px-3 py-2 text-small text-warning">
          <span className="min-w-0 flex-1">팀 정보를 다시 확인하지 못했습니다. 마지막으로 확인한 정보입니다.</span>
          <Button variant="ghost" onClick={onRetry}>다시 확인</Button>
        </div>
      )}
      <div className="flex items-center gap-4">
        <TeamCrest src={team.crestUrl} name={name} size={72} />
        <div className="flex min-w-0 flex-col gap-1">
          <h1 id="team-name" className="text-heading font-bold break-keep text-fg">{name}</h1>
          <p className="text-label text-fg-muted">
            {team.nameKo ? `${team.nameEn} · ${league.shortName}` : league.shortName}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex">
          <FavoriteToggle teamId={team.id} teamName={name} className="w-full lg:w-auto lg:min-w-48" />
        </div>
        {favorites.status === "unavailable" && (
          <p role="status" className="rounded-control bg-warning-bg px-3 py-2 text-small text-warning">
            이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 정보는 계속 볼 수 있습니다.
          </p>
        )}
      </div>
      <dl className="grid gap-3 lg:grid-cols-3 lg:gap-6">
        {facts.map((fact) => (
          <div key={fact.label} className="flex flex-col gap-1">
            <dt className="text-small text-fg-muted">{fact.label}</dt>
            <dd className="text-body font-medium text-fg">{fact.value}</dd>
          </div>
        ))}
      </dl>
      {form.status === "available" && form.data ? (
        <ol className="flex flex-wrap gap-1" aria-label={`${name} 최근 5경기 결과, 최신순`}>
          {form.data.map((match, index) => {
            const result = RESULT_LABEL[match.result];
            const goals =
              match.goalsFor === null || match.goalsAgainst === null ? "—" : `${match.goalsFor}:${match.goalsAgainst}`;
            const detail = `${formatShortDate(match.kickoffDateKst)} ${competitionName({ nameKo: match.competition, shortName: match.competition })} ${match.venue === "home" ? "홈" : "원정"} vs ${match.opponentName} ${goals}`;
            return (
              <li key={index} title={detail}>
                <Badge tone={result.tone}>
                  {result.label}
                  <span className="sr-only"> ({detail})</span>
                </Badge>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-small text-fg-muted">
          {form.status === "unavailable" ? "최근 경기 흐름을 확인하지 못했습니다." : "최근 공식 경기 기록이 없습니다."}
        </p>
      )}
    </section>
  );
}
