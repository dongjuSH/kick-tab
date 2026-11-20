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

test("pagination items: first and last page fixed, numbers around the page, … for the rest", () => {
  const { pageItems } = loader()("@/components/ui/Pagination");
  const w = (page, pages, numbers) => pageItems(page, pages, numbers).map((i) => (i === "gap" ? "…" : i)).join(" ");
  // Pages that fit are all shown, nothing more (Figma PC: 1 … 6 with 6 pages).
  assert.equal(w(1, 1, 9), "1");
  assert.equal(w(3, 5, 9), "1 2 3 4 5");
  assert.equal(w(8, 8, 9), "1 2 3 4 5 6 7 8");
  // Figma mobile (6 pages, 4 numbers): 1 2 3 … 6.
  assert.equal(w(1, 6, 4), "1 2 3 … 6");
  // PC, 2025-26 all (420 pages, 9 numbers).
  assert.equal(w(1, 420, 9), "1 2 3 4 5 6 7 8 … 420");
  assert.equal(w(2, 420, 9), "1 2 3 4 5 6 7 8 … 420");
  assert.equal(w(5, 420, 9), "1 2 3 4 5 6 7 8 … 420");
  assert.equal(w(6, 420, 9), "1 … 3 4 5 6 7 8 9 … 420");
  assert.equal(w(210, 420, 9), "1 … 207 208 209 210 211 212 213 … 420");
  assert.equal(w(417, 420, 9), "1 … 413 414 415 416 417 418 419 420");
  assert.equal(w(420, 420, 9), "1 … 413 414 415 416 417 418 419 420");
  // 320px phone (3 numbers): first, current, last.
  assert.equal(w(1, 420, 3), "1 2 … 420");
  assert.equal(w(2, 420, 3), "1 2 … 420");
  assert.equal(w(210, 420, 3), "1 … 210 … 420");
  assert.equal(w(419, 420, 3), "1 … 419 420");
  assert.equal(w(420, 420, 3), "1 … 419 420");
  // Team browse (8 pages).
  assert.equal(w(5, 8, 4), "1 … 5 6 … 8");
});

test("pagination width: numbers that fit the row with both arrows and two …", () => {
  const { numbersFor } = loader()("@/components/ui/Pagination");
  // 320px card row (254 + 24 into the padding) 3, 375px (333) 4, PC up to 9, never below 3.
  assert.deepEqual([100, 278, 333, 500, 540, 1000, 1254].map(numbersFor), [3, 3, 4, 7, 8, 9, 9]);
  // The widest row (n numbers, two …) always fits the width it was chosen for.
  for (const width of [278, 333, 400, 500, 700]) {
    const n = numbersFor(width);
    assert.ok(2 * 44 + n * 44 + 2 * 14 + (n + 3) * 4 <= width, `${width}px → ${n}`);
  }
});

test("pagination render: < 1 2 3 … 420 >, arrows disabled at the ends, current page marked", () => {
  const props = (page, pages) => ({ page, pages, onChange: () => {} });
  const labels = (html) => [...html.matchAll(/aria-label="(\d+)페이지"/g)].map((m) => Number(m[1]));
  const disabled = (html) => [...html.matchAll(/aria-label="(이전|다음) 페이지" disabled=""/g)].map((m) => m[1]);
  const gaps = (html) => (html.match(/…/g) ?? []).length;
  const { Pagination } = loader({ "./Icon": { Icon: () => null } })("@/components/ui/Pagination");
  // Server render (no width yet): the smallest row, 3 numbers.
  const render = (page, pages) => renderToStaticMarkup(React.createElement(Pagination, props(page, pages)));
  assert.equal(render(1, 1), "");
  const start = render(1, 420);
  assert.deepEqual(labels(start), [1, 2, 420]);
  assert.deepEqual(disabled(start), ["이전"]);
  assert.equal(gaps(start), 1);
  assert.match(start, /aria-current="page"[^>]*>1</);
  assert.doesNotMatch(start, /처음|끝/);
  const middle = render(210, 420);
  assert.deepEqual(labels(middle), [1, 210, 420]);
  assert.equal(gaps(middle), 2);
  assert.deepEqual(disabled(middle), []);
  const end = render(420, 420);
  assert.deepEqual(disabled(end), ["다음"]);
  assert.match(end, /aria-current="page"[^>]*>420</);
  // Order: < numbers >.
  assert.ok(middle.indexOf("이전 페이지") < middle.indexOf(">1<") && middle.indexOf(">420<") < middle.indexOf("다음 페이지"));
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
