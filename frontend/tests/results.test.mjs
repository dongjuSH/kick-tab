/* Chat 05 past results: URL rules, page navigation and the season dropdown, run on the real
 * TS/TSX modules with Node's test runner (same loader approach as match-regressions). */
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
function loader(mocks = {}) {
  const cache = new Map();
  function load(request, from = root) {
    if (Object.hasOwn(mocks, request)) return mocks[request];
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
    vm.runInNewContext(`(function(require,module,exports){${code}\n})`, { console, URLSearchParams }, { filename: file })(
      (name) => load(name, path.dirname(file)), loaded, loaded.exports,
    );
    return loaded.exports;
  }
  return load;
}

/** useResultsParams with a fixed URL; returns the hook result and the pushed URLs. */
function paramsFor(search) {
  const pushed = [];
  const load = loader({
    "next/navigation": {
      useSearchParams: () => new URLSearchParams(search),
      useRouter: () => ({ push: (url) => pushed.push(url) }),
      usePathname: () => "/results",
    },
    react: { ...React, useCallback: (fn) => fn },
  });
  return { params: load("@/features/results/useResultsParams").useResultsParams(), pushed };
}

test("season change keeps team and competitions and returns to page 1", () => {
  const { params, pushed } = paramsFor("season=2026&competitions=39,45&team=48&page=3");
  // Arrays come from the module's own realm: compare their contents.
  assert.equal(JSON.stringify([params.season, params.competitions, params.team, params.page]), "[2026,[39,45],48,3]");
  params.update({ season: 2025 });
  assert.equal(pushed.at(-1), "/results?season=2025&competitions=39%2C45&team=48");
});

test("clearing the team keeps season and competitions; reset keeps only the season", () => {
  const { params, pushed } = paramsFor("season=2025&competitions=61&team=83&page=2");
  params.update({ team: null });
  assert.equal(pushed.at(-1), "/results?season=2025&competitions=61");
  params.reset();
  assert.equal(pushed.at(-1), "/results?season=2025");
  params.update({ page: 4 });
  assert.equal(pushed.at(-1), "/results?season=2025&competitions=61&team=83&page=4");
});

test("an unparsable season is reported, never replaced", () => {
  const { params } = paramsFor("season=abc");
  assert.equal(params.season, null);
  assert.equal(params.seasonInvalid, true);
  assert.equal(paramsFor("").params.seasonInvalid, false);
  assert.equal(paramsFor("season=").params.seasonInvalid, false); // empty = not given
});

test("unreadable team, competitions and page are reported, not dropped or reset", () => {
  const invalid = (search) => JSON.stringify(paramsFor(search).params.invalid);
  assert.equal(invalid("season=2025&team=abc"), '["team"]');
  assert.equal(invalid("competitions=39,abc"), '["competitions"]');
  assert.equal(invalid("competitions=39,"), '["competitions"]');
  assert.equal(invalid("page=0"), '["page"]');
  assert.equal(invalid("page=x&team=-1"), '["team","page"]');
  assert.equal(invalid("team=4.5"), '["team"]');
  // Omitted or empty conditions are simply "every team / competition, first page".
  assert.equal(invalid(""), "[]");
  assert.equal(invalid("team=&competitions=&page="), "[]");
  // Valid conditions are read as before.
  const { params } = paramsFor("season=2025&competitions=39,45&team=48&page=3");
  assert.equal(invalid("season=2025&competitions=39,45&team=48&page=3"), "[]");
  assert.equal(JSON.stringify([params.competitions, params.team, params.page]), "[[39,45],48,3]");
});

test("pagination: three numbers, first/last reachable, ends disabled", () => {
  const { Pagination } = loader()("@/components/ui/Pagination");
  const render = (page, pages) => renderToStaticMarkup(React.createElement(Pagination, { page, pages, onChange: () => {} }));
  assert.equal(render(1, 1), "");
  const first = render(1, 400);
  const labels = (html) => [...html.matchAll(/aria-label="(\d+)페이지"/g)].map((m) => Number(m[1]));
  assert.deepEqual(labels(first), [1, 2, 3, 400]);
  assert.match(first, /<button[^>]*disabled=""[^>]*>이전/);
  const last = render(400, 400);
  assert.deepEqual(labels(last), [1, 398, 399, 400]);
  assert.match(last, /<button[^>]*disabled=""[^>]*>다음/);
  assert.match(last, /aria-current="page"[^>]*>400</);
  assert.deepEqual(labels(render(5, 9)), [1, 4, 5, 6, 9]);
});

test("season select names current and previous seasons and never shows a replacement", () => {
  const { SeasonSelect } = loader()("@/components/common/SeasonSelect");
  const seasons = [
    { season: 2026, label: "2026-27", current: true },
    { season: 2025, label: "2025-26", current: false },
  ];
  const html = (value) => renderToStaticMarkup(React.createElement(SeasonSelect, { seasons, value, onChange: () => {} }));
  assert.match(html(2025), /2025-26 시즌/);
  assert.match(html(null), /시즌 선택/);
  assert.doesNotMatch(html(null), /2026-27 시즌/);
});
