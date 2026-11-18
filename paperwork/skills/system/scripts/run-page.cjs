#!/usr/bin/env node
// Open the page of each example contract in a headless Chromium, as file://, at 1024 by 768, 1440 by 900 and
// 1920 by 1080 pixels, and drive it as a person with a pointer and a keyboard would.
//
// usage: run-page.cjs [diagram] [overlay] [moves] [search] [tasks]
// With no word it runs the five steps; it prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or
// FAIL, and exits 1 on a failure and 2 on a word it does not know.
//   diagram  make-page.py builds each example's page and it equals the built page kept beside the contract; a
//            contract the checker refuses builds none; the relay page checker prints `follows`; each level fills the
//            window, draws each node as a rectangle with its label and tag, none over another, nothing outside the
//            window, each state inside its region, one anchor per node, edge and area; no console error, no request.
//   overlay  the pointer resting on a node, an edge and an area, and on one record per item form the examples hold,
//            shows an overlay with one row per item, each in its form, inside the window, over a third of it at
//            most, off the element under the pointer (an area's is its header); it stays under the pointer and
//            after a click, and Escape closes it.
//   moves    each scenario marks each step on the record it names, on that record's level, in 80 characters at
//            most, under controls of a tenth of the window at most, forward and back by the arrow keys; three
//            orders of a move down, a move up, a search hit and a scenario step that changes level are walked back
//            and forward by the browser's history and by the page's own keys, and each view's address opens it.
//   search   each query of fixtures/search-queries.json typed into its example's page: the wanted record is the
//            first hit for 17 in 20 and among the first three for 19 in 20, and first for 3 in 4 of the misspelt
//            queries and of those typed with the Korean layout left on.
//   tasks    each rebuild question an example answers is two tasks: from the first view, `/`, the question typed
//            whole or as the words of its id, an arrow per hit above the question or the first of its answers, Enter, and the view shows
//            that answer, the question's first when the hit is the question; a
//            question whose answers are not among the hits shown is walked instead, by a click per level opened
//            and one on the answer, after the search is closed. The score is the mean reciprocal rank of the first
//            such hit among the eight shown, over every record of the contract; it must be above, and the mean
//            moves a task below, those fixtures/task-scores.json holds for the same questions on the page it names.
//            Each row of that file with a `query` is the question as a writer who never saw the contract worded
//            it; the same score over those must be above the one the file holds for them.
// overlay and moves also read each transition: its timing is not linear, and it lasts no time under reduced motion.
// Playwright is loaded from /private/tmp/relay-playwright/node_modules/playwright-core and the browser is the
// newest headless shell Playwright installed, never an installed Google Chrome.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const PLAYWRIGHT = "/private/tmp/relay-playwright/node_modules/playwright-core";
const SIZES = [[1024, 768], [1440, 900], [1920, 1080]];
const STEPS = ["diagram", "overlay", "moves", "search", "tasks"];
const KINDS = ["exact", "initials", "misspelt", "two-fields", "id", "korean-layout"];
const asked = process.argv.slice(2);
if (asked.some((word) => !STEPS.includes(word))) {
  console.error("usage: run-page.cjs [diagram] [overlay] [moves] [search] [tasks]");
  process.exit(2);
}

const check = (condition, reason) => { if (!condition) throw new Error(reason); };
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "system-page-"));
const examples = fs.readdirSync(path.join(ROOT, "examples")).filter((name) => fs.existsSync(path.join(ROOT, "examples", name, "contract.json"))).sort()
  .map((name) => ({ name, source: path.join(ROOT, "examples", name, "contract.json"), kept: path.join(ROOT, "examples", name, "page.html"), built: path.join(scratch, name + ".html") }));
const tags = JSON.parse(fs.readFileSync(path.join(ROOT, "assets", "tags.json"), "utf8"));
const python = (script, ...args) => spawnSync("python3", [script, ...args], { encoding: "utf8" });

function browserBinary() {
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  return shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64/chrome-headless-shell") : null;
}

function build() {
  for (const example of examples) {
    const made = python(path.join(ROOT, "scripts", "make-page.py"), example.source, example.built);
    check(made.status === 0, `make-page.py refused ${example.name}: ${(made.stderr || "").split("\n")[0]}`);
    example.contract = JSON.parse(fs.readFileSync(example.built, "utf8").match(/<script type="application\/json" id="page-data">(.*)<\/script>/)[1]);
    example.levelOf = {};
    for (const level of example.contract.levels) {
      example.levelOf[level.id] = level.id;
      for (const kind of ["nodes", "edges", "areas"]) for (const record of level[kind] || []) example.levelOf[record.id] = level.id;
    }
    const names = {};
    for (const level of example.contract.levels) for (const node of level.nodes) names[node.id] = node.label;
    for (const level of example.contract.levels) for (const edge of level.edges || []) edge.shown = edge.label.replace(/\{([a-z0-9-]+)\}/g, (whole, id) => names[id] || whole);
  }
}

