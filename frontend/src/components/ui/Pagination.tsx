import { Button } from "./Button";

/** 이전/다음 (ghost look): own classes, since padding added to Button loses to its px-4. */
const STEP =
  "inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center whitespace-nowrap rounded-control px-2 " +
  "text-body font-medium text-fg hover:bg-subtle disabled:cursor-not-allowed disabled:text-fg-muted " +
  "disabled:hover:bg-transparent sm:px-3";

/** Page numbers around the current page: three, kept inside 1..pages (Figma 53:926). */
function windowOf(page: number, pages: number): number[] {
  const start = Math.max(1, Math.min(page - 1, pages - 2));
  return Array.from({ length: Math.min(3, pages) }, (_, i) => start + i);
}

/**
 * Page navigation (Figma `결과 페이지` 53:926: 이전 · three numbers · 다음, 44px). From 640px
 * the first and last page are added with "…" when outside the three, so a long season's last
 * page is one press away; narrow screens keep the design's five buttons.
 */
export function Pagination({
  page,
  pages,
  onChange,
  label = "페이지",
}: {
  page: number;
  pages: number;
  onChange: (page: number) => void;
  label?: string;
}) {
  if (pages <= 1) return null;
  const numbers = windowOf(page, pages);
  // A wrapper hides the edge buttons: `hidden` on the Button itself loses to its inline-flex.
  const edge = (target: number) => (
    <span key={`edge-${target}`} className="hidden sm:inline-flex">
      <PageButton page={target} current={page} onChange={onChange} />
    </span>
  );
  const gap = (key: string) => (
    <span key={key} aria-hidden className="hidden w-4 text-center text-fg-muted sm:inline">
      …
    </span>
  );
  return (
    <nav aria-label={label} className="flex items-center justify-center gap-1 sm:gap-2">
      <button type="button" className={STEP} disabled={page <= 1} onClick={() => onChange(page - 1)}>
        이전
      </button>
      {numbers[0] > 1 && [edge(1), numbers[0] > 2 && gap("start")]}
      {numbers.map((n) => (
        <PageButton key={n} page={n} current={page} onChange={onChange} />
      ))}
      {numbers[numbers.length - 1] < pages && [
        numbers[numbers.length - 1] < pages - 1 && gap("end"),
        edge(pages),
      ]}
      <button type="button" className={STEP} disabled={page >= pages} onClick={() => onChange(page + 1)}>
        다음
      </button>
    </nav>
  );
}

function PageButton({
  page,
  current,
  onChange,
}: {
  page: number;
  current: number;
  onChange: (page: number) => void;
}) {
  const active = page === current;
  return (
    <Button
      variant={active ? "primary" : "ghost"}
      aria-current={active ? "page" : undefined}
      aria-label={`${page}페이지`}
      onClick={() => !active && onChange(page)}
      className="min-w-11 shrink-0"
    >
      {page}
    </Button>
  );
}
