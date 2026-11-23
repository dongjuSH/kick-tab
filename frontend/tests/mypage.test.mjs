/* My page screen rules (chat 09, MY-002~004), on the real TS module. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";

const root = fileURLToPath(new URL("../src", import.meta.url));
function load(request) {
  const file = `${path.join(root, request)}.ts`;
  assert.ok(fs.existsSync(file), request);
  const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  vm.runInNewContext(`(function(module,exports){${code}\n})`, { Date })(loaded, loaded.exports);
  return loaded.exports;
}

const m = load("features/mypage/model");
const { passwordValid } = load("features/auth/rules");

test("favourite count and limit: n / 10, only adding stops at 10", () => {
  assert.equal(m.favoriteCountText(3, 10), "3 / 10 · 내 계정에 저장");
  assert.equal(m.favoriteCountText(0, 10), "0 / 10 · 내 계정에 저장");
  assert.equal(m.favoriteAddBlocked(9, 10), false);
  assert.equal(m.favoriteAddBlocked(10, 10), true);
  assert.equal(m.favoriteLimitText(10), "관심 팀은 최대 10팀까지 등록할 수 있습니다. 다른 팀을 해제한 뒤 추가해 주세요.");
});

test("team link rule follows detailAvailable", () => {
  assert.equal(m.teamDetailNote(true), null);
  assert.equal(m.teamDetailNote(false), "팀 상세 미제공");
  assert.equal(m.teamDetailNote(null), "소속 미확인");
});

test("edited date only for edited reviews, dates in KST", () => {
  assert.equal(m.reviewDatesText("2026-11-20T03:00:00Z", null), "작성 2026.11.20");
  assert.equal(
    m.reviewDatesText("2026-11-20T03:00:00Z", "2026-11-21T01:00:00Z"),
    "작성 2026.11.20 · 수정 2026.11.21",
  );
  // 15:30 UTC is already the next day in KST.
  assert.equal(m.formatDotDate("2026-10-28T15:30:00Z"), "2026.10.29");
  assert.equal(m.formatDotDate("not a date"), "—");
  assert.equal(m.reactionsText(3, 0), "좋아요 3 · 싫어요 0");
});

test("password error codes map one to one onto fields", () => {
  assert.deepEqual({ ...m.passwordFieldError("PASSWORD_CURRENT_MISMATCH") }, {
    field: "currentPassword",
    message: "현재 비밀번호가 일치하지 않습니다.",
  });
  assert.equal(m.passwordFieldError("PASSWORD_RULE").field, "newPassword");
  assert.equal(m.passwordFieldError("PASSWORD_CONFIRM_MISMATCH").field, "newPasswordConfirm");
  // 429, network and server failures are the Failed state, not a field error.
  for (const code of ["RATE_LIMITED", "INTERNAL_ERROR", "FORBIDDEN", null, undefined, "toString"]) {
    assert.equal(m.passwordFieldError(code), null, String(code));
  }
});

test("local checks follow the server order: rule, then confirm", () => {
  assert.equal(m.localPasswordError(passwordValid("short1"), "short1", "other").field, "newPassword");
  assert.equal(m.localPasswordError(passwordValid("abcd1234"), "abcd1234", "abcd12345").field, "newPasswordConfirm");
  assert.equal(m.localPasswordError(passwordValid("abcd1234"), "abcd1234", "abcd1234"), null);
});

test("password change only for email accounts", () => {
  assert.equal(m.canChangePassword("email"), true);
  assert.equal(m.canChangePassword("kakao"), false);
  assert.equal(m.canChangePassword("google"), false);
  assert.equal(m.loginMethodLabel("email"), "이메일");
  assert.equal(m.loginMethodLabel("kakao"), "카카오");
  assert.equal(m.loginMethodLabel("google"), "구글");
});

test("a closed match refuses the edit with its own notice", () => {
  assert.equal(m.reviewEditRefusal(409, "CONFLICT"), m.REVIEW_CLOSED_TEXT);
  // Other refusals keep the server's message (restriction 403, missing review 404, validation 422).
  assert.equal(m.reviewEditRefusal(403, "REVIEW_RESTRICTED"), null);
  assert.equal(m.reviewEditRefusal(404, "NOT_FOUND"), null);
  assert.equal(m.reviewEditRefusal(409, "REVIEW_EXISTS"), null);
});
