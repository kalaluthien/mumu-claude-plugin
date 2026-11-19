#!/usr/bin/env node
// Open the page of each example contract in a headless Chromium, as file://, at 1024 by 768, 1440 by 900 and
// 1920 by 1080 pixels, and drive it as a person with a pointer and a keyboard would.
// Each page's timers run on a clock the run turns forward, so a step waits on the page and never sleeps.
//
// usage: run-page.cjs [diagram] [overlay] [fit] [clear] [moves] [changes] [search] [tasks] [sweep]
// With no word it runs the nine steps; it prints `PASS <step>` or `FAIL <step>: <reason>` per step with the
// step's seconds, then `PASS in <seconds> s` or `FAIL in <seconds> s` for the whole run, and exits 1 on a failure
// and 2 on a word it does not know.
//   diagram  make-page.py builds each example's page and it equals the built page kept beside the contract; a
//            contract the checker refuses builds none; the relay page checker prints `follows`; each level fills the
//            window, draws each node as a rectangle with its label and tag, none over another, nothing outside the
//            window, each state inside its region, one anchor per node, edge and area; no console error, no request.
//   overlay  the pointer resting on a node, an edge and an area, and on one record per item form the examples hold,
//            shows an overlay inside the window, over a third of it at most, off the element under the pointer (an
//            area's is its header), that scrolls nothing and counts the rows its later pages hold; it stays under
//            the pointer and after a click, which keeps it open with one row per item over its pages, each in its
//            form, and Escape closes it.
//   fit      on a copy of the first example whose first node cites an address of 300 characters with no break point,
//            that node's card has the same width and height under the pointer and kept, and no part of it reaches
//            past its sides.
//   clear    the pointer resting on each node of each example's levels raises a card that overlaps no node an edge
//            joins to that node.
//   moves    each scenario marks each step on the record it names, on that record's level, in 80 characters at
//            most, under controls of a tenth of the window at most, forward and back by the arrow keys; the
//            space key plays a scenario by itself and stops it, a step's button leads to that step, and the step
//            after the last offers the scenario again; a double click on a node that opens a level and on one
//            that opens none each adds one view to those the browser's back walks, printed as `a double click
//            adds one view`; three
//            orders of a move down, a move up, a search hit and a scenario step that changes level are walked back
//            and forward by the browser's history and by the page's own keys, and each view's address opens it.
//   changes  on a scratch copy of each example's contract one node no edge touches is planted, with a last step of
//            the first scenario that names it; then a node a scenario walks gets a new label, an edge a scenario
//            walks moves to another node of its level, and the planted node moves to another level. The checker
//            accepts the copy after each change, and the page built from it plays every scenario by the arrow
//            keys, each step on the level that now holds its record, the renamed node under its new label.
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
//   sweep    of the contracts in fixtures/ that the checker passes, the fewest it finds, four at most, that hold
//            between them every tag and every item form of the catalogue, a node no edge touches, a region of one
//            state and an `info` with no item, each taken for what it adds; each builds a page, and at 1440 by 900 each level draws as diagram asks, one overlay per item
//            form, kept by a click, shows its rows over its pages, each scenario plays to its last step on the page its levels opened and nothing
//            is written to the console; each empty shape the checker refuses is still refused. The step fails
//            when a page was sent to any address but each level's once or the run launched a second browser, and
//            unless it reports four faults it makes itself: a node's box removed, a form's rows removed, a console
//            error and a scenario a step short.
// overlay and moves also read each transition: its timing is not linear, and under reduced motion it only fades,
// each part hidden where it is shown; moves holds a level move part-way: no overlay rises until the level has arrived,
// and a move turned back goes on from the level still seen.
// The browser is the one ../../../lib/launch-browser.cjs starts.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const browsers = require(path.join(__dirname, "..", "..", "..", "lib", "launch-browser.cjs"));
const SIZES = [[1024, 768], [1440, 900], [1920, 1080]];
const STEPS = ["diagram", "overlay", "fit", "clear", "moves", "changes", "search", "tasks", "sweep"];
const REFUSED = ["area-known-no-node", "form-level-without-node", "form-empty-steps", "info-form-empty-code", "info-form-empty-list", "info-form-empty-text"]; // empty shapes no page has to draw, since the checker refuses them
const KINDS = ["exact", "initials", "misspelt", "two-fields", "id", "korean-layout"];
const asked = process.argv.slice(2);
if (asked.some((word) => !STEPS.includes(word))) {
  console.error("usage: run-page.cjs " + STEPS.map((word) => `[${word}]`).join(" "));
  process.exit(2);
}

const check = (condition, reason) => { if (!condition) throw new Error(reason); };
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "system-page-"));
const examples = fs.readdirSync(path.join(ROOT, "examples")).filter((name) => fs.existsSync(path.join(ROOT, "examples", name, "contract.json"))).sort()
  .map((name) => ({ name, source: path.join(ROOT, "examples", name, "contract.json"), kept: path.join(ROOT, "examples", name, "page.html"), built: path.join(scratch, name + ".html") }));
const tags = JSON.parse(fs.readFileSync(path.join(ROOT, "assets", "tags.json"), "utf8"));
const python = (script, ...args) => spawnSync("python3", [script, ...args], { encoding: "utf8" });
const UNFOLD = "import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); from contract_copies import copies; print(json.dumps(dict(copies(pathlib.Path(sys.argv[2])))))";

let launches = 0;
const loads = []; // each address a page was sent to, so a step can count what it opened
const launch = () => { launches += 1; return browsers.launch(); };

function make(example) { // the page of one contract file, and what its page data says of each record
  const made = python(path.join(ROOT, "scripts", "make-page.py"), example.source, example.built);
  check(made.status === 0, `make-page.py refused ${example.name}: ${(made.stdout + made.stderr).split("\n")[0]}`);
  example.contract = JSON.parse(fs.readFileSync(example.built, "utf8").match(/<script type="application\/json" id="page-data">(.*)<\/script>/)[1]);
  example.levelOf = {};
  for (const level of example.contract.levels) {
    example.levelOf[level.id] = level.id;
    for (const kind of ["nodes", "edges", "areas"]) for (const record of level[kind] || []) example.levelOf[record.id] = level.id;
  }
  const names = {};
  for (const level of example.contract.levels) for (const node of level.nodes) names[node.id] = node.label;
  for (const level of example.contract.levels) for (const edge of level.edges || []) edge.shown = edge.label.replace(/\{([a-z0-9-]+)\}/g, (whole, id) => names[id] || whole);
  return example;
}
const build = (wanted) => wanted.forEach(make);

