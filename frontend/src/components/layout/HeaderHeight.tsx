"use client";

import { useEffect, useRef } from "react";

/**
 * Keeps `--kt-header-height` equal to the sticky header's real height. The CSS value (138px) is the
 * designed height; the TOP 5 strip can grow (e.g. last week's week line wrapping at
 * 320px), and the scroll offset and the TOP 5 sheet/backdrop must follow the real bottom edge.
 */
export function HeaderHeight() {
  const marker = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const header = marker.current?.closest("header");
    if (!header) return;
    const root = document.documentElement;
    const sync = () => root.style.setProperty("--kt-header-height", `${Math.ceil(header.getBoundingClientRect().height)}px`);
    const observer = new ResizeObserver(sync);
    observer.observe(header);
    sync();
    return () => {
      observer.disconnect();
      root.style.removeProperty("--kt-header-height");
    };
  }, []);
  return <span ref={marker} hidden />;
}
