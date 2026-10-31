"use client";

import { Button } from "@/components/ui/Button";
import { useFeedback } from "./FeedbackProvider";

/** Entry point placed in the desktop footer and the mobile bottom bar (FEED-001). */
export function FeedbackButton({ className, fullWidth }: { className?: string; fullWidth?: boolean }) {
  const { openFeedback } = useFeedback();
  return (
    <Button
      variant="secondary"
      fullWidth={fullWidth}
      className={className}
      aria-haspopup="dialog"
      onClick={openFeedback}
    >
      의견 보내기
    </Button>
  );
}
