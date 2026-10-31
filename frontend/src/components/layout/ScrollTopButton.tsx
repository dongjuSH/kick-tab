"use client";

import { Button } from "@/components/ui/Button";

/** "맨 위로" in the desktop footer (COM-003). */
export function ScrollTopButton() {
  return (
    <Button
      variant="ghost"
      onClick={() => {
        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      }}
    >
      맨 위로
    </Button>
  );
}
