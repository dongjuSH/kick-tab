/* Team browse URL state and favourite refusal (chat 07), on the real TS modules with Node's runner. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const loadDependency = createRequire(import.meta.url);
const root = fileURLToPath(new URL("../src", import.meta.url));
function loader(mocks = {}, globals = {}) {
  const cache = new Map();
  function load(request, from = root) {
    if (mocks[request]) return mocks[request];
    if (!request.startsWith(".") && !request.startsWith("@/")) return loadDependency(request);
    let file = request.startsWith("@/") ? path.join(root, request.slice(2)) : path.resolve(from, request);
    file = [file, `${file}.ts`, `${file}.tsx`].find((c) => fs.existsSync(c) && fs.statSync(c).isFile());
    assert.ok(file, `module ${request}`);
    if (cache.has(file)) return cache.get(file).exports;
    const loaded = { exports: {} };
    cache.set(file, loaded);
    const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    vm.runInNewContext(`(function(require,module,exports){${code}\n})`, { console, URLSearchParams, ...globals }, { filename: file })(
      (name) => load(name, path.dirname(file)), loaded, loaded.exports,
    );
    return loaded.exports;
  }
  return load;
}

/** useTeamsParams with a fixed URL; returns the hook state and the pushed / replaced URLs. */
function paramsFor(search) {
  const pushed = [];
  const replaced = [];
  const load = loader({
    "next/navigation": {
      useSearchParams: () => new URLSearchParams(search),
      useRouter: () => ({ push: (url) => pushed.push(url), replace: (url) => replaced.push(url) }),
      usePathname: () => "/teams",
    },
    react: { ...React, useCallback: (fn) => fn },
  });
  return { params: load("@/features/teams/useTeamsParams").useTeamsParams(), pushed, replaced };
}

test("defaults: every league, no search, first page", () => {
  const { params } = paramsFor("");
  assert.deepEqual([params.league, params.q, params.page, params.invalid.length], [null, null, 1, 0]);
  const shared = paramsFor("league=140&q=%20레알%20&page=2").params;
  assert.deepEqual([shared.league, shared.q, shared.page], [140, "레알", 2]);
});

test("a league or search change starts on page 1 and keeps the other condition", () => {
  const { params, pushed, replaced } = paramsFor("league=39&q=맨&page=3");
  params.update({ league: 61 });
  assert.equal(decodeURIComponent(pushed.at(-1)), "/teams?league=61&q=맨");
  params.update({ q: "파리" }, { replace: true });
  assert.equal(decodeURIComponent(replaced.at(-1)), "/teams?league=39&q=파리");
  params.update({ league: null });
  assert.equal(decodeURIComponent(pushed.at(-1)), "/teams?q=맨");
  params.update({ q: null });
  assert.equal(pushed.at(-1), "/teams?league=39");
  params.update({ page: 4 });
  assert.equal(decodeURIComponent(pushed.at(-1)), "/teams?league=39&q=맨&page=4");
  params.reset();
  assert.equal(pushed.at(-1), "/teams");
});

test("leagues outside the five, unreadable pages and over-long searches are reported, never swapped", () => {
  assert.equal(JSON.stringify(paramsFor("league=2").params.invalid), JSON.stringify(["league"])); // UEFA: no browse list
  assert.equal(JSON.stringify(paramsFor("league=abc").params.invalid), JSON.stringify(["league"]));
  assert.equal(JSON.stringify(paramsFor("page=0").params.invalid), JSON.stringify(["page"]));
  assert.equal(JSON.stringify(paramsFor("page=abc").params.invalid), JSON.stringify(["page"]));
  assert.equal(JSON.stringify(paramsFor(`q=${"a".repeat(41)}`).params.invalid), JSON.stringify(["q"]));
  assert.equal(paramsFor("league=").params.invalid.length, 0); // empty = not given
});

function toggleMarkup(favorites, teamId) {
  const load = loader({ "./useFavorites": { useFavorites: () => favorites } });
  const { FavoriteToggle } = load("@/features/favorites/FavoriteToggle");
  return renderToStaticMarkup(React.createElement(FavoriteToggle, { teamId, teamName: "리버풀" }));
}

function favorites(status, ids) {
  return { status, ids, max: 5, has: (id) => ids.includes(id), add: () => "added", remove: () => "removed" };
}

test("FavoriteToggle: with five teams the others are refused (Figma 57:766), registered ones stay removable", () => {
  const full = favorites("ready", [1, 2, 3, 4, 5]);
  const other = toggleMarkup(full, 40);
  assert.match(other, /disabled=""/);
  assert.match(other, />최대 5개까지 등록할 수 있어요</);
  assert.match(other, /aria-label="리버풀 관심 팀 등록 불가, 최대 5개까지 등록할 수 있어요"/);
  const registered = toggleMarkup(full, 3);
  assert.doesNotMatch(registered, /disabled=""/);
  assert.match(registered, /★ 관심 팀 등록됨/);
  const four = toggleMarkup(favorites("ready", [1, 2, 3, 4]), 40);
  assert.doesNotMatch(four, /disabled=""/);
  assert.match(four, /☆ 관심 팀 등록/);
  // Blocked storage is not "full": the button stays and says why on press.
  assert.doesNotMatch(toggleMarkup(favorites("unavailable", []), 40), /disabled=""/);
});

test("a refusal caused by another tab's newer list refreshes every screen showing the old list", () => {
  const stored = new Map([["kt-fav-guest", "[1,2,3,4]"]]);
  const localStorage = { getItem: (k) => stored.get(k) ?? null, setItem: (k, v) => stored.set(k, String(v)) };
  const window = { localStorage, addEventListener() {}, removeEventListener() {} };
  const store = loader({}, { window })("@/features/favorites/store");
  let calls = 0;
  store.subscribeFavorites(() => calls++);
  assert.equal(store.readFavorites().ids.length, 4); // what the screens show
  stored.set("kt-fav-guest", "[1,2,3,4,5]"); // another tab, before its storage event arrives
  assert.equal(store.addFavorite(6), "limit");
  assert.equal(calls, 1); // the 5 / 5 notice and buttons re-read the list
  assert.equal(store.addFavorite(7), "limit");
  assert.equal(calls, 1); // nothing new: no extra notification
  assert.equal(stored.get("kt-fav-guest"), "[1,2,3,4,5]");
});

test("DataState empty: an optional action under the message; without one the markup is unchanged", () => {
  const { DataState } = loader()("@/components/ui/DataState");
  const h = React.createElement;
  const plain = renderToStaticMarkup(h(DataState, { status: "empty", emptyTitle: "T", emptyDescription: "D" }));
  assert.match(plain, /<p class="text-body text-fg-secondary">D<\/p><\/div>$/);
  const withAction = renderToStaticMarkup(
    h(DataState, { status: "empty", emptyTitle: "T", emptyDescription: "D", emptyAction: h("button", null, "검색어 지우기") }),
  );
  assert.match(withAction, /D<\/p><button>검색어 지우기<\/button><\/div>$/);
});
