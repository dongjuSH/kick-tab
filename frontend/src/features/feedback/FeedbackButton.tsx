"use client";

import { Button } from "@/components/ui/Button";
import { useFeedback } from "./FeedbackProvider";

/** Entry point in the footer on every page (FEED-001, Figma 304:3823). */
export function FeedbackButton({ className }: { className?: string }) {
  const { openFeedback } = useFeedback();
  return (
    <Button
      variant="secondary"
      className={className}
      aria-haspopup="dialog"
      onClick={openFeedback}
    >
      의견 보내기
    </Button>
  );
}
