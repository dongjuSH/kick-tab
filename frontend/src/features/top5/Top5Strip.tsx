"use client";

import { useQuery } from "@tanstack/react-query";
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
import { TOP5_TITLE, desktopSummary, mobileSummary, periodText, weekText } from "./model";
import { currentTopMatchesQuery } from "./queries";

const CLOSE_LABEL = "주목 경기 목록 닫기";
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

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

  const title = <PanelTitle>{TOP5_TITLE}</PanelTitle>;
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
  const summary = (text: (value: NonNullable<typeof data>) => string, skeleton: string) =>
    data ? (
      // whitespace-pre keeps the "  |  " gaps of the design between the two matches.
      <span className="overflow-hidden text-ellipsis whitespace-pre">{text(data)}</span>
    ) : isPending ? (
      <Skeleton className={skeleton} />
    ) : (
      <span className="truncate text-error">불러오지 못했습니다. 눌러서 다시 확인하세요.</span>
    );

  return (
    <div ref={root} className="border-b border-line bg-action-soft">
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
          className="flex w-full flex-col gap-1 rounded-control py-2 text-left"
        >
          <span className="flex w-full items-center gap-2">
            <Badge tone="accent">
              AI 선정
            </Badge>
            <span className="min-w-0 flex-1 text-small leading-[18px] font-bold text-fg lg:w-[310px] lg:flex-none lg:text-body lg:leading-[22px]">
              {TOP5_TITLE}
            </span>
            <span className="hidden w-[180px] shrink-0 text-small text-fg-muted lg:block">
              {data && weekText(data)}
            </span>
            <span className="hidden min-w-0 flex-1 text-small text-fg-secondary lg:flex">
              {summary(desktopSummary, "h-4 w-64")}
            </span>
            <span className="flex size-11 shrink-0 items-center justify-center">
              <Icon name="chevron-down" className={cx("transition-transform", open && "rotate-180")} />
            </span>
            <span className="sr-only">{open ? "목록 접기" : "목록 펼치기"}</span>
          </span>
          <span className="flex w-full text-small text-fg-secondary lg:hidden">
            {summary((value) => `${periodText(value)} · ${mobileSummary(value)}`, "h-4 w-56")}
          </span>
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
            className="fixed inset-x-0 bottom-0 top-(--kt-header-height) z-0 cursor-default bg-fg/12"
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
