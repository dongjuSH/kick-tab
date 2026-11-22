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

test("records query has no timer of its own: the match update drives it (MAT-004 rule 4, LIVE-004)", () => {
  const load = loader({ "@/lib/api/client": { apiFetch: () => { throw Error("unexpected network"); } } });
  const { matchRecordsQuery } = load("@/features/match/queries");
  for (const status of ["scheduled", "live", "finished"]) {
    const options = matchRecordsQuery(match(status));
    assert.equal(options.refetchInterval, undefined);
    assert.equal(options.refetchOnWindowFocus, false);
  }
});

test("page areas by state: no lineup or review area before kickoff, reviews beside finished records", () => {
  const { areasOf } = loader()("@/features/match/model");
  const of = (status, reviewsAvailable, headToHeadAvailable = false) =>
    areasOf({ ...info(status), reviewsAvailable, headToHeadAvailable });
  assert.deepEqual({ ...of("scheduled", false, true) }, { records: false, headToHead: true, reviews: false, reviewsBeside: false });
  assert.deepEqual({ ...of("live", true) }, { records: true, headToHead: false, reviews: true, reviewsBeside: false });
  assert.deepEqual({ ...of("finished", true) }, { records: true, headToHead: false, reviews: true, reviewsBeside: true });
  // Rulings and stopped matches: the server closes reviews.
  assert.deepEqual({ ...of("finished", false) }, { records: true, headToHead: false, reviews: false, reviewsBeside: false });
  assert.deepEqual({ ...of("abandoned", false) }, { records: true, headToHead: false, reviews: false, reviewsBeside: false });
});

test("timeline records carry an icon kind and text: goal, substitution, cards, cancelled goal (MAT-002)", () => {
  const { eventKind, eventText } = loader()("@/features/match/model");
  const ev = (type, detail, extra = {}) => ({ elapsed: 10, extra: null, side: "home", type, detail, player: "A", assist: null, ...extra });
  const cases = [
    // The team is the timeline column, not part of the text (MAT-002, Figma 52:151).
    [ev("goal", "Normal Goal", { assist: "B" }), "goal", "골 · A (도움 B)"],
    [ev("goal", "Missed Penalty", { assist: "B" }), "missed", "페널티킥 실축 · A"],
    [ev("subst", "Substitution 1", { assist: "B" }), "subst", "교체 · A → B"],
    [ev("card", "Yellow Card", { side: "away" }), "yellow", "경고 · A"],
    [ev("card", "Red Card", { side: "away" }), "red", "퇴장 · A"],
    [ev("card", "Second Yellow card"), "red", "경고 누적 퇴장 · A"],
    [ev("var", "Goal cancelled"), "cancelled", "골 취소 · A"],
    [ev("var", "Penalty confirmed"), "var", "VAR · 페널티킥 인정 · A"],
  ];
  for (const [event, kind, text] of cases) {
    assert.equal(eventKind(event), kind);
    assert.equal(eventText(event), text);
  }
});

test("timeline puts home events left, away right, unknown-team events in the middle (MAT-002)", () => {
  const h = hooks();
  const withEvents = { ...records, events: { status: "available", data: [
    { elapsed: 12, extra: null, side: "home", type: "goal", detail: "Normal Goal", player: "A", assist: null },
    { elapsed: 30, extra: null, side: "away", type: "card", detail: "Yellow Card", player: "Away Player", assist: null },
    { elapsed: 50, extra: null, side: null, type: "card", detail: "Yellow Card", player: "Unknown Player", assist: null },
    { elapsed: 79, extra: null, side: "home", type: "var", detail: "Goal cancelled", player: "A", assist: null },
  ] } };
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => ({ data: { data: withEvents, meta: { updatedAt: null } }, refetch() {} }) },
    "./queries": { matchRecordsQuery: () => ({}) },
  });
  const { MatchRecords } = load("@/features/match/MatchRecords");
  const { html } = h.render(MatchRecords, { info: info("finished"), tab: "timeline", onTab() {} });
  assert.equal((html.match(/<svg/g) ?? []).length, 4);
  // Header: home | 시간 | away.
  assert.match(html, /팀 50[\s\S]*시간[\s\S]*팀 42/);
  const rows = html.match(/<li[\s\S]*?<\/li>/g) ?? [];
  assert.equal(rows.length, 4);
  // Latest first; each sided row: [sr team] [home cell] [minute] [away cell].
  const cells = (row) => row.replace(/^<li[^>]*>/, "").replace(/<\/li>$/, "");
  assert.match(rows[0], /79′/);
  assert.match(cells(rows[0]), /^<span class="sr-only">팀 50, <\/span><span class="min-w-0">[\s\S]*골 취소 · A[\s\S]*<\/span><span[^>]*>79′<\/span><span class="min-w-0"><\/span>$/);
  assert.match(rows[1], /50′[\s\S]*Unknown Player[\s\S]*소속 미확인/);
  assert.doesNotMatch(rows[1], /sr-only/);
  assert.match(cells(rows[2]), /^<span class="sr-only">팀 42, <\/span><span class="min-w-0"><\/span><span[^>]*>30′<\/span><span class="min-w-0">[\s\S]*경고 · Away Player/);
  assert.doesNotMatch(html, /데이터 제공사가 전달한 이벤트만/);
});

