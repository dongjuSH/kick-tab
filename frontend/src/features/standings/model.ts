import type { DataStatus } from "@/components/ui/DataState";
import type { KnockoutLeg, KnockoutStage, KnockoutTie, RankingType } from "@/lib/api/types";

/**
 * The five leagues with a table (CMP-002: domestic cups have none), in chip order (Figma
 * 53:1353, main 234:8881). Names are the DB `name_ko` (06 개선 2026-11-20, guide §3.1 —
 * `useCompetitionLabel` reads them; these are the same seeded values while that loads).
 */
export const LEAGUES = [
  { id: 39, label: "프리미어리그" },
  { id: 140, label: "라리가" },
  { id: 135, label: "세리에 A" },
  { id: 78, label: "분데스리가" },
  { id: 61, label: "리그 1" },
] as const;

/** UEFA competitions after the leagues (LEAG-001·002, Figma 61:1653). */
export const UEFA = [
  { id: 2, label: "UEFA 챔피언스리그" },
  { id: 3, label: "UEFA 유로파리그" },
  { id: 848, label: "UEFA 컨퍼런스리그" },
] as const;

/** Every competition with a table, in chip order. */
export const COMPETITIONS = [...LEAGUES, ...UEFA] as const;

export const DEFAULT_LEAGUE = 39;

export function isUefa(id: number): boolean {
  return UEFA.some((c) => c.id === id);
}

export function competitionLabel(id: number): string {
  return COMPETITIONS.find((c) => c.id === id)?.label ?? "";
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

/**
 * A band of table places marked by one colour (row left bar and legend bar) and named once in
 * the legend. `tone` names the band colour token (`--kt-band-*`, 2026-11-24): UEFA direct
 * #2563eb / play-off #F59E0B / out #64748b, domestic relegation #b91c1c, and the domestic
 * relegation play-off in the same play-off colour (user decision).
 */
export interface Band {
  key: "direct" | "playoff" | "out" | "promotion-playoff" | "relegation";
  label: string;
  from: number;
  to: number;
  tone: "direct" | "playoff" | "out" | "relegation";
}

/**
 * Table bands by position (LEAG-002 rules 5·6, Figma 53:1353 / 61:1653): UEFA league phase
 * 1–8 straight to the round of 16, 9–24 the play-offs, 25–36 out; the bottom three of the
 * Premier League, LaLiga and Serie A relegated; 17th–18th of the Bundesliga and Ligue 1
 * relegated and their 16th to the relegation play-off. While matches remain a band is a zone
 * ("강등권", "16강 직행권"); once the table is complete it is the result ("강등", "16강 직행").
 * The provider's order decides who sits there.
 */
export function tableBands(league: number, size: number, complete: boolean): Band[] {
  if (isUefa(league)) {
    return [
      { key: "direct", label: complete ? "16강 직행" : "16강 직행권", from: 1, to: 8, tone: "direct" },
      { key: "playoff", label: complete ? "플레이오프 진출" : "플레이오프권", from: 9, to: 24, tone: "playoff" },
      { key: "out", label: complete ? "탈락" : "탈락권", from: 25, to: 36, tone: "out" },
    ];
  }
  if (size < 4) return [];
  const playoff = league === 78 || league === 61;
  const relegation: Band = {
    key: "relegation",
    label: complete ? "강등" : "강등권",
    from: playoff ? size - 1 : size - 2,
    to: size,
    tone: "relegation",
  };
  if (!playoff) return [relegation];
  const label = complete ? "승강 플레이오프" : "승강 플레이오프권";
  return [{ key: "promotion-playoff", label, from: size - 2, to: size - 2, tone: "playoff" }, relegation];
}

export function bandOf(bands: readonly Band[], rank: number): Band | null {
  return bands.find((band) => rank >= band.from && rank <= band.to) ?? null;
}

/** "18–20위", "16위". */
export function rangeText(band: Pick<Band, "from" | "to">): string {
  return band.from === band.to ? `${band.from}위` : `${band.from}–${band.to}위`;
}

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
