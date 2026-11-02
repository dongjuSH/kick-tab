"use client";

import { useEffect, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { parseIsoDate } from "@/lib/format/kst";

/**
 * Date bar (SCH-003, Figma 64:1475 desktop / 64:1526 mobile): today .. today+13 in one
 * horizontally scrolling row; about 12 dates fit on desktop and the arrows move by a page,
 * mobile scrolls by touch. `resetKey` brings the row back to the first group (filter reset).
 */
export function DateBar({
  dates,
  today,
  selected,
  onSelect,
  resetKey,
}: {
  dates: readonly string[];
  today: string;
  selected: string;
  onSelect: (date: string) => void;
  resetKey: number;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ start: true, end: false });

  const update = () => {
    const el = scroller.current;
    if (!el) return;
    setEdges({ start: el.scrollLeft <= 1, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1 });
  };

  useEffect(() => {
    scroller.current?.scrollTo({ left: 0 });
    update();
  }, [resetKey]);

  useEffect(() => {
    // Keep the chosen date in view (e.g. after a reload with ?date=).
    scroller.current
      ?.querySelector<HTMLElement>('[aria-pressed="true"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    update();
  }, [selected]);

  const page = (direction: 1 | -1) => {
    const el = scroller.current;
    if (el) el.scrollBy({ left: direction * (el.clientWidth - 62), behavior: "smooth" });
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
        className="min-w-0 flex-1 snap-x overflow-x-auto [scrollbar-width:none]"
        role="group"
        aria-label="날짜 선택 (오늘부터 14일)"
      >
        <div className="flex w-max gap-2">
          {dates.map((date) => {
            const parts = parseIsoDate(date)!;
            const isSelected = date === selected;
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={`${parts.month}월 ${parts.day}일 ${parts.weekday}요일${date === today ? " 오늘" : ""}`}
                onClick={() => onSelect(date)}
                className={cx(
                  "flex w-[54px] shrink-0 snap-start flex-col items-start gap-0.5 rounded-control p-2 text-center",
                  // Figma 225:1216: unselected dates have no fill.
                  isSelected ? "bg-action text-fg-inverse" : "text-fg hover:bg-subtle",
                )}
              >
                <span className="w-full text-caption">{date === today ? "오늘" : parts.weekday}</span>
                <span className="w-full text-subtitle font-bold">{parts.day}</span>
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
