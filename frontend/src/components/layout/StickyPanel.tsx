"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cx } from "@/components/ui/cx";

// Figma 308:4617 '우측 패널 · 자기 구간에서만 고정': sticks 12px under the header + TOP 5 strip;
// available height = window − header − 24px, and only when that is at least 520px and the
// panel fits in it (a taller panel or a low window keeps the normal layout).
const MIN_AVAILABLE = 520;
const RESERVED = 24;

/**
 * PC side panel of the main page that follows the scroll inside its own band (favourites
 * beside the schedule, standings beside the news) and stops at the band's end. Below 1024px
 * it is plain flow (mobile order: schedule, favourites, news, standings).
 */
export function StickyPanel({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [stick, setStick] = useState(false);

  useEffect(() => {
    const panel = ref.current;
    if (!panel) return;
    const desktop = matchMedia("(min-width: 1024px)");
    const check = () => {
      const header = document.querySelector("header")?.getBoundingClientRect().height ?? 0;
      const available = innerHeight - header - RESERVED;
      setStick(desktop.matches && available >= MIN_AVAILABLE && panel.offsetHeight <= available);
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

  return (
    <div ref={ref} className={cx(stick && "sticky top-[calc(var(--kt-header-height)+12px)]")}>
      {children}
    </div>
  );
}
