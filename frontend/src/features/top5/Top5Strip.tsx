"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { Fragment, useEffect, useId, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import type { TopMatches } from "@/lib/api/types";
import { DESKTOP_QUERY, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { Top5List } from "./Top5List";
import {
  PREPARING,
  TOP5_TITLE,
  isPrevious,
  lineupItems,
  noticeCopy,
  noticeOf,
  selectedText,
  weekLabel,
} from "./model";
import { currentTopMatchesQuery, isOutdated, topMatchesVersionQuery } from "./queries";

const CLOSE_LABEL = "주목 경기 목록 닫기";
const PANEL_NAME = "주목 경기 선정 목록";
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';
/** Lineup speed (Figma 159:923): 24px per second, linear. */
const TICKER_SPEED = 24;

/*
 * Strip layout (Figma 159:923). Mobile 84px: badge · title over the week · arrow on the first
 * row, the lineup on the second. Desktop 56px: one row with badge, title, week, lineup in the
 * remaining width and the arrow. Badge, title, week and arrow never move.
 */
const STRIP = "grid w-full grid-cols-[auto_minmax(0,1fr)_44px] grid-rows-[minmax(44px,auto)_20px] items-center gap-x-2.5 gap-y-1.5 pt-2 pb-1.5 text-left lg:flex lg:h-14 lg:gap-5 lg:py-0";
const BADGE = "col-start-1 row-start-1 shrink-0 rounded-badge bg-action px-2 py-1 text-small leading-[18px] font-bold text-fg-inverse";
const TITLE_BLOCK = "col-start-2 row-start-1 flex min-w-0 flex-col gap-[3px] lg:contents";
const TITLE = "truncate text-small leading-[18px] font-bold text-fg lg:shrink-0 lg:overflow-visible lg:text-body lg:leading-[22px]";
const WEEK_LINE = "flex flex-wrap items-center gap-x-1.5 text-small font-medium text-fg-secondary lg:shrink-0 lg:flex-nowrap lg:gap-5";
const VIEWPORT = "col-span-3 row-start-2 min-w-0 overflow-hidden text-small text-fg-secondary lg:flex-1 lg:text-body";
const ARROW = "col-start-3 row-start-1 flex size-11 shrink-0 items-center justify-center";

/**
 * Ranks 1-5 as one line that keeps running and starts again at rank 1 at any width: the lap
 * is repeated as many times as the viewport needs so the loop never shows a gap.
 */
function Lineup({ items }: { items: string[] }) {
  const viewport = useRef<HTMLSpanElement>(null);
  const lap = useRef<HTMLSpanElement>(null);
  const copy = useRef<HTMLSpanElement>(null);
  const [copies, setCopies] = useState(1);
  const key = items.join("|");

  useEffect(() => {
    const box = viewport.current;
    const first = lap.current;
    const next = copy.current;
    if (!box || !first || !next) return;
    const measure = () => {
      // Lap width plus the gap before the next copy (32px desktop / 28px mobile).
      const distance = next.offsetLeft - first.offsetLeft;
      if (distance <= 0) return;
      box.style.setProperty("--kt-ticker-distance", `${distance}px`);
      box.style.setProperty("--kt-ticker-duration", `${distance / TICKER_SPEED}s`);
      box.setAttribute("data-ready", "");
      setCopies(Math.max(1, Math.ceil(box.clientWidth / distance)));
    };
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    observer.observe(first);
    measure();
    return () => observer.disconnect();
  }, [key]);

  const run = (
    <>
      {items.map((item, index) => (
        <Fragment key={index}>
          {index > 0 && <span className="text-small font-medium text-fg-muted">·</span>}
          <span>{item}</span>
        </Fragment>
      ))}
    </>
  );
  return (
    <span ref={viewport} className="kt-ticker block overflow-hidden">
      <span className="sr-only">{items.join(", ")}</span>
      <span aria-hidden className="kt-ticker-track flex w-max gap-7 whitespace-nowrap lg:gap-8">
        <span ref={lap} className="flex items-center gap-3 lg:gap-[18px]">{run}</span>
        {Array.from({ length: copies }, (_, index) => (
          <span key={index} ref={index === 0 ? copy : undefined} className="kt-ticker-copy items-center gap-3 lg:gap-[18px]">
            {run}
          </span>
        ))}
      </span>
    </span>
  );
}

/** Week shown in the strip: last week is named as such and this week marked as in progress. */
function WeekLine({ data }: { data: TopMatches }) {
  return (
    <span className={WEEK_LINE}>
      <span className="whitespace-nowrap">{weekLabel(data)}</span>
      {isPrevious(data) && <span className="whitespace-nowrap">{PREPARING}</span>}
    </span>
  );
}

/** Panel/sheet heading (Figma 159:218 / 304:3837): the real week, preparing state, selection time. */
function PanelHeading({ data }: { data: TopMatches | undefined }) {
  const selected = data && selectedText(data);
  return (
    <span className="flex flex-col gap-1">
      <span className="sr-only">{PANEL_NAME} </span>
      <span className="text-subtitle leading-[27px] font-bold text-fg">{data ? weekLabel(data) : TOP5_TITLE}</span>
      {data && isPrevious(data) && <span className="text-small font-normal text-fg-secondary">{PREPARING}</span>}
      {selected && <span className="text-small font-normal text-fg-secondary">{selected}</span>}
    </span>
  );
}

/**
 * Makes everything outside `keep` inert (TOP 5 policy frame 168:348: the background is inert
 * while the desktop panel is open). Returns the undo function.
 */
function inertOutside(keep: HTMLElement): () => void {
  const changed: HTMLElement[] = [];
  for (let node: HTMLElement = keep; node.parentElement && node !== document.body; node = node.parentElement) {
    for (const sibling of node.parentElement.children) {
      if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
        sibling.inert = true;
        changed.push(sibling);
      }
    }
  }
  return () => changed.forEach((element) => (element.inert = false));
}

