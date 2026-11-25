"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { cx } from "@/components/ui/cx";
import { useScrollRow } from "@/lib/hooks/useScrollRow";
import { STAGES, type UefaStage } from "./model";

const PC = "(min-width: 1024px)";

/**
 * UEFA stage choice under the competition chips (LEAG-002 rule 6; Figma 449:6666 / 61:1653 /
 * 451:20753, 2026-11-24): sub-tabs, not chips — 44px high, 4px apart, 6px corners, 13px
 * Medium; the chosen one on #f1f5f9 in #2563eb, the others without a background in #475569.
 * A row wider than its box scrolls sideways (no arrows) and the chosen tab is kept in view.
 *
 * On PC the row starts under the "UEFA 챔피언스리그" chip: its left edge is measured from the
 * chip itself (`firstUefa`, the chip at that index in the competition row of the nearest
 * `[data-competition-choices]` box around these tabs), so it follows when the chip row is
 * scrolled or the window resized. Phones start at the left. (The box is found from the tabs'
 * own element: a parent's ref is not attached yet when a child's layout effect runs.)
 */
export function StageTabs({
  value,
  onChange,
  firstUefa,
}: {
  value: UefaStage | null;
  onChange: (stage: UefaStage) => void;
  firstUefa: number;
}) {
  const { ref: row, update, reveal } = useScrollRow<HTMLDivElement>();
  const box = useRef<HTMLDivElement>(null);
  const [inset, setInset] = useState(0);

  useLayoutEffect(() => {
    const own = box.current;
    const scope = own?.closest<HTMLElement>("[data-competition-choices]");
    if (!scope || !own) return;
    // The competition chip row is the first group in the box (the stage tabs come after it).
    const competitions = scope.querySelector<HTMLElement>('[role="group"]');
    const measure = () => {
      const chip = competitions?.querySelectorAll<HTMLElement>("button")[firstUefa];
      if (!chip || !matchMedia(PC).matches) {
        setInset(0);
        return;
      }
      const left = chip.getBoundingClientRect().left - own.getBoundingClientRect().left;
      // Never left of the box, and always room for a few tabs on the right.
      setInset(Math.round(Math.max(0, Math.min(left, own.clientWidth - 160))));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(scope);
    // The chips themselves can change width while the box keeps its size: a web font applied
    // late on a first visit (no font cache — 00 검수 2026-11-25: tab 28px right of the chip at
    // 1920 until a resize), or names replaced once `/competitions` arrives. Watch the chip
    // row's content, and measure again when fonts finish loading.
    if (competitions?.firstElementChild) observer.observe(competitions.firstElementChild);
    let live = true;
    void document.fonts?.ready.then(() => live && measure());
    document.fonts?.addEventListener("loadingdone", measure);
    // The competition row scrolling (‹ ›, wheel, swipe) moves the chip.
    scope.addEventListener("scroll", measure, true);
    window.addEventListener("resize", measure);
    return () => {
      live = false;
      observer.disconnect();
      document.fonts?.removeEventListener("loadingdone", measure);
      scope.removeEventListener("scroll", measure, true);
      window.removeEventListener("resize", measure);
    };
  }, [firstUefa]);

  useEffect(() => {
    reveal(row.current?.querySelector<HTMLElement>('[aria-pressed="true"]'), 8);
  }, [value, inset, row, reveal]);

  return (
    <div ref={box} style={{ paddingLeft: inset }}>
      <div
        ref={row}
        role="group"
        aria-label="단계"
        onScroll={update}
        className="relative overflow-x-auto [scrollbar-width:none]"
      >
        <div className="flex w-max items-center gap-1">
          {STAGES.map((stage) => {
            const selected = stage.value === value;
            return (
              <button
                key={stage.value}
                type="button"
                aria-pressed={selected}
                className={cx(
                  "inline-flex h-11 shrink-0 items-center rounded-[6px] px-3 text-label font-medium focus-visible:-outline-offset-3",
                  selected ? "bg-subtle text-action" : "text-fg-secondary hover:text-fg",
                )}
                onClick={() => onChange(stage.value)}
              >
                {stage.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
