"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { IconButton } from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { formatPeriod } from "@/lib/format/kst";
import { DESKTOP_QUERY, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { Top5List, scoreText, teamName } from "./Top5List";
import { currentTopMatchesQuery } from "./queries";

const TITLE = "이번 주 인기 경기";
const PANEL_TITLE = `${TITLE} TOP 5`;

/**
 * This week's TOP 5 strip, fixed under the header on every page (COM-003, TOP-003).
 * Desktop opens a full-width panel under the header with a dimmed page (Figma 128:3700);
 * below 1024px it opens a bottom sheet (Figma 128:4408).
 */
export function Top5Strip() {
  const { data, isPending, error, refetch, isStale } = useQuery(currentTopMatchesQuery);
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const panelId = useId();
  const titleId = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);

  // Close on navigation (a TOP 5 item was chosen or the page changed) and when the
  // layout switches between the desktop panel and the mobile sheet.
  const [last, setLast] = useState({ pathname, isDesktop });
  if (last.pathname !== pathname || last.isDesktop !== isDesktop) {
    setLast({ pathname, isDesktop });
    setOpen(false);
  }

  const closePanel = () => {
    setOpen(false);
    toggle.current?.focus();
  };

  // Desktop panel: move focus in on open, Escape closes and returns focus to the strip.
  useEffect(() => {
    if (!open || !isDesktop) return;
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, isDesktop]);

  const items = data?.items ?? [];
  const period = data?.period ? formatPeriod(data.period.start, data.period.end) : null;
  const list = (layout: "desktop" | "mobile") => (
    <Top5List
      layout={layout}
      data={data}
      isPending={isPending}
      error={error}
      onRetry={() => void refetch()}
      onSelect={() => setOpen(false)}
    />
  );

  return (
    <div className="border-b border-line bg-surface">
      <div className="kt-container">
        <button
          ref={toggle}
          type="button"
          aria-expanded={open}
          aria-controls={isDesktop ? panelId : undefined}
          aria-haspopup={isDesktop ? undefined : "dialog"}
          onClick={() => {
            // Expanding shows the latest selection when the cached one is older than 5 min.
            if (!open && isStale) void refetch();
            setOpen((value) => !value);
          }}
          // The strip is 43px tall (Figma); the ::before overhang makes the hit area 45px
          // without changing the header's 113/129px height (guide §6.6 44px touch target).
          className="relative flex min-h-[43px] w-full items-center gap-3 rounded-control py-2 text-left before:absolute before:inset-x-0 before:-inset-y-px before:content-['']"
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
              <span className="truncate">아직 선정된 경기가 없어요.</span>
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
        <div id={panelId} hidden={!open}>
          {/* Dimmed page below the header; clicking it closes the panel (Figma 128:4249). */}
          <button
            type="button"
            tabIndex={-1}
            aria-label="인기 경기 목록 닫기"
            onClick={closePanel}
            className="fixed inset-x-0 bottom-0 top-(--kt-header-height) z-0 cursor-default bg-fg/12"
          />
          <div className="kt-container absolute inset-x-0 top-full z-10">
            <section
              ref={panel}
              tabIndex={-1}
              aria-labelledby={titleId}
              className="flex max-h-[calc(100dvh-var(--kt-header-height)-16px)] flex-col gap-3 overflow-y-auto rounded-b-card border border-t-0 border-line bg-surface p-6 outline-none"
            >
              <div className="flex items-center gap-2">
                <h2 id={titleId} className="min-w-0 flex-1 text-title leading-7 font-bold">
                  {PANEL_TITLE}
                </h2>
                <IconButton icon="x" label="인기 경기 목록 닫기" onClick={closePanel} />
              </div>
              {open && list("desktop")}
            </section>
          </div>
        </div>
      ) : (
        <BottomSheet open={open} onClose={() => setOpen(false)} title={PANEL_TITLE} compact>
          {list("mobile")}
        </BottomSheet>
      )}
    </div>
  );
}
