import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";

const root = fileURLToPath(new URL("../src", import.meta.url));
const member = { id: "member-a", email: "a@example.invalid", nickname: "회원" };
const json = (data) => Response.json({ data });
const expired = () => Response.json({ error: { code: "AUTH_EXPIRED", message: "만료" } }, { status: 401 });

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

// Exercise the real session, API client and error conversion with an isolated browser store.
function browserSession(fetch) {
  const storage = {};
  Object.defineProperties(storage, {
    getItem: { value: (key) => storage[key] ?? null },
    setItem: { value: (key, value) => { storage[key] = value; } },
    removeItem: { value: (key) => { delete storage[key]; } },
  });
  const context = vm.createContext({
    window: {}, sessionStorage: storage, fetch, Headers, Response, DOMException, URLSearchParams,
  });
  const cache = new Map();
  function load(request, parent = root) {
    if (request === "react") return {};
    const file = `${request.startsWith("@/") ? path.join(root, request.slice(2)) : path.resolve(parent, request)}.ts`;
    if (cache.has(file)) return cache.get(file).exports;
    const loaded = { exports: {} };
    cache.set(file, loaded);
    const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    vm.runInContext(`(function(module,exports,require){${code}\n})`, context)(
      loaded, loaded.exports, (name) => load(name, path.dirname(file)),
    );
    return loaded.exports;
  }
  return { session: load("@/features/auth/session"), storage };
}

test("logout waits for an earlier refresh, blocks new refreshes, and coalesces callers", async () => {
  const refreshReply = deferred(), logoutReply = deferred(), logoutStarted = deferred();
  const calls = [];
  const { session, storage } = browserSession(async (url) => {
    calls.push(url);
    if (url.endsWith("/refresh")) { await refreshReply.promise; return json(member); }
    if (url.endsWith("/logout")) { logoutStarted.resolve(); await logoutReply.promise; return new Response(null, { status: 204 }); }
    if (url.endsWith("/me")) return json(null);
    throw new Error(`Unexpected request ${url}`);
  });
  storage.setItem("kt-review-draft:member-a:1", "private draft");
  storage.setItem("kt-feedback-draft", "feedback");
  try {
    const refresh = session.refreshSession();
    const first = session.logout(), second = session.logout();
    assert.deepEqual(calls, ["/api/v1/auth/refresh"]);
    assert.equal(first, second);
    refreshReply.resolve();
    await refresh;
    await logoutStarted.promise;
    assert.equal(await session.refreshSession(), false);
    assert.equal(calls.filter((url) => url.endsWith("/refresh")).length, 1);
    logoutReply.resolve();
    assert.equal(await first, true);
    assert.equal(await second, true);
    assert.equal(session.readAuth().status, "guest");
    assert.equal(calls.filter((url) => url.endsWith("/logout")).length, 1);
    assert.equal(storage.getItem("kt-review-draft:member-a:1"), null);
    assert.equal(storage.getItem("kt-feedback-draft"), "feedback");
  } finally {
    refreshReply.resolve();
    logoutReply.resolve();
  }
});

test("failed logout can refresh while checking the real session and preserves the draft", async () => {
  let expiredOnce = true, refreshes = 0;
  const { session, storage } = browserSession(async (url) => {
    if (url.endsWith("/logout")) return new Response(null, { status: 503 });
    if (url.endsWith("/refresh")) { refreshes++; return json(member); }
    if (url.endsWith("/me")) {
      if (expiredOnce) { expiredOnce = false; return expired(); }
      return json(member);
    }
    throw new Error(`Unexpected request ${url}`);
  });
  storage.setItem("kt-review-draft:member-a:1", "private draft");
  assert.equal(await session.logout(), false);
  assert.equal(refreshes, 1);
  assert.equal(session.readAuth().status, "member");
  assert.equal(storage.getItem("kt-review-draft:member-a:1"), "private draft");
});

test("a failed in-flight refresh does not prevent deliberate logout", async () => {
  const reply = deferred();
  let logouts = 0;
  const { session } = browserSession(async (url) => {
    if (url.endsWith("/refresh")) {
      await reply.promise;
      return Response.json({ error: { code: "AUTH_REQUIRED", message: "로그인 필요" } }, { status: 401 });
    }
    if (url.endsWith("/logout")) { logouts++; return new Response(null, { status: 204 }); }
    if (url.endsWith("/me")) return json(null);
    throw new Error(`Unexpected request ${url}`);
  });
  const refreshing = session.refreshSession();
  const ending = session.logout();
  reply.resolve();
  assert.equal(await refreshing, false);
  assert.equal(await ending, true);
  assert.equal(logouts, 1);
  assert.equal(session.readAuth().status, "guest");
});
