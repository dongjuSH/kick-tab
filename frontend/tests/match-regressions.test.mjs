/* Run the real TS/TSX modules with Node's test runner; no browser, network or new dependencies.
 * QueryObserver preserves TanStack's actual cache/structural-sharing behavior. Component
 * hooks are driven explicitly where time and successive query results must be controlled. */
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
import { QueryClient, QueryObserver } from "@tanstack/query-core";

const loadDependency = createRequire(import.meta.url);
const root = fileURLToPath(new URL("../src", import.meta.url));
function loader(mocks = {}, globals = {}) {
  const cache = new Map();
  function load(request, from = root) {
    if (Object.hasOwn(mocks, request)) return mocks[request];
    if (!request.startsWith(".") && !request.startsWith("@/")) return loadDependency(request);
    let file = request.startsWith("@/") ? path.join(root, request.slice(2)) : path.resolve(from, request);
    file = [file, `${file}.ts`, `${file}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
    assert.ok(file, `module ${request}`);
    if (cache.has(file)) return cache.get(file).exports;
    const loaded = { exports: {} };
    cache.set(file, loaded);
    const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    const execute = vm.runInNewContext(`(function(require,module,exports){${code}\n})`, {
      console, Date, URLSearchParams, ...globals,
    }, { filename: file });
    execute((name) => load(name, path.dirname(file)), loaded, loaded.exports);
    return loaded.exports;
  }
  return load;
}

function hooks() {
  const values = [];
  const dependencies = [];
  let cursor = 0;
  let effects = [];
  const same = (a, b) => a && b && a.length === b.length && a.every((x, i) => Object.is(x, b[i]));
  return {
    react: {
      ...React,
      useId: () => "test-id",
      useRef: (initial) => {
        const index = cursor++;
        return values[index] ??= { current: initial };
      },
      useState: (initial) => {
        const index = cursor++;
        if (!(index in values)) values[index] = initial;
        return [values[index], (value) => { values[index] = value; }];
      },
      useEffect: (effect, deps) => {
        const index = cursor++;
        if (!same(dependencies[index], deps)) {
          dependencies[index] = deps;
          effects.push(effect);
        }
      },
    },
    render(component, props) {
      cursor = 0;
      effects = [];
      const html = renderToStaticMarkup(React.createElement(component, props));
      const cleanups = effects.map((effect) => effect());
      return { html, cleanup: () => cleanups.forEach((cleanup) => cleanup?.()) };
    },
  };
}

const team = (id) => ({ id, name: `Team ${id}`, nameKo: `팀 ${id}`, crestUrl: null, detailAvailable: false });
const match = (status = "live") => ({
  id: 123, status, home: team(50), away: team(42),
  competition: { id: 39, nameKo: "프리미어리그" },
  kickoffAt: "2026-11-03T12:00:00Z", kickoffDateKst: "2026-11-03", timeConfirmed: true,
  score: { home: 1, away: 0, penaltyHome: null, penaltyAway: null }, elapsed: 90,
});
const info = (status) => ({ match: match(status), seasonLabel: "2026-27", round: null });
const records = {
  events: { status: "available", data: [] }, statistics: { status: "available", data: [] },
  lineups: { status: "not_yet", data: null }, players: { status: "not_provided", data: null },
};
const leaves = {
  "next/link": { __esModule: true, default: ({ children, ...props }) => React.createElement("a", props, children) },
  "@/components/common/TeamCrest": { TeamCrest: () => null, PlayerPhoto: () => null },
};

test("records wake for lineups, then poll live and stop after finish", () => {
  const load = loader({ "@/lib/api/client": { apiFetch: () => { throw Error("unexpected network"); } } });
  const { matchRecordsQuery } = load("@/features/match/queries");
  const now = Date.now();
  const scheduled = { ...match("scheduled"), kickoffAt: new Date(now + 2 * 60 * 60_000).toISOString() };
  const pending = { state: { data: { data: records } } };
  const wait = matchRecordsQuery(scheduled).refetchInterval(pending);
  assert.ok(wait > 59 * 60_000 && wait <= 60 * 60_000 + 1_000);
  scheduled.kickoffAt = new Date(now + 30 * 60_000).toISOString();
  assert.equal(matchRecordsQuery(scheduled).refetchInterval(pending), 10 * 60_000);
  assert.equal(matchRecordsQuery(scheduled).refetchInterval({ state: { data: { data: {
    ...records, lineups: { status: "available", data: [] },
  } } } }), false);
  assert.equal(matchRecordsQuery(match("live")).refetchInterval(pending), 60_000);
  assert.equal(matchRecordsQuery(match("finished")).refetchInterval(pending), false);
});

test("live to finished fetches final records once and keeps cached records on failure", () => {
  const h = hooks();
  let calls = 0;
  const result = { data: { data: records }, isError: false, refetch: () => { calls++; } };
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => result },
    "./queries": { matchRecordsQuery: () => ({}) },
  });
  const { MatchRecords } = load("@/features/match/MatchRecords");
  const props = { info: info("live"), tab: "timeline", onTab() {} };
  h.render(MatchRecords, props);
  assert.equal(calls, 0);
  props.info = info("finished");
  h.render(MatchRecords, props);
  assert.equal(calls, 1);
  result.isError = true;
  const { html } = h.render(MatchRecords, props);
  assert.equal(calls, 1);
  assert.match(html, /최신 기록으로 갱신하지 못했습니다/);
  assert.match(html, /아직 기록된 이벤트가 없습니다/);
});

test("abandoned match exposes timeline only even if URL selects another tab", () => {
  const h = hooks();
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => ({ data: { data: records }, refetch() {} }) },
    "./queries": { matchRecordsQuery: () => ({}) },
  });
  const { MatchRecords } = load("@/features/match/MatchRecords");
  const { html } = h.render(MatchRecords, { info: info("abandoned"), tab: "ratings", onTab() {} });
  assert.match(html, /타임라인/);
  assert.doesNotMatch(html, /role="tab"|팀 통계|선수 평점/);
});

test("live staleness warning advances with time while cached query timestamp is unchanged", () => {
  const h = hooks();
  const time = Date.now();
  let tick;
  let removed = 0;
  const load = loader({ ...leaves, react: h.react }, {
    Date: class extends Date { static now() { return time + 181_000; } },
    document: { visibilityState: "visible", addEventListener() {}, removeEventListener() { removed++; } },
    window: { setInterval(fn) { tick = fn; return 1; }, clearInterval() { removed++; }, addEventListener() {}, removeEventListener() { removed++; } },
  });
  const { Scoreboard } = load("@/features/match/Scoreboard");
  const props = { info: info("live"), updatedAt: new Date(time).toISOString(), checkedAt: time, heading: "경기" };
  const initial = h.render(Scoreboard, props);
  assert.doesNotMatch(initial.html, /갱신이 지연/);
  tick();
  assert.match(h.render(Scoreboard, props).html, /갱신이 지연/);
  initial.cleanup();
  assert.equal(removed, 3);
});

test("HTTP 200 unavailable H2H and both team forms have retry buttons", () => {
  const h = hooks();
  const unavailable = { status: "unavailable", data: null };
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => ({ data: { data: {
      meetings: unavailable, homeForm: unavailable, awayForm: unavailable,
    } }, refetch() {} }) },
    "./queries": { headToHeadQuery: () => ({}) },
  });
  const { HeadToHeadSection } = load("@/features/match/HeadToHeadSection");
  const { html } = h.render(HeadToHeadSection, { info: info("scheduled") });
  assert.equal((html.match(/다시 확인<\/button>/g) ?? []).length, 3);
  assert.match(html, /상대 전적을 불러오지 못했습니다/);
});

test("unchanged version checks retry a failed TOP5 replacement with TanStack structural sharing", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  const h = hooks();
  let fail = true;
  let calls = 0;
  const old = { version: 1, currentWeek: { start: "2026-11-02" }, view: "delayed",
    week: { start: "2026-11-02", end: "2026-11-08" }, items: [] };
  const fresh = { ...old, version: 2 };
  const currentOptions = { queryKey: ["top-matches", "current"], queryFn: async () => {
    calls++;
    if (fail) throw Error("mock failure");
    return fresh;
  }, staleTime: Infinity };
  client.setQueryData(currentOptions.queryKey, old);
  const observer = new QueryObserver(client, currentOptions);
  const unsubscribe = observer.subscribe(() => {});
  const versionKey = ["top-matches", "version"];
  const version = { version: 2, currentWeekStart: "2026-11-02" };
  client.setQueryData(versionKey, version, { updatedAt: 1 });
  const shared = client.getQueryData(versionKey);
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": {
      useQueryClient: () => client,
      useQuery: (options) => options === currentOptions
        ? { ...observer.getCurrentResult(), refetch: () => observer.refetch() }
        : { data: client.getQueryData(versionKey), dataUpdatedAt: client.getQueryState(versionKey).dataUpdatedAt },
    },
    "next/navigation": { usePathname: () => "/" },
    "@/lib/hooks/useMediaQuery": { DESKTOP_QUERY: "", useMediaQuery: () => true },
    "@/components/ui/Dialog": { BottomSheet: () => null },
    "./Top5List": { Top5List: () => null },
    "./queries": { currentTopMatchesQuery: currentOptions, topMatchesVersionQuery: {},
      isOutdated: (data, latest) => data.version !== latest.version },
  });
  try {
    const { Top5Strip } = load("@/features/top5/Top5Strip");
    h.render(Top5Strip, {});
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(calls, 1);
    assert.equal(client.getQueryData(currentOptions.queryKey).version, 1);
    fail = false;
    client.setQueryData(versionKey, { ...version }, { updatedAt: 2 });
    assert.equal(client.getQueryData(versionKey), shared);
    h.render(Top5Strip, {});
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(calls, 2);
    assert.equal(client.getQueryData(currentOptions.queryKey).version, 2);
  } finally {
    unsubscribe();
    client.clear();
  }
});
