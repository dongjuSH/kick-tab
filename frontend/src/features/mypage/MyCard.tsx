import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";

/** My page area card (Figma 52:2674: 24px padding, 16px radius, 18px bold title, 16px gaps). */
export function MyCard({ title, titleId, children }: { title: string; titleId: string; children: ReactNode }) {
  return (
    <section
      aria-labelledby={titleId}
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <h2 id={titleId} tabIndex={-1} className="text-subtitle font-bold text-fg outline-none">
        {title}
      </h2>
      {children}
    </section>
  );
}

/** Area error (Figma 639:8154): the message and a full-width '다시 시도'; other areas stay. */
export function AreaError({ text, onRetry }: { text: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col gap-4">
      <p className="text-body text-fg-secondary">{text}</p>
      <Button fullWidth onClick={onRetry}>
        다시 시도
      </Button>
    </div>
  );
}
