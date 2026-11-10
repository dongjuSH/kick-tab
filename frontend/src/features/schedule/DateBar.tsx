"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { parseIsoDate } from "@/lib/format/kst";

export type DateAvailability = "ready" | "empty" | "partial" | "unknown" | "pending";
const DATE_STATUS = { empty: "경기 없음", unknown: "확인 필요", partial: "일부 확인" };
// A narrow bar (320px: about 29px of text per date) shows these instead; the full words stay
// in each date's accessible name.
const DATE_STATUS_SHORT = { empty: "없음", unknown: "미확인", partial: "일부" };

/**
 * A horizontally scrolling row of 21 dates, opening at yesterday unless the selected
 * date needs to be brought into view. Arrows (every width) and touch both expose past dates.
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
  selected: string;
  onSelect: (date: string) => void;
  resetKey: number;
  availability: ReadonlyMap<string, DateAvailability>;
  visible: boolean;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const initialized = useRef("");
  // Where the row stood while the date view was on screen: the team view hides the bar and
  // clearing the team returns to exactly this position (SCH-006), not to the selected date.
  const lastLeft = useRef(0);
  const wasHidden = useRef(false);
  const [edges, setEdges] = useState({ start: true, end: false });

  const update = () => {
    const el = scroller.current;
    if (!el) return;
    // Only while on screen: a hidden (display: none) row reports 0.
    if (el.offsetParent !== null) lastLeft.current = el.scrollLeft;
    setEdges({ start: el.scrollLeft <= 1, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1 });
  };

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el) return;
    if (!visible) {
      wasHidden.current = true;
      return;
    }
    const key = `${today}:${resetKey}`;
    const target = el.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (initialized.current !== key) {
      initialized.current = key;
      el.scrollLeft = el.querySelector<HTMLElement>("[data-yesterday]")?.offsetLeft ?? 0;
    } else if (wasHidden.current) {
      el.scrollLeft = lastLeft.current;
      wasHidden.current = false;
      update();
      const observer = new ResizeObserver(update);
      observer.observe(el);
      return () => observer.disconnect();
    }
    wasHidden.current = false;
    if (target && (target.offsetLeft < el.scrollLeft
      || target.offsetLeft + target.offsetWidth > el.scrollLeft + el.clientWidth)) {
      el.scrollLeft = target.offsetLeft;
    }
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [resetKey, selected, today, visible]);

  const page = (direction: 1 | -1) => {
    const el = scroller.current;
    if (el) el.scrollBy({ left: direction * Math.max(64, el.clientWidth - 64),
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  };

  return (
    // Arrows at both ends on every width. Mobile (Figma 278:2575): 32px arrow slots (44px
    // targets) and five 52px-high dates 3px apart filling the row (44px wide at 375px, narrower
    // at 320px so five still fit); desktop (49:57) keeps 56×64.
    <div className="flex items-center gap-1.5 lg:gap-2">
      <IconButton icon="chevron-left" label="이전 날짜 보기" className="-mx-1.5 shrink-0 disabled:opacity-40 lg:mx-0" disabled={edges.start} onClick={() => page(-1)} />
      <div
        ref={scroller}
        onScroll={update}
        className="@container relative min-w-0 flex-1 snap-x overflow-x-auto [scrollbar-width:none]"
        role="group"
        aria-label="날짜 선택 (지난 3일부터 향후 17일까지)"
      >
        <div className="flex w-max gap-[3px] lg:gap-2">
          {dates.map((date, index) => {
            const parts = parseIsoDate(date)!;
            const isSelected = date === selected;
            const state = availability.get(date);
            const statusKey = state === "empty" || state === "unknown" || state === "partial" ? state : null;
            const status = statusKey ? DATE_STATUS[statusKey] : "";
            // The row opens at yesterday, which reads as its weekday like every other date.
            const yesterday = dates[index + 1] === today;
            const label = date === today ? "오늘" : parts.weekday;
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={`${parts.month}월 ${parts.day}일 ${parts.weekday}요일${date === today ? " 오늘" : ""}${status ? ` · ${status}` : ""}`}
                data-yesterday={yesterday ? "" : undefined}
                disabled={state === "empty"}
                onClick={() => onSelect(date)}
                className={cx(
                  "flex h-[52px] w-[calc((100cqw-12px)/5)] shrink-0 snap-start flex-col items-center overflow-hidden rounded-control px-0.5 pt-1 text-center lg:h-16 lg:w-14 lg:px-1 lg:pt-1.5",
                  state === "empty" ? "cursor-not-allowed text-fg-muted" :
                    isSelected ? "bg-action text-fg-inverse" : "text-fg hover:bg-subtle",
                )}
              >
                {/* Mobile: a status takes the weekday's slot so the date stays 52px high
                    (Figma 352:10189) — except today, which keeps "오늘" (the status stays in
                    its accessible name and the disabled grey); desktop shows it under the day. */}
                <span className={cx("text-caption", status && date !== today && "hidden lg:inline")}>{label}</span>
                {status && date !== today && (
                  <span className="max-w-full whitespace-nowrap text-[9px] leading-[17px] lg:hidden">
                    <span className="[@container_(max-width:200px)]:hidden">{status}</span>
                    <span className="hidden [@container_(max-width:200px)]:inline">{statusKey && DATE_STATUS_SHORT[statusKey]}</span>
                  </span>
                )}
                <span className="text-lead font-bold">{parts.day}</span>
                {status && <span className="hidden whitespace-nowrap text-[9px] leading-3 lg:inline">{status}</span>}
              </button>
            );
          })}
        </div>
      </div>
      <IconButton icon="chevron-right" label="다음 날짜 보기" className="-mx-1.5 shrink-0 disabled:opacity-40 lg:mx-0" disabled={edges.end} onClick={() => page(1)} />
    </div>
  );
}
