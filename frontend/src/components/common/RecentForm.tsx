"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { cx } from "@/components/ui/cx";
import type { RecentMatch } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";

/**
 * One finished match of a recent-five row, whatever its source (LEAG-002 rule 4, TEAM-001
 * rule 3, MAT-005 rule 4): a table's stored matches, or a team's official matches.
 */
export interface FormItem {
  key: string;
  /** KST date, "2026-11-07". */
  date: string;
  competition: string;
  home: string;
  away: string;
  goalsHome: number | null;
  goalsAway: number | null;
  /** The row team's result. */
  result: "W" | "D" | "L";
}

export const RESULT_LABEL: Record<FormItem["result"], string> = { W: "승", D: "무", L: "패" };

/** A recent match of a standings row or the team page (API `RecentMatch`). */
export function formItem(match: RecentMatch): FormItem {
  return {
    key: String(match.fixtureId),
    date: match.kickoffDateKst,
    competition: match.competition,
    home: match.home.nameKo ?? match.home.nameEn,
    away: match.away.nameKo ?? match.away.nameEn,
    goalsHome: match.goalsHome,
    goalsAway: match.goalsAway,
    result: match.result,
  };
}

const TONE: Record<FormItem["result"], string> = {
  W: "bg-live-bg text-live",
  D: "bg-subtle text-fg-secondary",
  L: "bg-error-bg text-error",
};
const POPUP_WIDTH = 248;
// Height of the two-line preview before it is measured (then its real height is used).
const POPUP_HEIGHT = 68;
// Gap between the item and the preview (the caret sits in it), and from the screen edges.
const GAP = 8;
const EDGE = 4;
// Time to move the mouse from an item onto its preview before the preview closes.
const CLOSE_DELAY = 150;

/** "2026.11.07". */
function dotDate(iso: string): string {
  return iso.replaceAll("-", ".");
}

function goals(value: number | null): string {
  return value === null ? MISSING : String(value);
}

interface Box {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/**
 * The part of the screen where an item can be seen: the viewport under the sticky site header
 * (header + TOP 5 strip, COM-003) and inside every scrolling or clipping ancestor — a
 * sideways-scrolling table on phones.
 */
function headerBottom(): number {
  return Math.max(0, document.querySelector("header.sticky")?.getBoundingClientRect().bottom ?? 0);
}

function visibleBox(el: HTMLElement): Box {
  const box: Box = { top: headerBottom(), bottom: window.innerHeight, left: 0, right: window.innerWidth };
  for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
    const style = getComputedStyle(node);
    if (!/(auto|scroll|hidden|clip)/.test(style.overflowX + style.overflowY)) continue;
    const rect = node.getBoundingClientRect();
    box.top = Math.max(box.top, rect.top);
    box.bottom = Math.min(box.bottom, rect.bottom);
    box.left = Math.max(box.left, rect.left);
    box.right = Math.min(box.right, rect.right);
  }
  return box;
}

interface Open {
  index: number;
  top: number;
  left: number;
  /** Caret position inside the preview, under (or over) the item's centre. */
  caret: number;
  /** Where the caret points from: the preview above or below its item; null when neither
   * side has room and the preview is moved over the item to stay on screen. */
  side: "above" | "below" | null;
}

/**
 * The recent-five row shared by the standings table, the UEFA league-phase table, team
 * detail and the head-to-head card (LEAG-002 rule 4, TEAM-001 rule 3, MAT-005 rule 4; Figma
 * 53:1353, popup 567:7275). Oldest first: the right-most item is the latest and only a border
 * marks it (the accessible name says "최신 경기"). Each item opens a preview — "date ·
 * competition" over "home – score – away" — on PC hover or keyboard focus and on a mobile tap.
 * It reads the given values only; opening it never calls the provider, and it links nowhere.
 * Fewer than five known matches show as many as there are.
 *
 * The preview is placed in the viewport (fixed), so a sideways-scrolling table never clips it.
 * Its measured height decides the side: above the item when it fits under the sticky header,
 * else below when it fits above the screen bottom, else moved into the space between them
 * (Codex 1차 지적 2: a low window). It never leaves the screen edges. It follows its item when the page or a table scrolls
 * and closes once the item is hidden — under the sticky header, outside the table's visible
 * part or off the screen — on Escape or on a tap elsewhere. The mouse can move onto the
 * preview without closing it; following a scroll never cancels a close already scheduled.
 */
