import { Button } from "@/components/ui/Button";

/**
 * Guest notice above the review list (MAT-003 rule 3, REV-001, Figma 52:151 · 52:404,
 * instance 408:16478 '비회원 로그인 안내'). It appears only where reviews are open, because
 * `ReviewSection` itself renders only when the server's `review_open` allows it (live incl.
 * INT, normal finish). The wording follows the functional spec.
 *
 * The box matches the latest Figma (primary full-width '로그인'). Its action is chat 02's
 * (user decision 2026-11-19: this pre-launch screen is not shipped as is): 02 turns this
 * button into the login entry that returns to this match's review area (returnTo/intent,
 * no automatic submit) and shows members the writing form instead of this box.
 */
export function ReviewLoginNotice() {
  return (
    <div className="flex flex-col gap-3 rounded-control bg-subtle p-4">
      <p className="text-body text-fg">로그인 후 경기 평가를 작성할 수 있습니다.</p>
      <Button variant="primary" fullWidth>
        로그인
      </Button>
    </div>
  );
}
