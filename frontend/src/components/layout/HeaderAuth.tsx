import { ButtonLink } from "@/components/ui/Button";

/**
 * Header auth area. Chat 01 renders the guest state only (로그인·회원가입).
 * Chat 02 replaces the body with useAuth(): member → 마이페이지·로그아웃
 * (Figma mobile-menu-member 62:1475, 81:3209). Keep the props so callers don't change.
 */
export function HeaderAuth({
  layout,
  onNavigate,
}: {
  layout: "desktop" | "menu";
  /** Mobile menu passes this to close the sheet after a link is chosen. */
  onNavigate?: () => void;
}) {
  if (layout === "desktop") {
    return (
      <div className="flex items-center">
        <ButtonLink href="/login" variant="ghost" className="w-24">
          로그인
        </ButtonLink>
        <ButtonLink href="/signup" variant="primary" className="w-24">
          회원가입
        </ButtonLink>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <ButtonLink href="/login" variant="primary" fullWidth onClick={onNavigate}>
        로그인
      </ButtonLink>
      <ButtonLink href="/signup" variant="ghost" fullWidth onClick={onNavigate}>
        회원가입
      </ButtonLink>
    </div>
  );
}