test("player ratings show one card per team, home first, with missing ratings as a dash (Figma 94:4418)", () => {
  const h = hooks();
  const players = [
    { playerId: 1, name: "Home Best", photoUrl: null, side: "home", rating: 8.4 },
    { playerId: 2, name: "Away Best", photoUrl: null, side: "away", rating: 8.1 },
    { playerId: 3, name: "Home Unrated", photoUrl: null, side: "home", rating: null },
  ];
  const withRatings = { ...records, players: { status: "available", data: players } };
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => ({ data: { data: withRatings, meta: { updatedAt: null } }, refetch() {} }) },
    "./queries": { matchRecordsQuery: () => ({}) },
  });
  const { MatchRecords } = load("@/features/match/MatchRecords");
  const { html } = h.render(MatchRecords, { info: info("finished"), tab: "ratings", onTab() {} });
  const cards = html.match(/<section class="flex min-w-0 flex-col rounded-control[\s\S]*?<\/section>/g) ?? [];
  assert.equal(cards.length, 2);
  assert.match(cards[0], /팀 50[\s\S]*Home Best[\s\S]*8\.4[\s\S]*Home Unrated[\s\S]*—/);
  assert.match(cards[1], /팀 42[\s\S]*Away Best[\s\S]*8\.1/);
  assert.doesNotMatch(cards[1], /Home/);
  assert.match(html, /미제공 평점은 —로 표시합니다/);
  assert.doesNotMatch(html, /<table/);
});

test("recent form uses the shared row: oldest first, home and away sides from the venue (MAT-005)", () => {
  const { formItems } = loader()("@/features/match/model");
  const items = formItems("도르트문트", [
    { kickoffDateKst: "2026-11-08", competition: "분데스리가", opponentName: "바이에른", venue: "away", goalsFor: 0, goalsAgainst: 3, result: "L" },
    { kickoffDateKst: "2026-11-01", competition: "DFB 포칼", opponentName: "라이프치히", venue: "home", goalsFor: 2, goalsAgainst: null, result: "W" },
  ]);
  assert.equal(
    JSON.stringify(items.map((i) => [i.date, i.competition, i.home, i.goalsHome, i.goalsAway, i.away, i.result])),
    JSON.stringify([
      ["2026-11-01", "DFB 포칼", "도르트문트", 2, null, "라이프치히", "W"],
      ["2026-11-08", "분데스리가", "바이에른", 3, 0, "도르트문트", "L"],
    ]),
  );
});

test("match reviews show the count only: no star rating or average", () => {
  const h = hooks();
  const list = { summary: { count: 2 }, items: [
    { id: 1, authorNickname: null, body: "좋은 경기", likes: 3, dislikes: 1, createdAt: "", updatedAt: "" },
    { id: 2, authorNickname: "축구좋아", body: "후반 집중력", likes: 0, dislikes: 0, createdAt: "", updatedAt: "" },
  ] };
  const reviewLoader = (data, react = h.react) => loader({ ...leaves, react,
    "@tanstack/react-query": { useQuery: () => ({ data, isPending: false }), useQueryClient: () => ({}) },
    "next/navigation": { useRouter: () => ({ push() {} }) },
    "@/features/auth/session": { useAuth: () => ({ status: "guest" }) },
    "./queries": { reviewsQuery: () => ({}) },
  }, { URL })("@/features/match/ReviewSection");
  const { html } = h.render(reviewLoader(list).ReviewSection, { fixtureId: 1, sort: "popular", onSort() {} });
  assert.match(html, /경기 평가/);
  // Guest notice as the latest Figma (408:16478): primary 로그인 → the login that returns to
  // this match's review area (02, AUTH-005).
  assert.match(html, /로그인 후 경기 평가를 작성할 수 있습니다\./);
  const login = html.match(/<a [^>]*>로그인<\/a>/)?.[0] ?? "";
  assert.match(login, /bg-action/);
  assert.match(login, /href="\/login\?returnTo=%2Fmatches%2F1&amp;intent=review%3A1"/);
  assert.match(html, /2건/);
  assert.match(html, /좋아요 3/);
  assert.match(html, /인기순/);
  assert.doesNotMatch(html, /평점|평균|★/);
  // Fresh hook slots: the list items (reactions) changed the hook order of the first render.
  const h2 = hooks();
  const none = h2.render(reviewLoader({ summary: { count: 0 }, items: [] }, h2.react).ReviewSection,
    { fixtureId: 1, sort: "latest", onSort() {} }).html;
  assert.match(none, /아직 평가가 없습니다/);
  assert.match(none, /평가 0건/);
});

