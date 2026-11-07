import type { HomeAway, SquadPlayer, TeamSeasonRecord } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";

/**
 * Team detail rules (TEAM-001~006) kept apart from the components so they can be tested.
 * A missing value is always "—" (never 0 or a value from somewhere else).
 */

/** Mobile tabs below the overview (PRD 16장: 경기·선수·기록·뉴스; 기록 = 시즌 기록 + 이적). */
export const TEAM_TABS = [
  { value: "matches", label: "경기" },
  { value: "players", label: "선수" },
  { value: "records", label: "기록" },
  { value: "news", label: "뉴스" },
] as const;
export type TeamTab = (typeof TEAM_TABS)[number]["value"];

export function isTeamTab(value: string | null): value is TeamTab {
  return TEAM_TABS.some((tab) => tab.value === value);
}

/** "이번 시즌 / 지난 시즌" switch of the season record and transfers (URL: `stats=last`). */
export type SeasonChoice = "this" | "last";
export const SEASON_TABS = [
  { value: "this", label: "이번 시즌" },
  { value: "last", label: "지난 시즌" },
] as const;

export function seasonOf(choice: SeasonChoice, current: number): number {
  return choice === "last" ? current - 1 : current;
}

// ---------------------------------------------------------------- players (TEAM-002)

const POSITIONS: Record<string, { order: number; label: string }> = {
  Goalkeeper: { order: 0, label: "GK" },
  Defender: { order: 1, label: "DF" },
  Midfielder: { order: 2, label: "MF" },
  Attacker: { order: 3, label: "FW" },
};

export function positionLabel(position: string | null): string {
  if (!position) return MISSING;
  return POSITIONS[position]?.label ?? position;
}

function positionOrder(position: string | null): number | null {
  if (!position) return null;
  return POSITIONS[position]?.order ?? 4;
}

export type SortKey =
  | "number"
  | "name"
  | "position"
  | "nationality"
  | "appearances"
  | "goals"
  | "assists"
  | "rating";
export interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}

/** TEAM-002 rule 2: position order (GK → DF → MF → FW) by default. */
export const DEFAULT_SORT: SortState = { key: "position", dir: "asc" };
export const PLAYERS_SHOWN = 10;

const STAT_KEYS: readonly SortKey[] = ["appearances", "goals", "assists", "rating"];

/** A new column starts with its natural order (records: most first); the same column flips. */
export function nextSort(current: SortState, key: SortKey): SortState {
  if (current.key === key) return { key, dir: current.dir === "asc" ? "desc" : "asc" };
  return { key, dir: STAT_KEYS.includes(key) ? "desc" : "asc" };
}

function value(player: SquadPlayer, key: SortKey): number | string | null {
  switch (key) {
    case "number":
      return player.number;
    case "name":
      return player.player.name;
    case "position":
      return positionOrder(player.position);
    case "nationality":
      return player.nationality;
    case "rating":
      return player.stats?.rating == null ? null : Number(player.stats.rating);
    default:
      return player.stats?.[key] ?? null;
  }
}

function compare(a: number | string, b: number | string): number {
  return typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "ko");
}

/**
 * Sorted copy of the same players (TEAM-002 "정렬 변경 시 같은 선수 집합"). Missing values
 * always go last in both directions; ties fall back to position, number, then name.
 */
export function sortPlayers(players: readonly SquadPlayer[], sort: SortState): SquadPlayer[] {
  const tiebreak = (a: SquadPlayer, b: SquadPlayer) => {
    for (const key of ["position", "number", "name"] as const) {
      const x = value(a, key);
      const y = value(b, key);
      if (x === y) continue;
      if (x === null) return 1;
      if (y === null) return -1;
      return compare(x, y);
    }
    return a.player.id - b.player.id;
  };
  return [...players].sort((a, b) => {
    const x = value(a, sort.key);
    const y = value(b, sort.key);
    if (x === null && y === null) return tiebreak(a, b);
    if (x === null) return 1;
    if (y === null) return -1;
    const order = compare(x, y);
    if (order === 0) return tiebreak(a, b);
    return sort.dir === "asc" ? order : -order;
  });
}

export function statText(value: number | null | undefined): string {
  return value == null ? MISSING : String(value);
}

/** Provider rating ("7.123") with one decimal; missing is "—". */
export function ratingText(rating: string | number | null | undefined): string {
  if (rating == null || rating === "") return MISSING;
  const number = Number(rating);
  return Number.isFinite(number) ? number.toFixed(1) : MISSING;
}

// ---------------------------------------------------------------- season record (TEAM-005)

export function recordText(wins: HomeAway, draws: HomeAway, loses: HomeAway, side: "home" | "away"): string {
  const w = wins[side];
  const d = draws[side];
  const l = loses[side];
  if (w === null || d === null || l === null) return MISSING;
  return `${w}승 ${d}무 ${l}패`;
}

export function seasonRows(record: TeamSeasonRecord): { label: string; value: string }[] {
  const goals =
    record.goalsFor.total === null && record.goalsAgainst.total === null
      ? MISSING
      : `${statText(record.goalsFor.total)} / ${statText(record.goalsAgainst.total)}`;
  return [
    { label: "득점 / 실점", value: goals },
    { label: "홈 성적", value: recordText(record.wins, record.draws, record.loses, "home") },
    { label: "원정 성적", value: recordText(record.wins, record.draws, record.loses, "away") },
    {
      label: "무실점 경기",
      value: record.cleanSheets.total === null ? MISSING : `${record.cleanSheets.total}경기`,
    },
    { label: "주 포메이션", value: record.formation ?? MISSING },
  ];
}

export function standingText(standing: { rank: number; points: number | null } | null): string {
  if (!standing) return MISSING;
  return standing.points === null ? `${standing.rank}위` : `${standing.rank}위 · ${standing.points}점`;
}

// ---------------------------------------------------------------- transfers (TEAM-006)

/** Provider transfer types in Korean; amounts and unknown words are shown as given. */
const TRANSFER_TYPES: Record<string, string> = {
  transfer: "완전 이적",
  loan: "임대",
  "return from loan": "임대 복귀",
  "back from loan": "임대 복귀",
  "free agent": "자유계약",
  "free transfer": "자유 이적",
  free: "자유 이적",
  "end of career": "은퇴",
};

export function transferTypeText(type: string | null): string {
  if (!type) return MISSING;
  return TRANSFER_TYPES[type.trim().toLowerCase()] ?? type;
}

/** "2027년 1월부터 집계됩니다" for a half that has not begun (TEAM-006 rule 5). */
export function notStartedText(start: string): string {
  const [year, month] = start.split("-").map(Number);
  return `${year}년 ${month}월부터 집계됩니다.`;
}

// ---------------------------------------------------------------- overview (TEAM-001)

export function venueText(venue: { name: string | null; capacity: number | null } | null): string {
  if (!venue || (!venue.name && venue.capacity === null)) return "미제공";
  const capacity = venue.capacity === null ? null : `${venue.capacity.toLocaleString("ko-KR")}석`;
  return [venue.name ?? "경기장 이름 미제공", capacity].filter(Boolean).join(" · ");
}
