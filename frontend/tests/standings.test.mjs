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
  assert.equal(paramsFor("league=848").params.league, 848); // UEFA league phase
  assert.equal(paramsFor("league=abc").params.league, null);
  const season = paramsFor("league=39&season=abc").params;
  assert.equal(JSON.stringify([season.season, season.seasonInvalid]), "[null,true]");
  const type = paramsFor("league=39&type=fouls").params;
  assert.equal(type.typeInvalid, true);
});

test("display rules: signed goal difference, missing values, shared ranks", () => {
  const model = loader()("@/features/standings/model");
  assert.equal(model.signed(15), "+15");
  assert.equal(model.signed(-2), "-2");
  assert.equal(model.signed(0), "0");
  assert.equal(model.signed(null), "—"); // missing is never 0
  assert.equal(model.numberText(null), "—");
  assert.equal(model.rankText(2, true), "공동 2");
  assert.equal(model.rankText(3, false), "3");
});

test("relegation marks come from the position: bottom three, or 16th play-off and 17th-18th", () => {
  const { leagueZone } = loader()("@/features/standings/model");
  const marks = (league, size, complete) =>
    Array.from({ length: size }, (_, i) => leagueZone(league, i + 1, size, complete))
      .map((z, i) => (z ? `${i + 1}:${z.label}:${z.tone}` : null))
      .filter(Boolean)
      .join(" ");
  for (const league of [39, 140, 135]) {
    assert.equal(marks(league, 20, false), "18:강등권:error 19:강등권:error 20:강등권:error");
    assert.equal(marks(league, 20, true), "18:강등:error 19:강등:error 20:강등:error");
  }
  for (const league of [78, 61]) {
    assert.equal(marks(league, 18, false), "16:승강 플레이오프권:warning 17:강등권:error 18:강등권:error");
    assert.equal(marks(league, 18, true), "16:승강 플레이오프:warning 17:강등:error 18:강등:error");
  }
});

test("UEFA league-phase bands: zones while it runs, results once it is over", () => {
  const { phaseBands } = loader()("@/features/standings/model");
  const text = (complete) => phaseBands(complete).map((b) => `${b.label} ${b.from}-${b.to}`).join(" / ");
  assert.equal(text(false), "16강 직행권 1-8 / 플레이오프권 9-24 / 탈락권 25-36");
  assert.equal(text(true), "16강 직행 1-8 / 플레이오프 진출 9-24 / 탈락 25-36");
});

test("UEFA: league phase by default, stage changes are history steps, a new competition resets the stage", () => {
  const { params, pushed } = paramsFor("league=2&season=2025");
  assert.equal(JSON.stringify([params.league, params.uefa, params.stage, params.stageInvalid]), '[2,true,"league",false]');
  params.select({ stage: "r16" });
  assert.equal(pushed.at(-1), "/standings?league=2&season=2025&stage=r16");
  const onStage = paramsFor("league=2&season=2025&stage=qf");
  onStage.params.select({ league: 3 });
  assert.equal(onStage.pushed.at(-1), "/standings?league=3&season=2025");
  onStage.params.select({ stage: "league" });
  assert.equal(onStage.pushed.at(-1), "/standings?league=2&season=2025");
  const bad = paramsFor("league=2&stage=groups").params;
  assert.equal(bad.stageInvalid, true);
  assert.equal(paramsFor("league=39").params.uefa, false);
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

test("main chips follow Figma 49:57 / 306:6221 (EPL·LaLiga·Serie A·Bundesliga·Ligue 1); standings tabs keep full names", () => {
  const { LEAGUES } = loader()("@/features/standings/model");
  assert.equal(LEAGUES.map((l) => l.chip).join("|"), "EPL|LaLiga|Serie A|Bundesliga|Ligue 1");
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

test("leg labels: numbers only from the API, a single stored match is never called 1차전", () => {
  const { legRows } = loader()("@/features/standings/model");
  const leg = (n) => ({ fixtureId: n ?? 0, leg: n });
  const labels = (legs, needed = 2, final = false) => JSON.stringify(legRows({ legs, legsNeeded: needed }, final).map((r) => r.label));
  assert.equal(labels([leg(1), leg(2)]), JSON.stringify(["1차전", "2차전"]));
  assert.equal(labels([]), JSON.stringify(["1차전", "2차전"]));
  assert.equal(labels([leg(null)]), JSON.stringify(["경기", "남은 경기"]));
  assert.equal(labels([leg(1)], 1, true), JSON.stringify(["결승"]));
  assert.equal(labels([], 1, true), JSON.stringify(["결승"]));
});