async function open(browser, example, size, options = {}) {
  const context = await browser.newContext({ viewport: { width: size[0], height: size[1] }, reducedMotion: options.still ? "reduce" : "no-preference" });
  const page = await context.newPage();
  page.faults = [];
  page.asked = [];
  page.on("console", (message) => message.type() === "error" && page.faults.push(message.text()));
  page.on("pageerror", (error) => page.faults.push(String(error)));
  page.on("request", (request) => { if (!request.url().startsWith("file://" + example.built)) page.asked.push(request.url()); });
  await page.goto("file://" + example.built + (options.at || ""));
  await rest(page);
  return page;
}
const rest = async (page) => {
  await page.waitForFunction(() => document.body.dataset.busy === "", null, { timeout: 5000 });
  await page.waitForTimeout(40);
};
const settled = async (page) => { await rest(page); await page.waitForTimeout(520); };
const view = (page) => page.evaluate(() => {
  const now = document.querySelector("#crumbs [aria-current]"), pinned = document.querySelector("#stage .pinned"), marked = document.querySelector("#stage .node.step, #stage .edge.step");
  const dots = [...document.querySelectorAll("#play .dots i")];
  return {
    address: location.hash, level: now ? now.dataset.level : null, pinned: pinned ? pinned.dataset.id || pinned.dataset.edge : null,
    playing: document.getElementById("play").classList.contains("show"), step: document.getElementById("play").classList.contains("show") ? dots.findIndex((dot) => dot.classList.contains("now")) : null, marked: marked ? marked.dataset.id : null,
  };
});
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---- diagram ----
async function diagram(browser) {
  for (const example of examples) {
    check(fs.existsSync(example.kept), `${example.name} keeps no built page`);
    check(fs.readFileSync(example.kept, "utf8") === fs.readFileSync(example.built, "utf8"), `${example.name}'s kept page differs from the one make-page.py builds`);
    const followed = python(path.resolve(ROOT, "..", "relay", "scripts", "check-page.py"), example.built);
    check(followed.status === 0 && followed.stdout.trim() === "follows", `the relay page checker says of ${example.name}: ${followed.stdout.trim().split("\n")[0]}`);
  }
  const refused = path.join(scratch, "refused.json"), unbuilt = path.join(scratch, "refused.html");
  const broken = JSON.parse(fs.readFileSync(examples[0].source, "utf8"));
  broken.edges[0].to = "no-such-node";
  fs.writeFileSync(refused, JSON.stringify(broken));
  check(python(path.join(ROOT, "scripts", "make-page.py"), refused, unbuilt).status === 1 && !fs.existsSync(unbuilt), "a contract the checker refuses built a page");
  for (const size of SIZES) for (const example of examples) {
    const page = await open(browser, example, size, { still: true });
    for (const level of example.contract.levels) {
      await page.goto("file://" + example.built + "#level=" + level.id);
      await rest(page);
      const fault = await page.evaluate((level) => {
        const box = (element) => element.getBoundingClientRect(), stage = document.getElementById("stage");
        const one = (id) => { const found = stage.querySelectorAll(`[data-id="${id}"]`); return found.length === 1 ? found[0] : null; };
        const inside = (rect, frame, slack = 0.5) => rect.left >= frame.left - slack && rect.top >= frame.top - slack && rect.right <= frame.right + slack && rect.bottom <= frame.bottom + slack;
        const whole = { left: 0, top: 0, right: innerWidth, bottom: innerHeight }, main = box(document.getElementById("diagram"));
        if (main.width * main.height < innerWidth * innerHeight * 0.8) return "the diagram covers under four fifths of the window";
        if (main.left > 0 || main.right < innerWidth) return "something sits beside the diagram";
        if (document.querySelector("nav:not(#crumbs), aside:not(#card)")) return "the page holds a menu or a panel";
        const rects = [];
        for (const node of level.nodes) {
          const card = one(node.id);
          if (!card) return `node ${node.id} has not one anchor`;
          const rect = box(card), style = getComputedStyle(card), name = card.querySelector("b");
          if (rect.width < 40 || rect.height < 20) return `node ${node.id} is not drawn`;
          if (parseFloat(style.borderTopLeftRadius) > Math.min(card.offsetWidth, card.offsetHeight) / 4 || style.clipPath !== "none") return `node ${node.id} is not a rectangle`;
          if (name.textContent !== node.label || name.scrollWidth > name.clientWidth) return `node ${node.id} does not show its whole label`;
          if (card.querySelector("small").textContent !== node.tag) return `node ${node.id} does not show its tag`;
          if (!inside(rect, whole)) return `node ${node.id} is outside the window`;
          for (const other of rects) if (rect.left < other.rect.right && other.rect.left < rect.right && rect.top < other.rect.bottom && other.rect.top < rect.bottom) return `node ${node.id} is over ${other.id}`;
          rects.push({ id: node.id, rect });
        }
        for (const area of level.areas || []) {
          const frame = one(area.id);
          if (!frame) return `area ${area.id} has not one anchor`;
          if (!inside(box(frame), whole)) return `area ${area.id} is outside the window`;
          if (!frame.textContent.includes(area.label) || !frame.textContent.includes(area.tag)) return `area ${area.id} does not show its label and tag`;
          for (const node of level.nodes) if (node.area === area.id && !inside(box(one(node.id)), box(frame))) return `node ${node.id} is outside its area ${area.id}`;
        }
        for (const edge of level.edges || []) {
          const drawn = one(edge.id);
          if (!drawn) return `edge ${edge.id} has not one anchor`;
          if (!inside(box(drawn.querySelector("path.line")), whole, 2)) return `edge ${edge.id} leaves the window`;
          const label = stage.querySelector(`.label[data-edge="${edge.id}"]`);
          if (!label || label.textContent !== edge.shown) return `edge ${edge.id} has no label`;
          if (!label.classList.contains("tucked") && !inside(box(label), whole)) return `the label of edge ${edge.id} is outside the window`;
        }
        return "";
      }, level);
      check(!fault, `${example.name} ${level.id} at ${size.join("x")}: ${fault}`);
    }
    check(!page.faults.length, `${example.name} at ${size.join("x")} wrote to the console: ${page.faults[0]}`);
    check(!page.asked.length, `${example.name} at ${size.join("x")} asked for ${page.asked[0]}`);
    await page.context().close();
  }
}

