import type { BadgeTone } from "@/components/ui/Badge";
import type { DataStatus } from "@/components/ui/DataState";
import type { KnockoutLeg, KnockoutStage, KnockoutTie, RankingType, RecentMatch } from "@/lib/api/types";

/**
 * The five leagues with a table (CMP-002: domestic cups have none), in the order of the
 * league chips (Figma 53:1353) and the main chips (Figma 49:368, "EPL").
 */
export const LEAGUES = [
  { id: 39, label: "Premier League", chip: "EPL" },
  { id: 140, label: "LaLiga", chip: "LaLiga" },
  { id: 135, label: "Serie A", chip: "Serie A" },
  { id: 78, label: "Bundesliga", chip: "Bundesliga" },
  { id: 61, label: "Ligue 1", chip: "Ligue 1" },
] as const;

/**
 * UEFA competitions next to the leagues (LEAG-002 rule 2, Figma 61:1653): the chip shows the
 * full name, headings the short one ("챔스 리그 페이즈 순위", "챔스 16강 대진").
 */
export const UEFA = [
  { id: 2, label: "Champions League", short: "챔스" },
  { id: 3, label: "Europa League", short: "유로파" },
  { id: 848, label: "Conference League", short: "컨퍼런스" },
] as const;

export const DEFAULT_LEAGUE = 39;

export function isUefa(id: number): boolean {
  return UEFA.some((c) => c.id === id);
}

export function competitionLabel(id: number): string {
  return [...LEAGUES, ...UEFA].find((c) => c.id === id)?.label ?? "";
}

/** UEFA stages, always all shown (rule 6); "league" is the league-phase table. */
export type UefaStage = "league" | KnockoutStage;
export const STAGES: readonly { value: UefaStage; label: string }[] = [
  { value: "league", label: "리그 페이즈" },
  { value: "playoff", label: "플레이오프" },
  { value: "r16", label: "16강" },
  { value: "qf", label: "8강" },
  { value: "sf", label: "4강" },
  { value: "final", label: "결승" },
];

export function isStage(value: string | null): value is UefaStage {
  return STAGES.some((s) => s.value === value);
}

export function stageLabel(stage: UefaStage): string {
  return STAGES.find((s) => s.value === stage)?.label ?? "";
}

export const RANKING_TYPES: readonly { value: RankingType; label: string }[] = [
  { value: "goals", label: "득점" },
  { value: "assists", label: "도움" },
  { value: "yellow", label: "경고" },
  { value: "red", label: "퇴장" },
  { value: "saves", label: "선방" },
];

export function isRankingType(value: string | null): value is RankingType {
  return RANKING_TYPES.some((t) => t.value === value);
}

/** "+15", "-2", "0"; a missing value is "—" (never 0). */
export function signed(value: number | null): string {
  if (value === null) return "—";
  return value > 0 ? `+${value}` : String(value);
}

export function numberText(value: number | null): string {
  return value === null ? "—" : String(value);
}

export interface Zone {
  label: string;
  tone: BadgeTone;
}

/**
 * Relegation marks drawn from the row's position (LEAG-002 rule 5, Figma 449:6462): the
 * bottom three of the Premier League, LaLiga and Serie A; 17th-18th of the Bundesliga and
 * Ligue 1, and their 16th as the relegation play-off place. While the season runs the mark is
 * a zone ("강등권", "승강 플레이오프권"); once every match is over (`complete`) it is the result
 * ("강등", "승강 플레이오프"). The provider's order decides who sits there.
 */
export function leagueZone(league: number, rank: number, size: number, complete: boolean): Zone | null {
  const playoff = league === 78 || league === 61;
  const relegated = playoff ? rank >= size - 1 : rank >= size - 2;
  if (relegated) return { label: complete ? "강등" : "강등권", tone: "error" };
  if (playoff && rank === size - 2) {
    return { label: complete ? "승강 플레이오프" : "승강 플레이오프권", tone: "warning" };
  }
  return null;
}

export interface PhaseBand {
  key: "direct" | "playoff" | "out";
  label: string;
  range: string;
  tone: BadgeTone;
  from: number;
  to: number;
}

/**
 * UEFA league-phase bands (rule 6, Figma 61:1653 / 61:2355): 1–8 straight to the round of
 * 16, 9–24 the play-offs, 25–36 out — "…권" while the phase runs, the result once it is over.
 */
export function phaseBands(complete: boolean): PhaseBand[] {
  return [
    { key: "direct", label: complete ? "16강 직행" : "16강 직행권", range: "1–8위", tone: "live", from: 1, to: 8 },
    { key: "playoff", label: complete ? "플레이오프 진출" : "플레이오프권", range: "9–24위", tone: "warning", from: 9, to: 24 },
    { key: "out", label: complete ? "탈락" : "탈락권", range: "25–36위", tone: "error", from: 25, to: 36 },
  ];
}

export const RESULT_LABEL: Record<RecentMatch["result"], string> = { W: "승", D: "무", L: "패" };

/**
 * DataState status of one query (guide §6.6): a failure with data already on screen keeps the
 * data and is reported as partial, never as an empty result — also when the last confirmed
 * result had no rows (Codex 1차 지적 2): "0 rows, then the refresh failed" is partial, and the
 * caller shows its empty wording inside the partial frame.
 */
export function dataStatus(
  query: { isPending: boolean; isError: boolean; data: unknown },
  empty: boolean,
  partial: boolean,
): DataStatus {
  if (query.isPending) return "loading";
  if (query.isError && query.data === undefined) return "error";
  if (partial) return "partial";
  return empty ? "empty" : "ready";
}

/** "공동 2" for a shared saves rank (Figma 57:599), otherwise the rank. */
export function rankText(rank: number, tied: boolean): string {
  return tied ? `공동 ${rank}` : String(rank);
}

/**
 * One row per leg the tie needs. A leg's number comes from the API (`leg`), given only when
 * every leg is stored: a single stored match may be the first or the second leg, so it is
 * "경기" and the leg not stored yet is "남은 경기" (Codex 2차 지적 3).
 */
export function legRows(
  tie: Pick<KnockoutTie, "legs" | "legsNeeded">,
  final: boolean,
): { label: string; leg: KnockoutLeg | undefined }[] {
  return Array.from({ length: Math.max(tie.legsNeeded, tie.legs.length) }, (_, index) => {
    const leg = tie.legs[index];
    if (final) return { label: "결승", leg };
    if (leg) return { label: leg.leg ? `${leg.leg}차전` : "경기", leg };
    // Nothing stored for the tie yet: the legs to come are still 1차전 and 2차전.
    return { label: tie.legs.length === 0 ? `${index + 1}차전` : "남은 경기", leg };
  });
}
