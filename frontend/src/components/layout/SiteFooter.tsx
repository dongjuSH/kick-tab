import { Logo } from "@/components/common/Logo";
import { FeedbackButton } from "@/features/feedback/FeedbackButton";
import { siteOperator } from "@/lib/site";

// No documents exist yet (P-12): shown as text without links until they are written.
const POLICY_ITEMS = [
  { label: "이용약관" },
  { label: "개인정보처리방침", emphasis: true },
  { label: "문의" },
];

const SOURCES = "데이터 API-Football · 뉴스 NAVER";

function PolicyLinks() {
  return (
    <ul aria-label="서비스 정책과 문의" className="flex items-center gap-5 text-small text-fg-secondary">
      {POLICY_ITEMS.map((item) => (
        <li key={item.label} title="준비 중" className={item.emphasis ? "font-bold" : undefined}>
          {item.label}
        </li>
      ))}
    </ul>
  );
}

/**
 * Operator line. The Figma values are fictional, so real ones come from settings
 * (SITE_OPERATOR_*); desktop shows one line, mobile three (Figma 127:3225 / 127:3250).
 */
function OperatorInfo() {
  const { name, representative, email, address } = siteOperator;
  if (!name && !representative && !email && !address) {
    return <p className="text-caption text-fg-muted">운영자 정보는 서비스 공개 전에 안내합니다.</p>;
  }
  const lines = [
    [name, representative && `대표 ${representative}`].filter(Boolean).join(" · "),
    email && `문의 ${email}`,
    address,
  ].filter(Boolean);
  return (
    <p className="text-caption text-fg-muted">
      {lines.map((line, index) => (
        <span key={index} className="block lg:inline">
          {index > 0 && <span className="hidden lg:inline"> · </span>}
          {line}
        </span>
      ))}
    </p>
  );
}

/**
 * Global footer (COM-003; Figma 49:532 desktop / 49:1012 mobile, redesigned 2026-10-31).
 * Page menus stay in the header. Feedback is in the footer on desktop and in the fixed
 * bottom bar on mobile.
 */
export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="kt-container flex flex-col gap-2 py-5 lg:gap-3">
        <div className="flex items-center gap-2 lg:gap-6">
          <Logo size="footer" />
          <div className="flex-1" />
          <p className="text-caption text-fg-muted lg:hidden">© 2026 KickTab</p>
          <div className="hidden items-center gap-6 lg:flex">
            <PolicyLinks />
            <FeedbackButton className="w-[120px]" />
          </div>
        </div>
        <div className="lg:hidden">
          <PolicyLinks />
        </div>
        <OperatorInfo />
        <div className="flex items-center gap-4 text-caption text-fg-muted">
          <p>{SOURCES}</p>
          <div className="flex-1" />
          <p className="hidden lg:block">© 2026 KickTab. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