// ---- overlay ----
function rowsOf(record, kind) {
  return (kind === "edge" ? 1 : 0) + (record.purpose ? 1 : 0) + Object.keys(record.info || {}).length + (record.opens ? 1 : 0) + (record.evidence ? 1 : 0);
}
function targets(example) { // a node, an edge and an area, then one record per item form
  const picked = [], forms = new Set();
  const formOf = (kind, record, name) => { const items = ((tags[kind] || {})[record.tag] || { items: [] }).items.concat((tags.common || {})[kind] || []); const item = items.find((one) => one.name === name); return item ? item.form : null; };
  for (const level of example.contract.levels) for (const [kind, group] of [["node", level.nodes], ["edge", level.edges || []], ["area", level.areas || []]]) for (const record of group) {
    const held = Object.keys(record.info || {}).map((name) => formOf(kind, record, name)).filter((form) => form && !forms.has(form));
    const first = !picked.some((one) => one.kind === kind);
    if (!first && !held.length) continue;
    held.forEach((form) => forms.add(form));
    picked.push({ kind, id: record.id, level: level.id, rows: rowsOf(record, kind), forms: Object.keys(record.info || {}).map((name) => formOf(kind, record, name)).filter(Boolean) });
  }
  return picked;
}
async function point(page, target) { // where the pointer rests for a record
  return page.evaluate((target) => {
    const stage = document.getElementById("stage"), middle = (rect) => ({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom } });
    if (target.kind === "node") { const rect = stage.querySelector(`.node[data-id="${target.id}"]`).getBoundingClientRect(); return { ...middle(rect), x: rect.left + 30, y: rect.bottom - 8 }; }
    if (target.kind === "area") {
      const header = stage.querySelector(`.area[data-id="${target.id}"] > header`), rect = header.getBoundingClientRect();
      for (const share of [0.08, 0.2, 0.35, 0.5, 0.65, 0.8]) {
        const x = rect.left + rect.width * share, y = rect.top + rect.height / 2, under = document.elementFromPoint(x, y);
        if (under && under.closest(".area > header") === header) return { ...middle(rect), x, y };
      }
      return null;
    }
    const label = stage.querySelector(`.label[data-edge="${target.id}"]`);
    if (!label.classList.contains("tucked")) return middle(label.getBoundingClientRect());
    const line = stage.querySelector(`.edge[data-id="${target.id}"] path.line`), matrix = line.getScreenCTM(), long = line.getTotalLength();
    for (const share of [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.12, 0.88]) {
      const spot = line.getPointAtLength(long * share).matrixTransform(matrix), under = document.elementFromPoint(spot.x, spot.y), group = under && under.closest(".edge");
      if (group && group.dataset.id === target.id) return { x: spot.x, y: spot.y, rect: { left: spot.x - 4, top: spot.y - 4, right: spot.x + 4, bottom: spot.y + 4 } };
    }
    return null;
  }, target);
}
async function overlay(browser) {
  const still = await open(browser, examples[0], SIZES[1], { still: true });
  check(await still.evaluate(() => parseFloat(getComputedStyle(document.getElementById("card")).transitionDuration) === 0), "the overlay still moves under reduced motion");
  await still.context().close();
  // every picked record at the middle size, on two pages; the first node, edge and area at the other sizes
  const shares = examples.flatMap((example) => SIZES.flatMap((size) => size === SIZES[1]
    ? [0, 1].map((share) => ({ size, example, picked: targets(example).filter((target, i) => i % 2 === share) }))
    : [{ size, example, picked: ["node", "edge", "area"].map((kind) => targets(example).find((target) => target.kind === kind)).filter(Boolean) }]));
  await Promise.all(shares.filter((one) => one.picked.length).map(async ({ size, example, picked }) => {
    const page = await open(browser, example, size);
    const timing = await page.evaluate(() => { const style = getComputedStyle(document.getElementById("card")); return { curve: style.transitionTimingFunction, long: Math.max(...style.transitionDuration.split(",").map(parseFloat)) }; });
    check(timing.long > 0 && timing.curve.includes("cubic-bezier") && !timing.curve.includes("linear"), `the overlay's transition is ${timing.curve} over ${timing.long}s`);
    const probe = async (target) => {
      const where = `${example.name} ${target.kind} ${target.id} at ${size.join("x")}`;
      await page.goto("file://" + example.built + "#level=" + target.level);
      await settled(page);
      const spot = await point(page, target);
      check(spot, `${where}: no part of it is under the pointer`);
      await page.mouse.move(2, size[1] - 2);
      await page.mouse.move(spot.x, spot.y, { steps: 4 });
      await page.waitForFunction((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; }, target.id, { timeout: 8000 }).catch(() => { throw new Error(`${where}: no overlay came`); });
      await page.waitForTimeout(320);
      const seen = await page.evaluate(() => {
        const card = document.getElementById("card"), rect = card.getBoundingClientRect();
        const rows = [...card.querySelectorAll("dl > div")].map((row) => ({ form: row.dataset.form, list: !!row.querySelector("dd > ul"), nested: !!row.querySelector("dd ul ul"), columns: row.querySelectorAll("dd table th").length, code: !!row.querySelector("dd pre code") }));
        return { rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom }, rows, markup: card.querySelectorAll("dd script, dd style, dd img, dd iframe").length };
      });
      check(seen.rows.length === target.rows, `${where}: the overlay holds ${seen.rows.length} rows for ${target.rows} items`);
      for (const form of target.forms) check(seen.rows.some((row) => row.form === form), `${where}: no row is drawn as ${form}`);
      for (const row of seen.rows) {
        check(row.form !== "list" || row.list, `${where}: a list is not drawn as a list`);
        check(row.form !== "table" || row.columns > 0, `${where}: a table has no columns`);
        check(row.form !== "tree" || row.list, `${where}: a tree is not drawn as nested lists`);
        check(row.form !== "code" || row.code, `${where}: code is not in a code block`);
      }
      check(!seen.markup, `${where}: the overlay ran text as markup`);
      const card = seen.rect;
      check(card.left >= 0 && card.top >= 0 && card.right <= size[0] && card.bottom <= size[1], `${where}: the overlay leaves the window`);
      check((card.right - card.left) * (card.bottom - card.top) <= size[0] * size[1] / 3, `${where}: the overlay covers over a third of the window`);
      check(card.right <= spot.rect.left || spot.rect.right <= card.left || card.bottom <= spot.rect.top || spot.rect.bottom <= card.top, `${where}: the overlay covers what it describes`);
      const shown = () => page.evaluate((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; }, target.id);
      const inside = [(card.left + card.right) / 2, (card.top + card.bottom) / 2];
      await Promise.all([page.mouse.move((spot.x + inside[0]) / 2, (spot.y + inside[1]) / 2), page.mouse.move(...inside)]);
      await page.waitForTimeout(450);
      check(await shown(), `${where}: the overlay left when the pointer moved into it`);
      await page.mouse.move(spot.x, spot.y, { steps: 6 });
      await page.mouse.click(spot.x, spot.y);
      await rest(page);
      await page.mouse.move(2, size[1] - 2, { steps: 4 });
      await page.waitForTimeout(450);
      check(await shown(), `${where}: the overlay closed after a click kept it`);
      await page.keyboard.press("Escape");
      await rest(page);
      await page.waitForTimeout(120);
      check(!(await page.evaluate(() => document.getElementById("card").classList.contains("show"))), `${where}: Escape left the overlay open`);
    };
    for (const target of picked) await probe(target).catch(() => probe(target)); // a busy machine can miss the pointer's timing once
    check(!page.faults.length, `${example.name} at ${size.join("x")} wrote to the console: ${page.faults[0]}`);
    await page.context().close();
  }));
}