async function open(browser, example, size, options = {}) {
  const context = await browser.newContext({ viewport: { width: size[0], height: size[1] }, reducedMotion: options.still ? "reduce" : "no-preference" });
  const page = await context.newPage();
  page.faults = [];
  page.asked = [];
  page.on("console", (message) => message.type() === "error" && page.faults.push(message.text()));
  page.on("pageerror", (error) => page.faults.push(String(error)));
  page.on("request", (request) => { if (!request.url().startsWith("file://" + example.built)) page.asked.push(request.url()); });
  await page.clock.install(); // the page's timers then run on a clock a step can turn forward, so no step sleeps
  const go = page.goto.bind(page);
  page.goto = (address) => { loads.push(address); return go(address); };
  await page.goto("file://" + example.built + (options.at || ""));
  await rest(page);
  return page;
}
const rest = async (page) => { // a move under way is carried to its end, since what a step reads is where the page comes to rest
  await page.evaluate(() => document.getAnimations().forEach((one) => { try { one.finish(); } catch (error) { /* one that never ends has no end to reach */ } }));
  await page.waitForFunction(() => document.body.dataset.busy === "", null, { timeout: 5000 });
  await page.clock.fastForward(40);
};
const settled = async (page) => { await rest(page); await page.clock.fastForward(520); };
const view = (page) => page.evaluate(() => {
  const now = document.querySelector("#crumbs [aria-current]"), pinned = document.querySelector("#stage .pinned"), marked = document.querySelector("#stage .node.step, #stage .edge.step");
  const dots = [...document.querySelectorAll("#play .dots button")];
  return {
    address: location.hash, level: now ? now.dataset.level : null, pinned: pinned ? pinned.dataset.id || pinned.dataset.edge : null,
    playing: document.getElementById("play").classList.contains("show"), step: document.getElementById("play").classList.contains("show") ? dots.findIndex((dot) => dot.classList.contains("now")) : null, marked: marked ? marked.dataset.id : null,
  };
});
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// What is wrong with the level the page shows, or nothing: the one test of a level that diagram and sweep share.
const drawn = (page, level) => page.evaluate((level) => {
  const box = (element) => element.getBoundingClientRect(), stage = document.getElementById("stage");
  const words = (tag) => tag.replace(/[A-Z]/g, (letter) => " " + letter.toLowerCase()); // a tag is shown as the words its id joins
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
    if (name.textContent !== node.label || name.scrollWidth > name.clientWidth || box(name).top < rect.top || box(card.querySelector("small")).bottom > rect.bottom) return `node ${node.id} does not show its whole label`;
    if (card.querySelector("small").textContent !== words(node.tag)) return `node ${node.id} does not show its tag`;
    if (!inside(rect, whole)) return `node ${node.id} is outside the window`;
    for (const other of rects) if (rect.left < other.rect.right && other.rect.left < rect.right && rect.top < other.rect.bottom && other.rect.top < rect.bottom) return `node ${node.id} is over ${other.id}`;
    rects.push({ id: node.id, rect });
  }
  for (const area of level.areas || []) {
    const frame = one(area.id);
    if (!frame) return `area ${area.id} has not one anchor`;
    if (!inside(box(frame), whole)) return `area ${area.id} is outside the window`;
    if (!frame.textContent.includes(area.label) || !frame.textContent.includes(words(area.tag))) return `area ${area.id} does not show its label and tag`;
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

// ---- diagram ----
const CARDED = (id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; };
async function rested(page, target, size, where) { // the pointer comes from a corner to rest on TARGET until its overlay shows
  const spot = await point(page, target);
  check(spot, `${where}: no part of it is under the pointer`);
  await page.mouse.move(2, size[1] - 2);
  await page.mouse.move(spot.x, spot.y, { steps: 4 });
  await page.waitForFunction(CARDED, target.id, { timeout: 8000 }).catch(() => { throw new Error(`${where}: no overlay came`); });
  return spot;
}
async function searched(page, text) { // the hits the search lists for TEXT
  await page.keyboard.press("/");
  await page.keyboard.insertText(text);
  await page.clock.fastForward(30);
  return page.evaluate(() => [...document.querySelectorAll("#hits [data-hit]")].map((row) => row.dataset.hit));
}
const quiet = (page, where) => check(!page.faults.length, `${where} wrote to the console: ${page.faults[0]}`);
const grouped = (level) => [["node", level.nodes], ["edge", level.edges || []], ["area", level.areas || []]];

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
  await Promise.all(SIZES.flatMap((size) => examples.map(async (example) => {
    const page = await open(browser, example, size, { still: true });
    for (const level of example.contract.levels) {
      await page.goto("file://" + example.built + "#level=" + level.id);
      await rest(page);
      const fault = await drawn(page, level);
      check(!fault, `${example.name} ${level.id} at ${size.join("x")}: ${fault}`);
    }
    quiet(page, `${example.name} at ${size.join("x")}`);
    check(!page.asked.length, `${example.name} at ${size.join("x")} asked for ${page.asked[0]}`);
    await page.context().close();
  })));
}

// ---- overlay ----
function rowsOf(record, kind) {
  return (kind === "edge" ? 1 : 0) + (record.purpose ? 1 : 0) + Object.keys(record.info || {}).length + (record.opens ? 1 : 0) + (record.evidence ? 1 : 0);
}
const formOf = (kind, record, name) => { const items = ((tags[kind] || {})[record.tag] || { items: [] }).items.concat((tags.common || {})[kind] || []); const item = items.find((one) => one.name === name); return item ? item.form : null; };
function targets(example) { // a node, an edge and an area, then one record per item form
  const picked = [], forms = new Set();
  for (const level of example.contract.levels) for (const [kind, group] of grouped(level)) for (const record of group) {
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
const card = (page) => page.evaluate(() => { // the overlay as it stands: where it is, how each row is drawn and how many rows its later pages hold
  const card = document.getElementById("card"), rect = card.getBoundingClientRect(), turn = card.querySelector("footer .turn"), paged = turn ? turn.textContent.match(/(\d+) of (\d+)/) : null;
  const rows = [...card.querySelectorAll("dl > div")].map((row) => ({ form: row.dataset.form, list: !!row.querySelector("dd > ul"), nested: !!row.querySelector("dd ul ul"), columns: row.querySelectorAll("dd table th").length, code: !!row.querySelector("dd pre code") }));
  return { rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom }, rows, after: paged ? paged[2] - paged[1] : 0, scrolls: card.scrollHeight > card.clientHeight + 1, markup: card.querySelectorAll("dd script, dd style, dd img, dd iframe").length };
});
async function leaves(page, dropped = null) { // the kept overlay over its pages, turned by its More rows button; DROPPED is a form whose rows are taken out of each page before it is read
  const read = [];
  for (let leaf = 0; leaf < 12; leaf++) {
    if (dropped) await page.evaluate((form) => document.querySelectorAll(`#card dl > div[data-form="${form}"]`).forEach((row) => row.remove()), dropped);
    read.push(await card(page));
    if (!read[leaf].after) break;
    await page.click("#card .turn");
  }
  return { rects: read.map((one) => one.rect), rows: read.flatMap((one) => one.rows), markup: read.reduce((sum, one) => sum + one.markup, 0) };
}
function rowFault(seen, target) { // what is wrong with the rows a kept overlay shows for a record, or nothing
  if (seen.rows.length !== target.rows) return `the kept overlay holds ${seen.rows.length} rows for ${target.rows} items`;
  for (const form of target.forms) if (!seen.rows.some((row) => row.form === form)) return `no row is drawn as ${form}`;
  for (const row of seen.rows) {
    if (row.form === "list" && !row.list) return "a list is not drawn as a list";
    if (row.form === "table" && !row.columns) return "a table has no columns";
    if (row.form === "tree" && !row.list) return "a tree is not drawn as nested lists";
    if (row.form === "code" && !row.code) return "code is not in a code block";
  }
  return seen.markup ? "the kept overlay ran text as markup" : "";
}
async function overlay(browser) {
  const still = await open(browser, examples[0], SIZES[1], { still: true });
  check(await still.evaluate(() => !/transform|all/.test(getComputedStyle(document.getElementById("card")).transitionProperty)), "the overlay still moves under reduced motion");
  const shifts = await still.evaluate(() => ["card", "chip", "play", "palette"].filter((id) => { // a part that only fades stands hidden where it stands shown
    const part = document.getElementById(id), hidden = getComputedStyle(part).transform;
    part.classList.add("show");
    const shown = getComputedStyle(part).transform;
    part.classList.remove("show");
    return hidden !== shown;
  }));
  check(!shifts.length, `under reduced motion ${shifts.join(", ")} shifts as it shows`);
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
      const spot = await rested(page, target, size, where);
      await page.clock.fastForward(320);
      const framed = (box, what) => {
        check(box.left >= 0 && box.top >= 0 && box.right <= size[0] && box.bottom <= size[1], `${where}: ${what} leaves the window`);
        check((box.right - box.left) * (box.bottom - box.top) <= size[0] * size[1] / 3, `${where}: ${what} covers over a third of the window`);
      };
      const seen = await card(page);
      check(seen.rows.length + seen.after === target.rows, `${where}: the overlay holds ${seen.rows.length} rows and pages ${seen.after} for ${target.rows} items`);
      check(!seen.scrolls || seen.rows.length === 1, `${where}: the overlay scrolls inside`);
      check(!seen.markup, `${where}: the overlay ran text as markup`);
      const box = seen.rect;
      framed(box, "the overlay");
      check(box.right <= spot.rect.left || spot.rect.right <= box.left || box.bottom <= spot.rect.top || spot.rect.bottom <= box.top, `${where}: the overlay covers what it describes`);
      const shown = () => page.evaluate(CARDED, target.id);
      const inside = [(box.left + box.right) / 2, (box.top + box.bottom) / 2];
      await Promise.all([page.mouse.move((spot.x + inside[0]) / 2, (spot.y + inside[1]) / 2), page.mouse.move(...inside)]);
      await page.clock.fastForward(450);
      check(await shown(), `${where}: the overlay left when the pointer moved into it`);
      await page.mouse.move(spot.x, spot.y, { steps: 6 });
      await page.mouse.click(spot.x, spot.y);
      await rest(page);
      await page.mouse.move(2, size[1] - 2, { steps: 4 });
      await page.clock.fastForward(450);
      check(await shown(), `${where}: the overlay closed after a click kept it`);
      const kept = await leaves(page);
      for (const rect of kept.rects) framed(rect, "the kept overlay");
      const wrong = rowFault(kept, target);
      check(!wrong, `${where}: ${wrong}`);
      await page.keyboard.press("Escape");
      await rest(page);
      await page.clock.fastForward(120);
      check(!(await page.evaluate(() => document.getElementById("card").classList.contains("show"))), `${where}: Escape left the overlay open`);
    };
    for (const target of picked) await probe(target).catch(() => probe(target)); // a busy machine can miss the pointer's timing once
    quiet(page, `${example.name} at ${size.join("x")}`);
    await page.context().close();
  }));
}

