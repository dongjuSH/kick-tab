"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

// Figma 308:4617 '우측 패널 · 자기 구간에서만 고정': sticks 12px under the header + TOP 5 strip.
const GAP = 12;

/**
 * PC side panel of the main page that follows the scroll inside its own band (favourites
 * beside the schedule, standings beside the news) and stops at the band's end. Below 1280px
 * the page is one column and this is plain flow (schedule, favourites, news, standings).
 *
 * A panel taller than the window (favourites opened with '더 보기', a low window) used to drop
 * the sticking and scroll away (2026-11-24 report): it now scrolls with the page until its
 * bottom is 12px above the window's bottom and stays there, so every part of it is reachable
 * and it still follows the band.
 */
export function StickyPanel({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [top, setTop] = useState<number | null>(null);

  useEffect(() => {
    const panel = ref.current;
    if (!panel) return;
    const desktop = matchMedia("(min-width: 1280px)");
    const check = () => {
      if (!desktop.matches) return setTop(null);
      const header = document.querySelector("header")?.getBoundingClientRect().height ?? 0;
      const under = header + GAP;
      // Fits: under the header. Taller: its bottom edge is what stays in view.
      setTop(Math.min(under, innerHeight - GAP - panel.offsetHeight));
    };
    // The observer also reports once on observe, so the first check needs no extra call.
    const observer = new ResizeObserver(check);
    observer.observe(panel);
    const header = document.querySelector("header");
    if (header) observer.observe(header);
    addEventListener("resize", check);
    desktop.addEventListener("change", check);
    return () => {
      observer.disconnect();
      removeEventListener("resize", check);
      desktop.removeEventListener("change", check);
    };
  }, []);

  const style: CSSProperties | undefined = top === null ? undefined : { position: "sticky", top };
  return (
    <div ref={ref} style={style}>
      {children}
    </div>
  );
}