// ---- moves ----
async function scenarios(browser, example, size, most) {
  const page = await open(browser, example, size, { still: true });
  for (const scenario of (example.contract.scenarios || []).slice(0, most)) {
    const where = `${example.name} scenario ${scenario.id} at ${size.join("x")}`;
    await page.goto("file://" + example.built);
    await rest(page);
    await page.click("#scenarios");
    await page.click(`#hits [data-hit="${scenario.id}"]`);
    await rest(page);
    const order = scenario.steps.map((step, i) => i).concat(scenario.steps.map((step, i) => i).reverse().slice(1));
    for (let turn = 0; turn < order.length; turn++) {
      const i = order[turn], step = scenario.steps[i];
      if (turn) { await page.keyboard.press(turn < scenario.steps.length ? "ArrowRight" : "ArrowLeft"); await rest(page); }
      const seen = await page.evaluate((at) => {
        const marked = [...document.querySelectorAll("#stage .node.step, #stage .edge.step, #stage .area.step")].map((element) => element.dataset.id);
        const area = (id) => { const rect = document.getElementById(id).getBoundingClientRect(); return document.getElementById(id).classList.contains("show") ? rect.width * rect.height : 0; };
        const token = document.getElementById("token");
        return { marked, level: document.body.dataset.level, step: +document.body.dataset.step, words: document.getElementById("chip").textContent.length, controls: area("play") + area("chip"), runs: !!token && token.classList.contains("run"), edge: !!document.querySelector(`#stage .edge[data-id="${at}"]`) };
      }, step.at);
      check(seen.step === i, `${where}: the key left it at step ${seen.step}, not ${i}`);
      check(seen.level === example.levelOf[step.at], `${where} step ${i}: on level ${seen.level}, not ${example.levelOf[step.at]}`);
      check(seen.marked.length === 1 && seen.marked[0] === step.at, `${where} step ${i}: marks ${seen.marked.join(",") || "nothing"}, not ${step.at}`);
      check(seen.words <= 80, `${where} step ${i}: shows ${seen.words} characters`);
      check(seen.controls <= size[0] * size[1] / 10, `${where} step ${i}: its controls cover over a tenth of the window`);
      check(!seen.edge || seen.runs, `${where} step ${i}: no mark moves along the edge`);
    }
  }
  check(!page.faults.length, `${example.name} wrote to the console: ${page.faults[0]}`);
  await page.context().close();
}
async function mixed(browser, example, size, order) {
  const page = await open(browser, example, size, { still: true });
  const contract = example.contract, where = `${example.name} ${order.join(">")} at ${size.join("x")}`;
  const crossing = (contract.scenarios || []).find((scenario) => new Set(scenario.steps.map((step) => example.levelOf[step.at])).size > 1);
  check(crossing, `${example.name} holds no scenario that changes level`);
  const deep = contract.levels[contract.levels.length - 1].nodes[0];
  const views = [await view(page)];
  const note = async () => { await rest(page); const now = await view(page); if (now.address !== views[views.length - 1].address) views.push(now); };
  const moves = {
    down: async () => {
      if (!(await page.$("#stage .node .open"))) { await page.click("#crumbs button"); await note(); }
      await page.mouse.move(2, size[1] - 2); await rest(page); // off the diagram, so no overlay lies over the button
      await page.click("#stage .node .open"); await note();
    },
    up: async () => {
      if ((await page.$$("#crumbs button")).length < 2) await moves.down();
      const path = await page.$$("#crumbs button");
      await path[path.length - 2].click(); await note();
    },
    search: async () => {
      await page.keyboard.press("/");
      await page.keyboard.type(deep.label);
      await page.waitForSelector(`#hits [data-hit="${deep.id}"]`);
      await page.click(`#hits [data-hit="${deep.id}"]`); await note();
      check((await view(page)).pinned === deep.id, `${where}: the search hit ${deep.id} is not picked`);
    },
    step: async () => {
      await page.click("#scenarios");
      await page.click(`#hits [data-hit="${crossing.id}"]`); await note();
      const first = example.levelOf[crossing.steps[0].at];
      for (let i = 1; i < crossing.steps.length; i++) {
        await page.keyboard.press("ArrowRight"); await note();
        if (example.levelOf[crossing.steps[i].at] !== first) break;
      }
      check((await view(page)).level !== first, `${where}: the scenario step changed no level`);
    },
  };
  for (const move of order) await moves[move]();
  check(views.length > order.length, `${where}: ${views.length} views after ${order.length} moves`);
  const walk = async (label, back, forward) => {
    for (let i = views.length - 2; i >= 0; i--) { await back(); await rest(page); const now = await view(page); check(same(now, views[i]), `${where}: ${label} back shows ${JSON.stringify(now)}, not ${JSON.stringify(views[i])}`); }
    for (let i = 1; i < views.length; i++) { await forward(); await rest(page); const now = await view(page); check(same(now, views[i]), `${where}: ${label} forward shows ${JSON.stringify(now)}, not ${JSON.stringify(views[i])}`); }
  };
  await walk("the browser's history", () => page.goBack(), () => page.goForward());
  await walk("the page's keys", () => page.keyboard.press("["), () => page.keyboard.press("]"));
  check(!page.faults.length, `${where} wrote to the console: ${page.faults[0]}`);
  await page.context().close();
  for (const kept of views) {
    const fresh = await open(browser, example, size, { still: true, at: kept.address });
    const now = await view(fresh);
    check(same(now, kept), `${where}: the address ${kept.address} opens ${JSON.stringify(now)}, not ${JSON.stringify(kept)}`);
    await fresh.context().close();
  }
}
async function moves(browser) {
  const moving = await open(browser, examples[0], SIZES[1]);
  const timing = await moving.evaluate(() => {
    const stage = getComputedStyle(document.getElementById("stage")), token = [...document.styleSheets].flatMap((sheet) => [...sheet.cssRules]).find((rule) => rule.selectorText === "#token.run");
    return { level: stage.transitionTimingFunction, long: Math.max(...stage.transitionDuration.split(",").map(parseFloat)), step: token ? token.style.animation : "" };
  });
  check(timing.long > 0 && timing.level.includes("cubic-bezier") && !timing.level.includes("linear"), `a level move's transition is ${timing.level} over ${timing.long}s`);
  check(/var\(--ease\)|cubic-bezier/.test(timing.step) && !timing.step.includes("linear"), `a scenario step's mark moves as ${timing.step || "nothing"}`);
  await moving.context().close();
  const still = await open(browser, examples[0], SIZES[1], { still: true });
  const stopped = await still.evaluate(() => {
    const token = document.getElementById("token");
    token.classList.add("run");
    return [getComputedStyle(document.getElementById("stage")).transitionDuration, getComputedStyle(token).animationDuration].every((value) => value.split(",").every((one) => parseFloat(one) === 0));
  });
  check(stopped, "a level move or a scenario step still moves under reduced motion");
  await still.context().close();
  await Promise.all(SIZES.flatMap((size) => examples.map((example) => scenarios(browser, example, size, size === SIZES[1] ? Infinity : 1)))
    .concat(examples.flatMap((example) => [["down", "search", "up", "step"], ["search", "step", "down", "up"], ["step", "up", "search", "down"]].map((order) => mixed(browser, example, SIZES[1], order)))));
}

