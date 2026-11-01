import { FeedbackButton } from "@/features/feedback/FeedbackButton";

/**
 * Mobile fixed bottom area with 의견 보내기 (Figma 81:3164). Below 1024px only.
 * The spacer keeps the footer's last line from hiding behind the bar.
 */
export function MobileBottomBar() {
  return (
    <>
      <div aria-hidden className="h-[calc(76px+env(safe-area-inset-bottom))] lg:hidden" />
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface px-4 pt-4 pb-[calc(16px+env(safe-area-inset-bottom))] lg:hidden">
        <FeedbackButton fullWidth />
      </div>
    </>
  );
}