export function RecentForm({ matches, teamName }: { matches: readonly FormItem[]; teamName: string }) {
  const [open, setOpen] = useState<Open | null>(null);
  const pointer = useRef<string>("mouse");
  // Whether this item's preview was already open when the press began (a tap then closes it).
  const wasOpen = useRef(false);
  const id = useId();
  const anchor = useRef<HTMLElement | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const popup = useRef<HTMLDivElement>(null);
  const popupHeight = useRef(POPUP_HEIGHT);

  const keep = useCallback(() => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  }, []);
  const close = useCallback(() => {
    keep();
    setOpen(null);
  }, [keep]);
  const closeSoon = useCallback(() => {
    keep();
    closeTimer.current = setTimeout(() => setOpen(null), CLOSE_DELAY);
  }, [keep]);
  useEffect(() => keep, [keep]);

  // Places the preview at its item, or closes it when the item is hidden.
  const place = useCallback((index: number, el: HTMLElement) => {
    anchor.current = el;
    const rect = el.getBoundingClientRect();
    const box = visibleBox(el);
    const middle = (rect.left + rect.right) / 2;
    if (rect.bottom <= box.top || rect.top >= box.bottom || middle < box.left || middle > box.right) {
      setOpen(null);
      return;
    }
    const height = popupHeight.current;
    const top = headerBottom() + EDGE;
    const bottom = window.innerHeight - EDGE;
    let side: Open["side"] = null;
    let y = Math.min(Math.max(top, rect.bottom + GAP), bottom - height);
    if (rect.top - GAP - height >= top) {
      side = "above";
      y = rect.top - GAP - height;
    } else if (rect.bottom + GAP + height <= bottom) {
      side = "below";
      y = rect.bottom + GAP;
    }
    const width = Math.min(POPUP_WIDTH, window.innerWidth - 16);
    const left = Math.min(Math.max(8, middle - width / 2), window.innerWidth - width - 8);
    const caret = Math.min(Math.max(12, middle - left), width - 12);
    setOpen({ index, top: Math.max(top, y), left, caret, side });
  }, []);

  // The first placement uses an estimate; once drawn, the real height places it again.
  useLayoutEffect(() => {
    const height = popup.current?.offsetHeight;
    if (!open || !height || Math.abs(height - popupHeight.current) < 1) return;
    popupHeight.current = height;
    if (anchor.current) place(open.index, anchor.current);
  }, [open, place]);
  // Opening on hover, focus or tap: a pending close is cancelled.
  const show = useCallback(
    (index: number, el: HTMLElement) => {
      keep();
      place(index, el);
    },
    [keep, place],
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    const follow = () => anchor.current && place(open.index, anchor.current);
    const onDown = (event: PointerEvent) => {
      if (!(event.target as Element).closest?.(`[data-recent="${id}"]`)) close();
    };
    window.addEventListener("scroll", follow, true);
    window.addEventListener("resize", follow);
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onDown);
    return () => {
      window.removeEventListener("scroll", follow, true);
      window.removeEventListener("resize", follow);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown);
    };
  }, [open, close, place, id]);

  if (matches.length === 0) return <span className="text-fg-muted">{MISSING}</span>;
  const shown = open ? matches[open.index] : null;

  return (
    <div data-recent={id} className="flex items-center">
      <ul className="flex items-center gap-1" aria-label={`${teamName} 최근 ${matches.length}경기, 오래된 경기부터`}>
        {matches.map((match, index) => {
          const latest = index === matches.length - 1;
          const result = RESULT_LABEL[match.result];
          return (
            <li key={match.key}>
              <button
                type="button"
                aria-describedby={open?.index === index ? `${id}-popup` : undefined}
                aria-label={`${latest ? "최신 경기 " : ""}${result}: ${dotDate(match.date)} ${match.competition} ${match.home} ${goals(match.goalsHome)} 대 ${goals(match.goalsAway)} ${match.away}`}
                className={cx(
                  // 24px visual box; the 44px touch target comes from the before: layer.
                  "relative inline-flex size-6 items-center justify-center rounded-badge text-caption font-bold",
                  "before:absolute before:-inset-x-0.5 before:-inset-y-2.5 before:content-['']",
                  TONE[match.result],
                  latest && "ring-1 ring-current ring-inset",
                )}
                onPointerDown={(event) => {
                  pointer.current = event.pointerType;
                  wasOpen.current = open?.index === index;
                }}
                onPointerEnter={(event) => event.pointerType === "mouse" && show(index, event.currentTarget)}
                onPointerLeave={(event) => event.pointerType === "mouse" && closeSoon()}
                onFocus={(event) => show(index, event.currentTarget)}
                onBlur={close}
                onClick={(event) => {
                  // A tap toggles the preview (focus may have opened it during this same tap);
                  // a mouse already opened it on hover.
                  if (pointer.current !== "mouse" && wasOpen.current) close();
                  else show(index, event.currentTarget);
                }}
              >
                <span aria-hidden>{result}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {open && shown && (
        <div
          ref={popup}
          id={`${id}-popup`}
          role="tooltip"
          // Hoverable: moving the mouse from the item onto the preview keeps it open.
          onPointerEnter={(event) => event.pointerType === "mouse" && keep()}
          onPointerLeave={(event) => event.pointerType === "mouse" && closeSoon()}
          style={{ top: open.top, left: open.left, width: Math.min(POPUP_WIDTH, window.innerWidth - 16) }}
          className="fixed z-50 flex flex-col gap-1 rounded-control border border-line bg-surface px-3 py-2.5 shadow-lg"
        >
          {open.side && (
            <span
              aria-hidden
              style={{ left: open.caret }}
              className={cx(
                "absolute size-2.5 -translate-x-1/2 rotate-45 border-line bg-surface",
                open.side === "below" ? "-top-[6px] border-t border-l" : "-bottom-[6px] border-r border-b",
              )}
            />
          )}
          <span className="truncate text-small text-fg-secondary tabular-nums">
            {dotDate(shown.date)} · {shown.competition}
          </span>
          <span className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-small text-fg">
            <span className="truncate">{shown.home}</span>
            <span className="text-body font-bold text-action tabular-nums">
              {goals(shown.goalsHome)} : {goals(shown.goalsAway)}
            </span>
            <span className="truncate text-right">{shown.away}</span>
          </span>
        </div>
      )}
    </div>
  );
}
