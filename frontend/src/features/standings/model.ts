import type { DataStatus } from "@/components/ui/DataState";
import type { RankingType, StandingRow } from "@/lib/api/types";

/**
 * The five leagues with a table (CMP-002: cups and UEFA have none), in the order of the
 * league tabs (Figma 53:1425) and the main chips (Figma 49:368, "EPL").
 */
export const LEAGUES = [
  { id: 39, label: "Premier League", chip: "EPL" },
  { id: 140, label: "LaLiga", chip: "LaLiga" },
  { id: 135, label: "Serie A", chip: "Serie A" },
  { id: 78, label: "Bundesliga", chip: "BUN" },
  { id: 61, label: "Ligue 1", chip: "Ligue 1" },
] as const;

export const DEFAULT_LEAGUE = 39;

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

export type FormResult = "승" | "무" | "패";

/** Provider letters W/D/L → 승/무/패, kept in the provider's order. Unknown letters drop. */
export function formResults(form: string | null): FormResult[] {
  const map: Record<string, FormResult> = { W: "승", D: "무", L: "패" };
  return [...(form ?? "")].flatMap((letter) => (map[letter] ? [map[letter]] : []));
}

/**
 * Past-season wording of the table's own description (Figma 61:1653: "당시 강등"). The current
 * table has no mark: its zones are not decided yet (Figma 53:1353).
 */
export function zoneLabel(row: StandingRow): string | null {
  if (row.zone === "relegation") return "당시 강등";
  if (row.zone === "relegation_playoff") return "당시 승강 PO";
  return null;
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