test("team crest and name are one link only for team-browse teams", () => {
  const h = hooks();
  const { Scoreboard } = loader({ ...leaves, react: h.react })("@/features/match/Scoreboard");
  const base = info("finished");
  const props = { info: { ...base, match: { ...base.match, home: { ...team(50), detailAvailable: true } } },
    updatedAt: null, checkedAt: 0, heading: "경기" };
  const { html } = h.render(Scoreboard, props);
  const links = html.match(/<a [^>]*>[\s\S]*?<\/a>/g) ?? [];
  assert.equal(links.length, 1);
  assert.match(links[0], /href="\/teams\/50"/);
  assert.match(links[0], /팀 50/);
  assert.doesNotMatch(html, /teams\/42/);
  assert.match(html, /팀 42/);
  assert.doesNotMatch(html, /팀 상세 미제공/);
});

test("live to finished fetches final records once and keeps cached records on failure", () => {
  const h = hooks();
  let calls = 0;
  const options = [];
  const result = { data: { data: records, meta: { updatedAt: null } }, isError: false,
    refetch: (o) => { calls++; options.push(o); } };
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => result },
    "./queries": { matchRecordsQuery: () => ({}) },
  });
  const { MatchRecords } = load("@/features/match/MatchRecords");
  const props = { info: info("live"), infoUpdatedAt: 1, tab: "timeline", onTab() {} };
  h.render(MatchRecords, props);
  assert.equal(calls, 0);
  // Each live match update reads the record once, joining a read already running.
  props.infoUpdatedAt = 2;
  h.render(MatchRecords, props);
  assert.equal(calls, 1);
  assert.deepEqual({ ...options[0] }, { cancelRefetch: false });
  h.render(MatchRecords, props);
  assert.equal(calls, 1);
  // The update that brings the finish reads the final record exactly once (Codex 2026-11-11).
  props.info = info("finished");
  props.infoUpdatedAt = 3;
  h.render(MatchRecords, props);
  assert.equal(calls, 2);
  assert.equal(options[1], undefined);
  // A finished match is not re-read by later match updates.
  props.infoUpdatedAt = 4;
  h.render(MatchRecords, props);
  assert.equal(calls, 2);
  result.isError = true;
  const { html } = h.render(MatchRecords, props);
  assert.equal(calls, 2);
  assert.match(html, /최신 기록으로 갱신하지 못했습니다/);
  assert.match(html, /아직 기록된 이벤트가 없습니다/);
});

