"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { formatPeriod } from "@/lib/format/kst";
import { DESKTOP_QUERY, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { Top5List, scoreText, teamName } from "./Top5List";
import { currentTopMatchesQuery } from "./queries";

const TITLE = "이번 주 인기 경기";

/**
 * This week's TOP 5 strip, fixed under the header on every page (COM-003, TOP-003).
 * Desktop opens a panel below the strip; below 1024px it opens a bottom sheet.
 */
export function Top5Strip() {
  const query = useQuery(currentTopMatchesQuery);
  const { data, isPending, error, refetch } = query;
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const panelId = useId();
  const root = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  // Close on navigation (a TOP 5 item was chosen or the page changed) and when the
  // layout switches between the desktop panel and the mobile sheet.
  const [last, setLast] = useState({ pathname, isDesktop });
  if (last.pathname !== pathname || last.isDesktop !== isDesktop) {
    setLast({ pathname, isDesktop });
    setOpen(false);
  }

  // Desktop panel: Escape and outside clicks close it; focus returns to the toggle.
  useEffect(() => {
    if (!open || !isDesktop) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
      }
    };
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, isDesktop]);

  const items = data?.items ?? [];
  const period = data?.period ? formatPeriod(data.period.start, data.period.end) : null;
  const list = (
    <Top5List
      data={data}
      isPending={isPending}
      error={error}
      onRetry={() => void refetch()}
      onSelect={() => setOpen(false)}
    />
  );

  return (
    <div ref={root} className="relative border-b border-line bg-surface">
      <div className="kt-container py-2">
        <button
          ref={toggle}
          type="button"
          aria-expanded={open}
          aria-controls={isDesktop ? panelId : undefined}
          aria-haspopup={isDesktop ? undefined : "dialog"}
          onClick={() => setOpen((value) => !value)}
          className="flex min-h-[27px] w-full items-center gap-3 rounded-control text-left"
        >
          <Badge tone="info">TOP 5</Badge>
          <span className="shrink-0 whitespace-pre text-small font-medium text-fg">
            {TITLE}
            {period && <span className="hidden lg:inline">{`  ·  ${period}`}</span>}
          </span>
          <span className="hidden min-w-0 flex-1 items-center gap-3 overflow-hidden text-small text-fg-secondary lg:flex">
            {isPending ? (
              <Skeleton className="h-4 w-64" />
            ) : error ? (
              <span className="truncate text-error">불러오지 못했습니다. 눌러서 다시 확인하세요.</span>
            ) : items.length === 0 ? (
              <span className="truncate">이번 주 인기 경기를 준비 중입니다.</span>
            ) : (
              items.slice(0, 2).map((item) => (
                <span key={item.match.id} className="min-w-0 shrink truncate whitespace-pre">
                  {`${item.rank}  ${teamName(item.match.home)} ${scoreText(
                    item.match.score.home,
                    item.match.score.away,
                  )} ${teamName(item.match.away)}`}
                </span>
              ))
            )}
          </span>
          <span className="flex-1 lg:hidden" />
          <Icon name="chevron-down" className={cx("shrink-0 transition-transform", open && "rotate-180")} />
          <span className="sr-only">{open ? "인기 경기 목록 접기" : "인기 경기 목록 펼치기"}</span>
        </button>
      </div>

      {isDesktop ? (
        <div
          id={panelId}
          hidden={!open}
          className="kt-container absolute inset-x-0 top-full z-40 flex justify-end"
        >
          <section
            aria-label={`${TITLE} TOP 5`}
            className="mt-2 w-full max-w-[420px] rounded-card border border-line bg-surface p-6 shadow-lg"
          >
            <h2 className="mb-4 text-title font-bold">{TITLE} TOP 5</h2>
            {open && list}
          </section>
        </div>
      ) : (
        <BottomSheet open={open} onClose={() => setOpen(false)} title={`${TITLE} TOP 5`}>
          {list}
        </BottomSheet>
      )}
    </div>
  );
}