// ---- fit and clear ----
const LONG = "https://example.com/" + "a".repeat(280); // an address of 300 characters with no point to break it at
const HEADER = "column-" + "b".repeat(53); // a table header of 60 characters with no point to break it at
const carded = (page, id) => page.waitForFunction((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; }, id, { timeout: 8000 });
async function hoverNode(page, id, size) { // the pointer brought onto a node, and the card it raises come to rest
  const find = () => page.evaluate((id) => { // a point of the node's box that nothing drawn over it hides
    const element = document.querySelector(`#stage .node[data-id="${id}"]`), rect = element.getBoundingClientRect();
    for (const [x, y] of [[.5, .5], [.2, .8], [.8, .8], [.2, .2], [.8, .2], [.5, .9], [.5, .1]]) {
      const at = { x: rect.left + rect.width * x, y: rect.top + rect.height * y }, under = document.elementFromPoint(at.x, at.y);
      if (under && under.closest(".node") === element) return at;
    }
    return null;
  }, id);
  let spot = await find();
  if (!spot) { // the card of the last node hides it, so the pointer leaves until that card has gone
    await page.mouse.move(2, size[1] - 2);
    await page.clock.fastForward(450);
    await page.waitForFunction(() => !document.getElementById("card").classList.contains("show"), null, { timeout: 4000 });
    spot = await find();
  }
  check(spot, `no part of ${id} is under the pointer`);
  await page.mouse.move(spot.x, spot.y);
  await carded(page, id);
  await rest(page);
  return spot;
}
async function turnTo(page, text) { // the card's pages turned until one shows TEXT, as a person looking for it would
  for (let leaf = 0; leaf < 12; leaf++) {
    if (await page.evaluate((text) => document.getElementById("card").textContent.includes(text), text)) return true;
    if (!(await page.locator("#card .turn").count())) return false;
    await page.click("#card .turn");
    await rest(page);
  }
  return false;
}
const measure = (page) => page.evaluate(() => { // the card's box, the first part of it that reaches past its sides, whether it scrolls and whether its button lies outside it
  const card = document.getElementById("card"), rect = card.getBoundingClientRect(), turn = card.querySelector(".turn");
  const out = [...card.querySelectorAll("*")].find((part) => { const box = part.getBoundingClientRect(); return box.width && (box.left < rect.left - 0.5 || box.right > rect.right + 0.5); });
  return { rows: card.querySelectorAll("dl > div").length, width: rect.width, height: rect.height, out: out ? `${out.tagName.toLowerCase()} of ${Math.round(out.getBoundingClientRect().width)} px` : "", scrolls: card.scrollHeight > card.clientHeight + 1, lost: !!turn && turn.getBoundingClientRect().bottom > rect.bottom + 0.5 };
});
async function fit(browser) {
  const example = examples[0], flat = JSON.parse(fs.readFileSync(example.source, "utf8")), node = flat.nodes[0];
  flat.sources = (flat.sources || []).concat([{ id: "long-address", path: LONG, says: "an address with no break point" }]);
  node.evidence = ["long-address"];
  node.info = { ...(node.info || {}), failure: { columns: [HEADER, "what happens"], rows: [["a fault", "the run stops"]] } };
  const copy = { name: example.name + "-long", source: path.join(scratch, example.name + "-long.json"), built: path.join(scratch, example.name + "-long.html") };
  fs.writeFileSync(copy.source, JSON.stringify(flat));
  make(copy);
  await Promise.all(SIZES.map(async (size) => {
    const where = `${copy.name} ${node.id} at ${size.join("x")}`, page = await open(browser, copy, size, { at: "#level=" + node.level });
    const looks = async (state) => { // the card turned to the page of each long text, as it stands there
      const seen = [];
      for (const [text, what] of [[LONG, "the address"], [HEADER, "the long table header"]]) {
        check(await turnTo(page, text), `${where}: no page of the ${state} card shows ${what}`);
        const one = await measure(page);
        check(!one.out, `${where}: the ${state} card holds a ${one.out} wider than itself, on the page of ${what}`);
        check(!one.scrolls, `${where}: the ${state} card scrolls on the page of ${what}`);
        check(!one.lost, `${where}: the ${state} card's More rows button lies below it, on the page of ${what}`);
        seen.push(one);
      }
      return seen;
    };
    const spot = await hoverNode(page, node.id, size), hovered = await looks("hovered");
    await page.mouse.click(spot.x, spot.y);
    await page.mouse.move(2, size[1] - 2, { steps: 4 });
    await page.clock.fastForward(450);
    await rest(page);
    const kept = await looks("kept");
    hovered.forEach((one, i) => check(Math.abs(one.width - kept[i].width) < 0.5 && Math.abs(one.height - kept[i].height) < 0.5, `${where}: the hovered card is ${Math.round(one.width)} by ${Math.round(one.height)} px and the kept one ${Math.round(kept[i].width)} by ${Math.round(kept[i].height)}`));
    check(!page.faults.length, `${where}: the page wrote to the console: ${page.faults[0]}`);
    await page.context().close();
  }));
}
async function clear(browser) {
  const faults = [];
  const stress = (example, kind, change) => { // a copy of an example whose every node's card CHANGE makes long
    const flat = JSON.parse(fs.readFileSync(example.source, "utf8")), many = Array.from({ length: 59 }, (unused, i) => ({ id: `many-${i}`, path: `src/part-${i}.md`, says: "a source" }));
    flat.sources = (flat.sources || []).concat(many, [{ id: "long-address", path: LONG, says: "an address with no break point" }]);
    for (const node of flat.nodes) change(node, many.map((one) => one.id));
    const copy = { name: `${example.name}-${kind}`, source: path.join(scratch, `${example.name}-${kind}.json`), built: path.join(scratch, `${example.name}-${kind}.html`), stressed: true };
    fs.writeFileSync(copy.source, JSON.stringify(flat));
    return make(copy);
  };
  const stressed = examples.flatMap((example) => [
    stress(example, "tall", (node, many) => { node.purpose = Array(6).fill(node.purpose).join(" "); node.evidence = many.concat("long-address"); }), // rows taller than the room a card has
    stress(example, "wide", (node) => { node.evidence = ["long-address"]; node.info = { ...(node.info || {}), failure: { columns: [HEADER, "what happens"], rows: [["a fault", "the run stops"]] } }; }), // rows of text with no point to break at
  ]);
  const groups = examples.flatMap((example) => SIZES.map((size) => [example, size])).concat(stressed.map((example) => [example, SIZES[0]])).flatMap(([example, size]) => example.contract.levels.flatMap((level) => { // a page per 12 nodes, so a large level takes no longer than a small one
    const split = [];
    for (let i = 0; i < level.nodes.length; i += 12) split.push({ example, size, level, nodes: level.nodes.slice(i, i + 12) });
    return split;
  }));
  await Promise.all(groups.map(async ({ example, size, level, nodes }) => {
    const page = await open(browser, example, size, { at: "#level=" + level.id });
    await settled(page);
    for (const node of nodes) {
      const tied = [...new Set((level.edges || []).flatMap((edge) => edge.from === node.id ? [edge.to] : edge.to === node.id ? [edge.from] : []))].filter((id) => id !== node.id);
      if (!tied.length) continue;
      const came = await hoverNode(page, node.id, size).catch(() => hoverNode(page, node.id, size)).then(() => true, () => false); // a busy machine can miss the pointer's timing once
      if (!came) { faults.push(`${example.name} ${node.id} at ${size.join("x")} raises no card`); continue; }
      const covered = await page.evaluate((tied) => {
        const card = document.getElementById("card").getBoundingClientRect();
        return tied.filter((id) => {
          const element = document.querySelector(`#stage .node[data-id="${id}"]`), box = element && element.getBoundingClientRect();
          return box && Math.min(card.right, box.right) - Math.max(card.left, box.left) > 0.5 && Math.min(card.bottom, box.bottom) - Math.max(card.top, box.top) > 0.5;
        });
      }, tied);
      const room = covered.length && example.stressed && await page.evaluate(([id, tied]) => { // a long card is held to the rule only where some spot of the window would hold it clear
        const card = document.getElementById("card").getBoundingClientRect(), grow = (element, by) => { const box = element.getBoundingClientRect(); return { left: box.left - by, top: box.top - by, right: box.right + by, bottom: box.bottom + by }; };
        const walls = [grow(document.querySelector(`#stage .node[data-id="${id}"]`), 8), ...["tools", "crumbs"].map((bar) => grow(document.getElementById(bar), 8)), ...tied.map((one) => grow(document.querySelector(`#stage .node[data-id="${one}"]`), 4))];
        for (let x = 8; x <= innerWidth - card.width - 8; x += 4) for (let y = 8; y <= innerHeight - card.height - 8; y += 4) if (!walls.some((wall) => Math.min(x + card.width, wall.right) > Math.max(x, wall.left) && Math.min(y + card.height, wall.bottom) > Math.max(y, wall.top))) return true;
        return false;
      }, [node.id, tied]);
      if (covered.length && (!example.stressed || room)) faults.push(`${example.name} ${node.id} at ${size.join("x")} covers ${covered.join(", ")}`);
      for (let leaf = 0; example.stressed && leaf < 12; leaf++) { // each page of a long card holds its button and scrolls only round a row taller than the card
        const one = await measure(page);
        if (one.lost || one.scrolls && one.rows > 1) { faults.push(`${example.name} ${node.id} at ${size.join("x")} ${one.lost ? "puts its More rows button below the card" : "scrolls"} on page ${leaf + 1}`); break; }
        const turn = await page.locator("#card .turn").textContent().catch(() => "");
        const [, to, of] = turn.match(/(\d+) of (\d+)/) || [];
        if (!to || to === of) break;
        const pressed = await page.click("#card .turn", { timeout: 4000 }).then(() => "", (error) => error.message.split("\n").filter((line) => /not stable|detached|intercepts|outside/.test(line)).slice(-1)[0] || error.message.split("\n")[0]);
        if (pressed) { faults.push(`${example.name} ${node.id} at ${size.join("x")} lets no one press More rows on page ${leaf + 1}: ${pressed.trim()}`); break; }
        await rest(page);
      }
    }
    await page.context().close();
  }));
  check(!faults.length, `${faults.length} hover cards cover a node an edge joins to their own or page wrongly, as ${faults.slice(0, 3).join("; ")}`);
}