test("abandoned match exposes timeline only even if URL selects another tab", () => {
  const h = hooks();
  const load = loader({ ...leaves, react: h.react,
    "@tanstack/react-query": { useQuery: () => ({ data: { data: records, meta: { updatedAt: null } }, refetch() {} }) },
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

test("after kickoff a still-scheduled match reads 상태 확인 중, never 예정 (03 guest UX 2026-11-09)", () => {
  const { awaitingStatus } = loader()("@/lib/format/match");
  const kickoff = Date.parse("2026-11-10T18:00:00Z");
  const match = { status: "scheduled", timeConfirmed: true, kickoffAt: "2026-11-10T18:00:00Z" };
  assert.equal(awaitingStatus(match, kickoff - 60_000), false);
  assert.equal(awaitingStatus(match, kickoff + 60_000), true);
  // The server render passes 0 (no clock), and an unfixed time or a started match never waits.
  assert.equal(awaitingStatus(match, 0), false);
  assert.equal(awaitingStatus({ ...match, timeConfirmed: false }, kickoff + 60_000), false);
  assert.equal(awaitingStatus({ ...match, status: "live" }, kickoff + 60_000), false);
});

test("main team view starts at every competition and clearing restores the earlier date and competitions (SCH-006, 2026-11-10)", () => {
  const { withTeam, withoutTeam } = loader()("@/features/schedule/useScheduleParams");
  const decode = (q) => Object.fromEntries(new URLSearchParams(q));
  // Date view with Serie A on 11/14 → pick a team: every competition, return point saved.
  const picked = withTeam("date=2026-11-14&competitions=135", 50);
  assert.deepEqual(decode(picked), { date: "2026-11-14", team: "50", from: "135" });
  // Narrowing the team view and switching teams keep the return point; a new team starts at all.
  const narrowed = new URLSearchParams(picked); narrowed.set("competitions", "39");
  assert.deepEqual(decode(withTeam(narrowed.toString(), 42)), { date: "2026-11-14", team: "42", from: "135" });
  // Clearing restores date and competitions.
  assert.deepEqual(decode(withoutTeam(narrowed.toString())), { date: "2026-11-14", competitions: "135" });
  // From "every competition" (no competitions param) the restore is every competition again.
  const fromAll = withTeam("date=2026-11-12", 50);
  assert.equal(new URLSearchParams(fromAll).get("from"), "all");
  assert.deepEqual(decode(withoutTeam(fromAll)), { date: "2026-11-12" });
  // A shared team link without a return point clears to every competition.
  assert.deepEqual(decode(withoutTeam("team=50&competitions=39")), {});
});

test("applying competitions skips unconfirmed dates and moves to the nearest confirmed match day (SCH-004, Figma 308:4631)", () => {
  const { nearestMatchDate } = loader()("@/features/schedule/useScheduleParams");
  const dates = ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"];
  const states = { "2026-11-09": "ready", "2026-11-10": "empty", "2026-11-11": "unknown", "2026-11-12": "ready", "2026-11-13": "ready" };
  const stateOf = (d) => states[d];
  // Codex case: today 11/10 confirmed empty, 11/11 unconfirmed, 11/12 has matches → 11/12.
  assert.equal(nearestMatchDate(dates, "2026-11-10", "2026-11-10", stateOf), "2026-11-12");
  // A date with matches (or an unconfirmed one) stays; past dates are never chosen.
  assert.equal(nearestMatchDate(dates, "2026-11-10", "2026-11-12", stateOf), undefined);
  assert.equal(nearestMatchDate(dates, "2026-11-10", "2026-11-11", stateOf), undefined);
  // Before the availability arrives nothing moves.
  assert.equal(nearestMatchDate(dates, "2026-11-10", "2026-11-10", (d) => (d === "2026-11-10" ? "empty" : "pending")), undefined);
});

test("default match day: today when it has a match, else the nearest later one, else none (SCH-002, 2026-11-19)", () => {
  const { defaultMatchDate } = loader()("@/features/schedule/useScheduleParams");
  const dates = ["2026-11-13", "2026-11-14", "2026-11-15", "2026-11-19", "2026-11-20"];
  assert.equal(defaultMatchDate(dates, "2026-11-19"), "2026-11-19");
  // No match today (11/17): the next match day, never a past one.
  assert.equal(defaultMatchDate(dates, "2026-11-17"), "2026-11-19");
  // Nothing ahead: no default ("예정 일정 없음" with the past days still on the bar).
  assert.equal(defaultMatchDate(dates, "2026-11-21"), null);
  assert.equal(defaultMatchDate([], "2026-11-19"), null);
});

test("KST date turns at 15:00 UTC and the period reads as its real first and last day", () => {
  const { kstTodayIso, formatDateRange } = loader()("@/lib/format/kst");
  assert.equal(kstTodayIso(new Date("2026-11-18T14:59:59Z")), "2026-11-18");
  assert.equal(kstTodayIso(new Date("2026-11-18T15:00:00Z")), "2026-11-19");
  assert.equal(kstTodayIso(new Date("2026-12-31T15:00:00Z")), "2027-01-01");
  assert.equal(formatDateRange("2026-11-06", "2026-12-02"), "2026.11.06–12.02");
  assert.equal(formatDateRange("2026-12-20", "2027-01-08"), "2026.12.20–2027.01.08");
});

test("match card: HH:mm or 시간 미정, and VS only between the teams of a scheduled match (2026-11-19)", () => {
  const { kickoffTime, scoreText } = loader()("@/lib/format/match");
  const base = { kickoffAt: "2026-11-19T11:30:00Z", timeConfirmed: true, status: "scheduled",
    score: { home: null, away: null } };
  assert.equal(kickoffTime(base), "20:30");
  assert.equal(kickoffTime({ ...base, kickoffAt: "2026-11-18T15:05:00Z" }), "00:05");
  assert.equal(kickoffTime({ ...base, timeConfirmed: false }), "시간 미정");
  assert.equal(scoreText(base), "VS");
  assert.equal(scoreText({ ...base, status: "postponed" }), "—");
  assert.equal(scoreText({ ...base, status: "live", score: { home: 1, away: 0 } }), "1 : 0");
  assert.equal(scoreText({ ...base, status: "finished", score: { home: 2, away: 2 } }), "2 : 2");
  assert.equal(scoreText({ ...base, status: "finished" }), "—");
});

test("a vanished date announces the new target again when Back restores different competitions (N12)", () => {
  const values = [];
  let cursor = 0;
  let dirty = false;
  let effects = [];
  const react = {
    ...React,
    useState(initial) {
      const index = cursor++;
      if (!(index in values)) values[index] = typeof initial === "function" ? initial() : initial;
      return [values[index], (value) => {
        const next = typeof value === "function" ? value(values[index]) : value;
        if (!Object.is(next, values[index])) { values[index] = next; dirty = true; }
      }];
    },
    useEffect(effect) { effects.push(effect); },
  };
  let date = "2026-11-21";
  let competitions = [78];
  let period = {
    today: "2026-11-19", start: "2026-11-21", end: "2026-11-23",
    dates: [
      { date: "2026-11-21", competitionIds: [39, 78], unknownCompetitionIds: [] },
      { date: "2026-11-22", competitionIds: [39], unknownCompetitionIds: [] },
      { date: "2026-11-23", competitionIds: [78], unknownCompetitionIds: [] },
    ],
  };
  const update = (change) => { date = change.date; dirty = true; };
  const pending = { isPending: true, isError: false };
  const success = (data) => ({ data, isPending: false, isError: false, isSuccess: true, refetch() {} });
  const emptyList = { data: [], meta: { failedCompetitionIds: [], updatedAt: null } };
  const { ScheduleSection } = loader({
    react,
    "@tanstack/react-query": { useQuery: (options) => {
      if (options.queryKey[0] === "availability") return success(period);
      if (options.queryKey[0] === "date") return success(emptyList);
      return pending;
    } },
    "@/lib/hooks/useHydrated": { useHydrated: () => true },
    "@/features/favorites/useFavorites": { useFavorites: () => ({ status: "ready", ids: [] }) },
    "@/components/common/CompetitionFilter": { CompetitionFilter: () => null },
    "@/components/common/MatchCard": { MatchCard: () => null },
    "@/components/common/TeamSearch": { TeamSearch: () => null },
    "@/components/ui/Button": { Button: ({ children }) => React.createElement("button", null, children) },
    "@/features/favorites/FavoriteTeamButtons": { FavoriteTeamButtons: () => null },
    "./DateBar": { DateBar: () => null },
    "./queries": {
      competitionsQuery: { queryKey: ["competitions"] },
      fixtureAvailabilityQuery: () => ({ queryKey: ["availability"] }),
      fixturesByDateQuery: (day) => ({ queryKey: ["date", day] }),
      teamScheduleQuery: () => ({ queryKey: ["team"] }),
      favoriteScheduleQuery: () => ({ queryKey: ["favorites"] }),
    },
    "./useScheduleParams": {
      defaultMatchDate: (dates, today) => dates.find((day) => day >= today) ?? null,
      useScheduleParams: () => ({ today: period.today, date, competitions, team: null, update }),
    },
  })("@/features/schedule/ScheduleSection");
  const render = () => {
    for (let attempt = 0; attempt < 10; attempt++) {
      cursor = 0; dirty = false; effects = [];
      const html = renderToStaticMarkup(React.createElement(ScheduleSection));
      if (dirty) continue; // React discards effects of a render-phase state update.
      effects.forEach((effect) => effect());
      if (!dirty) return html;
    }
    assert.fail("the schedule did not settle after navigation");
  };

  render(); // Remember 11/21 in Bundesliga, then push EPL with the same date.
  competitions = [39]; render();
  period = { ...period, start: "2026-11-22", dates: period.dates.slice(1) };
  assert.ok(render().includes("11/22(일) 경기로 이동했습니다."));
  assert.equal(date, "2026-11-22");
  // Back restores the same vanished date with Bundesliga: its next match is 11/23.
  date = "2026-11-21"; competitions = [78];
  assert.ok(render().includes("11/23(월) 경기로 이동했습니다."));
  assert.equal(date, "2026-11-23");
});
