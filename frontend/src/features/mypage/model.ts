/**
 * My page screen rules (chat 09, MY-001~004). Pure functions, fixed by `tests/mypage.test.mjs`.
 */

/** "3 / 10 · 내 계정에 저장" (MY-002, Figma 52:2674 · 656:27025). */
export function favoriteCountText(count: number, max: number): string {
  return `${count} / ${max} · 내 계정에 저장`;
}

/** At the limit only adding stops; removing stays available (D-07-3). */
export function favoriteAddBlocked(count: number, max: number): boolean {
  return count >= max;
}

/** Limit notice under the count (Figma 656:27025). */
export function favoriteLimitText(max: number): string {
  return `관심 팀은 최대 ${max}팀까지 등록할 수 있습니다. 다른 팀을 해제한 뒤 추가해 주세요.`;
}

/** Team name link rule (TeamRef.detailAvailable): true links, false / null say why not. */
export function teamDetailNote(detailAvailable: boolean | null): string | null {
  if (detailAvailable === true) return null;
  return detailAvailable === false ? "팀 상세 미제공" : "소속 미확인";
}

/** "2026.11.20" in KST. Unknown values give "—". */
export function formatDotDate(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "—";
  const kst = new Date(time + 9 * 3600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${kst.getUTCFullYear()}.${pad(kst.getUTCMonth() + 1)}.${pad(kst.getUTCDate())}`;
}

/**
 * Written / edited line of a review (MY-003, Figma 639:8132): '작성 YYYY.MM.DD', and
 * ' · 수정 YYYY.MM.DD' only when the review was changed after writing (`editedAt` set).
 */
export function reviewDatesText(createdAt: string, editedAt: string | null): string {
  const written = `작성 ${formatDotDate(createdAt)}`;
  return editedAt ? `${written} · 수정 ${formatDotDate(editedAt)}` : written;
}

/** "좋아요 3 · 싫어요 0". */
export function reactionsText(likes: number, dislikes: number): string {
  return `좋아요 ${likes} · 싫어요 ${dislikes}`;
}

/** A closed match refuses the edit with 409 (live or normal finish only, `review_open`). */
export const REVIEW_CLOSED_TEXT = "수정할 수 없는 경기입니다. 진행 중이거나 정상 종료된 경기의 평가만 수정할 수 있어요.";

/** Edit refusal shown in the form: only the closed-match conflict (409 CONFLICT) has its own text. */
export function reviewEditRefusal(status: number, code: string): string | null {
  return status === 409 && code === "CONFLICT" ? REVIEW_CLOSED_TEXT : null;
}

export type LoginMethod = "email" | "kakao" | "google";

export function loginMethodLabel(method: LoginMethod): string {
  return method === "email" ? "이메일" : method === "kakao" ? "카카오" : "구글";
}

/** Password change is offered to email accounts only (social accounts: SocialReference 639:8244). */
export function canChangePassword(method: LoginMethod): boolean {
  return method === "email";
}

export type PasswordField = "currentPassword" | "newPassword" | "newPasswordConfirm";

/** Field and Figma text for each password error code (one code ↔ one field, 639:7452). */
export const PASSWORD_ERRORS: Record<string, { field: PasswordField; message: string }> = {
  PASSWORD_CURRENT_MISMATCH: { field: "currentPassword", message: "현재 비밀번호가 일치하지 않습니다." },
  PASSWORD_RULE: { field: "newPassword", message: "8~64자 · 영문·숫자를 각각 1자 이상 입력해 주세요." },
  PASSWORD_CONFIRM_MISMATCH: { field: "newPasswordConfirm", message: "새 비밀번호와 일치하지 않습니다." },
};

/** Field error for a server error code; anything else (429, network, 5xx) is the Failed state. */
export function passwordFieldError(code: string | null | undefined): { field: PasswordField; message: string } | null {
  return code && Object.hasOwn(PASSWORD_ERRORS, code) ? PASSWORD_ERRORS[code] : null;
}

/**
 * What the screen can already tell before sending, in the server's order (rule → confirm);
 * the current password is only checked by the server. `ruleOk` is `passwordValid(newPassword)`.
 */
export function localPasswordError(
  ruleOk: boolean,
  newPassword: string,
  confirm: string,
): { field: PasswordField; message: string } | null {
  if (!ruleOk) return PASSWORD_ERRORS.PASSWORD_RULE;
  if (newPassword !== confirm) return PASSWORD_ERRORS.PASSWORD_CONFIRM_MISMATCH;
  return null;
}

export const PASSWORD_FAILED_TEXT = "변경하지 못했습니다. 입력 내용은 유지됩니다. 다시 시도해 주세요.";
