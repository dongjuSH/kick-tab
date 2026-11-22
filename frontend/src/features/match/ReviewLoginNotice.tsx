import { ButtonLink } from "@/components/ui/Button";
import { loginHref } from "@/features/auth/returnTo";

/**
 * Guest notice above the review list (MAT-003 rule 3, REV-001, Figma 52:151 · 52:404,
 * instance 408:16478 '비회원 로그인 안내'). It appears only where reviews are open, because
 * `ReviewSection` itself renders only when the server's `review_open` allows it (live incl.
 * INT, normal finish).
 *
 * '로그인' opens the login with this match as the return path and a review intent
 * (AUTH-005): after login the review area of this match opens — new input, or the
 * member's own review to edit — and nothing is submitted by itself.
 */
export function ReviewLoginNotice({ fixtureId }: { fixtureId: number }) {
  return (
    <div className="flex flex-col gap-3 rounded-control bg-subtle p-4">
      <p className="text-body text-fg">로그인 후 경기 평가를 작성할 수 있습니다.</p>
      <ButtonLink href={loginHref(`/matches/${fixtureId}`, `review:${fixtureId}`)} variant="primary" fullWidth>
        로그인
      </ButtonLink>
    </div>
  );
}
