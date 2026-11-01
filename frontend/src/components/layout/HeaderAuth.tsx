import { ButtonLink } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";

/**
 * Header auth area (Figma 133:4077 desktop / 133:4134 mobile menu): 로그인 ghost +
 * 회원가입 primary, 12px apart, on every screen size. Chat 01 renders the guest state
 * only; chat 02 replaces the body with useAuth() (member → 마이페이지·로그아웃,
 * Figma 62:1475, 81:3209). Keep the props so callers don't change.
 */
export function HeaderAuth({
  layout,
  onNavigate,
}: {
  layout: "desktop" | "menu";
  /** Mobile menu passes this to close the sheet after a link is chosen. */
  onNavigate?: () => void;
}) {
  const item = layout === "desktop" ? "w-24" : "flex-1";
  return (
    <div className={cx("flex items-center gap-3", layout === "menu" && "w-full")}>
      <ButtonLink href="/login" variant="ghost" className={item} onClick={onNavigate}>
        로그인
      </ButtonLink>
      <ButtonLink href="/signup" variant="primary" className={item} onClick={onNavigate}>
        회원가입
      </ButtonLink>
    </div>
  );
}
