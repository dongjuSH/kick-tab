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

test("pagination window: consecutive numbers around the page, pushed inward at the ends", () => {
  const { pageWindow } = loader()("@/components/ui/Pagination");
  const w = (page, pages, numbers) => pageWindow(page, pages, numbers).join(" ");
  // Every page when they fit (team browse 2 pages, Figma 6 pages).
  assert.equal(w(1, 2, 7), "1 2");
  assert.equal(w(1, 6, 7), "1 2 3 4 5 6");
  // PC, 2025-26 all (420 pages, 7 numbers): the count stays 7 at either end.
  assert.equal(w(1, 420, 7), "1 2 3 4 5 6 7");
  assert.equal(w(4, 420, 7), "1 2 3 4 5 6 7");
  assert.equal(w(5, 420, 7), "2 3 4 5 6 7 8");
  assert.equal(w(16, 420, 7), "13 14 15 16 17 18 19");
  assert.equal(w(210, 420, 7), "207 208 209 210 211 212 213");
  assert.equal(w(420, 420, 7), "414 415 416 417 418 419 420");
  // 375px (3) and 320px (1).
  assert.equal(w(3, 6, 3), "2 3 4");
  assert.equal(w(1, 420, 3), "1 2 3");
  assert.equal(w(420, 420, 3), "418 419 420");
  assert.equal(w(6, 6, 1), "6");
  assert.equal(w(210, 420, 1), "210");
});

test("pagination width: (row − four arrows and gaps) ÷ 48px, 1 to 7 numbers", () => {
  const { numbersFor } = loader()("@/components/ui/Pagination");
  // 320px card row (254 + 24 into the padding) 1, 375px (333) 3, PC 7.
  assert.deepEqual([0, 278, 333, 400, 1254].map((w) => numbersFor(w)), [1, 1, 3, 4, 7]);
  // Without « » two more fit: 320px shows team browse's two pages as ‹ 1 2 ›.
  assert.deepEqual([0, 278, 333, 1254].map((w) => numbersFor(w, 2)), [1, 3, 5, 7]);
  for (const width of [278, 333, 400, 500]) {
    for (const arrows of [2, 4]) {
      const n = numbersFor(width, arrows);
      assert.ok((arrows + n) * 44 + (arrows + n - 1) * 4 <= width, `${width}px ${arrows} → ${n}`);
    }
  }
});

test("pagination render: « ‹ numbers › », ends disabled, « » only when pages are hidden", () => {
  const props = (page, pages) => ({ page, pages, onChange: () => {} });
  const labels = (html) => [...html.matchAll(/<button[^>]*aria-label="([^"]+)"/g)].map((m) => m[1]);
  const disabled = (html) => [...html.matchAll(/aria-label="([^"]+)" disabled=""/g)].map((m) => m[1]);
  const { Pagination } = loader({ "./Icon": { Icon: () => null } })("@/components/ui/Pagination");
  // Server render (no width yet): the narrowest row, one number.
  const render = (page, pages) => renderToStaticMarkup(React.createElement(Pagination, props(page, pages)));
  assert.equal(render(1, 1), "");
  const start = render(1, 420);
  assert.deepEqual(labels(start), ["첫 페이지", "이전 페이지", "1페이지", "다음 페이지", "마지막 페이지"]);
  assert.deepEqual(disabled(start), ["첫 페이지", "이전 페이지"]);
  assert.match(start, /aria-current="page"[^>]*>1</);
  assert.doesNotMatch(start, /…/);
  assert.deepEqual(disabled(render(210, 420)), []);
  const end = render(420, 420);
  assert.deepEqual(disabled(end), ["다음 페이지", "마지막 페이지"]);
  assert.match(end, /aria-current="page"[^>]*>420</);
});

test("season select shows '2025-26 시즌' on the trigger and options, never a replacement", () => {
  const seasons = [
    { season: 2026, label: "2026-27", current: true },
    { season: 2025, label: "2025-26", current: false },
  ];
  const { SeasonSelect } = loader()("@/components/common/SeasonSelect");
  const html = (value) => renderToStaticMarkup(React.createElement(SeasonSelect, { seasons, value, onChange: () => {} }));
  assert.match(html(2025), />2025-26 시즌</);
  assert.match(html(null), /시즌 선택/);
  assert.doesNotMatch(html(null), /2026-27 시즌/);

  // Opened list (the `open` state forced on): every option reads "YYYY-YY 시즌" only.
  const opened = loader({
    react: { ...React, useState: (initial) => [initial === false ? true : initial, () => {}], useEffect: () => {} },
  })("@/components/common/SeasonSelect").SeasonSelect;
  const list = renderToStaticMarkup(React.createElement(opened, { seasons, value: 2026, onChange: () => {} }));
  const options = [...list.matchAll(/role="option"[^>]*>([^<]*)</g)].map((m) => m[1]);
  assert.deepEqual(options, ["2026-27 시즌", "2025-26 시즌"]);
  assert.doesNotMatch(list, /현재 시즌|이전 시즌/);
});

test("favourite team buttons: one row for the schedule and past results", () => {
  const { FavoriteTeamButtons } = loader()("@/features/favorites/FavoriteTeamButtons");
  const teams = [
    { id: 50, nameKo: "맨체스터 시티", nameEn: "Manchester City", crestUrl: null, detailAvailable: true },
    { id: 48, nameKo: null, nameEn: "West Ham", crestUrl: null, detailAvailable: false },
  ];
  const render = (activeId) =>
    renderToStaticMarkup(React.createElement(FavoriteTeamButtons, { teams, activeId, onSelect: () => {}, label: "관심 팀 지난 경기" }));
  const html = render(48);
  assert.match(html, /role="group" aria-label="관심 팀 지난 경기"/);
  assert.match(html, /★<\/span>관심 팀/);
  assert.match(html, /aria-pressed="false"[^>]*>맨체스터 시티</);
  assert.match(html, /aria-pressed="true"[^>]*>West Ham</);
  assert.equal(renderToStaticMarkup(React.createElement(FavoriteTeamButtons, { teams: [], activeId: null, onSelect: () => {}, label: "x" })), "");
});

test("club world cup: year only for a held tournament, never a '2026' edition", () => {
  const cwc = {
    id: 15, nameKo: "FIFA 클럽 월드컵", shortName: "FIFA Club World Cup", group: "FIFA",
    currentSeason: { season: 2026, label: "2026-27", availability: "no_data" },
    seasons: [
      { season: 2026, label: "2026-27", availability: "no_data" },
      { season: 2025, label: "2025-26", availability: "available" },
    ],
  };
  const { CompetitionFilter } = loader()("@/components/common/CompetitionFilter");
  const summary = (season) => {
    const html = renderToStaticMarkup(
      React.createElement(CompetitionFilter, { competitions: [cwc], selected: [15], onChange: () => {}, season }),
    );
    return html.match(/aria-label="대회 선택: ([^"]+)"/)[1];
  };
  assert.equal(summary(2025), "FIFA 클럽 월드컵 2025");
  assert.equal(summary(2026), "FIFA 클럽 월드컵");
});
