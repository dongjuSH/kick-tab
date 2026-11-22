/**
 * Terms and privacy documents (P-12). Drafts live in `docs/legal/` and are not public yet,
 * so every link shows '준비 중'. When a document is confirmed: add its page at `href`
 * (e.g. `app/terms/page.tsx`), set `published: true` here, and change the backend
 * `TERMS_VERSION` from "draft" to the document's version — the signup '보기' and the footer
 * then open it from the same place without other changes.
 */
export type LegalDocumentId = "terms" | "privacy" | "privacy-consent";

export const LEGAL_DOCUMENTS: Record<LegalDocumentId, { title: string; href: string; published: boolean }> = {
  terms: { title: "서비스 이용약관", href: "/terms", published: false },
  privacy: { title: "개인정보처리방침", href: "/privacy", published: false },
  "privacy-consent": { title: "개인정보 수집·이용 동의", href: "/privacy/consent", published: false },
};