// ---- moves ----
async function scenarios(browser, example, size, walked, named = null, lent = null) { // NAMED is a node whose label is read, on a walk that only goes forward; LENT is a page already open, played on with no load
  const page = lent || await open(browser, example, size, { still: true });
  for (const scenario of walked) {
    const where = `${example.name} scenario ${scenario.id} at ${size.join("x")}`;
    if (lent) await page.keyboard.press("Escape"); // a lent page is opened once, so the play before is ended, not loaded away
    else await page.goto("file://" + example.built);
    await rest(page);
    await page.click("#scenarios");
    const listed = await page.textContent(`#hits [data-hit="${scenario.id}"]`);
    await page.click(`#hits [data-hit="${scenario.id}"]`);
    await rest(page);
    const titled = await page.textContent("#play .title");
    check(!/\{[a-z0-9-]+\}/.test(listed + titled), `${where}: its title names a record by its id in braces`);
    const order = scenario.steps.map((step, i) => i).concat(named ? [] : scenario.steps.map((step, i) => i).reverse().slice(1));
    for (let turn = 0; turn < order.length; turn++) {
      const i = order[turn], step = scenario.steps[i];
      if (turn) { await page.keyboard.press(turn < scenario.steps.length ? "ArrowRight" : "ArrowLeft"); await rest(page); }
      const seen = await page.evaluate(([at, named]) => {
        const marked = [...document.querySelectorAll("#stage .node.step, #stage .edge.step, #stage .area.step")].map((element) => element.dataset.id);
        const area = (id) => { const rect = document.getElementById(id).getBoundingClientRect(); return document.getElementById(id).classList.contains("show") ? rect.width * rect.height : 0; };
        const token = document.getElementById("token");
        const label = (id) => { // a node's label as drawn, or nothing when part of it lies outside its box
          const node = document.querySelector(`#stage .node[data-id="${id}"]`), name = node && node.querySelector("b");
          return name && name.scrollWidth <= name.clientWidth && name.getBoundingClientRect().top >= node.getBoundingClientRect().top && node.querySelector("small").getBoundingClientRect().bottom <= node.getBoundingClientRect().bottom ? name.textContent : null;
        };
        return { marked, level: document.body.dataset.level, step: +document.body.dataset.step, label: named && label(named.id), words: document.getElementById("chip").textContent.length, controls: area("play") + area("chip"), runs: !!token && token.classList.contains("run"), edge: !!document.querySelector(`#stage .edge[data-id="${at}"]`) };
      }, [step.at, named]);
      check(seen.step === i, `${where}: the key left it at step ${seen.step}, not ${i}`);
      if (named && seen.level === example.levelOf[named.id]) { check(seen.label === named.label, `${where} step ${i}: node ${named.id} reads ${seen.label}, not ${named.label}`); named.seen = true; }
      check(seen.level === example.levelOf[step.at], `${where} step ${i}: on level ${seen.level}, not ${example.levelOf[step.at]}`);
      check(seen.marked.length === 1 && seen.marked[0] === step.at, `${where} step ${i}: marks ${seen.marked.join(",") || "nothing"}, not ${step.at}`);
      check(named || seen.words <= 80, `${where} step ${i}: shows ${seen.words} characters`); // a note that names the renamed node holds its long new label
      check(seen.controls <= size[0] * size[1] / 10, `${where} step ${i}: its controls cover over a tenth of the window`);
      check(!seen.edge || seen.runs, `${where} step ${i}: no mark moves along the edge`);
    }
  }
  if (lent) return;
  quiet(page, example.name);
  await page.context().close();
}
async function plays(browser, example) { // a scenario that plays by itself, a step's own button and the step after the last
  const page = await open(browser, example, SIZES[1], { still: true });
  const scenario = example.contract.scenarios.reduce((short, one) => (one.steps.length < short.steps.length ? one : short)), last = scenario.steps.length - 1, where = `${example.name} scenario ${scenario.id}`;
  const step = () => page.evaluate(() => +document.body.dataset.step);
  await page.click("#scenarios");
  const listed = await page.textContent(`#hits [data-hit="${scenario.id}"]`);
  check(listed.includes(`${scenario.steps.length} steps`), `${where}: the list shows ${listed}, not its ${scenario.steps.length} steps`);
  await page.click(`#hits [data-hit="${scenario.id}"]`);
  await rest(page);
  await page.mouse.move(2, 2);
  check(await page.getByRole("button", { name: "Play" }).isVisible(), `${where}: no button is named Play`);
  await page.keyboard.press("Space");
  check((await step()) === 1 && (await page.getByRole("button", { name: "Pause" }).isVisible()), `${where}: the space key did not start the play at once`);
  if (last > 1) { await page.clock.fastForward(6000); check((await step()) === 2, `${where}: the play did not go on by itself`); }
  await page.keyboard.press("Space");
  const held = await step();
  await page.clock.fastForward(700);
  check((await step()) === held && (await page.getByRole("button", { name: "Play" }).isVisible()), `${where}: the space key did not stop the play`);
  await page.getByRole("button", { name: `Step ${last + 1}`, exact: true }).click();
  await rest(page);
  check((await step()) === last, `${where}: the button of step ${last + 1} led to step ${(await step()) + 1}`);
  check(!(await page.locator("#next").isDisabled()) && !(await page.locator("#again").isVisible()), `${where}: the last step already shows the end`);
  await page.keyboard.press("ArrowRight");
  await rest(page);
  const ended = await page.evaluate(() => ({ step: +document.body.dataset.step, marked: document.querySelectorAll("#stage .step").length, chip: document.getElementById("chip").classList.contains("show") }));
  check(ended.step === last + 1 && !ended.marked && !ended.chip, `${where}: after the last step the page shows ${JSON.stringify(ended)}`);
  check(await page.locator("#again").isVisible(), `${where}: the end offers no replay`);
  check((await page.locator("#onward").isVisible()) === (example.contract.scenarios.length > 1), `${where}: the end offers another scenario only when one exists`);
  const address = await page.evaluate(() => location.hash);
  const fresh = await open(browser, example, SIZES[1], { still: true, at: address });
  check(await fresh.locator("#again").isVisible(), `${where}: the address ${address} does not open the end`);
  await fresh.context().close();
  await page.click("#again");
  await rest(page);
  check((await step()) === 0, `${where}: Replay led to step ${(await step()) + 1}`);
  quiet(page, where);
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
  quiet(page, where);
  await page.context().close();
  for (const kept of views) {
    const fresh = await open(browser, example, size, { still: true, at: kept.address });
    const now = await view(fresh);
    check(same(now, kept), `${where}: the address ${kept.address} opens ${JSON.stringify(now)}, not ${JSON.stringify(kept)}`);
    await fresh.context().close();
  }
}
async function moves(browser) {
  const drawn = async (page) => { // the level move a click on a node's open button starts, and the mark of a scenario step
    await page.mouse.move(2, 2);
    await page.click("#stage .node .open");
    return page.evaluate(() => {
      const token = document.getElementById("token");
      token.classList.add("run");
      return { level: [document.getElementById("stage"), document.querySelector(".stage.old")].flatMap((stage) => (stage ? stage.getAnimations() : [])).map((one) => ({ curve: one.effect.getTiming().easing, long: one.effect.getTiming().duration, wait: one.effect.getTiming().delay, moves: one.effect.getKeyframes().some((frame) => "transform" in frame) })),
        step: { name: getComputedStyle(token).animationName, curve: getComputedStyle(token).animationTimingFunction } };
    });
  };
  const moving = await open(browser, examples[0], SIZES[1]);
  const timing = await drawn(moving);
  check(timing.level.length === 2 && timing.level.every((one) => one.long > 0 && one.moves && one.curve.includes("cubic-bezier")), `a level move is drawn as ${JSON.stringify(timing.level)}`);
  check(new Set(timing.level.map((one) => one.wait)).size === 2, "the level left and the level entered move at once, not one after the other");
  check(timing.step.curve.includes("cubic-bezier"), `a scenario step's mark moves as ${timing.step.curve}`);
  await moving.context().close();
  const turned = await open(browser, examples[0], SIZES[1]); // a level move held part-way, with the pointer on a node of the level arriving
  await turned.mouse.move(2, 2);
  const leave = () => turned.evaluate(() => {
    document.querySelector("#stage .node .open").click();
    document.getAnimations().forEach((one) => { one.pause(); one.currentTime = 140; });
    const node = document.querySelector("#stage .node");
    node.dispatchEvent(new PointerEvent("pointerover", { bubbles: true }));
    return { id: node.dataset.id, left: +getComputedStyle(document.querySelector(".stage.old")).opacity };
  });
  const carded = (id) => turned.evaluate(CARDED, id);
  const first = await turned.evaluate(() => document.body.dataset.level), entered = await leave();
  await turned.clock.fastForward(400);
  check(!(await carded(entered.id)), "an overlay rises over a level still arriving");
  await rest(turned);
  await turned.clock.fastForward(200);
  check(await carded(entered.id), "no overlay comes for the node under the pointer once its level has arrived");
  const home = async () => { await turned.keyboard.press("["); await turned.waitForFunction((level) => document.body.dataset.level === level, first); };
  await home();
  await rest(turned);
  const again = await leave();
  await home(); // turned back while the level left is half gone
  const resumed = await turned.evaluate(() => [document.getElementById("stage"), document.querySelector(".stage.old")].flatMap((stage) => (stage ? stage.getAnimations() : [])).map((one) => +one.effect.getKeyframes()[0].opacity));
  check(again.left > 0 && again.left < 1 && resumed.length > 0 && resumed.every((from) => Math.abs(from - again.left) < 0.05), `a move turned back with the level left at opacity ${again.left} goes on from opacity ${resumed.join(", ") || "nothing"}`);
  await turned.context().close();
  for (const example of examples) { // a double click on a node that opens a level and on one that opens none
    const first = example.contract.levels[0], opener = first.nodes.find((node) => node.opens), plain = first.nodes.find((node) => !node.opens);
    check(opener && plain, `${example.name} holds no node that opens a level, or none that opens none, on its first level`);
    for (const node of [opener, plain]) {
      const page = await open(browser, example, SIZES[1]), before = await view(page), views = await page.evaluate(() => history.length);
      const spot = await point(page, { kind: "node", id: node.id });
      await page.mouse.dblclick(spot.x, spot.y);
      await rest(page);
      const after = await view(page), added = (await page.evaluate(() => history.length)) - views;
      check(added === 1, `${example.name}: a double click on ${node.id} added ${added} views`);
      check(node.opens ? after.level === node.opens && !after.pinned : after.level === first.id && after.pinned === node.id, `${example.name}: a double click on ${node.id} shows ${JSON.stringify(after)}`);
      await page.goBack();
      await rest(page);
      check(same(await view(page), before), `${example.name}: one step back from a double click on ${node.id} shows ${JSON.stringify(await view(page))}`);
      await page.context().close();
    }
  }
  console.log("a double click adds one view");
  const still = await open(browser, examples[0], SIZES[1], { still: true });
  const stopped = await drawn(still);
  check(stopped.level.length === 2 && stopped.level.every((one) => !one.moves && one.long > 0 && one.long <= 500) && stopped.step.name === "appear", `under reduced motion a level move is ${JSON.stringify(stopped.level)} and a step's mark ${stopped.step.name}`);
  await still.context().close();
  await Promise.all(examples.map((example) => plays(browser, example)).concat(SIZES.flatMap((size) => examples.flatMap((example) => (size === SIZES[1] ? (example.contract.scenarios || []).map((scenario) => [scenario]) : [(example.contract.scenarios || []).slice(0, 1)]).map((walked) => scenarios(browser, example, size, walked))))
    .concat(examples.flatMap((example) => [["down", "search", "up", "step"], ["search", "step", "down", "up"], ["step", "up", "search", "down"]].map((order) => mixed(browser, example, SIZES[1], order))))));
}

