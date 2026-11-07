/* Team detail rules (chat 08): player sort / missing values, season rows, transfer wording. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";

const loadDependency = createRequire(import.meta.url);
const root = fileURLToPath(new URL("../src", import.meta.url));
function load(request, from = root, cache = new Map()) {
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
  vm.runInNewContext(`(function(require,module,exports){${code}\n})`, { console }, { filename: file })(
    (name) => load(name, path.dirname(file), cache), loaded, loaded.exports,
  );
  return loaded.exports;
}

const model = load("@/features/team-detail/model");
// Values from the vm context have their own prototypes: compare plain copies.
const plain = (value) => JSON.parse(JSON.stringify(value));

function player(id, name, position, number, stats, nationality = "France") {
  return { player: { id, name, photoUrl: null }, position, number, nationality, stats };
}
const stats = (goals, rating = "7.0") => ({ appearances: 3, minutes: 200, goals, assists: 0, rating });
const squad = [
  player(1, "Striker", "Attacker", 9, stats(5)),
  player(2, "Keeper", "Goalkeeper", 1, stats(0)),
  player(3, "Youth", "Midfielder", null, null, null),
  player(4, "Back", "Defender", 4, stats(1)),
  player(5, "Unknown", null, 30, stats(null)),
];

test("default order is GK, DF, MF, FW with missing position last", () => {
  const order = plain(model.sortPlayers(squad, model.DEFAULT_SORT).map((p) => p.player.name));
  assert.deepEqual(order, ["Keeper", "Back", "Youth", "Striker", "Unknown"]);
});

test("missing values stay last in both directions and the set never changes", () => {
  const desc = plain(model.sortPlayers(squad, { key: "goals", dir: "desc" }).map((p) => p.player.id));
  const asc = plain(model.sortPlayers(squad, { key: "goals", dir: "asc" }).map((p) => p.player.id));
  assert.deepEqual(desc.slice(0, 3), [1, 4, 2]);
  assert.deepEqual(asc.slice(0, 3), [2, 4, 1]);
  assert.deepEqual(new Set(desc.slice(3)), new Set([3, 5]));
  assert.deepEqual(new Set(asc.slice(3)), new Set([3, 5]));
  assert.deepEqual([...desc].sort(), [1, 2, 3, 4, 5]);
});

test("a new column starts with most first for records, then flips", () => {
  assert.deepEqual(plain(model.nextSort(model.DEFAULT_SORT, "goals")), { key: "goals", dir: "desc" });
  assert.deepEqual(plain(model.nextSort({ key: "goals", dir: "desc" }, "goals")), { key: "goals", dir: "asc" });
  assert.deepEqual(plain(model.nextSort(model.DEFAULT_SORT, "name")), { key: "name", dir: "asc" });
});

test("missing numbers and ratings are a dash, never 0", () => {
  assert.equal(model.statText(null), "—");
  assert.equal(model.statText(0), "0");
  assert.equal(model.ratingText(null), "—");
  assert.equal(model.ratingText("7.123"), "7.1");
  assert.equal(model.positionLabel(null), "—");
  assert.equal(model.positionLabel("Attacker"), "FW");
});

test("season rows keep missing parts as a dash", () => {
  const side = (home, away, total) => ({ home, away, total });
  const rows = model.seasonRows({
    wins: side(4, 3, 7), draws: side(0, 0, 0), loses: side(1, 1, 2),
    goalsFor: side(11, 9, 20), goalsAgainst: side(6, 4, 10), cleanSheets: side(1, 2, null),
    formation: null,
  });
  assert.deepEqual(plain(rows.map((r) => r.value)), ["20 / 10", "4승 0무 1패", "3승 0무 1패", "—", "—"]);
  assert.equal(model.standingText(null), "—");
  assert.equal(model.standingText({ rank: 2, points: 21 }), "2위 · 21점");
});

test("transfer wording: known provider types in Korean, others as given", () => {
  assert.equal(model.transferTypeText("Loan"), "임대");
  assert.equal(model.transferTypeText("Return from loan"), "임대 복귀");
  assert.equal(model.transferTypeText("€ 10M"), "€ 10M");
  assert.equal(model.transferTypeText(null), "—");
  assert.equal(model.notStartedText("2027-01-01"), "2027년 1월부터 집계됩니다.");
  assert.equal(model.seasonOf("last", 2026), 2025);
});

test("venue shows name and capacity, missing as 미제공", () => {
  assert.equal(model.venueText({ name: "Etihad Stadium", capacity: 55097 }), "Etihad Stadium · 55,097석");
  assert.equal(model.venueText(null), "미제공");
});
