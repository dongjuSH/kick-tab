/* Standings URL state and display rules (chat 06), on the real TS modules with Node's runner. */
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

/** useStandingsParams with a fixed URL; returns the hook, pushed URLs and replaced URLs. */
function paramsFor(search) {
  const pushed = [];
  const replaced = [];
  const load = loader(
    {
      "next/navigation": {
        useSearchParams: () => new URLSearchParams(search),
        useRouter: () => ({ push: (url) => pushed.push(url) }),
        usePathname: () => "/standings",
      },
      react: { ...React, useCallback: (fn) => fn },
    },
    { window: { history: { replaceState: (_s, _t, url) => replaced.push(url) } } },
  );
  return { params: load("@/features/standings/useStandingsParams").useStandingsParams(), pushed, replaced };
}

test("defaults: Premier League, current season, goals", () => {
  const { params } = paramsFor("");
  assert.equal(JSON.stringify([params.league, params.season, params.type, params.typeInvalid]), '[39,null,"goals",false]');
});

test("a season change keeps league and ranking type; the type only replaces the entry", () => {
  const { params, pushed, replaced } = paramsFor("league=78&season=2026&type=saves");
  params.select({ season: 2025 });
  assert.equal(pushed.at(-1), "/standings?league=78&season=2025&type=saves");
  params.select({ league: 61 });
  assert.equal(pushed.at(-1), "/standings?league=61&season=2026&type=saves");
  params.selectType("red");
  assert.equal(replaced.at(-1), "/standings?league=78&season=2026&type=red");
  assert.equal(pushed.length, 2);
});

test("cups, unreadable leagues, seasons and types are reported, never replaced", () => {
  assert.equal(paramsFor("league=45").params.league, null); // FA Cup has no table
  assert.equal(paramsFor("league=abc").params.league, null);
  const season = paramsFor("league=39&season=abc").params;
  assert.equal(JSON.stringify([season.season, season.seasonInvalid]), "[null,true]");
  const type = paramsFor("league=39&type=fouls").params;
  assert.equal(type.typeInvalid, true);
});

test("display rules: signed goal difference, W/D/L in provider order, past zones, shared ranks", () => {
  const model = loader()("@/features/standings/model");
  assert.equal(model.signed(15), "+15");
  assert.equal(model.signed(-2), "-2");
  assert.equal(model.signed(0), "0");
  assert.equal(model.signed(null), "—"); // missing is never 0
  assert.equal(model.numberText(null), "—");
  assert.equal(model.formResults("LWWDW").join(""), "패승승무승");
  assert.equal(model.formResults(null).length, 0);
  assert.equal(model.zoneLabel({ zone: "relegation" }), "당시 강등");
  assert.equal(model.zoneLabel({ zone: "relegation_playoff" }), "당시 승강 PO");
  assert.equal(model.zoneLabel({ zone: null }), null);
  assert.equal(model.rankText(2, true), "공동 2");
  assert.equal(model.rankText(3, false), "3");
});

test("data status: loading, failure without data, empty, and a failed refresh that keeps data", () => {
  const { dataStatus } = loader()("@/features/standings/model");
  assert.equal(dataStatus({ isPending: true, isError: false, data: undefined }, true, false), "loading");
  assert.equal(dataStatus({ isPending: false, isError: true, data: undefined }, true, false), "error");
  assert.equal(dataStatus({ isPending: false, isError: false, data: {} }, true, false), "empty");
  // A refetch that failed while a table is on screen keeps the table (partial, not error).
  assert.equal(dataStatus({ isPending: false, isError: true, data: {} }, false, true), "partial");
  assert.equal(dataStatus({ isPending: false, isError: false, data: {} }, false, false), "ready");
});

test("0 rows then a failed refresh is partial, never a normal empty result (Codex 1차 지적 2)", () => {
  const { dataStatus } = loader()("@/features/standings/model");
  // Server: the last stored result had no rows and a later refresh failed (meta.refreshFailed).
  assert.equal(dataStatus({ isPending: false, isError: false, data: {} }, true, true), "partial");
  // Browser: a refetch failed while an empty result was on screen.
  assert.equal(dataStatus({ isPending: false, isError: true, data: {} }, true, true), "partial");
  // A confirmed empty result without any failure stays empty.
  assert.equal(dataStatus({ isPending: false, isError: false, data: {} }, true, false), "empty");
});

test("main chips follow Figma 49:368 (EPL·LaLiga·Serie A·BUN·Ligue 1); standings tabs keep full names", () => {
  const { LEAGUES } = loader()("@/features/standings/model");
  assert.equal(LEAGUES.map((l) => l.chip).join("|"), "EPL|LaLiga|Serie A|BUN|Ligue 1");
  assert.equal(LEAGUES.map((l) => l.label).join("|"), "Premier League|LaLiga|Serie A|Bundesliga|Ligue 1");
});

test("DataState partial: an action sits next to the notice; without one the markup is unchanged", () => {
  const { DataState } = loader()("@/components/ui/DataState");
  const h = React.createElement;
  const plain = renderToStaticMarkup(h(DataState, { status: "partial", partialNotice: "N" }, "body"));
  assert.ok(plain.startsWith('<div><p class="mb-3 rounded-control bg-subtle px-3 py-2 text-small text-fg-secondary">N</p>body'));
  const withAction = renderToStaticMarkup(
    h(DataState, { status: "partial", partialNotice: "N", partialAction: h("button", null, "다시 확인") }, "body"),
  );
  assert.match(withAction, /<p class="min-w-0 flex-1[^"]*">N<\/p><button>다시 확인<\/button><\/div>body/);
});
