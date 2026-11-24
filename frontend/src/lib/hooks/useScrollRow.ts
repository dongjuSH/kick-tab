"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";

/**
 * A row that scrolls sideways with ‹ › buttons (league chips, favourite-team chips): whether
 * each end is reached, whether it overflows at all, and paging. The edges follow the row's
 * size and its content's size (chips added, removed or renamed).
 */
export function useScrollRow<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [edges, setEdges] = useState({ start: true, end: true });

  const update = useCallback(() => {
    const box = ref.current;
    if (!box) return;
    setEdges({ start: box.scrollLeft <= 1, end: box.scrollLeft + box.clientWidth >= box.scrollWidth - 1 });
  }, []);

  useLayoutEffect(() => {
    const box = ref.current;
    if (!box) return;
    update();
    const observer = new ResizeObserver(update);
    observer.observe(box);
    if (box.firstElementChild) observer.observe(box.firstElementChild);
    // Items added or removed (a favourite team registered or released) change the width too.
    const changes = new MutationObserver(update);
    changes.observe(box, { childList: true, subtree: true, characterData: true });
    return () => {
      observer.disconnect();
      changes.disconnect();
    };
  }, [update]);

  /** Move by the visible width less `overlap` px (0: one full viewport). */
  const page = useCallback((direction: 1 | -1, overlap = 0) => {
    const box = ref.current;
    if (!box) return;
    box.scrollBy({
      left: direction * Math.max(overlap || 1, box.clientWidth - overlap),
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
    });
  }, []);

  /** Scroll just enough to show `item` (a descendant), `margin` px clear of the edge. */
  const reveal = useCallback((item: HTMLElement | null | undefined, margin = 0) => {
    const box = ref.current;
    if (!box || !item) return;
    // The row is the item's offset parent (`relative`), so offsets are in its scroll space.
    const left = item.offsetLeft;
    const right = left + item.offsetWidth;
    if (left < box.scrollLeft) box.scrollLeft = left - margin;
    else if (right > box.scrollLeft + box.clientWidth) box.scrollLeft = right - box.clientWidth + margin;
    update();
  }, [update]);

  return { ref, edges, overflow: !(edges.start && edges.end), update, page, reveal };
}
