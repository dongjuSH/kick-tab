"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { NewsCard } from "@/components/common/NewsCard";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { teamNewsQuery } from "./queries";
import { AREA } from "./TeamMatches";

/**
 * TEAM-004 · NEWS-003 (Figma 52:1254 팀 관련 뉴스, mobile 58:924): the same card as the main
 * news for articles linked to this team by an unambiguous alias, newest first, six at a time
 * up to the 24 newest (the server caps the list; the main news keeps 48).
 * The badge is the article's own competition (no league badge is guessed from the team).
 * No related article is an empty state; another team's news is never used instead.
 */
export function TeamNews({ teamId }: { teamId: number }) {
  const news = useInfiniteQuery(teamNewsQuery(teamId));
  const articles = news.data?.pages.flatMap((page) => page.data) ?? [];
  const meta = news.data?.pages[0]?.meta;
  // Relative times are computed only once articles exist (never in the server prerender).
  const now = articles.length ? new Date() : null;
  // TEAM-004 · NEWS-003 · UF-11 (2026-11-18): the "no article" message only.
  const emptyTitle = "현재 확인할 수 있는 팀 관련 뉴스가 없습니다.";
  // A failed collection or re-check is said first, also when the confirmed list is empty
  // (Codex 1차 지적 9): never just "no news".
  const refreshFailed = Boolean(meta?.stale) || news.isRefetchError;
  const status = news.isPending
    ? "loading"
    : news.isError && news.data === undefined
      ? "error"
      : refreshFailed
        ? "partial"
        : articles.length === 0
          ? "empty"
          : "ready";
  const retry = () => void news.refetch();

  return (
    <section aria-labelledby="team-news" className={AREA}>
      <h2 id="team-news" className="text-title font-bold">팀 관련 뉴스</h2>
      <DataState
        status={status}
        error={news.error}
        errorTitle="뉴스를 불러오지 못했습니다"
        onRetry={retry}
        retryLabel="다시 시도"
        emptyTitle={emptyTitle}
        partialNotice="최신 뉴스를 불러오지 못해 마지막으로 수집한 기사를 보여줍니다."
        partialAction={<Button onClick={retry}>다시 시도</Button>}
        loadingFallback={
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-[170px]" />
            <Skeleton className="h-[170px]" />
          </div>
        }
      >
        {articles.length === 0 ? (
          <StateMessage title={emptyTitle} />
        ) : (
          <ul className="grid gap-4 md:grid-cols-2">
            {articles.map((article) => (
              <li key={article.id}>
                <NewsCard article={article} now={now!} />
              </li>
            ))}
          </ul>
        )}
        {news.hasNextPage && (
          <Button fullWidth className="mt-4" disabled={news.isFetchingNextPage} onClick={() => news.fetchNextPage()}>
            {news.isFetchingNextPage ? "불러오는 중" : `관련 뉴스 더 보기 (${articles.length}/${meta?.total ?? articles.length})`}
          </Button>
        )}
        {news.isFetchNextPageError && (
          <p role="alert" className="mt-2 text-small text-error">
            추가 뉴스를 불러오지 못했습니다. 관련 뉴스 더 보기를 다시 눌러 주세요.
          </p>
        )}
      </DataState>
      <p className="text-caption text-fg-muted">
        팀 관련 최신 기사를 최대 24개까지 표시합니다.
        <br />
        뉴스 제공: 네이버 검색 · 기사 원문과 출처를 확인하세요.
      </p>
    </section>
  );
}
