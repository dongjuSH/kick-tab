import Link from "next/link";
import { cx } from "./cx";

type PageEntry = number | "gap";

/** Page numbers with gaps, e.g. 1 … 4 5 6 … 20. */
function pageEntries(page: number, totalPages: number, siblings = 1): PageEntry[] {
  if (totalPages <= 0) return [];
  const pages = new Set([1, totalPages]);
  for (let p = page - siblings; p <= page + siblings; p += 1) {
    if (p >= 1 && p <= totalPages) pages.add(p);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const entries: PageEntry[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) entries.push("gap");
    entries.push(p);
  });
  return entries;
}

interface PaginationProps {
  page: number;
  totalPages: number;
  /** URL for a page (screen state lives in the URL, guide §6.6). */
  hrefFor: (page: number) => string;
  label?: string;
  className?: string;
}

const ITEM = "inline-flex min-h-11 min-w-11 items-center justify-center rounded-control px-2 text-body";

export function Pagination({ page, totalPages, hrefFor, label = "페이지 이동", className }: PaginationProps) {
  if (totalPages <= 1) return null;
  const edge = (target: number, text: string, disabled: boolean) =>
    disabled ? (
      <span className={cx(ITEM, "text-fg-muted")} aria-disabled>
        {text}
      </span>
    ) : (
      <Link className={cx(ITEM, "text-fg-secondary hover:bg-subtle")} href={hrefFor(target)} scroll={false}>
        {text}
      </Link>
    );

  return (
    <nav aria-label={label} className={cx("flex flex-wrap items-center justify-center gap-1", className)}>
      {edge(page - 1, "이전", page <= 1)}
      {pageEntries(page, totalPages).map((entry, index) =>
        entry === "gap" ? (
          <span key={`gap-${index}`} className={cx(ITEM, "text-fg-muted")} aria-hidden>
            …
          </span>
        ) : (
          <Link
            key={entry}
            href={hrefFor(entry)}
            scroll={false}
            aria-current={entry === page ? "page" : undefined}
            className={cx(
              ITEM,
              entry === page ? "bg-selected font-bold text-action" : "text-fg-secondary hover:bg-subtle",
            )}
          >
            {entry}
          </Link>
        ),
      )}
      {edge(page + 1, "다음", page >= totalPages)}
    </nav>
  );
}
