/* Chat 01 guest improvements: TOP 5 strip copy and states (Figma 159:923), run on the real
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

const team = (id, nameKo) => ({ id, nameKo, nameEn: `Team ${id}`, crestUrl: null, detailAvailable: true });
const item = (rank, home, away) => ({
  rank, reason: "이유", selectedKickoffAt: "2026-11-02T11:30:00Z",
  match: { id: rank, status: "scheduled", kickoffAt: "2026-11-02T11:30:00Z", timeConfirmed: true,
    home, away, competition: { id: 39, nameKo: "프리미어리그", shortName: "Premier League" } },
});
const LAST_WEEK = {
  version: 7, view: "list", week: { start: "2026-11-02", end: "2026-11-08" },
  currentWeek: { start: "2026-11-09", end: "2026-11-15" }, selectedAt: "2026-11-01T15:00:00Z",
  items: [item(1, team(40, "리버풀"), team(33, "맨체스터 유나이티드")), item(2, team(529, "바르셀로나"), team(541, null))],
};

test("last week's list kept while selecting shows its real week and the preparing state", () => {
  const model = loader()("@/features/top5/model");
  assert.equal(model.isPrevious(LAST_WEEK), true);
  assert.equal(model.weekLabel(LAST_WEEK), "지난주 11/2–11/8");
  assert.equal(model.weekLabel({ ...LAST_WEEK, week: LAST_WEEK.currentWeek }), "11/9–11/15");
  assert.equal(model.PREPARING, "이번 주 결과 준비 중");
  // Ranks 1..n in order; a missing Korean name falls back to the English one.
  assert.equal(model.lineupItems(LAST_WEEK).join(" · "), "1위 리버풀 vs 맨체스터 유나이티드 · 2위 바르셀로나 vs Team 541");
});

test("delay notice and no-match notices are distinct texts", () => {
  const model = loader()("@/features/top5/model");
  const delayed = { ...LAST_WEEK, view: "delayed", week: LAST_WEEK.currentWeek, items: [] };
  assert.equal(model.noticeOf(delayed), "delayed");
  assert.equal(model.noticeCopy("delayed", delayed).title, "이번 주 주목 경기 업데이트가 지연되고 있습니다.");
  const none = { ...delayed, view: "none" };
  assert.equal(model.noticeCopy(model.noticeOf(none), none).title, "이번 주 지원 대회의 예정 경기가 없습니다");
  assert.equal(model.noticeCopy("none", { ...none, week: LAST_WEEK.week }).title, "지난주 지원 대회의 예정 경기가 없었습니다");
});

test("strip keeps the fixed title and badge and names last week while this week is prepared", () => {
  const load = loader({
    "@tanstack/react-query": {
      useQuery: (options) => options.queryKey ? { data: LAST_WEEK, isPending: false } : { data: undefined },
      useQueryClient: () => ({}),
    },
    "next/navigation": { usePathname: () => "/" },
    "@/lib/hooks/useMediaQuery": { DESKTOP_QUERY: "", useMediaQuery: () => true },
    "@/components/ui/Dialog": { BottomSheet: () => null },
    "./Top5List": { Top5List: () => null },
    "./queries": { currentTopMatchesQuery: { queryKey: ["c"] }, topMatchesVersionQuery: {}, isOutdated: () => false },
  });
  const { Top5Strip } = load("@/features/top5/Top5Strip");
  const html = renderToStaticMarkup(React.createElement(Top5Strip));
  for (const text of ["AI 선정", "이번 주 주목 경기 TOP 5", "지난주 11/2–11/8", "이번 주 결과 준비 중", "1위 리버풀 vs 맨체스터 유나이티드"]) {
    assert.ok(html.includes(text), text);
  }
  assert.ok(!html.includes("지난주 주목 경기 TOP 5"), "the title stays fixed");
});
