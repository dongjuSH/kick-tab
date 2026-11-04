"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { IconButton } from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { DESKTOP_QUERY, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { Top5List } from "./Top5List";
import {
  isPrevious,
  lineupText,
  noticeCopy,
  noticeOf,
  periodText,
  titleOf,
} from "./model";
import { currentTopMatchesQuery, isOutdated, topMatchesVersionQuery } from "./queries";

const CLOSE_LABEL = "주목 경기 목록 닫기";
// Before the first answer the strip names this week's list (the title follows the data).
const DEFAULT_TITLE = "이번 주 주목 경기 TOP 5";
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';
const STRIP_LAYOUT = "grid min-h-[72px] w-full grid-cols-[minmax(0,1fr)_44px] grid-rows-[44px_1fr] items-center gap-x-2 rounded-control text-left lg:min-h-11 lg:grid-cols-[auto_minmax(0,1fr)_44px] lg:grid-rows-1 lg:gap-x-4";
const SUMMARY_POSITION = "col-span-2 row-start-2 min-w-0 self-start pb-2 text-small text-fg-secondary lg:col-span-1 lg:col-start-2 lg:row-start-1 lg:self-center lg:pb-0";

function Lineup({ text }: { text: string }) {
  const viewport = useRef<HTMLSpanElement>(null);
  const first = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const box = viewport.current;
    const item = first.current;
    if (!box || !item) return;
    const measure = () => {
      const width = item.getBoundingClientRect().width;
      const distance = width + 48;
      box.style.setProperty("--kt-ticker-distance", `${distance}px`);
      box.style.setProperty("--kt-ticker-duration", `${distance / 32}s`);
      box.toggleAttribute("data-overflow", width > box.clientWidth);
    };
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    observer.observe(item);
    measure();
    return () => observer.disconnect();
  }, [text]);
  return (
    <span ref={viewport} className="kt-ticker block overflow-hidden">
      <span className="sr-only">{text}</span>
      <span aria-hidden className="kt-ticker-track flex w-max gap-12 whitespace-nowrap">
        <span ref={first}>{text}</span>
        <span className="kt-ticker-copy">{text}</span>
      </span>
    </span>
  );
}

/** "AI 선정" badge over the title (Figma 159:924 header); read together as the heading. */
function PanelTitle({ children }: { children: ReactNode }) {
  return (
    <span className="flex flex-col items-start gap-1">
      <Badge tone="accent">
        AI 선정
      </Badge>
      {children}
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
 * Figma 159:923). Desktop opens a 1280px panel right under the header with a dimmed,
 * inert page (128:3700); below 1024px it opens a bottom sheet (128:4408, 167:6697).
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

  const titleText = data ? titleOf(data) : DEFAULT_TITLE;
  const title = <PanelTitle>{titleText}</PanelTitle>;
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
    <div ref={root} className="bg-action-soft">
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
          className={cx("kt-ticker-trigger", STRIP_LAYOUT)}
        >
          <span className="col-start-1 row-start-1 flex min-w-0 flex-wrap items-center gap-x-2 text-small lg:flex-nowrap">
            <span className="shrink-0 font-medium text-action">AI 선정</span>
            <span className="font-bold lg:hidden">{data && isPrevious(data) ? "지난주 TOP 5" : "이번 주 TOP 5"}</span>
            <span className="hidden whitespace-nowrap font-bold lg:inline lg:text-body">{titleText}</span>
            {data && <span className="whitespace-nowrap text-fg-secondary">{periodText(data)}</span>}
          </span>
          <span className={SUMMARY_POSITION}>
            {data ? (notice ? noticeCopy(notice, data).short : <Lineup text={lineupText(data)} />)
              : isPending ? <Skeleton className="h-4 w-40" />
              : <span className="text-error">불러오지 못했습니다. 눌러서 다시 확인하세요.</span>}
          </span>
          <span className="col-start-2 row-start-1 flex size-11 items-center justify-center lg:col-start-3">
            <Icon name="chevron-down" className={cx("transition-transform motion-reduce:transition-none", open && "rotate-180")} />
          </span>
          <span className="sr-only">{open ? "목록 접기" : "목록 펼치기"}</span>
        </button>
      </div>

      {isDesktop ? (
        <div id={panelId} hidden={!open}>
          {/* Dimmed page below the header; clicking it closes the panel (Figma 128:3700). */}
          <button
            type="button"
            tabIndex={-1}
            aria-label={CLOSE_LABEL}
            onClick={closePanel}
            className="fixed inset-x-0 bottom-0 top-(--kt-header-height) z-0 cursor-pointer bg-fg/12"
          />
          {/* The container's side gutters let clicks through to the dimmed backdrop. */}
          <div className="kt-container pointer-events-none absolute inset-x-0 top-full z-10">
            <section
              ref={panel}
              role="dialog"
              aria-modal="true"
              aria-labelledby={titleId}
              className="pointer-events-auto flex max-h-[calc(100dvh-var(--kt-header-height)-16px)] flex-col gap-3 rounded-b-card bg-surface p-6"
            >
              <div className="flex items-center gap-2">
                <h2 id={titleId} className="min-w-0 flex-1 text-title font-bold">
                  {title}
                </h2>
                <IconButton icon="x" label={CLOSE_LABEL} onClick={closePanel} data-dialog-close />
              </div>
              {open && list("desktop")}
            </section>
          </div>
        </div>
      ) : (
        <BottomSheet
          id={panelId}
          open={open}
          onClose={() => setOpen(false)}
          title={title}
          closeLabel={CLOSE_LABEL}
          initialFocus="close"
          compact
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
    <div className="bg-action-soft" aria-busy>
      <div className="kt-container">
        <div className={STRIP_LAYOUT}>
          <span className="text-small font-bold lg:text-body">AI 선정 <span className="lg:hidden">이번 주 TOP 5</span><span className="hidden lg:inline">{DEFAULT_TITLE}</span></span>
          <span className={SUMMARY_POSITION}><Skeleton className="h-4 w-40" /></span>
        </div>
      </div>
    </div>
  );
}
