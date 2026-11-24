/* Login return paths (open redirect) and signup rules (chat 02), on the real TS modules. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";

const root = fileURLToPath(new URL("../src", import.meta.url));
function load(request) {
  const file = [`${path.join(root, request)}.ts`].find((c) => fs.existsSync(c));
  assert.ok(file, request);
  const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  vm.runInNewContext(`(function(module,exports){${code}\n})`, { URL, URLSearchParams })(loaded, loaded.exports);
  return loaded.exports;
}

const { safeReturnTo, reviewIntent, loginHref, isMemberOnlyPath } = load("features/auth/returnTo");
const { signupStatus, nicknameValid, nicknameError, NICKNAME_BLOCKED, NICKNAME_RULE, passwordValid } =
  load("features/auth/rules");

test("returnTo keeps internal paths only", () => {
  assert.equal(safeReturnTo("/matches/12?sort=latest#reviews"), "/matches/12?sort=latest#reviews");
  assert.equal(safeReturnTo("/teams"), "/teams");
  for (const bad of [
    null,
    "",
    "https://evil.example/x",
    "//evil.example/x",
    "/\\evil.example",
    "\\\\evil.example",
    "javascript:alert(1)",
    "/\t/evil.example",
    "matches/1",
    "/login?returnTo=/x",
    "/signup",
    "/password-reset",
  ]) {
    assert.equal(safeReturnTo(bad), "/", String(bad));
  }
});

test("only review intents are read and login links stay internal", () => {
  assert.equal(reviewIntent("review:123"), 123);
  for (const bad of ["review:", "review:0", "review:abc", "bookmark:1", "news:3", null]) {
    assert.equal(reviewIntent(bad), null);
  }
  assert.equal(loginHref("/matches/5", "review:5"), "/login?returnTo=%2Fmatches%2F5&intent=review%3A5");
  assert.equal(loginHref("https://evil.example"), "/login?returnTo=%2F");
  assert.equal(isMemberOnlyPath("/mypage"), true);
  assert.equal(isMemberOnlyPath("/matches/1"), false);
});

test("screen rules match the server (P-04)", () => {
  assert.equal(nicknameValid("축구회원"), true);
  // User decision 2026-11-24: impersonation words and direct profanity, contained, any case,
  // digits ignored. The backend test compares the word list with the server's.
  assert.equal(nicknameError("킥탭운영자"), NICKNAME_BLOCKED);
  assert.equal(nicknameError("Admin7"), NICKNAME_BLOCKED);
  assert.equal(nicknameError("씨8발"), NICKNAME_BLOCKED);
  assert.equal(nicknameError("개새끼"), NICKNAME_BLOCKED);
  assert.equal(nicknameError("토트넘팬7"), null);
  assert.equal(nicknameError("가"), NICKNAME_RULE);
  assert.equal(nicknameValid("가"), false);
  assert.equal(nicknameValid("ㄱㄴㄷ"), false);
  assert.equal(nicknameValid("a".repeat(13)), false);
  assert.equal(passwordValid("abcd1234"), true);
  assert.equal(passwordValid("abcdefgh"), false);
  assert.equal(passwordValid("12345678"), false);
  assert.equal(passwordValid("a1".repeat(32) + "x"), false);
});

test("signup is ready only with verification, valid input and all three confirmations", () => {
  const all = { termsOfService: true, privacyCollection: true, age14OrOlder: true };
  const none = { termsOfService: false, privacyCollection: false, age14OrOlder: false };
  const input = { verified: true, nickname: "축구회원", password: "abcd1234", passwordConfirm: "abcd1234" };
  assert.deepEqual({ ...signupStatus({ ...input, verified: false, confirmations: none }) }, {
    ready: false,
    message: "이메일 인증·입력 조건·필수 확인을 모두 완료해야 가입할 수 있습니다.",
  });
  assert.equal(signupStatus({ ...input, verified: false, confirmations: all }).message, "이메일 인증을 완료해 주세요.");
  assert.equal(signupStatus({ ...input, nickname: "가", confirmations: all }).message, "닉네임과 비밀번호 입력을 확인해 주세요.");
  assert.equal(signupStatus({ ...input, passwordConfirm: "x", confirmations: all }).ready, false);
  for (const [key, message] of [
    ["termsOfService", "서비스 이용약관 동의를 확인해 주세요."],
    ["privacyCollection", "개인정보 수집·이용 동의를 확인해 주세요."],
    ["age14OrOlder", "만 14세 이상인지 확인해 주세요."],
  ]) {
    const status = signupStatus({ ...input, confirmations: { ...all, [key]: false } });
    assert.deepEqual({ ...status }, { ready: false, message });
  }
  assert.deepEqual({ ...signupStatus({ ...input, confirmations: all }) }, { ready: true, message: "가입하면 바로 로그인됩니다." });
});
