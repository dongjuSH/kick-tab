"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { parseIsoDate } from "@/lib/format/kst";

export type DateAvailability = "ready" | "empty" | "partial" | "unknown" | "pending";
const DATE_STATUS = { empty: "경기 없음", unknown: "확인 필요", partial: "일부 확인" };

/**
 * A horizontally scrolling row of 21 dates, opening at yesterday unless the selected
 * date needs to be brought into view. Desktop arrows and touch both expose past dates.
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
  const [edges, setEdges] = useState({ start: true, end: false });

  const update = () => {
    const el = scroller.current;
    if (!el) return;
    setEdges({ start: el.scrollLeft <= 1, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1 });
  };

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!visible || !el) return;
    const key = `${today}:${resetKey}`;
    if (initialized.current !== key) {
      initialized.current = key;
      el.scrollLeft = el.querySelector<HTMLElement>("[data-yesterday]")?.offsetLeft ?? 0;
    }
    const target = el.querySelector<HTMLElement>('[aria-pressed="true"]');
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
    <div className="flex items-center gap-2">
      {/* Wrapper decides visibility: "hidden" on the button itself would fight its inline-flex. */}
      <span className="hidden lg:block">
        <IconButton icon="chevron-left" label="이전 날짜 보기" className="disabled:opacity-40" disabled={edges.start} onClick={() => page(-1)} />
      </span>
      <div
        ref={scroller}
        onScroll={update}
        className="relative min-w-0 flex-1 snap-x overflow-x-auto [scrollbar-width:none]"
        role="group"
        aria-label="날짜 선택 (지난 3일부터 향후 17일까지)"
      >
        <div className="flex w-max gap-2">
          {dates.map((date, index) => {
            const parts = parseIsoDate(date)!;
            const isSelected = date === selected;
            const state = availability.get(date);
            const status = state === "empty" || state === "unknown" || state === "partial" ? DATE_STATUS[state] : "";
            const yesterday = dates[index + 1] === today;
            const label = date === today ? "오늘" : yesterday ? "어제" : parts.weekday;
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={`${parts.month}월 ${parts.day}일 ${parts.weekday}요일${date === today ? " 오늘" : yesterday ? " 어제" : ""}${status ? ` · ${status}` : ""}`}
                data-yesterday={yesterday ? "" : undefined}
                disabled={state === "empty"}
                onClick={() => onSelect(date)}
                className={cx(
                  "flex h-16 w-14 shrink-0 snap-start flex-col items-center rounded-control px-1 pt-1.5 text-center",
                  state === "empty" ? "cursor-not-allowed text-fg-muted" :
                    isSelected ? "bg-action text-fg-inverse" : "text-fg hover:bg-subtle",
                )}
              >
                <span className="text-caption">{label}</span>
                <span className="text-lead font-bold">{parts.day}</span>
                {status && <span className="whitespace-nowrap text-[9px] leading-3">{status}</span>}
              </button>
            );
          })}
        </div>
      </div>
      <span className="hidden lg:block">
        <IconButton icon="chevron-right" label="다음 날짜 보기" className="disabled:opacity-40" disabled={edges.end} onClick={() => page(1)} />
      </span>
    </div>
  );
}
