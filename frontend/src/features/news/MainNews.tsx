"use client";

import { infiniteQueryOptions, useInfiniteQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ChipLabel, chipClass } from "@/components/ui/chip";
import { NEWS_BADGE_LABELS, NewsCard } from "@/components/common/NewsCard";
import { Button } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { NewsBadge, NewsItem, NewsMeta } from "@/lib/api/types";

const PAGE_SIZE = 6;
const BADGES = Object.keys(NEWS_BADGE_LABELS) as NewsBadge[];

function newsQuery(badge: NewsBadge | null) {
  return infiniteQueryOptions({
    queryKey: queryKeys.news.list(badge),
    queryFn: ({ pageParam, signal }) =>
      apiFetch<NewsItem[], NewsMeta>("/news", { query: { badge, cursor: pageParam, size: PAGE_SIZE }, signal }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.meta.nextCursor,
    staleTime: 5 * 60_000,
    refetchInterval: 60_000,
  });
}

/**
 * "주요 뉴스" (NEWS-001·002, Figma 49:438 / 49:915): six cards, then "뉴스 더 보기"; league /
 * UEFA chips filter by the rule-based badge. The badge choice is not part of the schedule
 * filter reset (SCH-006).
 */
export function MainNews() {
  const [badge, setBadge] = useState<NewsBadge | null>(null);
  const news = useInfiniteQuery(newsQuery(badge));
  const articles = news.data?.pages.flatMap((page) => page.data) ?? [];
  const meta = news.data?.pages[0]?.meta;
  // Relative times are computed only once articles exist (never in the server prerender).
  const now = articles.length ? new Date() : null;

  // Only a failure with nothing loaded replaces the list: a failed "더 보기" page or
  // background refresh keeps the articles already shown.
  const status = news.isPending
    ? "loading"
    : news.isError && articles.length === 0
      ? "error"
      : articles.length === 0
        ? "empty"
        : meta?.stale
          ? "partial"
          : "ready";

  return (
    <section
      aria-labelledby="news-title"
      className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6"
    >
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
        <h2 id="news-title" className="text-subtitle font-bold">주요 뉴스</h2>
        <p className="text-small text-fg-secondary">매시간 수집 · 전체 최신 최대 48개</p>
      </div>
      <div className="-mx-1 overflow-x-auto px-1 py-1 [scrollbar-width:none]" role="group" aria-label="뉴스 분류">
        <div className="flex w-max gap-2">
          {[null, ...BADGES].map((value) => (
            <button
              key={value ?? "all"}
              type="button"
              aria-pressed={badge === value}
              className={chipClass(badge === value)}
              onClick={() => setBadge(value)}
            >
              <ChipLabel>{value ? NEWS_BADGE_LABELS[value] : "전체"}</ChipLabel>
            </button>
          ))}
        </div>
      </div>

      <DataState
        status={status}
        error={news.error}
        errorTitle="뉴스를 불러오지 못했습니다"
        onRetry={() => news.refetch()}
        emptyTitle={badge ? "선택한 분류의 뉴스가 없습니다" : "관련 한국어 뉴스가 없습니다"}
        emptyDescription={meta?.stale ? "최신 뉴스 수집에 실패했습니다." : "대회를 확실히 판단할 수 없는 기사는 보여주지 않습니다."}
        partialNotice="최신 뉴스를 불러오지 못해 마지막으로 수집한 기사를 보여줍니다."
        loadingFallback={
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-[170px]" />
            <Skeleton className="h-[170px]" />
          </div>
        }
      >
        {meta?.noNew && !meta.stale && !news.isRefetchError && (
          <p className="mb-4 rounded-control bg-subtle p-3 text-small text-fg-secondary">
            새로 수집된 뉴스가 없어 기존 목록을 표시합니다.
          </p>
        )}
        <ul className="grid gap-4 md:grid-cols-2">
          {articles.map((article) => (
            <li key={article.id}>
              <NewsCard article={article} now={now!} />
            </li>
          ))}
        </ul>
        {news.hasNextPage && (
          <Button
            fullWidth
            className="mt-4"
            disabled={news.isFetchingNextPage}
            onClick={() => news.fetchNextPage()}
          >
            {news.isFetchingNextPage ? "불러오는 중" : `뉴스 더 보기 (${articles.length}/${meta?.total ?? articles.length})`}
          </Button>
        )}
        {news.isFetchNextPageError && (
          <p role="alert" className="mt-2 text-small text-error">
            추가 뉴스를 불러오지 못했습니다. 뉴스 더 보기를 다시 눌러 주세요.
          </p>
        )}
        {news.isRefetchError && (
          <p role="alert" className="mt-2 text-small text-warning">
            최신 뉴스로 갱신하지 못해 이전에 불러온 기사를 보여줍니다.
          </p>
        )}
      </DataState>

      <p className="text-caption text-fg-muted">뉴스 제공: 네이버 검색 · 기사 원문과 출처를 확인하세요.</p>
    </section>
  );
}