// ---- search ----
async function search(browser) {
  const queries = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures", "search-queries.json"), "utf8"));
  check(queries.length >= 40, `the query file holds ${queries.length} queries`);
  for (const kind of KINDS) for (const typed of ["whole", "half"]) check(queries.some((query) => query.kind === kind && query.typed === typed), `the query file holds no ${kind} query typed ${typed}`);
  const pages = {};
  for (const example of examples) pages[example.name] = await open(browser, example, SIZES[1], { still: true });
  const tally = {}, count = (name, hit) => { tally[name] = tally[name] || { hit: 0, of: 0 }; tally[name].of += 1; tally[name].hit += hit ? 1 : 0; };
  const missed = [];
  for (const query of queries) {
    const page = pages[query.example];
    check(page && examples.find((example) => example.name === query.example).levelOf[query.wants] !== undefined || (page && JSON.stringify(examples.find((example) => example.name === query.example).contract).includes(`"id": "${query.wants}"`)) || (page && JSON.stringify(examples.find((example) => example.name === query.example).contract).includes(`"id":"${query.wants}"`)), `the query ${query.query} wants ${query.wants}, which ${query.example} does not hold`);
    await page.keyboard.press("/");
    await page.keyboard.insertText(query.query);
    await page.waitForTimeout(30);
    const hits = await page.evaluate(() => [...document.querySelectorAll("#hits [data-hit]")].map((row) => row.dataset.hit));
    await page.keyboard.press("Escape");
    const place = hits.indexOf(query.wants);
    count("first", place === 0); count("three", place >= 0 && place < 3); count(query.kind, place === 0);
    if (place !== 0) missed.push(`${query.query} (${query.kind}) wants ${query.wants}, got ${hits.slice(0, 3).join(",") || "nothing"}`);
  }
  for (const page of Object.values(pages)) await page.context().close();
  const share = (name) => tally[name].hit / tally[name].of;
  const line = `first ${tally.first.hit}/${tally.first.of}, in three ${tally.three.hit}/${tally.three.of}, misspelt ${tally.misspelt.hit}/${tally.misspelt.of}, korean-layout ${tally["korean-layout"].hit}/${tally["korean-layout"].of}`;
  console.log(line);
  for (const miss of missed) console.log("  " + miss);
  check(share("first") >= 17 / 20 && share("three") >= 19 / 20 && share("misspelt") >= 3 / 4 && share("korean-layout") >= 3 / 4, line);
}

