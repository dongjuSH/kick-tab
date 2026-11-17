"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { cx } from "@/components/ui/cx";
import type { RecentMatch } from "@/lib/api/types";
import { RESULT_LABEL } from "./model";

const TONE: Record<RecentMatch["result"], string> = {
  W: "bg-live-bg text-live",
  D: "bg-subtle text-fg-secondary",
  L: "bg-error-bg text-error",
};
const POPUP_WIDTH = 248;
// Room the preview needs above its item (two lines and the gap); otherwise it opens below.
const POPUP_ROOM = 88;
// Time to move the mouse from an item onto its preview before the preview closes.
const CLOSE_DELAY = 150;

function name(team: RecentMatch["home"]): string {
  return team.nameKo ?? team.nameEn;
}

/** "2026.11.07". */
function dotDate(iso: string): string {
  return iso.replaceAll("-", ".");
}

interface Box {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/**
 * The part of the screen where an item can be seen: the viewport under the sticky site header
 * (header + TOP 5 strip, COM-003) and inside every scrolling or clipping ancestor — the
 * sideways-scrolling table on phones (Codex 2차 지적 4).
 */
function visibleBox(el: HTMLElement): Box {
  const header = document.querySelector("header.sticky")?.getBoundingClientRect();
  const box: Box = { top: Math.max(0, header?.bottom ?? 0), bottom: window.innerHeight, left: 0, right: window.innerWidth };
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
  below: boolean;
}

/**
 * Last five finished matches of the table, oldest first; the right-most one is the latest and
 * says so ("최신") (LEAG-002 rule 4, Figma 53:1353). Each item opens a preview — date and
 * "home – score – away" (Figma 450:6663) — on PC hover or keyboard focus and on a mobile tap.
 * The preview reads the stored match; opening it never calls the provider. It is placed in
 * the viewport (fixed), so the sideways-scrolling table never clips it. It follows its item
 * when the page or the table scrolls (moving focus with Tab scrolls the page) and closes once
 * the item is hidden — under the sticky header, outside the table's visible part or off the
 * screen — on Escape or on a tap elsewhere. The mouse can move onto the preview without
 * closing it.
 */
export function RecentForm({ matches, teamName }: { matches: readonly RecentMatch[]; teamName: string }) {
  const [open, setOpen] = useState<Open | null>(null);
  const pointer = useRef<string>("mouse");
  // Whether this item's preview was already open when the press began (a tap then closes it).
  const wasOpen = useRef(false);
  const id = useId();
  const anchor = useRef<HTMLElement | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // Places the preview at its item (or closes it when the item is hidden). Following a scroll
  // only moves it: a close already scheduled by the mouse leaving stays (Codex 3차 지적 3).
  const place = useCallback((index: number, el: HTMLElement) => {
    anchor.current = el;
    const rect = el.getBoundingClientRect();
    const box = visibleBox(el);
    const middle = (rect.left + rect.right) / 2;
    if (rect.bottom <= box.top || rect.top >= box.bottom || middle < box.left || middle > box.right) {
      setOpen(null);
      return;
    }
    const below = rect.top - box.top < POPUP_ROOM;
    const left = Math.min(Math.max(8, rect.right - POPUP_WIDTH), window.innerWidth - POPUP_WIDTH - 8);
    setOpen({ index, top: below ? rect.bottom + 8 : rect.top - 8, left, below });
  }, []);
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

  if (matches.length === 0) return <span className="text-fg-muted">—</span>;
  const shown = open ? matches[open.index] : null;

  return (
    <div data-recent={id} className="flex items-center gap-1">
      <ul className="flex items-center gap-1" aria-label={`${teamName} 최근 ${matches.length}경기, 오래된 경기부터`}>
        {matches.map((match, index) => {
          const latest = index === matches.length - 1;
          const result = RESULT_LABEL[match.result];
          return (
            <li key={match.fixtureId}>
              <button
                type="button"
                aria-describedby={open?.index === index ? `${id}-popup` : undefined}
                aria-label={`${latest ? "최신 경기 " : ""}${result}: ${dotDate(match.kickoffDateKst)} ${name(match.home)} ${match.goalsHome} 대 ${match.goalsAway} ${name(match.away)}`}
                className={cx(
                  // 24px visual box; the 44px touch target comes from the before: layer.
                  "relative inline-flex h-6 items-center gap-1 rounded-badge px-1.5 text-caption font-bold",
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
                {latest && (
                  <span aria-hidden className="text-2xs font-medium">
                    최신
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {open && shown && (
        <div
          id={`${id}-popup`}
          role="tooltip"
          // Hoverable: moving the mouse from the item onto the preview keeps it open.
          onPointerEnter={(event) => event.pointerType === "mouse" && keep()}
          onPointerLeave={(event) => event.pointerType === "mouse" && closeSoon()}
          style={{ top: open.top, left: open.left, width: POPUP_WIDTH }}
          className={cx(
            "fixed z-50 flex flex-col gap-1 rounded-control border border-line bg-surface px-3 py-2.5 shadow-lg",
            !open.below && "-translate-y-full",
          )}
        >
          <span className="text-small text-fg-secondary tabular-nums">{dotDate(shown.kickoffDateKst)}</span>
          <span className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-small text-fg">
            <span className="truncate">{name(shown.home)}</span>
            <span className="text-body font-bold text-action tabular-nums">
              {shown.goalsHome} : {shown.goalsAway}
            </span>
            <span className="truncate text-right">{name(shown.away)}</span>
          </span>
        </div>
      )}
    </div>
  );
}
