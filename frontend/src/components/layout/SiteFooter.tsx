import { Logo } from "@/components/common/Logo";
import { FeedbackButton } from "@/features/feedback/FeedbackButton";
import { SITE_TAGLINE, siteOperator } from "@/lib/site";
import { ScrollTopButton } from "./ScrollTopButton";

// No documents exist yet (P-12), so these are shown without links and marked 준비 중.
const POLICY_ITEMS = [
  { label: "서비스 소개" },
  { label: "이용약관" },
  { label: "개인정보처리방침", emphasis: true },
  { label: "문의" },
];

function OperatorInfo() {
  const { name, representative, email, address } = siteOperator;
  if (!name && !representative && !email && !address) {
    return <p className="text-small text-fg-muted">운영자 정보는 서비스 공개 전에 안내합니다.</p>;
  }
  const lead = [name, representative && `대표 ${representative}`].filter(Boolean).join(" · ");
  return (
    <div className="flex flex-col gap-1.5 text-small">
      <p className="text-fg-secondary">
        {lead}
        {lead && email && <span className="hidden lg:inline">{"  |  "}</span>}
        {email && (
          <span className="block lg:inline">
            서비스 문의 <a className="underline-offset-2 hover:underline" href={`mailto:${email}`}>{email}</a>
          </span>
        )}
      </p>
      {address && <p className="text-fg-muted">{address}</p>}
    </div>
  );
}

/**
 * Global footer (COM-003; Figma 49:532 desktop / 49:1012 mobile). Page menus stay in the
 * header. Feedback and 맨 위로 are in the footer on desktop; on mobile, feedback moves to
 * the fixed bottom bar.
 */
export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="kt-container flex flex-col gap-5 py-8">
        <div className="flex items-center gap-3">
          <Logo size="footer" />
          <div className="flex-1" />
          <div className="hidden items-center gap-3 lg:flex">
            <ScrollTopButton />
            <FeedbackButton className="w-[120px]" />
          </div>
        </div>
        <p className="text-body font-medium">{SITE_TAGLINE}</p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-small text-fg-secondary lg:gap-x-6">
          <ul className="contents" aria-label="서비스 정책과 문의">
            {POLICY_ITEMS.map((item) => (
              <li key={item.label} className={item.emphasis ? "font-bold" : undefined}>
                {item.label}
              </li>
            ))}
          </ul>
          <span className="text-fg-muted">준비 중</span>
        </div>
        <OperatorInfo />
        <hr className="border-line" />
        {/* Source notices (Figma). The rights line is provisional until V-09/V-10 are confirmed. */}
        <div className="flex flex-col gap-5 text-caption text-fg-muted">
          <p className="whitespace-pre-wrap">{"경기·팀 데이터 API-Football  ·  뉴스 NAVER"}</p>
          <p>데이터 갱신이 지연될 수 있습니다. 기사와 구단 콘텐츠의 권리는 각 권리자에게 있습니다.</p>
          <p>© 2026 KickTab. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
