"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { parseIsoDate } from "@/lib/format/kst";

export type DateAvailability = "ready" | "empty" | "partial" | "unknown" | "pending";
const DATE_STATUS = { unknown: "확인 필요", partial: "일부 확인" };
// A narrow bar (320px: about 29px of text per date) shows these instead; the full words stay
// in each date's accessible name.
const DATE_STATUS_SHORT = { unknown: "미확인", partial: "일부" };
// PC dates are about 64px (Figma 278:2398: eleven in the 1280 layout): the row holds as many
// whole dates of at least 60px as fit and stretches them to fill it, so no date is ever cut.
const DESKTOP_DAY_MIN = 60;

/**
 * The common match-day row (SCH-002, Figma 234:8881 / 234:9750): only dates with a match,
 * each with its weekday and month/day. It opens with the latest past match day first, so that
 * day and the selected one (today or the next match day) are both in view. Arrows (every
 * width) and touch scroll it one whole date at a time: the row always shows whole dates only
 * (2026-11-24), the arrows move by a full row and touch scrolling snaps to a date.
 */
export function DateBar({
  dates,
  today,
  selected,
  onSelect,
  resetKey,
  availability,
  visible,
}: {
  dates: readonly string[];
  today: string;
  selected: string | null;
  onSelect: (date: string) => void;
  resetKey: number;
  availability: ReadonlyMap<string, DateAvailability>;
  visible: boolean;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const row = useRef<HTMLDivElement>(null);
  // Width of one date plus the gap, and how many dates the row shows.
  const cell = useRef({ step: 0, count: 0 });
  const initialized = useRef("");
  // Where the row stood while the date view was on screen: the team view hides the bar and
  // clearing the team returns to exactly this position (SCH-006), not to the selected date.
  const lastLeft = useRef(0);
  const wasHidden = useRef(false);
  const [edges, setEdges] = useState({ start: true, end: false });
  const ready = dates.length > 0;
  const shown = dates.join(",");

  // Fit whole dates: PC as many 60px-or-wider dates as the row holds, phones five (four when
  // the row is 240px or less). A changed width keeps the same first date in view.
  const fit = () => {
    const el = scroller.current;
    const inner = row.current;
    if (!el || !inner || el.clientWidth === 0) return;
    const width = el.clientWidth;
    const gap = parseFloat(getComputedStyle(inner).columnGap) || 0;
    const count = matchMedia("(min-width: 1024px)").matches
      ? Math.max(1, Math.floor((width + gap) / (DESKTOP_DAY_MIN + gap)))
      : width <= 240 ? 4 : 5;
    const day = (width - (count - 1) * gap) / count;
    const previous = cell.current.step;
    cell.current = { step: day + gap, count };
    if (Math.abs(previous - (day + gap)) < 0.01) return;
    const first = previous ? Math.round(el.scrollLeft / previous) : null;
    inner.style.setProperty("--kt-day-width", `${day}px`);
    if (first !== null) el.scrollLeft = first * (day + gap);
  };

  const update = () => {
    const el = scroller.current;
    if (!el) return;
    // Only while on screen: a hidden (display: none) row reports 0.
    if (el.offsetParent !== null) lastLeft.current = el.scrollLeft;
    setEdges({ start: el.scrollLeft <= 1, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1 });
  };

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el || !ready) return;
    if (!visible) {
      wasHidden.current = true;
      return;
    }
    const key = `${today}:${resetKey}`;
    const target = el.querySelector<HTMLElement>('[aria-pressed="true"]');
    fit();
    const observe = () => {
      update();
      const observer = new ResizeObserver(() => {
        fit();
        update();
      });
      observer.observe(el);
      return () => observer.disconnect();
    };
    if (initialized.current !== key) {
      initialized.current = key;
      el.scrollLeft = el.querySelector<HTMLElement>("[data-last-past]")?.offsetLeft ?? 0;
    } else if (wasHidden.current) {
      el.scrollLeft = lastLeft.current;
      wasHidden.current = false;
      return observe();
    }
    wasHidden.current = false;
    if (target && target.offsetLeft < el.scrollLeft) el.scrollLeft = target.offsetLeft;
    else if (target && target.offsetLeft + target.offsetWidth > el.scrollLeft + el.clientWidth) {
      // Keep the past day in view when it fits: bring the selection in from the right edge.
      el.scrollLeft = target.offsetLeft + target.offsetWidth - el.clientWidth;
    }
    return observe();
  }, [ready, resetKey, selected, shown, today, visible]);

  // One full row of whole dates per press, landing on a date edge.
  const page = (direction: 1 | -1) => {
    const el = scroller.current;
    const { step, count } = cell.current;
    if (!el || !step) return;
    const first = Math.round(el.scrollLeft / step) + direction * count;
    el.scrollTo({ left: Math.max(0, first * step),
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  };
  const lastPast = dates.findLast((date) => date < today);

  return (
    // Arrows at both ends on every width. Mobile (Figma 234:9750): 32px arrow slots (44px
    // targets) and five dates 3px apart filling the row (four when the row is 240px or less);
    // desktop (278:2398): whole ~64×52 dates 4px apart, arrows 8px from the row.
    <div className="flex items-center gap-1.5 lg:gap-2">
      <IconButton icon="chevron-left" label="이전 날짜 보기" className="-mx-1.5 shrink-0 disabled:opacity-40 lg:mx-0" disabled={edges.start} onClick={() => page(-1)} />
      <div
        ref={scroller}
        onScroll={update}
        className="@container relative min-w-0 flex-1 snap-x snap-mandatory overflow-x-auto [scrollbar-width:none]"
        role="group"
        aria-label="경기 날짜 선택"
      >
        <div ref={row} className="flex w-max gap-[3px] lg:gap-1">
          {dates.map((date) => {
            const parts = parseIsoDate(date)!;
            const isSelected = date === selected;
            const state = availability.get(date);
            const statusKey = state === "unknown" || state === "partial" ? state : null;
            const status = statusKey ? DATE_STATUS[statusKey] : "";
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={`${parts.month}월 ${parts.day}일 ${parts.weekday}요일${status ? ` · ${status}` : ""}`}
                data-last-past={date === lastPast ? "" : undefined}
                onClick={() => onSelect(date)}
                className={cx(
                  "relative flex min-h-[52px] w-(--kt-day-width,60px) shrink-0 snap-start flex-col items-center justify-center overflow-hidden rounded-control border px-0.5 py-1 text-center",
                  isSelected ? "border-action bg-selected text-action" : "border-transparent text-fg hover:bg-subtle",
                )}
              >
                <span className={cx("text-caption", !isSelected && "text-fg-muted")}>{parts.weekday}</span>
                {/* A bar of 240px or less (375px and below) shows four dates so month/day fit;
                    at 320px (about 42px each) the text steps down to 14px so "11/15" is never cut. */}
                <span className="whitespace-nowrap text-[15px] font-medium leading-[22px] [@container_(max-width:190px)]:text-[14px]">
                  {parts.month}/{parts.day}
                </span>
                {status && (
                  <span className="max-w-full whitespace-nowrap text-[10px] leading-3 text-fg-muted">
                    <span className="[@container_(max-width:200px)]:hidden">{status}</span>
                    <span className="hidden [@container_(max-width:200px)]:inline">{statusKey && DATE_STATUS_SHORT[statusKey]}</span>
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
      <IconButton icon="chevron-right" label="다음 날짜 보기" className="-mx-1.5 shrink-0 disabled:opacity-40 lg:mx-0" disabled={edges.end} onClick={() => page(1)} />
    </div>
  );
}
