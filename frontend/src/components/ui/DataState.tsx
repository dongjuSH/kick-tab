import type { ReactNode } from "react";
import { isApiError } from "@/lib/api/errors";
import { Button } from "./Button";
import { cx } from "./cx";
import { Icon } from "./Icon";
import { Skeleton } from "./Skeleton";

/**
 * Standard request states (COM-004, guide §4·§6.6): loading / ready / empty / partial /
 * error / denied. Empty and error copy are always different so "no data" is never mistaken
 * for a failure; "denied" is for member-only data (e.g. a login prompt as `deniedAction`).
 */
export type DataStatus = "loading" | "ready" | "empty" | "partial" | "error" | "denied";

interface DataStateProps {
  status: DataStatus;
  children?: ReactNode;
  loadingFallback?: ReactNode;
  emptyTitle?: ReactNode;
  emptyDescription?: ReactNode;
  /** Error from the query; ApiError messages are shown as-is. */
  error?: unknown;
  errorTitle?: ReactNode;
  onRetry?: () => void;
  /** Shown above the data when some fields/blocks were not provided. */
  partialNotice?: ReactNode;
  deniedTitle?: ReactNode;
  deniedDescription?: ReactNode;
  deniedAction?: ReactNode;
  className?: string;
}

const DEFAULT_ERROR = "잠시 후 다시 시도해 주세요.";

export function StateMessage({
  title,
  description,
  action,
  tone = "neutral",
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  /** neutral = search icon (Figma empty/success state), error = info icon (57:150), plain = no icon. */
  tone?: "neutral" | "plain" | "error";
  className?: string;
}) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cx("flex flex-col items-center gap-3 p-6 text-center", className)}
    >
      {tone === "neutral" && <Icon name="search" />}
      {tone === "error" && <Icon name="info" />}
      <p className="text-lead font-bold text-fg">{title}</p>
      {description && <p className="text-body text-fg-secondary">{description}</p>}
      {action}
    </div>
  );
}

export function DataState({
  status,
  children,
  loadingFallback,
  emptyTitle = "표시할 정보가 없습니다",
  emptyDescription,
  error,
  errorTitle = "정보를 불러오지 못했습니다",
  onRetry,
  partialNotice = "일부 정보는 제공되지 않습니다.",
  deniedTitle = "로그인이 필요합니다",
  deniedDescription,
  deniedAction,
  className,
}: DataStateProps) {
  if (status === "loading") {
    return (
      <div aria-busy className={className}>
        {loadingFallback ?? (
          <div className="flex flex-col gap-2 p-4">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-1/2" />
          </div>
        )}
        <span className="sr-only">불러오는 중</span>
      </div>
    );
  }
  if (status === "error") {
    return (
      <StateMessage
        tone="error"
        className={className}
        title={errorTitle}
        description={isApiError(error) ? error.message : DEFAULT_ERROR}
        action={onRetry && <Button onClick={onRetry}>다시 확인</Button>}
      />
    );
  }
  if (status === "denied") {
    return (
      <StateMessage
        tone="plain"
        className={className}
        title={deniedTitle}
        description={deniedDescription}
        action={deniedAction}
      />
    );
  }
  if (status === "empty") {
    return <StateMessage className={className} title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <div className={className}>
      {status === "partial" && (
        <p className="mb-3 rounded-control bg-subtle px-3 py-2 text-small text-fg-secondary">{partialNotice}</p>
      )}
      {children}
    </div>
  );
}