/**
 * AI weekly TOP 5 strip, fixed under the header on every page (COM-003, TOP-003,
 * Figma 159:923). Desktop unfolds a panel of the content width (max 1280px) right under the
 * strip and folds it back up (159:218); below 1024px it opens a bottom sheet (159:621).
 */
export function Top5Strip() {
  const { data, isPending, error, refetch, isStale } = useQuery(currentTopMatchesQuery);
  const versionQuery = useQuery(topMatchesVersionQuery);
  const version = versionQuery.data;
  const queryClient = useQueryClient();
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const panelId = useId();
  const titleId = useId();
  const root = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);

  // Close on navigation (a TOP 5 match was chosen or the page changed) and when the
  // layout switches between the desktop panel and the mobile sheet.
  const [last, setLast] = useState({ pathname, isDesktop });
  if (last.pathname !== pathname || last.isDesktop !== isDesktop) {
    setLast({ pathname, isDesktop });
    setOpen(false);
  }

  // A replaced public result (new week, delay notice, recovery) or a new KST week is
  // fetched as soon as the version check sees it; the 30-minute refresh is not relied on.
  useEffect(() => {
    if (data && version && isOutdated(data, version)) {
      // Successful checks can share the same data object. Retry a failed replacement on
      // the next check, without cancelling a replacement that is already in flight.
      void queryClient.invalidateQueries(
        { queryKey: currentTopMatchesQuery.queryKey },
        { cancelRefetch: false },
      );
    }
  }, [data, version, versionQuery.dataUpdatedAt, queryClient]);

  const closePanel = () => {
    setOpen(false);
    toggle.current?.focus();
  };

  // Desktop panel (168:348 '접근성'): first focus on the close button, Tab/Shift+Tab cycle
  // inside the panel, the page behind is inert, Escape closes and returns focus to the strip.
  useEffect(() => {
    const section = panel.current;
    if (!open || !isDesktop || !root.current || !section) return;
    const restore = inertOutside(root.current);
    section.querySelector<HTMLElement>("[data-dialog-close]")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
        return;
      }
      if (event.key !== "Tab") return;
      const items = [...section.querySelectorAll<HTMLElement>(FOCUSABLE)];
      const first = items[0];
      const lastItem = items.at(-1);
      const active = document.activeElement;
      if (!first || !lastItem) return;
      if (!section.contains(active)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && active === lastItem) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      restore();
    };
  }, [open, isDesktop]);

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
  const notice = data && noticeOf(data);

  return (
    <div ref={root} className="border-b border-line bg-selected">
      <div className="kt-container">
        <button
          ref={toggle}
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          aria-haspopup="dialog"
          onClick={() => {
            // Expanding shows the latest data when the cached copy is older than 5 min.
            if (!open && isStale) void refetch();
            setOpen((value) => !value);
          }}
          className={cx("kt-ticker-trigger rounded-control", STRIP)}
        >
          <span className={BADGE}>AI 선정</span>
          <span className={TITLE_BLOCK}>
            <span className={TITLE}>{TOP5_TITLE}</span>
            {data ? <WeekLine data={data} /> : <Skeleton className="h-4 w-20" />}
          </span>
          <span className={VIEWPORT}>
            {data ? (
              notice ? <span className="block truncate">{noticeCopy(notice, data).title}</span>
                : <Lineup items={lineupItems(data)} />
            ) : isPending ? <Skeleton className="h-4 w-40" />
              : <span className="block truncate text-error">불러오지 못했습니다. 눌러서 다시 확인하세요.</span>}
          </span>
          <span className={ARROW}>
            <Icon name="chevron-down" className={cx("transition-transform motion-reduce:transition-none", open && "rotate-180")} />
          </span>
          <span className="sr-only">{open ? "목록 접기" : "목록 펼치기"}</span>
        </button>
      </div>

      {isDesktop ? (
        <div id={panelId}>
          {/* Dimmed page below the header; clicking it closes the panel. */}
          {open && (
            <button
              type="button"
              tabIndex={-1}
              aria-label={CLOSE_LABEL}
              onClick={closePanel}
              className="fixed inset-x-0 bottom-0 top-(--kt-header-height) z-0 cursor-pointer bg-fg/12"
            />
          )}
          {/* The container's side gutters let clicks through to the dimmed backdrop. */}
          <div className="kt-container pointer-events-none absolute inset-x-0 top-full z-10">
            <section
              ref={panel}
              role="dialog"
              aria-modal="true"
              aria-labelledby={titleId}
              data-open={open ? "" : undefined}
              // Out of the tab order and the accessibility tree as soon as it starts folding.
              inert={!open}
              className="kt-top5-panel pointer-events-auto flex max-h-[calc(100dvh-var(--kt-header-height)-16px)] flex-col gap-3 rounded-b-card bg-surface px-6 py-5"
            >
              <div className="flex items-start gap-2">
                <h2 id={titleId} className="min-w-0 flex-1">
                  <PanelHeading data={data} />
                </h2>
                <IconButton icon="x" label={CLOSE_LABEL} onClick={closePanel} data-dialog-close />
              </div>
              {list("desktop")}
            </section>
          </div>
        </div>
      ) : (
        <BottomSheet
          id={panelId}
          open={open}
          onClose={() => setOpen(false)}
          title={<PanelHeading data={data} />}
          closeLabel={CLOSE_LABEL}
          initialFocus="close"
          compact
          className="kt-top5-sheet"
        >
          {list("mobile")}
        </BottomSheet>
      )}
    </div>
  );
}

/**
 * The strip before the current path is known (pages with a runtime param, guide §3.1):
 * same box and height, no data yet.
 */
export function Top5StripFallback() {
  return (
    <div className="border-b border-line bg-selected" aria-busy>
      <div className="kt-container">
        <div className={STRIP}>
          <span className={BADGE}>AI 선정</span>
          <span className={TITLE_BLOCK}>
            <span className={TITLE}>{TOP5_TITLE}</span>
            <Skeleton className="h-4 w-20" />
          </span>
          <span className={VIEWPORT}><Skeleton className="h-4 w-40" /></span>
        </div>
      </div>
    </div>
  );
}
