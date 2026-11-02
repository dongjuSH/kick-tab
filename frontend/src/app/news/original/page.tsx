import type { Metadata } from "next";
import { Suspense } from "react";
import { OriginalRedirect } from "@/features/news/OriginalRedirect";

export const metadata: Metadata = { title: "원문 기사로 이동", robots: { index: false } };

/**
 * Hand-off to the original article (NEWS-004): `/news/original?id=<article id>`. Not a news
 * page: it checks the link once and replaces itself with the press site, or explains when
 * the article no longer answers.
 */
export default function NewsOriginalPage() {
  return (
    <div className="kt-container flex flex-1 items-center justify-center py-16">
      <Suspense>
        <OriginalRedirect />
      </Suspense>
    </div>
  );
}
