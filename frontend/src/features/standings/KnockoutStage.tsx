"use client";

import { useQuery } from "@tanstack/react-query";
import { TeamCrest } from "@/components/common/TeamCrest";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { DataState } from "@/components/ui/DataState";
import { cx } from "@/components/ui/cx";
import { ListSkeleton } from "@/features/schedule/ScheduleSection";
import { isApiError } from "@/lib/api/errors";
import type { KnockoutLeg, KnockoutStage as Stage, KnockoutTeamSlot, KnockoutTie } from "@/lib/api/types";
import { formatKstMonthDayTime } from "@/lib/format/kst";
import { teamName } from "@/lib/format/match";
import { dataStatus, legRows, stageLabel } from "./model";
import { knockoutsQuery } from "./queries";
import { useCompetitionLabel } from "./useCompetitionLabel";

const STATE: Record<KnockoutTie["state"], { label: string; tone: BadgeTone }> = {
  finished: { label: "종료", tone: "accent" },
  live: { label: "진행 중", tone: "live" },
  scheduled: { label: "예정", tone: "neutral" },
  undecided: { label: "예정 · 대진 미정", tone: "neutral" },
};

/**
 * One UEFA knockout stage (LEAG-002 rule 7; Figma 451:20753 PC / 451:20778 mobile, card
 * 450:6662). Ties come from stored matches only: legs with date and result, then the
 * aggregate and the team that goes through (the final: one match and the winner). A place
 * whose team is not known shows "A–B전 승자" only when stored matches fix that path, and
 * "상대 미정" when the other side is known; a tie not announced yet is "예정 · 대진 미정".
 */
export function KnockoutStage({ league, season, stage }: { league: number; season: number | null; stage: Stage }) {
  const round = useQuery(knockoutsQuery(league, season, stage));
  const ties = round.data?.data.ties ?? [];
  const label = useCompetitionLabel();
  const failed = Boolean(round.data?.meta.refreshFailed || round.isError);

  return (
    <section aria-labelledby="knockout-title" className="flex min-w-0 flex-col gap-4">
      <h2 id="knockout-title" className="text-subtitle font-bold">
        {label(league)} {stageLabel(stage)} 대진
      </h2>
      <DataState
        status={dataStatus(round, ties.length === 0, failed)}
        loadingFallback={<ListSkeleton />}
        error={round.error}
        onRetry={isApiError(round.error) && round.error.status === 404 ? undefined : () => round.refetch()}
        emptyTitle="대진 정보가 없습니다"
        partialNotice="최신 대진으로 갱신하지 못해 마지막으로 확인한 경기를 표시합니다."
      >
        <ul className="grid items-start gap-3 lg:grid-cols-2 lg:gap-4">
          {ties.map((tie, index) => (
            <li key={tie.legs[0]?.fixtureId ?? `tie-${index}`}>
              <TieCard tie={tie} final={stage === "final"} />
            </li>
          ))}
        </ul>
      </DataState>
    </section>
  );
}

function slotName(slot: KnockoutTeamSlot, otherKnown: boolean): string | null {
  if (slot.team) return teamName(slot.team);
  if (slot.winnerOf && slot.winnerOf.length === 2) {
    return `${teamName(slot.winnerOf[0])}–${teamName(slot.winnerOf[1])}전 승자`;
  }
  return otherKnown ? "상대 미정" : null;
}

function TieCard({ tie, final }: { tie: KnockoutTie; final: boolean }) {
  const state = STATE[tie.state];
  const homeKnown = Boolean(tie.home.team || tie.home.winnerOf);
  const awayKnown = Boolean(tie.away.team || tie.away.winnerOf);
  const home = slotName(tie.home, awayKnown);
  const away = slotName(tie.away, homeKnown);
  const rows = legRows(tie, final);

  return (
    <article className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
      <Badge tone={state.tone} className="self-start">
        {state.label}
      </Badge>
      {home && away && (
        <p className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 text-body font-bold">
          <SlotTitle slot={tie.home} name={home} home />
          <span className="text-small font-normal text-fg-muted">vs</span>
          <SlotTitle slot={tie.away} name={away} />
        </p>
      )}
      <div className="flex flex-col">
        {rows.map((row, index) => (
          <LegRow key={index} label={row.label} leg={row.leg} last={index === rows.length - 1} />
        ))}
      </div>
      {tie.winner && (
        <p className="flex flex-wrap items-center justify-between gap-2 rounded-control bg-subtle px-3 py-2 text-small">
          <span className="text-fg-secondary tabular-nums">
            {final ? "결과" : "합산"} {tie.aggregateHome} : {tie.aggregateAway}
            {tie.penaltyHome !== null && ` · 승부차기 ${tie.penaltyHome} : ${tie.penaltyAway}`}
          </span>
          <span className="font-bold text-action">
            {teamName(tie.winner)} {final ? "우승" : "진출"}
          </span>
        </p>
      )}
    </article>
  );
}

/**
 * One side of the tie title (Figma 451:20753 PC / 451:20778 mobile): phones read "로고 팀 vs
 * 로고 팀"; PC centres the pair on "vs" as "팀 로고 vs 로고 팀" — the home crest sits next to
 * "vs" (visual order only; the DOM keeps crest then name).
 */
function SlotTitle({ slot, name, home = false }: { slot: KnockoutTeamSlot; name: string; home?: boolean }) {
  return (
    <span
      className={cx(
        "flex min-w-0 items-center gap-2",
        home && "lg:flex-row-reverse lg:text-right",
        !slot.team && "text-fg-secondary",
      )}
    >
      {slot.team && <TeamCrest src={slot.team.crestUrl} name={name} size={20} />}
      <span className="min-w-0 break-keep">{name}</span>
    </span>
  );
}

function LegRow({ label, leg, last }: { label: string; leg: KnockoutLeg | undefined; last: boolean }) {
  const played = leg && (leg.status === "finished" || leg.status === "live");
  return (
    <div className={cx("flex flex-col gap-1.5 py-2.5", !last && "border-b border-line")}>
      <p className="flex items-center justify-between gap-2 text-small">
        <span className="font-bold text-fg">{label}</span>
        <span className="text-fg-secondary tabular-nums">
          {leg && leg.timeConfirmed ? formatKstMonthDayTime(leg.kickoffAt) : "일시 미정"}
        </span>
      </p>
      {leg && (
        <p className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-small text-fg-secondary">
          <span className="truncate">{teamName(leg.home)}</span>
          <span className="text-center font-bold text-action tabular-nums">
            {played && leg.score.home !== null && leg.score.away !== null
              ? `${leg.score.home} : ${leg.score.away}`
              : "VS"}
            {leg.score.penaltyHome !== null && (
              <span className="block text-caption font-medium text-fg-secondary">
                PK {leg.score.penaltyHome}:{leg.score.penaltyAway}
              </span>
            )}
          </span>
          <span className="truncate text-right">{teamName(leg.away)}</span>
        </p>
      )}
    </div>
  );
}
