import { FeedbackButton } from "@/features/feedback/FeedbackButton";
import { siteOperator } from "@/lib/site";

// No documents exist yet (P-12): shown as text without links until they are written.
const POLICY_ITEMS = [
  { label: "이용약관" },
  { label: "개인정보처리방침", emphasis: true },
  { label: "문의" },
];

// Image sources and rights notice are still being checked (user, 2026-11-10): keep the Figma
// line as is until they are confirmed.
const SOURCES = "데이터 API-Football · 뉴스 NAVER";

/**
 * Operator line. Until the service is public the design's notice is shown; real details come
 * from settings (SITE_OPERATOR_*) once they exist.
 */
function operatorText(): string {
  const { name, representative, email, address } = siteOperator;
  const parts = [name, representative && `대표 ${representative}`, email && `문의 ${email}`, address];
  return parts.some(Boolean) ? parts.filter(Boolean).join(" · ") : "운영자 정보는 서비스 공개 전에 안내합니다.";
}

/**
 * Global footer without a logo (COM-003, Figma 304:3823). Desktop: policies·문의 left and
 * 의견 보내기 right, then under a divider the operator notice·sources left and the copyright
 * right. Mobile stacks policies → 의견 보내기 → operator·sources → copyright.
 */
export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="kt-container flex flex-col gap-3 py-5 text-small">
        <div className="flex flex-col items-start gap-3 lg:flex-row lg:items-center">
          <ul aria-label="서비스 정책과 문의" className="flex items-center gap-4 whitespace-nowrap text-fg-secondary lg:flex-1">
            {POLICY_ITEMS.map((item) => (
              <li key={item.label} title="준비 중" className={item.emphasis ? "font-bold" : undefined}>
                {item.label}
              </li>
            ))}
          </ul>
          <FeedbackButton className="w-[120px]" />
        </div>
        <hr className="border-line" />
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:gap-6">
          <div className="flex flex-col gap-1 lg:flex-1">
            <p className="text-fg-secondary">{operatorText()}</p>
            <p className="text-fg-muted">{SOURCES}</p>
          </div>
          <p className="text-fg-muted lg:text-right">© 2026 KickTab. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