// ---- changes ----
const PLANTED = "part-set-apart";
const RENAMED = "the part named anew, at a length no box holds on one line"; // longer than the widest node holds on one line, so the page must go on to a second
function changed(example) { // a copy of one example's contract that holds the planted node and the three changes, the checker asked after each
  const planted = JSON.parse(fs.readFileSync(example.source, "utf8"));
  check(planted.levels.length > 1 && (planted.scenarios || []).length, `${example.name} has one level or no scenario, so nothing can change under a scenario`);
  planted.nodes.push({ id: PLANTED, label: "the part set apart", tag: planted.nodes.find((node) => node.level === planted.levels[0].id).tag, level: planted.levels[0].id, purpose: "Stand on the level that asks about it." });
  planted.scenarios[0].steps.push({ at: PLANTED });
  const walked = new Set(planted.scenarios.flatMap((scenario) => scenario.steps.map((step) => step.at)));
  const levelOf = Object.fromEntries(planted.nodes.map((node) => [node.id, node.level]));
  const fixed = new Set((planted.properties || []).flatMap((item) => (item.paths || []).flat()));
  const renamed = planted.nodes.find((node) => node.id !== PLANTED && (walked.has(node.id) || planted.edges.some((edge) => walked.has(edge.id) && edge.to === node.id)));
  check(renamed, `${example.name}: no scenario walks a node`);
  const source = path.join(scratch, `${example.name}-changed.json`);
  const accepted = (contract) => { fs.writeFileSync(source, JSON.stringify(contract)); return python(path.join(ROOT, "scripts", "check-contract.py"), "check", source).status === 0; };
  check(accepted(planted), `${example.name}: the checker refuses the planted node`);
  planted.nodes.find((node) => node.id === renamed.id).label = RENAMED;
  check(accepted(planted), `${example.name}: the checker refuses node ${renamed.id} under a new label`);
  const ends = planted.edges.filter((edge) => walked.has(edge.id) && edge.tag !== "transition" && !fixed.has(edge.id)).flatMap((edge) => planted.nodes
    .filter((node) => node.level === levelOf[edge.from] && node.tag !== "state" && node.id !== edge.from && node.id !== edge.to && !planted.edges.some((other) => other.from === edge.from && other.to === node.id)).map((node) => [edge, node.id]));
  const moved = ends.find(([edge, end]) => { const old = edge.to; edge.to = end; return accepted(planted) || ((edge.to = old), false); }); // an end a rule of the contract forbids is passed over
  check(moved, `${example.name}: no edge a scenario walks can move to another node of its level`);
  planted.nodes.find((node) => node.id === PLANTED).level = planted.levels[1].id;
  check(accepted(planted), `${example.name}: the checker refuses the planted node on another level`);
  return { name: `${example.name} after its changes`, source, built: source.replace(/json$/, "html"), named: { id: renamed.id, label: RENAMED }, moved: { id: moved[0].id, to: moved[1] } };
}
async function changes(browser) {
  await Promise.all(examples.map(changed).map(async (copy) => {
    make(copy);
    const edge = copy.contract.levels.flatMap((level) => level.edges || []).find((one) => one.id === copy.moved.id);
    check(copy.contract.scenarios[0].steps.slice(-1)[0].at === PLANTED && copy.levelOf[PLANTED] === copy.contract.levels[1].id && edge.to === copy.moved.to, `${copy.name}: the page holds another contract than the changed one`);
    await Promise.all(copy.contract.scenarios.map((scenario) => scenarios(browser, copy, SIZES[1], [scenario], copy.named)));
    check(copy.named.seen, `${copy.name}: no step shows the level of ${copy.named.id}`);
  }));
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
    const holder = examples.find((example) => example.name === query.example);
    check(page && (holder.levelOf[query.wants] !== undefined || JSON.stringify(holder.contract).includes(`"id":"${query.wants}"`)), `the query ${query.query} wants ${query.wants}, which ${query.example} does not hold`);
    const hits = await searched(page, query.query);
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
  const hits = await searched(page, typed || question.asks.replace(/\{([a-z0-9-]+)\}/g, (whole, id) => names[id] || "").replace(/`/g, ""));
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
    quiet(page, example.name);
    await page.context().close();
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

// ---- sweep ----
async function sweep(browser) {
  const folder = path.join(ROOT, "fixtures"), checker = path.join(ROOT, "scripts", "check-contract.py"), size = SIZES[1];
  const rules = python(checker, "rules").stdout.split("\n").filter(Boolean).map((line) => line.split(":")[0]);
  const ruleOf = (name) => rules.find((rule) => name === rule || name.startsWith(rule + "-"));
  const unfolded = spawnSync("python3", ["-c", UNFOLD, path.join(ROOT, "..", "..", "lib"), folder], { encoding: "utf8" });
  check(unfolded.status === 0, `the fixtures' copies do not unfold: ${unfolded.stderr.trim().split("\n").pop()}`);
  const kept = JSON.parse(unfolded.stdout); // each contract of fixtures/ by name, unfolded as the checker unfolds it, so the sweep draws what the checker checked
  for (const name of REFUSED) check(ruleOf(name) && kept[name], `fixtures/ holds no ${name} named for a rule`);
  const replayed = python(checker, "fixtures"); // each fixture named for a rule breaks that rule alone, the refused shapes among them
  check(replayed.status === 0, `the checker's fixtures: ${replayed.stdout.split("\n").find((line) => line.startsWith("FAIL")) || "no verdict"}`);
  const brings = (contract) => { // what a contract gives the sweep to draw: its tags, the forms of its items and its empty shapes
    const found = new Set(), groups = { node: contract.nodes || [], edge: contract.edges || [], area: contract.areas || [] };
    for (const [kind, group] of Object.entries(groups)) for (const record of group) {
      found.add(`the ${kind} tag ${record.tag}`);
      for (const name of Object.keys(record.info || {})) found.add(`the form ${formOf(kind, record, name)}`);
      if (record.info && !Object.keys(record.info).length) found.add("an `info` with no item");
    }
    if (groups.node.some((node) => !groups.edge.some((edge) => edge.from === node.id || edge.to === node.id))) found.add("a node no edge touches");
    if (groups.area.some((area) => area.tag === "region" && groups.node.filter((node) => node.level === area.level && node.area === area.id).length === 1)) found.add("a region of one state");
    return found;
  };
  const passing = Object.keys(kept).filter((name) => !ruleOf(name)).sort().map((name) => {
    const source = path.join(scratch, "swept-" + name + ".json");
    fs.writeFileSync(source, JSON.stringify(kept[name]));
    return { name, source, built: source.replace(/json$/, "html"), brings: brings(kept[name]) };
  });
  const left = new Set(["node", "edge", "area"].flatMap((kind) => Object.keys(tags[kind]).map((tag) => `the ${kind} tag ${tag}`)).concat(tags.forms.map((form) => `the form ${form}`), ["a node no edge touches", "a region of one state", "an `info` with no item"]));
  const swept = [], adds = (example) => [...example.brings].filter((one) => left.has(one)).length;
  while (left.size && swept.length < 4) { // the contract that brings most of what is still to draw, so a new fixture never crowds the sweep
    const best = passing.filter((example) => !swept.includes(example)).sort((a, b) => adds(b) - adds(a))[0];
    if (!best || !adds(best)) break;
    swept.push(best);
    best.brings.forEach((one) => left.delete(one));
  }
  check(!left.size, `${swept.length < 4 ? "no contract the checker passes holds" : "four contracts the checker passes cannot hold"} ${[...left].join(", ")}`);
  build(swept);
  swept.sort((a, b) => Math.sign((a.contract.scenarios || []).length) - Math.sign((b.contract.scenarios || []).length)); // one with a scenario last, for the fault made on its page
  const held = { node: new Set(), edge: new Set(), area: new Set() }, forms = new Set(), before = loads.length, plays = [];
  const all = (kind) => swept.flatMap((example) => example.contract.levels.flatMap((level) => (level[kind] || []).map((record) => ({ ...record, level }))));
  const shapes = { // the empty shapes the checker passes, which a page must draw too
    "a node no edge touches": all("nodes").some((node) => !(node.level.edges || []).some((edge) => edge.from === node.id || edge.to === node.id)),
    "a region of one state": all("areas").some((area) => area.tag === "region" && area.level.nodes.filter((node) => node.area === area.id).length === 1),
    "an `info` with no item": ["nodes", "edges", "areas"].some((kind) => all(kind).some((record) => record.info && !Object.keys(record.info).length)),
  };
  for (const [shape, found] of Object.entries(shapes)) check(found, `no swept contract holds ${shape}`);
  const visit = async (example, level, page) => {
    const address = "#level=" + level.id;
    if (!page) return open(browser, example, size, { still: true, at: address });
    await page.goto("file://" + example.built + address);
    await rest(page);
    return page;
  };
  let page = null, missed = "the sweep made no fault of its own";
  for (const example of swept) {
    const wanted = targets(example).sort((a, b) => new Set(b.forms).size - new Set(a.forms).size); // the records of most forms first, so few overlays show them all
    page = null;
    for (const level of example.contract.levels) {
      const where = `${example.name} ${level.id}`;
      page = await visit(example, level, page);
      const fault = await drawn(page, level);
      check(!fault, `${where}: ${fault}`);
      for (const [kind, group] of grouped(level)) for (const record of group) held[kind].add(record.tag);
      for (const target of wanted.filter((one) => one.level === level.id)) {
        if (target.forms.every((form) => forms.has(form))) continue;
        const spot = await rested(page, target, size, `${where} ${target.id}`);
        await page.mouse.click(spot.x, spot.y); // a click keeps the overlay, which then shows every row over its pages
        await rest(page);
        const wrong = rowFault(await leaves(page), target);
        check(!wrong, `${where} ${target.id}: ${wrong}`);
        if (!forms.size) { // the first overlay, with the rows of one form taken out, must read as wrong
          if (await page.locator("#card .turn").count()) await page.click("#card .turn"); // from its last page round to its first
          missed = rowFault(await leaves(page, target.forms[0]), target) ? "" : "the sweep passes an overlay with a form's rows removed";
        }
        target.forms.forEach((form) => forms.add(form));
        await page.keyboard.press("Escape");
        await page.mouse.move(2, size[1] - 2);
        await rest(page);
      }
    }
    const shown = page; // its scenarios play on the page its levels opened, beside the next contract's levels
    plays.push(scenarios(browser, example, size, example.contract.scenarios || [], null, shown).then(() => {
      quiet(shown, example.name);
      check(!shown.asked.length, `${example.name} asked for ${shown.asked[0]}`);
      return example === swept[swept.length - 1] ? null : shown.context().close();
    }));
    plays[plays.length - 1].catch(() => {}); // read where all are awaited
  }
  await Promise.all(plays);
  check(!missed, missed);
  const last = swept[swept.length - 1], played = (last.contract.scenarios || [])[0];
  check(played, "no swept contract holds a scenario");
  const short = { ...last, contract: { ...last.contract, scenarios: [{ ...played, steps: played.steps.concat(played.steps.slice(-1)) }] } }; // one step more than the page holds
  const stopped = await scenarios(browser, short, size, short.contract.scenarios, null, page).then(() => "", (error) => error.message);
  check(stopped.includes(`step ${played.steps.length}: marks nothing`), `the sweep passes a scenario that stops a step early: ${stopped || "no fault"}`);
  await page.keyboard.press("Escape");
  await rest(page);
  const here = await page.evaluate(() => document.body.dataset.level), level = last.contract.levels.find((one) => one.id === here);
  const whole = await drawn(page, level);
  check(!whole, `${last.name} ${here} after its scenarios: ${whole}`);
  await page.evaluate((id) => document.querySelector(`#stage [data-id="${id}"]`).remove(), level.nodes[0].id);
  check(await drawn(page, level), "the sweep passes a level with a node's box removed");
  await page.evaluate(() => console.error("written by the sweep"));
  check(page.faults.length === 1, "the sweep passes a page that wrote an error to the console");
  await page.context().close();
  for (const kind of ["node", "edge", "area"]) for (const tag of Object.keys(tags[kind])) check(held[kind].has(tag), `no swept contract holds the ${kind} tag ${tag}`);
  for (const form of tags.forms) check(forms.has(form), `no swept overlay shows the form ${form}`);
  const levels = swept.reduce((sum, example) => sum + example.contract.levels.length, 0), went = loads.slice(before).sort();
  const due = swept.flatMap((example) => example.contract.levels.map((level) => "file://" + example.built + "#level=" + level.id)).sort();
  check(same(went, due), `the sweep opened ${went.length} addresses for ${levels} levels, each to be opened once`);
  check(launches === 1, `the run launched ${launches} browsers`);
  console.log(`${swept.map((example) => example.name).join(", ")} of ${passing.length} contracts the checker passes, ${levels} levels, ${forms.size} forms, ${swept.reduce((sum, example) => sum + (example.contract.scenarios || []).length, 0)} scenarios; refused by the checker and left out: ${REFUSED.join(", ")}`);
}

async function main() {
  if (browsers.missing()) {
    console.log(`FAIL setup: ${browsers.missing()}`);
    return 1;
  }
  let failed = 0, browser = null;
  try {
    const names = asked.length ? asked : STEPS;
    if (names.some((name) => name !== "sweep")) build(examples);
    browser = await launch();
    const steps = { diagram, overlay, fit, clear, moves, changes, search, tasks, sweep };
    for (const name of names) { // one step at a time, since pages that share a busy machine miss the pointer's timing
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
  console.log(`${failed ? "FAIL" : "PASS"} in ${process.uptime().toFixed(1)} s`);
  return failed ? 1 : 0;
}

main().then((code) => process.exit(code));
