import Link from "next/link";
import { LEGAL_DOCUMENTS, type LegalDocumentId } from "./documents";

/**
 * A terms/privacy link that is plain text ('… 준비 중') until the document is published
 * (`documents.ts`). Signup shows '보기'; the footer passes the document name as `label`.
 */
export function LegalLink({
  document,
  label = "보기",
  className,
}: {
  document: LegalDocumentId;
  label?: string;
  className?: string;
}) {
  const { title, href, published } = LEGAL_DOCUMENTS[document];
  if (!published) {
    return label === "보기" ? (
      <span className={className}>보기 준비 중</span>
    ) : (
      <span className={className} title="준비 중">
        {label}
      </span>
    );
  }
  return (
    <Link href={href} className={className} aria-label={label === "보기" ? `${title} 보기` : undefined}>
      {label}
    </Link>
  );
}