// ---- tasks ----
async function task(page, example, question, typed) {
  const contract = example.contract, names = {};
  for (const level of contract.levels) for (const node of level.nodes.concat(level.areas || [])) names[node.id] = node.label;
  const shows = async (id) => { const hash = (await view(page)).address; return [`level=${id}`, `at=${id}`, `scenario=${id}`].some((part) => hash.split(/[#&]/).includes(part)); };
  await page.keyboard.press("/");
  await page.keyboard.insertText(typed || question.asks.replace(/\{([a-z0-9-]+)\}/g, (whole, id) => names[id] || "").replace(/`/g, ""));
  await page.waitForTimeout(30);
  const hits = await page.evaluate(() => [...document.querySelectorAll("#hits [data-hit]")].map((row) => row.dataset.hit));
  const place = hits.findIndex((hit) => hit === question.id || question.answers.includes(hit));
  if (place >= 0) {
    for (let i = 0; i < place; i++) await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await rest(page);
    const led = hits[place] === question.id ? question.answers[0] : hits[place];
    check(await shows(led), `${example.name} ${question.id}: the hit ${hits[place]} does not show ${led}`);
    return { place, moves: 3 + place, hits };
  }
  await page.keyboard.press("Escape");
  await page.goto("file://" + example.built + "#"); // a walk starts at the first view; a search starts anywhere
  await page.reload();
  await rest(page);
  const openers = {};
  for (const level of contract.levels) for (const node of level.nodes) if (node.opens) openers[node.opens] = node.id;
  const depth = (id) => { let level = example.levelOf[id], count = 0; while (openers[level]) { level = example.levelOf[openers[level]]; count += 1; } return count; };
  const nodes = question.answers.filter((id) => names[id] && contract.levels.some((level) => level.nodes.some((node) => node.id === id))).sort((a, b) => depth(a) - depth(b));
  const listed = question.answers.find((id) => (contract.scenarios || []).concat(contract.properties || []).some((record) => record.id === id));
  check(nodes.length || listed, `${example.name} ${question.id}: no answer is a node, a scenario or a property to walk to`);
  if (!nodes.length || (listed && depth(nodes[0]) > 0)) {
    await page.click((contract.scenarios || []).some((record) => record.id === listed) ? "#scenarios" : "#properties");
    await page.click(`#hits [data-hit="${listed}"]`);
    await rest(page);
    check(await shows(listed), `${example.name} ${question.id}: the listed ${listed} is not the view shown`);
    return { place: null, moves: 5, hits };
  }
  const way = [];
  for (let level = example.levelOf[nodes[0]]; openers[level]; level = example.levelOf[openers[level]]) way.unshift(openers[level]);
  for (const opener of way) { await page.click(`#stage .node[data-id="${opener}"] .open`); await rest(page); }
  await page.click(`#stage .node[data-id="${nodes[0]}"]`, { position: { x: 6, y: 6 } });
  await rest(page);
  check(await shows(nodes[0]), `${example.name} ${question.id}: the node ${nodes[0]} walked to is not the view shown`);
  return { place: null, moves: 3 + way.length + 1, hits };
}
async function tasks(browser) {
  const kept = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures", "task-scores.json"), "utf8"));
  await Promise.all(examples.map(async (example) => {
    const page = await open(browser, example, SIZES[1], { still: true });
    const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length, gain = (place) => (place === null ? 0 : 1 / (place + 1));
    const now = {}, before = Object.fromEntries(kept.filter((row) => row.example === example.name).map((row) => [row.task, row]));
    for (const question of (example.contract.questions || []).filter((one) => one.answers)) for (const short of [false, true]) now[question.id + (short ? " short" : "")] = await task(page, example, question, short && question.id.replace(/-/g, " "));
    for (const row of Object.values(before).filter((one) => one.query)) now[row.task] = await task(page, example, example.contract.questions.find((one) => one.id === row.task.split(" ")[0]), row.query);
    check(!page.faults.length, `${example.name} wrote to the console: ${page.faults[0]}`);
    await page.context().close();
    example.tasks = now;
    const shared = Object.keys(now).filter((id) => before[id] && !before[id].query), reworded = Object.keys(now).filter((id) => before[id] && before[id].query);
    check(shared.length >= 10, `${example.name}: fixtures/task-scores.json holds ${shared.length} of its questions`);
    const score = mean(shared.map((id) => gain(now[id].place))), was = mean(shared.map((id) => gain(before[id].place)));
    const count = mean(shared.map((id) => now[id].moves)), counted = mean(shared.map((id) => before[id].moves));
    const line = `${example.name}: ${shared.length} tasks, mean reciprocal rank of the question or its first answer among the 8 hits shown, typed whole and as its id's words, ${score.toFixed(2)} (${kept[0].page} ${was.toFixed(2)}), ${count.toFixed(1)} moves a task (${kept[0].page} ${counted.toFixed(1)})`;
    const worded = mean(reworded.map((id) => gain(now[id].place))), once = mean(reworded.map((id) => gain(before[id].place)));
    const said = `${example.name}: ${reworded.length} tasks typed in a reader's words, the same rank ${worded.toFixed(2)} (${before[reworded[0]].page} ${once.toFixed(2)})`;
    console.log([line, said].concat(shared.concat(reworded).filter((id) => now[id].place !== 0).map((id) => `  ${id} wants ${example.contract.questions.find((one) => one.id === id.split(" ")[0]).answers.join(",")}, got ${now[id].hits.slice(0, 3).join(",") || "nothing"}`)).join("\n"));
    check(score > was && count < counted, line);
    check(reworded.length >= 5 && worded > once, said);
  }));
}

async function main() {
  const binary = browserBinary();
  if (!fs.existsSync(path.join(PLAYWRIGHT, "package.json")) || !binary || !fs.existsSync(binary)) {
    console.log("FAIL setup: install playwright-core into /private/tmp/relay-playwright and its chromium-headless-shell");
    return 1;
  }
  let failed = 0, browser = null;
  try {
    build();
    browser = await require(PLAYWRIGHT).chromium.launch({ executablePath: binary });
    const steps = { diagram, overlay, moves, search, tasks };
    for (const name of asked.length ? asked : STEPS) { // one step at a time, since pages that share a busy machine miss the pointer's timing
      const started = Date.now(), line = await steps[name](browser).then(() => `PASS ${name}`, (error) => `FAIL ${name}: ${error.message.split("\n")[0]}`);
      failed += line.startsWith("FAIL");
      console.log(`${line} (${((Date.now() - started) / 1000).toFixed(1)} s)`);
    }
  } catch (error) {
    failed += 1;
    console.log(`FAIL setup: ${error.message.split("\n")[0]}`);
  } finally {
    if (browser) await browser.close();
    fs.rmSync(scratch, { recursive: true, force: true });
  }
  console.log(failed ? "FAIL" : "PASS");
  return failed ? 1 : 0;
}

main().then((code) => process.exit(code));
