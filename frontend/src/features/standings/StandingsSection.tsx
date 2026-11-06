"use client";

import { useQuery } from "@tanstack/react-query";
import { SeasonSelect } from "@/components/common/SeasonSelect";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, tabId, tabPanelId } from "@/components/ui/Tabs";
import { seasonsQuery } from "@/features/results/queries";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { useHydrated } from "@/lib/hooks/useHydrated";
import { LEAGUES } from "./model";
import { PlayerRankings } from "./PlayerRankings";
import { StandingsTable } from "./StandingsTable";
import { useStandingsParams } from "./useStandingsParams";

const LEAGUE_TABS = LEAGUES.map((l) => ({ value: String(l.id), label: l.label }));

/**
 * League standings page (LEAG-002·004, UF-10; Figma 53:1353 / 53:2047, 61:1653, states 57:599):
 * season dropdown, league tabs, the team table and player rankings of the same league
 * season. Changing the season or league switches both together, keeps the ranking type and
 * starts the player list at ten again. An unsupported league or season is reported and never
 * replaced by another one.
 */
export function StandingsSection() {
  const hydrated = useHydrated();
  const params = useStandingsParams();
  const seasons = useQuery(seasonsQuery);

  if (!hydrated) return <SectionSkeleton />;

  const unsupportedSeason =
    params.seasonInvalid ||
    (params.season !== null && seasons.isSuccess && !seasons.data.some((s) => s.season === params.season));
  const seasonValue = unsupportedSeason
    ? null
    : (params.season ?? seasons.data?.find((s) => s.current)?.season ?? null);

  let content;
  if (params.league === null) {
    content = (
      <StateMessage
        tone="error"
        title="지원하지 않는 리그입니다"
        description="리그 순위는 5대 리그만 제공합니다. 위에서 리그를 골라 주세요."
      />
    );
  } else if (unsupportedSeason) {
    content = (
      <StateMessage
        tone="error"
        title="지원하지 않는 시즌입니다"
        description="시즌 선택에서 조회할 시즌을 골라 주세요. 다른 시즌으로 바꿔 보여주지 않습니다."
      />
    );
  } else {
    // Remounted per league and season: the player list starts at ten again (UF-10).
    content = (
      <div
        key={`${params.league}-${params.season}`}
        className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start"
      >
        <StandingsTable league={params.league} season={params.season} />
        <PlayerRankings
          league={params.league}
          season={params.season}
          type={params.type}
          typeInvalid={params.typeInvalid}
          onTypeChange={params.selectType}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {seasons.data ? (
        <SeasonSelect
          seasons={seasons.data}
          value={seasonValue}
          onChange={(season) => params.select({ season })}
        />
      ) : seasons.isError ? (
        <p className="flex items-center gap-2 text-small text-error">
          시즌 목록을 불러오지 못했습니다.
          <Button className="min-h-9" onClick={() => seasons.refetch()}>
            다시 확인
          </Button>
        </p>
      ) : (
        <Skeleton className="h-11 w-full sm:w-[220px]" />
      )}
      <Tabs
        items={LEAGUE_TABS}
        value={params.league === null ? null : String(params.league)}
        onChange={(league) => params.select({ league: Number(league) })}
        label="리그"
        idBase="league"
      />
      {params.league === null ? (
        content
      ) : (
        <div role="tabpanel" id={tabPanelId("league", String(params.league))} aria-labelledby={tabId("league", String(params.league))}>
          {content}
        </div>
      )}
    </div>
  );
}
