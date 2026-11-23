import { memberRequest } from "@/features/auth/session";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { MyReview } from "@/lib/api/types";

/** GET /me/reviews: the member's reviews, newest first (MY-003). Dropped on member change. */
export const myReviewsQuery = {
  queryKey: queryKeys.me.reviews(),
  queryFn: ({ signal }: { signal: AbortSignal }) =>
    memberRequest(async () => (await apiFetch<MyReview[]>("/me/reviews", { signal })).data),
};
