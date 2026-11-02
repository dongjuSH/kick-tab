import { Badge } from "@/components/ui/Badge";
import type { NewsBadge, NewsItem } from "@/lib/api/types";
import { formatRelativeKst } from "@/lib/format/kst";

export const NEWS_BADGE_LABELS: Record<NewsBadge, string> = {
  EPL: "EPL",
  LaLiga: "LaLiga",
  SerieA: "Serie A",
  Bundesliga: "Bundesliga",
  Ligue1: "Ligue 1",
  UEFA: "UEFA",
};

/**
 * News card (NEWS-001·004, Figma 49:457): badge, provider title and description, the
 * original link's host and time. No thumbnail, no article body. The card opens the original
 * article in a new tab through a one-time link check (/news/original?id=, NEWS-004). The
 * bookmark button is added by chat 02 (members only).
 */
export function NewsCard({ article, now }: { article: NewsItem; now: Date }) {
  return (
    <a
      href={`/news/original?id=${article.id}`}
      target="_blank"
      rel="noopener"
      className="flex h-full flex-col gap-2.5 rounded-tile border border-line bg-surface p-4 hover:bg-subtle"
    >
      {article.badge && (
        <span>
          <Badge size="caption">{NEWS_BADGE_LABELS[article.badge]}</Badge>
        </span>
      )}
      <h3 className="text-body font-bold text-fg">{article.title}</h3>
      {article.description && <p className="text-label text-fg-secondary">{article.description}</p>}
      <p className="mt-auto text-caption text-fg-muted">
        {article.sourceDomain} · {formatRelativeKst(article.publishedAt, now)} · 원문 보기 ↗
        <span className="sr-only"> (새 창)</span>
      </p>
    </a>
  );
}
