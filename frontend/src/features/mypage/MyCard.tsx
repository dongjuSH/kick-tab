import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";

/**
 * My page area card (Figma 52:2674: 24px padding, 16px radius, 18px bold title, 16px gaps).
 * The title row may carry an icon before the title, a note after it and an action at its
 * right end (관심 팀: '★ 관심 팀 3 / 10 … 팀 추가').
 */
export function MyCard({
  title,
  titleId,
  icon,
  note,
  action,
  children,
}: {
  title: string;
  titleId: string;
  icon?: ReactNode;
  note?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      aria-labelledby={titleId}
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div className="flex items-center gap-2">
        {icon}
        <h2 id={titleId} tabIndex={-1} className="text-subtitle font-bold text-fg outline-none">
          {title}
        </h2>
        {note}
        {action && <span className="ml-auto">{action}</span>}
      </div>
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
