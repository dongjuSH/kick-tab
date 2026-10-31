/**
 * Korea Standard Time formatting (guide §6.4/§6.6). The API sends UTC ISO strings; the
 * screen shows KST without a timezone label.
 */
export const KST_TIME_ZONE = "Asia/Seoul";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: KST_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const partsFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: KST_TIME_ZONE,
  year: "numeric",
  month: "numeric",
  day: "numeric",
  weekday: "short",
});

const WEEKDAY_INDEX: Record<string, number> = {
  Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6,
};

export interface KstDateParts {
  year: number;
  month: number;
  day: number;
  /** Korean weekday letter, e.g. "월". */
  weekday: (typeof WEEKDAYS)[number];
}

function toDate(value: string | Date): Date | null {
  const date = typeof value === "string" ? new Date(value) : value;
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Calendar parts of an instant in KST. */
export function kstParts(value: string | Date): KstDateParts | null {
  const date = toDate(value);
  if (!date) return null;
  const parts = Object.fromEntries(partsFormatter.formatToParts(date).map((p) => [p.type, p.value]));
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    weekday: WEEKDAYS[WEEKDAY_INDEX[parts.weekday] ?? 0],
  };
}

/** "03:30" (24-hour KST). */
export function formatKstTime(value: string | Date): string {
  const date = toDate(value);
  return date ? timeFormatter.format(date) : MISSING;
}

/** "10월 29일 목요일". */
export function formatKstLongDate(value: string | Date): string {
  const p = kstParts(value);
  return p ? `${p.month}월 ${p.day}일 ${p.weekday}요일` : MISSING;
}

/**
 * Calendar date without time ("2026-10-26", e.g. kickoffDateKst or TOP 5 period).
 * Parsed as-is so no timezone shift can move the day.
 */
export function parseIsoDate(value: string): KstDateParts | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const weekday = WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()];
  return { year, month, day, weekday };
}

/** "10/26(월)" */
export function formatShortDate(value: string): string {
  const p = parseIsoDate(value);
  return p ? `${p.month}/${p.day}(${p.weekday})` : MISSING;
}

/** TOP 5 aggregation period, e.g. "10/26(월)~11/1(일)" (TOP-003). */
export function formatPeriod(start: string, end: string): string {
  return `${formatShortDate(start)}~${formatShortDate(end)}`;
}

/** Shown for values the provider did not supply (guide §4). */
export const MISSING = "—";

export function orMissing<T>(value: T | null | undefined, format: (v: T) => string = String): string {
  return value === null || value === undefined ? MISSING : format(value);
}
