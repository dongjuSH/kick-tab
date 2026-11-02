"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type { NewsLink } from "@/lib/api/types";

/**
 * Checks the original link from the reader's browser (so request limits apply per reader)
 * and moves on to it. Only a 404/410 answer shows the "cannot be confirmed" notice, and even
 * then the original address stays available: one failure never means "deleted" (NEWS-004).
 */
export function OriginalRedirect() {
  const id = Number(useSearchParams().get("id"));
  const link = useQuery({
    queryKey: queryKeys.news.link(id),
    queryFn: async ({ signal }) => (await apiFetch<NewsLink>(`/news/${id}/link`, { signal })).data,
    enabled: Number.isInteger(id) && id > 0,
    retry: false,
    staleTime: Infinity,
  });
  const target = link.data && link.data.status !== "gone" ? link.data.url : null;

  useEffect(() => {
    if (target) window.location.replace(target);
  }, [target]);

  if (link.isError || !(Number.isInteger(id) && id > 0)) {
    return (
      <StateMessage
        tone="error"
        title="원문 정보를 불러오지 못했습니다"
        description={isApiError(link.error) ? link.error.message : "잠시 후 다시 시도해 주세요."}
        action={<ButtonLink href="/">경기 일정으로 이동</ButtonLink>}
      />
    );
  }
  if (link.data?.status === "gone") {
    return (
      <StateMessage
        tone="plain"
        title="원문 기사를 확인할 수 없습니다"
        description="언론사에서 기사를 삭제했거나 주소가 바뀌었을 수 있습니다. 일시적인 문제일 수 있으니 원문 주소를 직접 열어 볼 수 있습니다."
        action={
          <ButtonLink href={link.data.url} rel="noopener noreferrer">
            원문 주소 열기
          </ButtonLink>
        }
      />
    );
  }
  return <p className="text-body text-fg-secondary">원문 기사로 이동하고 있습니다…</p>;
}
