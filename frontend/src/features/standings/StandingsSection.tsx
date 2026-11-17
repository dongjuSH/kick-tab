"use client";

import { useQuery } from "@tanstack/react-query";
import { SeasonSelect } from "@/components/common/SeasonSelect";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { seasonsQuery } from "@/features/results/queries";
import { SectionSkeleton } from "@/features/schedule/ScheduleSection";
import { useHydrated } from "@/lib/hooks/useHydrated";
import { ChipRow, type ChipItem } from "./ChipRow";
import { KnockoutStage } from "./KnockoutStage";
import { LeaguePhaseTable } from "./LeaguePhaseTable";
import { LEAGUES, STAGES, UEFA, type UefaStage } from "./model";
import { PlayerRankings } from "./PlayerRankings";
import { StandingsTable } from "./StandingsTable";
import { useStandingsParams } from "./useStandingsParams";

const COMPETITION_CHIPS: ChipItem<string>[] = [
  ...LEAGUES.map((l) => ({ value: String(l.id), label: l.label })),
  ...UEFA.map((c, index) => ({ value: String(c.id), label: c.label, groupStart: index === 0 })),
];

/**
 * League standings page (LEAG-002·004, UF-10; Figma 53:1353 / 53:2047, UEFA 61:1653 / 61:2355,
 * knockouts 451:20753 / 451:20778): one white area holding the season dropdown, the
 * competition chips (five leagues | UEFA), the UEFA stage chips and the content. Five leagues
 * show the team table beside (PC) or above (mobile) the player rankings; a UEFA competition
 * opens on its league phase and every stage stays selectable. A new season or competition
 * keeps the ranking type and starts the player list at ten again. An unsupported competition,
 * season or stage is reported and never replaced by another one.
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
        title="지원하지 않는 대회입니다"
        description="5대 리그와 UEFA 3개 대회 중에서 골라 주세요."
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
  } else if (params.uefa && params.stageInvalid) {
    content = (
      <StateMessage
        tone="error"
        title="조회 조건을 확인할 수 없습니다"
        description="주소의 단계가 올바르지 않습니다. 위에서 단계를 골라 주세요."
      />
    );
  } else if (params.uefa) {
    content =
      params.stage === "league" ? (
        <LeaguePhaseTable key={`${params.league}-${params.season}`} league={params.league} season={params.season} />
      ) : (
        <KnockoutStage league={params.league} season={params.season} stage={params.stage} />
      );
  } else {
    // Remounted per league and season: the player list starts at ten again (UF-10).
    content = (
      <div key={`${params.league}-${params.season}`} className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_292px] lg:gap-0">
        <div className="min-w-0 lg:pr-6">
          <StandingsTable league={params.league} season={params.season} />
        </div>
        <div className="min-w-0 border-t border-line pt-6 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6">
          <PlayerRankings
            league={params.league}
            season={params.season}
            type={params.type}
            typeInvalid={params.typeInvalid}
            onTypeChange={params.selectType}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4 lg:p-6">
      {seasons.data ? (
        <SeasonSelect seasons={seasons.data} value={seasonValue} onChange={(season) => params.select({ season })} />
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
      <ChipRow
        items={COMPETITION_CHIPS}
        value={params.league === null ? null : String(params.league)}
        onChange={(league) => params.select({ league: Number(league) })}
        label="대회"
      />
      {params.uefa && (
        <ChipRow<UefaStage>
          items={STAGES}
          value={params.stageInvalid ? null : params.stage}
          onChange={(stage) => params.select({ stage })}
          label="단계"
        />
      )}
      <div className="mt-3 border-t border-line pt-6">{content}</div>
    </div>
  );
}
