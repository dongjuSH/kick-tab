"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { isApiError } from "@/lib/api/errors";
import type { ReviewSort } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { HeadToHeadSection } from "./HeadToHeadSection";
import { MatchRecords, RECORD_TABS, type RecordTab } from "./MatchRecords";
import { areasOf } from "./model";
import { matchInfoQuery } from "./queries";
import { ReviewSection } from "./ReviewSection";
import { Scoreboard } from "./Scoreboard";
import { StatusNotice } from "./StatusNotice";

interface NavigationApi {
  canGoBack?: boolean;
}

/** "‹ 경기 목록으로": back to the list the visitor came from (its filters and scroll kept)
 * when that page is ours, otherwise the main schedule. */
function BackLink() {
  const router = useRouter();
  return (
    <Link
      href="/"
      onClick={(event) => {
        const navigation = (window as { navigation?: NavigationApi }).navigation;
        if (navigation?.canGoBack) {
          event.preventDefault();
          router.back();
        }
      }}
      className="self-start rounded-control text-label font-medium text-fg-secondary hover:text-fg"
    >
      ‹ 경기 목록으로
    </Link>
  );
}

function isRecordTab(value: string | null): value is RecordTab {
  return RECORD_TABS.some((tab) => tab.value === value);
}

/**
 * Match detail (MAT-001~005, REV-004, UF-08; Figma 52:151 / 52:404 and the state set 57:205).
 * One page per match id; its areas switch with the match status (MAT-001 table). The
 * record tab and the review order live in the URL (`?tab=stats&sort=latest`).
 */
export function MatchDetail({ id }: { id: number }) {
  const query = useQuery(matchInfoQuery(id));
  const params = useSearchParams();
  const pathname = usePathname();
  const heading = useRef<HTMLHeadingElement>(null);
  const focused = useRef(false);

  const tabParam = params.get("tab");
  const tab: RecordTab = isRecordTab(tabParam) ? tabParam : "timeline";
  const sort: ReviewSort = params.get("sort") === "latest" ? "latest" : "popular";
  const setParam = (key: string, value: string, fallback: string) => {
    const next = new URLSearchParams(params);
    if (value === fallback) next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    // Native history update: synced with useSearchParams, no server round trip (Next docs).
    window.history.replaceState(null, "", qs ? `${pathname}?${qs}` : pathname);
  };

  // TOP 5 policy 168:348: after choosing a match, focus moves to the detail heading.
  const loaded = Boolean(query.data);
  useEffect(() => {
    if (loaded && !focused.current) {
      focused.current = true;
      heading.current?.focus({ preventScroll: true });
    }
  }, [loaded]);

  if (!query.data) {
    if (isApiError(query.error) && query.error.status === 404) {
      return (
        <StateMessage
          tone="error"
          title="경기를 찾을 수 없습니다"
          description="주소가 바뀌었거나 제공되지 않는 경기입니다. 다른 경기로 대신 안내하지 않습니다."
          action={<ButtonLink href="/">경기 일정으로 이동</ButtonLink>}
        />
      );
    }
    return (
      <div className="rounded-card border border-line bg-surface p-4 lg:p-6">
        <DataState
          status={query.isPending ? "loading" : "error"}
          error={query.error}
          onRetry={() => void query.refetch()}
          errorTitle="경기 정보를 불러오지 못했습니다"
          loadingFallback={
            <div className="flex flex-col items-center gap-4 py-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-12 w-72" />
              <Skeleton className="h-4 w-48" />
            </div>
          }
        />
      </div>
    );
  }

  const info = query.data.data;
  const areas = areasOf(info);
  const title = `${teamName(info.match.home)} 대 ${teamName(info.match.away)} 경기 상세`;

  return (
    <>
      <BackLink />
      <Scoreboard
        info={info}
        updatedAt={query.data.meta.updatedAt}
        checkedAt={query.dataUpdatedAt}
        heading={
          <h1 ref={heading} tabIndex={-1} className="sr-only">
            {title}
          </h1>
        }
      />
      {query.isError && (
        <div role="alert" className="rounded-control bg-warning-bg p-3 text-small text-warning">
          최신 경기 정보로 갱신하지 못했습니다. 마지막으로 확인한 정보를 보여줍니다.
          <Button variant="ghost" onClick={() => void query.refetch()}>다시 확인</Button>
        </div>
      )}
      <StatusNotice info={info} />
      {areas.headToHead && <HeadToHeadSection info={info} />}
      {(areas.records || areas.lineupOnly) && (
        <MatchRecords info={info} tab={tab} onTab={(value) => setParam("tab", value, "timeline")} />
      )}
      {areas.reviews && (
        <ReviewSection fixtureId={id} sort={sort} onSort={(value) => setParam("sort", value, "popular")} />
      )}
      {areas.reviewLater && (
        <p className="rounded-control bg-subtle p-3 text-small text-fg-secondary">
          경기가 종료되면 평점과 후기를 남길 수 있습니다.
        </p>
      )}
    </>
  );
}
