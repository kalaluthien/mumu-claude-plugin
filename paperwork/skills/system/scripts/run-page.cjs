#!/usr/bin/env node
// Open the page of each example contract in a headless Chromium, as file://, at 1024 by 768, 1440 by 900 and
// 1920 by 1080 pixels, and drive it as a person with a pointer and a keyboard would.
// Each page's timers run on a clock the run turns forward, so a step waits on the page and never sleeps.
//
// usage: run-page.cjs [diagram] [shapes] [overlay] [fit] [clear] [moves] [changes] [search] [titles] [results] [regex] [ranking] [recent] [tasks] [sweep] [names] [glosses] [badges] [counts] [note] [formulas] [code] [tables] [layout] [wrap] [fonts]
// With no word it runs the twenty-six steps; it prints `PASS <step>` or `FAIL <step>: <reason>` per step with the
// step's seconds, then `PASS in <seconds> s` or `FAIL in <seconds> s` for the whole run, and exits 1 on a failure
// and 2 on a word it does not know.
//   diagram  make-page.py builds each example's page and it equals the built page kept beside the contract; a
//            contract the checker refuses builds none; the relay page checker prints `follows`; each level fills the
//            window, draws each node as a rectangle with its label and tag, none over another, nothing outside the
//            window, each state inside its region, one anchor per node, edge and area; no console error, no request;
//            no edge label shows a brace or a backtick and no card's address an unresolved `{record-id}` or a
//            backtick, printed as `<n> edge labels and <m> card addresses read, none with a brace or a backtick`; every
//            card row of a record whose contract text holds a backtick shows none, printed as `<k> card rows with a code
//            span read, none with a backtick`, the card's heading counted as a row; on a copy of the second example
//            whose every node label holds a code span, no crumb, scenario title, next-level
//            hint, step or open button tooltip or card heading shows a backtick, printed as `<j> titles, tooltips and
//            card headings read on a copy whose every label holds a code span, none with a backtick`.
//   shapes   at 1440 by 900, on every level of each example, in the light scheme, each `state` node's corners are 12 px
//            or more, each other node's 4 px or less but a `dataStore`'s, which curve its top and bottom across its
//            width under a drawn lid rim its label starts below, no button inside a node is rounder than the node, each
//            `region` and `trustZone` area has a dashed border and each other frame a solid one, and no text shows
//            beside the diagram but the crumbs and the tools, so no legend; each scenario step on a `state` or a
//            `dataStore`, each pick of one and the pointer resting on one mark its border, a data store's lid rim with it; in the light and the
//            dark scheme, on each example and on a copy of one whose level of the most frames has them all made lanes, each
//            `lane` and `phase` band shows no border and its name inside its top edge, and, read from its pixels, has
//            an oklch chroma of 0.015 to 0.045, a hue 45 degrees or more from the scenario mark's and an oklab distance
//            of 0.02 or more from the canvas and from the band before it by position, a hue 45 degrees or more from the
//            two bands before it, the fourth band of a level the
//            tint of the first; on that copy a card chip naming a lane of its own level, under the pointer, marks the
//            lane's name, at 4.5:1 or more on its fill, and the fill and draws no border round it, and one naming a region
//            marks its border, in light and
//            dark, printed as `named area: PASS` or `named area: FAIL, <reason>`; it prints one line per outcome.
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
//   moves    each scenario marks each step on the record it names, on that record's level, under controls of a
//            tenth of the window at most, forward and back by the arrow keys; the space key plays a scenario by itself and stops it, a step's button leads to that step, and the step
//            after the last offers the scenario again; a double click on a node that opens a level and on one
//            that opens none each adds one view to those the browser's back walks, printed as `a double click
//            adds one view`; three
//            orders of a move down, a move up, a search hit and a scenario step that changes level are walked back
//            and forward by the browser's history and by the page's own keys, and each view's address opens it.
//            At each size every step's note covers no lane header and no shown edge label, a step whose next record
//            is on another level names that level beside its controls, and a move down, back up, and down turned back
//            mid-way frames, part-way, the node the level entered grows from; these print as `<n> step notes at three sizes cover no lane header
//            and no shown edge label` and `<n> steps whose next record is on another level name that level, <m> level
//            moves frame the node they grow from`.
//   changes  on a scratch copy of each example's contract one node no edge touches is planted, with a last step of
//            the first scenario that names it; then a node a scenario walks gets a new label, an edge a scenario
//            walks moves to another node of its level, and the planted node moves to another level. The checker
//            accepts the copy after each change, and the page built from it plays every scenario by the arrow
//            keys, each step on the level that now holds its record, the renamed node under its new label.
//   search   each query of fixtures/search-queries.json typed into its example's page: the wanted record is the
//            first hit for 17 in 20 and among the first three for 19 in 20, and first for 3 in 4 of the misspelt
//            queries and of those typed with the Korean layout left on; an alias query, a word its contract holds only in
//            an alias, a Korean one among them, finds its record first, which names the field `matched alias`. On
//            page-changes `the zzqxv wobbly` shows the no-result state and `the zzqxv watcher` lists watcher first,
//            printed as `stop word: PASS`; a query picked in the regular expression mode comes back from the recent
//            queries after a reload with the mode on, and one kept as bare text with it off, printed as `regex recall: PASS`; a
//            text picked from plain, then from regex, leaves one recent row that comes back in regex mode, printed as `recent set: PASS`.
//   titles   on each example's page the Claims list shows each claim by its title, and a click on the first
//            claim's hit opens a card headed by that title; on a copy of the self example whose reader's purpose
//            names `{checker}` mid-sentence, the reader's card shows the label `Checker` there as written.
//   results  on each example's page a word only one node's purpose holds lists that node with an excerpt of its
//            purpose on its own line, the word marked and tinted, and its id's words show the name or the id marked; a word start, initials
//            and a misspelt word mark exactly the letters matched; Down, Down, Up names the second hit the input's
//            active option and Enter picks it, Escape closes; a query nothing matches restates itself with a hint;
//            and each query of the search step lists its hits within 50 ms of the page's main thread time on
//            page-changes, the largest example, in its fastest of up to five runs.
//   regex    the button and Alt+R turn the regular expression mode on and off, shown pressed; the whole input is
//            one pattern, case ignored, with no slips or initials; Enter on the focused button presses it; `watcher|flush` marks either word; a bad pattern
//            says `Not a regular expression` with its reason, in red in the light and dark schemes; the key line
//            names Alt+R and the pressed button looks pressed.
//   ranking  each query of fixtures/ranking-queries.json typed into its example's page; the mean reciprocal rank of
//            the wanted record among the eight hits shown is above the base's, from the place the file holds for
//            each query on paperwork-v0.14.13.
//   recent   nine queries each picked from on page-changes: the empty search lists the last eight, newest first,
//            above the questions, each with a clock; typing keeps those that start with it, the typed part plain
//            and the rest bold on one line, while the top record stays the chosen one, a recent query a move
//            away; one removed by Enter on its remove button stays gone after a reload; a copy of the page at another path in the
//            same browser lists none; a page whose storage throws keeps them for the tab.
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
//   names    on each example page a kept card's chip for a record its text names as `{id}` marks that record in the diagram, and
//            one for a record of a level below marks the node of the card's level that opens it, which one example at least holds;
//            an edge's sentence, an opener's opens row and an area's initial row name their records as chips.
//   glosses  on each example page the first match of each term in a kept card is marked once, and the pointer on it shows the
//            term's meaning; a click on a card's sources mark shows each cited source's path and what it says; on a copy of the
//            first example a term is marked capitalised and plural, its meaning draws its formula and code, and a step's
//            note marks no term, chip or guess, as no crumb or scenario title, a slug, can.
//   badges   on a copy of the first example, a text holding `(guess)` and a claim whose status is unknown or fails each show
//            a badge naming that state, and a claim that holds shows none.
//   counts   on a copy of the first example whose first level's first node holds five claims that hold, one named on it twice,
//            one with no status, one first on another level and one with a fault, one unknown, one conflicting and one that fails,
//            each edge of that level but the last one a claim that fails, and its first area one claim that holds, at each size in
//            light and dark, each node, edge and area of the level shows one badge per claim on it, its kind's initial, its status's
//            `✓`, `?`, `!` or `✗` and `*` for a claim that holds with a fault, a tucked label's badges still shown, and a record
//            with none shows none; a node's and an area's badges sit inside it, a node's clear of its name, tag and open button,
//            and an edge's within 16 px of its label; each fill keeps its status's hue at its least chroma, each pair 0.08 or more
//            apart in oklab, its text at 4.5:1 or more, printed as `count badges: PASS` or `count badges: FAIL, <reason>`; the
//            pointer on each badge of that node, of an edge, of that area and of each one whose label is tucked shows its record's
//            card listing each claim on it as a chip under `claims`, each once, and a click on the badge keeps its claim's card on
//            the level of the first record the claim names; a click on each chip shows that claim's card headed by its title on
//            that level, still so once the pointer has rested where it clicked, and so when a pointer resting on the chip
//            since its page loaded clicks it unmoved and shakes 1 px, and while the pointer has moved 2 px or less from there no
//            record it comes over raises a card, though one moved 2.5 px does; and with the node's card kept, each badge of a
//            record dimmed around it shows at 0.75 opacity or less, the node's own at full, printed as `count lists: PASS` or
//            `count lists: FAIL, <reason>`.
//   note     on each example at each size, each step's note shows a left bar 3 px or wider and a first line `Step <n>`, both
//            in the scenario mark's hue within 20 degrees at an oklch chroma of 0.1 or more, no edge label shows a border, and
//            no count outside the badges, such as the play bar's, takes a badge's ring or rounding.
//   formulas the example that holds formulas draws an inline one as MathML on its sentence's line and a display one centered on
//            its own line, with no TeX left; on a copy of the first example, the planted formulas draw a fraction, a root, a sum,
//            each script, Greek letters and relations; check-contract.py refuses a copy whose formula holds `\foo`.
//   code     on that copy, a backtick span draws as inline code on its sentence's line and a fence as a block keeping its line
//            breaks and indent, with no backtick shown.
//   tables   on each example page a kept card's table draws no line on the table, its rows or its cells, and its header reads
//            apart from its rows by a muted, heavier text.
//   layout   each example at 1440 by 900, light and dark, each level at rest, a card kept on one record per item form,
//            the search listing hits of two kinds or more and a scenario's bar, measured on the ink a reader sees:
//            proximity, each group of the card (head, item, footer), the search (hit, kind, keys), the bars (tools,
//            scenario bar), the nodes and each area's header with its nodes, its parts at most half as far apart as
//            the group from the next; common region, no part past its frame; alignment, a column's parts on one edge
//            within 1 px; scale, every margin, padding and gap of those parts 0, 2, 4, 8, 12, 16, 24 or 32 px and the two
//            key-hint rows spaced alike; contrast, every text of those parts shown at 4.5:1 or more on its ground. It
//            prints a line per principle, then the groups it measured, and fails unless it finds the fault it plants for
//            each principle on a kept card. Every level of page-changes at rest in light holds at most half of the
//            crowded parallel pairs, two runs of different edges under 16 px apart beside each other for over 24 px, that
//            3dd6783c drew, printed as `parallel room: PASS` or `parallel room: FAIL` with the count.
//   wrap     on a copy of the first example whose first scenario's first three steps hold Korean notes of 150 characters
//            or more, whose first node's purpose is such a text and whose first node's label holds a word of 40 letters,
//            the checker accepts the copy, and at each size each of those notes shows whole over two lines or more inside
//            the window, and the note, the node's label and each text of the node's kept card split no word across two
//            lines and reach past no side of their box.
//   fonts    on copies of each example whose token sheet sets every type size and line height as shipped and twice as large, at 1440 by
//            900, every area's label made longer, on every level, each node's label and tag and each area's header, its
//            badges included, split no word across two lines, keep each word inside their box across and their lines inside
//            the node or area down, no node's tag runs under its badges, and no area's badge is shorter than its text, printed as `<n> labels, tags and headers read at <sizes> and at <sizes>, none split or cut off`.
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
const { check, same, python, tags: catalogue } = require(path.join(__dirname, "..", "..", "..", "lib", "check-step.cjs"));
const SIZES = [[1024, 768], [1440, 900], [1920, 1080]];
const STEPS = ["diagram", "shapes", "overlay", "fit", "clear", "moves", "changes", "search", "titles", "results", "regex", "ranking", "recent", "tasks", "sweep", "names", "glosses", "badges", "counts", "note", "formulas", "code", "tables", "layout", "wrap", "fonts"];
const REFUSED = ["area-known-no-node", "form-level-without-node", "form-empty-steps", "info-form-empty-code", "info-form-empty-list", "info-form-empty-text"]; // empty shapes no page has to draw, since the checker refuses them
const KINDS = ["exact", "initials", "misspelt", "two-fields", "id", "korean-layout", "alias"];
const asked = process.argv.slice(2);
if (asked.some((word) => !STEPS.includes(word))) {
  console.error("usage: run-page.cjs " + STEPS.map((word) => `[${word}]`).join(" "));
  process.exit(2);
}

const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "system-page-"));
const examples = fs.readdirSync(path.join(ROOT, "examples")).filter((name) => fs.existsSync(path.join(ROOT, "examples", name, "contract.json"))).sort()
  .map((name) => ({ name, source: path.join(ROOT, "examples", name, "contract.json"), kept: path.join(ROOT, "examples", name, "page.html"), built: path.join(scratch, name + ".html") }));
const tags = catalogue(path.join(ROOT, "assets", "tags.json"));
const UNFOLD = "import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); from contract_copies import copies; print(json.dumps(dict(copies(pathlib.Path(sys.argv[2])))))";

let launches = 0;
const loads = []; // each address a page was sent to, so a step can count what it opened
const launch = () => { launches += 1; return browsers.launch(); };

function make(example) { // the page of one contract file, and what its page data says of each record
  const made = python(path.join(ROOT, "scripts", "make-page.py"), example.source, example.built);
  check(made.status === 0, `make-page.py refused ${example.name}: ${(made.stdout + made.stderr).split("\n")[0]}`);
  example.contract = JSON.parse(fs.readFileSync(example.built, "utf8").match(/<script type="application\/json" id="page-data">([\s\S]*?)<\/script>/)[1]);
  example.levelOf = {};
  for (const level of example.contract.levels) {
    example.levelOf[level.id] = level.id;
    for (const kind of ["nodes", "edges", "areas"]) for (const record of level[kind] || []) example.levelOf[record.id] = level.id;
  }
  const names = {};
  for (const level of example.contract.levels) for (const node of level.nodes) names[node.id] = node.label;
  const shown = (text) => text.replace(/\{([a-z0-9-]+)\}/g, (whole, id) => names[id] || whole).replace(/`/g, ""); // a text as the page draws it: each named record by its label, code with no backticks
  for (const level of example.contract.levels) { level.shown = shown(level.title); for (const edge of level.edges || []) edge.shown = shown(edge.label); }
  return example;
}
const build = (wanted) => wanted.forEach(make);

async function open(browser, example, size, options = {}) {
  const context = await browser.newContext({ viewport: { width: size[0], height: size[1] }, reducedMotion: options.still ? "reduce" : "no-preference", colorScheme: options.scheme || "light" });
  const page = await context.newPage();
  page.faults = [];
  page.asked = [];
  page.on("console", (message) => message.type() === "error" && page.faults.push(message.text()));
  page.on("pageerror", (error) => page.faults.push(String(error)));
  page.on("request", (request) => { if (!request.url().startsWith("file://" + example.built)) page.asked.push(request.url()); });
  await page.clock.install(); // the page's timers then run on a clock a step can turn forward, so no step sleeps
  if (options.held) await page.clock.pauseAt(Date.now() + 1000); // and only when it does, so a busy machine that slows the pointer leaves the page's time as it is
  const go = page.goto.bind(page);
  page.goto = (address) => { loads.push(address); return go(address); };
  await page.goto("file://" + example.built + (options.at || ""));
  await rest(page);
  return page;
}
const PAGES = 4; // the pages a step drives at once, since each page more slows every pointer event of the others
async function each(items, work) { // WORK done for each of ITEMS, at most PAGES at a time
  const waiting = [...items];
  await Promise.all(Array.from({ length: Math.min(PAGES, waiting.length) }, async () => { while (waiting.length) await work(waiting.shift()); }));
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
    const corners = [style.borderTopLeftRadius, style.borderBottomRightRadius].map((value) => { const [across, down = across] = value.split(" "); return [across.endsWith("%") ? parseFloat(across) / 100 * card.offsetWidth : parseFloat(across), parseFloat(down)]; });
    if (style.clipPath !== "none" || corners.some(([across, down]) => 2 * down >= card.offsetHeight || 2 * across > card.offsetWidth || (node.tag !== "dataStore" && 2 * across >= card.offsetWidth))) return `node ${node.id} is not a rectangle`; // its sides stay straight, and its top and bottom too but a data store's
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
    const said = label && [...label.childNodes].filter((part) => !(part.classList && part.classList.contains("claims"))).map((part) => part.textContent).join(""); // the label's words, its badges apart
    if (!label || said !== edge.shown) return `edge ${edge.id} has no label`;
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
  await page.clock.fastForward(450);
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
  const read = { labels: 0, addresses: 0, rows: 0 }; // what was read for a code mark
  for (const example of examples) {
    check(fs.existsSync(example.kept), `${example.name} keeps no built page`);
    check(fs.readFileSync(example.kept, "utf8") === fs.readFileSync(example.built, "utf8"), `${example.name}'s kept page differs from the one make-page.py builds`);
    const followed = python(path.join(ROOT, "scripts", "check-page.py"), example.built);
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
      const labels = await page.evaluate(() => [...document.querySelectorAll("#stage .label")].map((label) => label.textContent)), marked = labels.find((text) => /[{}`]/.test(text));
      read.labels += labels.length;
      check(!marked, `${example.name} ${level.id} at ${size.join("x")}: an edge label reads ${marked}`);
      const fault = await drawn(page, level);
      check(!fault, `${example.name} ${level.id} at ${size.join("x")}: ${fault}`);
      for (const [kind, group] of grouped(level)) for (const record of group) {
        const spans = size === SIZES[0] && JSON.stringify([record.label, record.title, record.info || {}]).includes("`"); // a row's text is the same at every size
        if (!(record.info || {}).address && !spans) continue;
        await page.goto("file://" + example.built + "#level=" + level.id + "&at=" + record.id);
        await rest(page);
        const rows = new Map();
        for (let leaf = 0; leaf < 12; leaf++) { // the card's pages turned until the last row shows
          const shown = await page.evaluate(() => ({ rows: [["heading", document.querySelector("#card h2").textContent], ...[...document.querySelectorAll("#card dl > div")].map((one) => [one.querySelector("dt").textContent, one.querySelector("dd").textContent])], turn: (document.querySelector("#card .turn") || {}).textContent || "" }));
          for (const [name, text] of shown.rows) rows.set(name, text);
          const [, to, all] = shown.turn.match(/–(\d+) of (\d+)/) || [];
          if (!to || to === all) break;
          await page.evaluate(() => document.querySelector("#card .turn").click()); // a pointer brought onto a card lays it out again, which may drop the button a pointer click waits on
        }
        if ((record.info || {}).address) {
          const address = rows.has("address") ? rows.get("address") : null;
          check(address !== null && !/\{[a-z0-9-]+\}|`/.test(address), `${example.name} ${kind} ${record.id} at ${size.join("x")}: its card's address reads ${address}`);
          read.addresses += 1;
        }
        if (spans) for (const [name, text] of rows) {
          check(!text.includes("`"), `${example.name} ${kind} ${record.id}: its card's ${name} row reads ${text}`);
          read.rows += 1;
        }
      }
    }
    quiet(page, `${example.name} at ${size.join("x")}`);
    check(!page.asked.length, `${example.name} at ${size.join("x")} asked for ${page.asked[0]}`);
    await page.context().close();
  })));
  read.titles = await spans(browser);
  console.log(`${read.labels} edge labels and ${read.addresses} card addresses read, none with a brace or a backtick`);
  console.log(`${read.rows} card rows with a code span read, none with a backtick`);
  console.log(`${read.titles} titles, tooltips and card headings read on a copy whose every label holds a code span, none with a backtick`);
}
async function spans(browser) { // a copy of the second example whose every node label holds a code span, walked step by step
  const example = examples[1], flat = JSON.parse(fs.readFileSync(example.source, "utf8"));
  for (const node of flat.nodes) node.label += " `mark`";
  const copy = { name: example.name + "-marked", source: path.join(scratch, example.name + "-marked.json"), built: path.join(scratch, example.name + "-marked.html") };
  fs.writeFileSync(copy.source, JSON.stringify(flat));
  make(copy);
  const page = await open(browser, copy, SIZES[0], { still: true }), texts = () => page.evaluate(() => [...document.querySelectorAll("#crumbs, #play .title, #onto:not([hidden]), #card.show h2")].map((one) => one.textContent)
    .concat([...document.querySelectorAll("#play .dots [title], #stage .open")].flatMap((one) => [one.title, one.getAttribute("aria-label") || ""])));
  let read = 0;
  const clean = async (where) => { const seen = await texts(); read += seen.length; const marked = seen.find((text) => text.includes("`")); check(!marked, `${copy.name} ${where}: a reader sees ${marked}`); };
  for (const scenario of copy.contract.scenarios || []) {
    await page.goto("file://" + copy.built + "#scenario=" + scenario.id + "&step=0&level=" + copy.levelOf[scenario.steps[0].at]);
    await rest(page);
    for (let i = 0; i < scenario.steps.length; i++) {
      if (i) { await page.keyboard.press("ArrowRight"); await rest(page); }
      await clean(`scenario ${scenario.id} step ${i}`);
    }
  }
  for (const level of copy.contract.levels) for (const node of level.nodes) {
    await page.goto("file://" + copy.built + "#level=" + level.id + "&at=" + node.id);
    await rest(page);
    await clean(`node ${node.id}`);
  }
  quiet(page, copy.name);
  await page.context().close();
  return read;
}

// ---- shapes ----
const oklab = (rgb) => { // a pixel's sRGB as OKLab, so a tint's lightness, chroma and hue are read as a person sees them
  const [r, g, b] = rgb.map((c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b), s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
};
const chroma = ([, a, b]) => Math.hypot(a, b), hue = ([, a, b]) => (Math.atan2(b, a) * 180 / Math.PI + 360) % 360;
const apart = (x, y) => Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]), turn = (x, y) => { const d = Math.abs(x - y) % 360; return Math.min(d, 360 - d); };
const outlines = (page) => page.evaluate(() => { // each node's corners, lid and buttons and each area's border and fill, as the level shown draws them
  const stage = document.getElementById("stage"), pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  pen.canvas.width = pen.canvas.height = 1;
  const canvas = getComputedStyle(document.body).backgroundColor;
  const pixel = (color, under = canvas) => { pen.clearRect(0, 0, 1, 1); pen.fillStyle = under; pen.fillRect(0, 0, 1, 1); pen.fillStyle = color; pen.fillRect(0, 0, 1, 1); return [...pen.getImageData(0, 0, 1, 1).data]; };
  const corner = (element, value) => { const [across, down = across] = value.split(" "), px = (one, length) => one.endsWith("%") ? parseFloat(one) / 100 * length : parseFloat(one); return [px(across, element.offsetWidth), px(down, element.offsetHeight)]; };
  const corners = (element) => { const style = getComputedStyle(element); return [style.borderTopLeftRadius, style.borderTopRightRadius, style.borderBottomRightRadius, style.borderBottomLeftRadius].map((value) => corner(element, value)); };
  const line = (style, side) => ({ style: style[`border${side}Style`], width: parseFloat(style[`border${side}Width`]), seen: pixel(style[`border${side}Color`], "transparent")[3] > 0 });
  const top = (element) => element.getBoundingClientRect().top;
  return {
    canvas: pixel(canvas), mark: pixel(getComputedStyle(document.documentElement).getPropertyValue("--mark")),
    nodes: [...stage.querySelectorAll(".node")].map((card) => {
      const lid = getComputedStyle(card, "::after"), drawn = lid.content !== "none" && lid.display !== "none";
      return { id: card.dataset.id, w: card.offsetWidth, h: card.offsetHeight, corners: corners(card), inner: [...card.querySelectorAll("button:not(.claim)")].map((button) => Math.max(...corners(button).flat())),
        lid: drawn ? { w: parseFloat(lid.width), h: parseFloat(lid.height), top: parseFloat(lid.top), round: lid.borderBottomLeftRadius, rim: line(lid, "Bottom") } : null, label: top(card.querySelector("b")) - top(card) };
    }),
    areas: [...stage.querySelectorAll(".area")].map((frame) => {
      const style = getComputedStyle(frame), box = frame.getBoundingClientRect(), header = frame.firstElementChild.getBoundingClientRect();
      return { id: frame.dataset.id, x: box.left, y: box.top, sides: ["Top", "Right", "Bottom", "Left"].map((side) => line(style, side)), fill: pixel(style.backgroundColor), name: frame.firstElementChild.textContent, head: [header.top - box.top, header.left - box.left] };
    }),
  };
});
async function shapes(browser) {
  const tally = { states: 0, others: 0, stores: 0, dashed: 0, solid: 0, bands: 0, levels: 0, marks: 0 }, BANDS = ["lane", "phase"];
  const framed = (one) => JSON.parse(fs.readFileSync(one.source, "utf8")).areas.filter((area) => area.tag !== "region"); // a region holds states, which no lane may
  const most = (one) => Math.max(...Object.values(framed(one).reduce((count, area) => ({ ...count, [area.level]: (count[area.level] || 0) + 1 }), {})));
  const example = [...examples].sort((a, b) => most(b) - most(a))[0], flat = JSON.parse(fs.readFileSync(example.source, "utf8"));
  const counts = framed(example).reduce((count, area) => ({ ...count, [area.level]: (count[area.level] || 0) + 1 }), {}), fullest = Object.keys(counts).find((level) => counts[level] === most(example));
  for (const area of flat.areas) if (area.level === fullest && area.tag !== "region") { area.tag = "lane"; delete area.info; }
  const band = flat.areas.find((area) => area.level === fullest && area.tag === "lane"), frame = flat.areas.find((area) => area.tag === "region");
  const namers = new Map([band, frame].map((area) => [area, flat.nodes.find((node) => node.level === area.level)]));
  for (const [area, namer] of namers) namer.purpose = `${namer.purpose} It works beside {${area.id}}.`; // a card chip that names a band, or a framed area, of its own level
  const copy = { name: example.name + "-lanes", source: path.join(scratch, example.name + "-lanes.json"), built: path.join(scratch, example.name + "-lanes.html") };
  fs.writeFileSync(copy.source, JSON.stringify(flat));
  make(copy);
  check(copy.contract.levels.some((level) => (level.areas || []).filter((area) => area.tag === "lane").length >= 4), `${copy.name} holds no level of four lanes`);
  const named = [];
  for (const scheme of ["light", "dark"]) for (const [area, namer] of namers) { // the pointer on a chip marks a band by its name and a tint, never by a border, and a framed area by its border
    const page = await open(browser, copy, SIZES[1], { still: true, scheme, at: `#level=${area.level}&at=${namer.id}` }), where = `${copy.name} in ${scheme}`;
    const looks = (id) => page.evaluate((id) => {
      const area = document.querySelector(`#stage .area[data-id="${id}"]`), style = getComputedStyle(area), pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
      const seen = (color) => { pen.clearRect(0, 0, 1, 1); pen.fillStyle = color; pen.fillRect(0, 0, 1, 1); return pen.getImageData(0, 0, 1, 1).data[3] > 0; };
      return { on: area.classList.contains("named"), sides: ["Top", "Right", "Bottom", "Left"].filter((side) => style[`border${side}Style`] !== "none" && parseFloat(style[`border${side}Width`]) > 0 && seen(style[`border${side}Color`])), edge: style.borderTopColor, name: getComputedStyle(area.firstElementChild).color, tint: style.backgroundImage, spot: ((box) => ({ x: Math.round(box.left + 4), y: Math.round(box.bottom - 3) }))(area.firstElementChild.getBoundingClientRect()) };
    }, id);
    const legible = async (look) => { // the name's colour against the band's drawn pixel below its text, at 4.5:1 or more
      const shot = (await page.screenshot({ clip: { x: look.spot.x, y: look.spot.y, width: 1, height: 1 } })).toString("base64");
      return page.evaluate(async ({ shot, name }) => {
        const image = new Image(), pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
        image.src = "data:image/png;base64," + shot;
        await image.decode();
        pen.drawImage(image, 0, 0);
        const under = pen.getImageData(0, 0, 1, 1).data;
        pen.clearRect(0, 0, 1, 1); pen.fillStyle = under[3] ? `rgb(${under[0]} ${under[1]} ${under[2]})` : "#fff"; pen.fillRect(0, 0, 1, 1); pen.fillStyle = name; pen.fillRect(0, 0, 1, 1);
        const over = pen.getImageData(0, 0, 1, 1).data;
        const light = (color) => { const [r, g, b] = [...color].slice(0, 3).map((value) => { value /= 255; return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
        return (Math.max(light(over), light(under)) + 0.05) / (Math.min(light(over), light(under)) + 0.05);
      }, { shot, name: look.name });
    };
    const chip = page.locator(`#card .ref[data-ref="${area.id}"]`).first();
    check(await chip.count(), `${where}: the card of ${namer.id} shows no chip for ${area.id}`);
    const before = await looks(area.id);
    await chip.hover();
    await rest(page);
    const after = await looks(area.id), what = `${where}: the chip for ${area.tag} ${area.id}`, ratio = area === band ? await legible(after) : 0;
    if (!after.on) named.push(`${what} marks nothing`);
    else if (area === band && after.sides.length) named.push(`${what} draws a border on its ${after.sides.join(", ").toLowerCase()} side`);
    else if (area === band && (after.name === before.name || after.tint === before.tint)) named.push(`${what} leaves its ${after.name === before.name ? "name" : "fill"} as it was`);
    else if (area === band && ratio < 4.5) named.push(`${what} shows its name at ${ratio.toFixed(2)}:1 on its tint, under 4.5:1`);
    else if (area === frame && (after.sides.length < 4 || after.edge === before.edge)) named.push(`${what} leaves its border as it was`);
    quiet(page, where);
    await page.context().close();
  }
  console.log(`named area: ${named.length ? "FAIL, " + named[0] : "PASS, a card chip naming a lane band marks its name, legible at 4.5:1, and tint with no border, and one naming a region marks its border, in light and dark"}`);
  check(!named.length, named[0]);
  const read = async (one, scheme) => {
    const page = await open(browser, one, SIZES[1], { still: true, scheme });
    for (const level of one.contract.levels) {
      await page.goto("file://" + one.built + "#level=" + level.id);
      await rest(page);
      const seen = await outlines(page), where = `${one.name} ${level.id} in ${scheme}`, tagOf = Object.fromEntries([...level.nodes, ...(level.areas || [])].map((record) => [record.id, record]));
      const canvas = oklab(seen.canvas), mark = hue(oklab(seen.mark));
      check((canvas[0] < 0.5) === (scheme === "dark"), `${where}: the canvas reads a lightness of ${canvas[0].toFixed(2)}`);
      if (scheme === "light" && one !== copy) for (const node of seen.nodes) {
        const tag = tagOf[node.id].tag, across = node.corners.map(([x]) => x), down = node.corners.map(([, y]) => y), least = Math.min(...across, ...down);
        check(node.inner.every((radius) => radius <= least + 0.5), `${where}: node ${node.id} holds a button rounder than its ${least} px corner`);
        if (tag === "dataStore") {
          check(across.every((x) => x >= node.w / 2 - 1) && down.every((y) => y >= 4 && y <= 12), `${where}: data store ${node.id} has corners ${node.corners.map((pair) => pair.join(" by ")).join(", ")} px, not a top and bottom curved across its width`);
          const lid = node.lid, depth = 2 * Math.max(...down);
          check(lid && lid.rim.seen && lid.rim.style !== "none" && lid.rim.width > 0 && lid.round === "50%" && Math.abs(lid.w - node.w) <= 2 && Math.abs(lid.h - depth) <= 2 && lid.top <= 0, `${where}: data store ${node.id} draws no lid rim as wide as itself`);
          check(node.label >= depth, `${where}: the label of data store ${node.id} starts ${node.label} px down, inside its ${depth} px lid`);
          tally.stores += 1;
        } else if (tag === "state") {
          check(least >= 12, `${where}: state ${node.id} has a ${least} px corner`);
          tally.states += 1;
        } else {
          check(Math.max(...across, ...down) <= 4, `${where}: ${tag} node ${node.id} has a ${Math.max(...across, ...down)} px corner`);
          tally.others += 1;
        }
      }
      if (scheme === "light" && one !== copy) {
        const told = await page.evaluate(() => [...document.body.querySelectorAll("*")].filter((element) => element.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && element.children.length === 0 && element.textContent.trim() && !element.closest("#stage, #crumbs, #tools")).map((element) => element.textContent.trim()));
        check(!told.length, `${where}: beside the diagram the page shows ${told[0]}`);
        tally.levels += 1;
      }
      const bands = [];
      for (const area of seen.areas) {
        const tag = tagOf[area.id].tag, shown = area.sides.filter((side) => side.style !== "none" && side.width > 0 && side.seen);
        if (BANDS.includes(tag)) { check(!shown.length, `${where}: ${tag} ${area.id} shows a border`); bands.push(area); continue; }
        if (scheme !== "light" || one === copy) continue;
        const dashed = tag === "region" || tag === "trustZone";
        check(shown.length === 4 && shown.every((side) => side.style === (dashed ? "dashed" : "solid")), `${where}: ${tag} ${area.id} has a ${area.sides.map((side) => side.style).join(" ")} border, not ${dashed ? "dashed" : "solid"}`);
        tally[dashed ? "dashed" : "solid"] += 1;
      }
      bands.sort((a, b) => a.y - b.y || a.x - b.x);
      bands.forEach((band, i) => {
        const tint = oklab(band.fill), name = `${where}: band ${band.id}`;
        check(chroma(tint) >= 0.015 && chroma(tint) <= 0.045, `${name} has an oklch chroma of ${chroma(tint).toFixed(3)}`);
        check(turn(hue(tint), mark) >= 45, `${name} has a hue ${turn(hue(tint), mark).toFixed(0)} degrees from the scenario mark's`);
        check(apart(tint, canvas) >= 0.02, `${name} is ${apart(tint, canvas).toFixed(3)} from the canvas`);
        if (i) check(apart(tint, oklab(bands[i - 1].fill)) >= 0.02, `${name} is ${apart(tint, oklab(bands[i - 1].fill)).toFixed(3)} from the band before it`);
        for (const back of [1, 2]) if (i >= back) check(turn(hue(tint), hue(oklab(bands[i - back].fill))) >= 45, `${name} has a hue ${turn(hue(tint), hue(oklab(bands[i - back].fill))).toFixed(0)} degrees from the band ${back} before it`);
        if (i >= 3) check(apart(tint, oklab(bands[i - 3].fill)) < 0.005, `${name} is not the tint of the band three before it`);
        check(band.name.includes(tagOf[band.id].label) && band.head[0] >= 0 && band.head[0] <= 2 && band.head[1] >= 0 && band.head[1] <= 2, `${name} does not show its name inside its top edge`);
        tally.bands += 1;
      });
    }
    quiet(page, `${one.name} in ${scheme}`);
    await page.context().close();
  };
  for (const scheme of ["light", "dark"]) await Promise.all([...examples, copy].map((one) => read(one, scheme)));
  await Promise.all(examples.map(async (example) => { // a state or a data store a scenario steps on, or a reader picks, still shows its mark all round its shape
    const page = await open(browser, example, SIZES[1], { still: true }), shaped = new Set(example.contract.levels.flatMap((level) => level.nodes.filter((node) => node.tag === "state" || node.tag === "dataStore").map((node) => node.id)));
    const marked = async (id, mark) => { await page.waitForFunction((id) => { const card = document.querySelector(`#stage .node[data-id="${id}"]`), lid = getComputedStyle(card, "::after"); return card.getAnimations({ subtree: true }).every((one) => one.playState === "finished") && (lid.content === "none" || lid.borderBottomColor === getComputedStyle(card).borderTopColor); }, id, { timeout: 4000 }).catch(() => null); return page.evaluate(([id, mark]) => {
      const card = document.querySelector(`#stage .node[data-id="${id}"]`), style = getComputedStyle(card), lid = getComputedStyle(card, "::after");
      return { on: card.matches(mark === "hover" ? ":hover" : "." + mark), shadow: style.boxShadow, border: style.borderTopColor, rim: lid.content === "none" ? style.borderTopColor : lid.borderBottomColor, rest: (() => { const probe = document.body.appendChild(document.createElement("div")); probe.style.border = "1px solid var(--border)"; const color = getComputedStyle(probe).borderTopColor; probe.remove(); return color; })() }; // a node's border at rest
    }, [id, mark]); };
    const looks = (seen, mark, where) => check(seen.on && seen.border !== seen.rest && seen.rim === seen.border && (mark !== "step" || seen.shadow !== "none"), `${where}: its ${mark} mark shows ${JSON.stringify(seen)}`);
    for (const scenario of example.contract.scenarios || []) for (const [i, step] of scenario.steps.entries()) if (shaped.has(step.at)) {
      await page.goto("file://" + example.built + "#scenario=" + scenario.id + "&step=" + i + "&level=" + example.levelOf[step.at]);
      await rest(page);
      looks(await marked(step.at, "step"), "step", `${example.name} scenario ${scenario.id} step ${i + 1} on ${step.at}`);
      tally.marks += 1;
    }
    for (const id of shaped) {
      await page.goto("file://" + example.built + "#level=" + example.levelOf[id]);
      await rest(page);
      const free = () => page.evaluate((id) => { // a point of the node nothing else covers
        const card = document.querySelector(`#stage .node[data-id="${id}"]`), box = card.getBoundingClientRect();
        for (const y of [0.75, 0.5, 0.9, 0.3]) for (const x of [0.5, 0.25, 0.75, 0.1, 0.9]) { const spot = { x: box.left + box.width * x, y: box.top + box.height * y }; const top = document.elementFromPoint(spot.x, spot.y); if (top && card.contains(top) && !top.closest(".open")) return spot; }
        return null;
      }, id);
      for (let tries = 0; tries < 5; tries += 1) { // a node the stage draws again under a still pointer is hovered only once the pointer moves again
        const spot = await free();
        check(spot, `${example.name} ${id}: no part of it is free for the pointer`);
        await page.mouse.move(2, 2);
        await page.mouse.move(spot.x, spot.y, { steps: 2 });
        if (await page.evaluate((id) => document.querySelector(`#stage .node[data-id="${id}"]`).matches(":hover"), id)) break;
      }
      looks(await marked(id, "hover"), "hover", `${example.name} ${id} under the pointer`);
      await page.mouse.move(2, 2);
      await page.goto("file://" + example.built + "#level=" + example.levelOf[id] + "&at=" + id);
      await rest(page);
      looks(await marked(id, "pinned"), "pinned", `${example.name} ${id} picked`);
      tally.marks += 2;
    }
    quiet(page, `${example.name} marks`);
    await page.context().close();
  }));
  check(tally.states && tally.others && tally.stores && tally.dashed && tally.solid && tally.bands && tally.levels && tally.marks, `a shape went unread: ${JSON.stringify(tally)}`);
  console.log(`${tally.states} state nodes rounded 12 px or more, ${tally.others} other nodes 4 px or less, none with an inner box rounder than itself`);
  console.log(`${tally.stores} data stores drawn as cylinders, each label below the lid`);
  console.log(`${tally.marks} scenario steps and picks on a state or a data store and the pointer resting on one show their mark round the whole shape`);
  console.log(`${tally.dashed} region and trust zone areas dashed, ${tally.solid} module and deployment areas solid, ${tally.levels} levels with no legend`);
  console.log(`${tally.bands} lane and phase bands read in light and dark, none framed, each a muted pastel apart from the canvas and its neighbours, three tints in turn, their hues 45 degrees apart`);
}

// ---- overlay ----
function rowsOf(record, kind, claims = []) { // a record's card rows: its sentence, purpose, items, opens and evidence, and one row listing the claims on it
  const held = claims.some((one) => (one.on || []).includes(record.id));
  return (kind === "edge" ? 1 : 0) + (record.purpose ? 1 : 0) + Object.keys(record.info || {}).length + (record.opens ? 1 : 0) + (record.evidence ? 1 : 0) + (held ? 1 : 0);
}
const formOf = (kind, record, name) => { const items = ((tags[kind] || {})[record.tag] || { items: [] }).items.concat((tags.common || {})[kind] || []); const item = items.find((one) => one.name === name); return item ? item.form : null; };
function targets(example) { // a node, an edge and an area, then one record per item form
  const picked = [], forms = new Set();
  for (const level of example.contract.levels) for (const [kind, group] of grouped(level)) for (const record of group) {
    const held = Object.keys(record.info || {}).map((name) => formOf(kind, record, name)).filter((form) => form && !forms.has(form));
    const first = !picked.some((one) => one.kind === kind);
    if (!first && !held.length) continue;
    held.forEach((form) => forms.add(form));
    picked.push({ kind, id: record.id, level: level.id, rows: rowsOf(record, kind, example.contract.claims), forms: Object.keys(record.info || {}).map((name) => formOf(kind, record, name)).filter(Boolean) });
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
  await each(shares.filter((one) => one.picked.length), async ({ size, example, picked }) => {
    const page = await open(browser, example, size, { held: true });
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
    for (const target of picked) await probe(target);
    quiet(page, `${example.name} at ${size.join("x")}`);
    await page.context().close();
  });
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
  await page.clock.fastForward(450);
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
  await each(groups, async ({ example, size, level, nodes }) => {
    const page = await open(browser, example, size, { at: "#level=" + level.id, held: true });
    await settled(page);
    for (const node of nodes) {
      const tied = [...new Set((level.edges || []).flatMap((edge) => edge.from === node.id ? [edge.to] : edge.to === node.id ? [edge.from] : []))].filter((id) => id !== node.id);
      if (!tied.length) continue;
      const came = await hoverNode(page, node.id, size).then(() => true, () => false);
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
  });
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
        return { marked, level: document.body.dataset.level, step: +document.body.dataset.step, label: named && label(named.id), controls: area("play") + area("chip"), runs: !!token && token.classList.contains("run"), edge: !!document.querySelector(`#stage .edge[data-id="${at}"]`) };
      }, [step.at, named]);
      check(seen.step === i, `${where}: the key left it at step ${seen.step}, not ${i}`);
      if (named && seen.level === example.levelOf[named.id]) { check(seen.label === named.label, `${where} step ${i}: node ${named.id} reads ${seen.label}, not ${named.label}`); named.seen = true; }
      check(seen.level === example.levelOf[step.at], `${where} step ${i}: on level ${seen.level}, not ${example.levelOf[step.at]}`);
      check(seen.marked.length === 1 && seen.marked[0] === step.at, `${where} step ${i}: marks ${seen.marked.join(",") || "nothing"}, not ${step.at}`);
      check(seen.controls <= size[0] * size[1] / 10, `${where} step ${i}: its controls cover over a tenth of the window`);
      check(!seen.edge || seen.runs, `${where} step ${i}: no mark moves along the edge`);
    }
  }
  if (lent) return;
  quiet(page, example.name);
  await page.context().close();
}
async function notes(browser, example, size, tally) { // each step of each scenario: its note clear of every lane header and shown edge label, and a step whose next record is on another level naming that level
  const page = await open(browser, example, size, { still: true });
  for (const scenario of example.contract.scenarios || []) {
    await page.keyboard.press("Escape");
    await page.goto("file://" + example.built + "#scenario=" + scenario.id + "&step=0&level=" + example.levelOf[scenario.steps[0].at]);
    await rest(page);
    for (let i = 0; i < scenario.steps.length; i++) {
      const where = `${example.name} scenario ${scenario.id} step ${i} at ${size.join("x")}`;
      if (i) { await page.keyboard.press("ArrowRight"); await rest(page); }
      const seen = await page.evaluate(() => {
        const box = (element) => element.getBoundingClientRect(), chip = document.getElementById("chip"), hint = document.getElementById("onto");
        const laps = (a, b) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > 0.5 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 0.5;
        const shown = (element) => element.checkVisibility({ visibilityProperty: true }) && +getComputedStyle(element).opacity > 0.05;
        const covered = !chip.classList.contains("show") ? [] : [...document.querySelectorAll("#stage .area > header")].map((header) => ["lane header", header.parentElement.dataset.id, header])
          .concat([...document.querySelectorAll("#stage .label")].filter(shown).map((label) => ["edge label", label.dataset.edge, label])).filter(([, , element]) => laps(box(chip), box(element))).map(([what, id]) => `${what} ${id}`);
        return { noted: +chip.classList.contains("show"), covered, hint: hint && !hint.hidden && box(hint).width > 0 ? hint.textContent : "" };
      });
      check(!seen.covered.length, `${where}: its note covers ${seen.covered.join(", ")}`);
      tally.notes += seen.noted;
      const next = scenario.steps[i + 1], away = next && example.levelOf[next.at] !== example.levelOf[scenario.steps[i].at] ? example.contract.levels.find((level) => level.id === example.levelOf[next.at]) : null;
      tally.onto += !!away;
      check(away ? seen.hint.toLowerCase().includes(away.shown.toLowerCase()) : !seen.hint, away ? `${where}: the next step is on ${away.shown}, and the hint reads ${seen.hint || "nothing"}` : `${where}: the next step stays on this level, and a hint reads ${seen.hint}`);
    }
  }
  quiet(page, `${example.name} notes at ${size.join("x")}`);
  await page.context().close();
}
async function origins(browser, example, tally) { // a move down and back up, held at three moments: a mark names the node the level entered grows from
  const page = await open(browser, example, SIZES[1]);
  const opener = example.contract.levels[0].nodes.find((node) => node.opens);
  const held = () => page.evaluate((id) => {
    const moving = document.getAnimations(); // held past its end, a move with no fill leaves this list, so it is finished from here
    const missed = [150, 450, 750].map((moment) => {
      moving.forEach((one) => { one.pause(); one.currentTime = moment; });
      const mark = document.getElementById("origin");
      return mark && mark.dataset.for === id && +getComputedStyle(mark).opacity > 0.2 && mark.getBoundingClientRect().width > 0 ? "" : `at ${moment} ms`;
    }).filter(Boolean);
    moving.forEach((one) => one.finish());
    return missed;
  }, opener.id);
  for (const way of ["down", "up", "down turned back"]) {
    await page.evaluate(([way, id]) => {
      if (way === "up") return history.back();
      document.querySelector(`#stage .node[data-id="${id}"] .open`).click();
      if (way !== "down") document.getAnimations().forEach((one) => { one.pause(); one.currentTime = 150; }); // the move held 150 ms in, then turned back
    }, [way, opener.id]);
    if (way === "down turned back") await page.evaluate(() => history.back());
    if (way !== "down") await page.waitForFunction((level) => document.body.dataset.level === level, example.contract.levels[0].id);
    const missed = await held();
    check(!missed.length, `${example.name}: a move ${way} through ${opener.id} marks no node it grows from ${missed.join(", ")}`);
    tally.framed += 1;
    await rest(page);
    check(await page.evaluate(() => { const mark = document.getElementById("origin"); return !mark || +getComputedStyle(mark).opacity < 0.05; }), `${example.name}: the mark of the node a level grows from stays after the move ${way}`);
  }
  quiet(page, `${example.name} origins`);
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
      if (!(await page.$("#stage .node .open"))) { await page.click("#crumbs > button"); await note(); }
      await page.mouse.move(2, size[1] - 2); await rest(page); // off the diagram, so no overlay lies over the button
      await page.click("#stage .node .open"); await note();
    },
    up: async () => {
      if ((await page.$$("#crumbs > button")).length < 2) await moves.down();
      const path = await page.$$("#crumbs > button");
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
  const tally = { notes: 0, onto: 0, framed: 0 }; // what the notes and the level moves were read for
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
    .concat(examples.flatMap((example) => [["down", "search", "up", "step"], ["search", "step", "down", "up"], ["step", "up", "search", "down"]].map((order) => mixed(browser, example, SIZES[1], order))))
    .concat(SIZES.flatMap((size) => examples.map((example) => notes(browser, example, size, tally))), examples.map((example) => origins(browser, example, tally)))));
  console.log(`${tally.notes} step notes at three sizes cover no lane header and no shown edge label`);
  console.log(`${tally.onto} steps whose next record is on another level name that level, ${tally.framed} level moves frame the node they grow from`);
}

// ---- changes ----
const PLANTED = "part-set-apart";
const RENAMED = "Part named anew, at a length no box holds on one line"; // longer than the widest node holds on one line, so the page must go on to a second
function changed(example) { // a copy of one example's contract that holds the planted node and the three changes, the checker asked after each
  const planted = JSON.parse(fs.readFileSync(example.source, "utf8"));
  check(planted.levels.length > 1 && (planted.scenarios || []).length, `${example.name} has one level or no scenario, so nothing can change under a scenario`);
  planted.nodes.push({ id: PLANTED, label: "Part set apart", tag: planted.nodes.find((node) => node.level === planted.levels[0].id).tag, level: planted.levels[0].id, purpose: "Stand where its question is asked." });
  planted.scenarios[0].steps.push({ at: PLANTED });
  const walked = new Set(planted.scenarios.flatMap((scenario) => scenario.steps.map((step) => step.at)));
  const levelOf = Object.fromEntries(planted.nodes.map((node) => [node.id, node.level]));
  const fixed = new Set((planted.claims || []).flatMap((item) => (item.paths || []).flat()));
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
    if (query.kind === "alias") { // a word the contract says nowhere but in an alias
      const unaliased = JSON.stringify(holder.contract, (key, value) => key === "aliases" ? undefined : value).toLowerCase();
      check(!unaliased.includes(query.query.toLowerCase()), `the alias query ${query.query} is a word ${query.example} holds outside its aliases`);
    }
    const hits = await searched(page, query.query);
    const where = await page.evaluate(() => ((document.querySelector("#hits [data-hit]") || document).querySelector(".where") || {}).textContent || "");
    await page.keyboard.press("Escape");
    const place = hits.indexOf(query.wants), told = query.kind !== "alias" || place === 0 && where.startsWith("matched alias: ");
    count("first", place === 0); count("three", place >= 0 && place < 3); count(query.kind, place === 0 && told);
    if (place !== 0 || !told) missed.push(`${query.query} (${query.kind}) wants ${query.wants}, got ${hits.slice(0, 3).join(",") || "nothing"}${told ? "" : ", its first hit naming no matched alias"}`);
  }
  for (const page of Object.values(pages)) await page.context().close();
  const share = (name) => tally[name].hit / tally[name].of;
  const line = `first ${tally.first.hit}/${tally.first.of}, in three ${tally.three.hit}/${tally.three.of}, misspelt ${tally.misspelt.hit}/${tally.misspelt.of}, korean-layout ${tally["korean-layout"].hit}/${tally["korean-layout"].of}, alias ${tally.alias.hit}/${tally.alias.of}`;
  console.log(line);
  for (const miss of missed) console.log("  " + miss);
  const failed = [];
  for (const [name, scenario] of [["stop word", stopWord], ["regex recall", regexRecall], ["recent set", recentSet]]) {
    const outcome = await scenario(browser).then((detail) => `PASS ${detail}`, (error) => { failed.push(name); return `FAIL ${error.message.split("\n")[0]}`; });
    console.log(`${name}: ${outcome}`);
  }
  check(share("first") >= 17 / 20 && share("three") >= 19 / 20 && share("misspelt") >= 3 / 4 && share("korean-layout") >= 3 / 4 && share("alias") === 1, line);
  check(!failed.length, `${failed.join(" and ")} failed`);
}
async function stopWord(browser) { // a long query's stop word alone finds nothing, and the query's other words still rank
  const page = await open(browser, examples.find((example) => example.name === "page-changes"), SIZES[1], { still: true });
  await page.keyboard.press("/");
  const stray = await typed(page, "the zzqxv wobbly"), none = await said(page);
  check(!stray.length && none && none.title.includes("the zzqxv wobbly"), `the zzqxv wobbly lists ${stray.length} records (${stray.slice(0, 3).map((hit) => hit.id).join(",")}), not the no-result state`);
  const kept = await typed(page, "the zzqxv watcher");
  check(kept.length && kept[0].id === "watcher", `the zzqxv watcher lists ${kept.map((hit) => hit.id).slice(0, 3).join(",") || "nothing"}, not watcher first`);
  quiet(page, "page-changes");
  await page.context().close();
  return "the zzqxv wobbly shows no results; the zzqxv watcher lists watcher first";
}
async function regexRecall(browser) { // a recent query comes back in the mode it was picked in, after a reload too, and one an earlier page kept as bare text comes back plain
  const page = await open(browser, examples.find((example) => example.name === "page-changes"), SIZES[1], { still: true });
  const pressed = () => page.evaluate(() => document.getElementById("regex").getAttribute("aria-pressed"));
  const pickRecent = async (text) => { await page.keyboard.press("/"); await page.fill("#query", ""); await page.clock.fastForward(30); await page.click(`#hits [data-recent="${text}"] .text`); await page.clock.fastForward(30); };
  await page.keyboard.press("/"); await page.click("#regex"); await typed(page, "watcher|flush"); await page.keyboard.press("Enter"); await rest(page);
  await page.evaluate(() => { const shelf = Object.keys(localStorage).find((key) => key.startsWith("paperwork-system-recent ")); localStorage.setItem(shelf, JSON.stringify([...JSON.parse(localStorage.getItem(shelf)), "the flush"])); });
  await page.reload(); await rest(page);
  await pickRecent("watcher|flush");
  const strict = await page.evaluate(() => [...document.querySelectorAll("#hits [data-hit]")].length);
  check(await pressed() === "true" && (await page.inputValue("#query")) === "watcher|flush" && strict && !(await said(page)), `watcher|flush picked from recent queries after a reload comes back with the toggle ${await pressed() === "true" ? "on" : "off"}, ${strict} hits`);
  await page.keyboard.press("Escape");
  await pickRecent("the flush");
  check(await pressed() === "false" && (await page.inputValue("#query")) === "the flush", `the flush, kept as bare text, picked from recent queries in the regular expression mode comes back with the toggle ${await pressed() === "true" ? "on" : "off"}`);
  quiet(page, "page-changes");
  await page.context().close();
  return "watcher|flush comes back with the toggle on after a reload; the flush, kept as bare text, comes back with it off";
}

async function recentSet(browser) { // one text run in both modes is one recent row, in the mode it last ran in
  const page = await open(browser, examples.find((example) => example.name === "page-changes"), SIZES[1], { still: true });
  for (const toggle of [false, true]) { await page.keyboard.press("/"); if (toggle) await page.click("#regex"); await typed(page, "flush"); await page.keyboard.press("Enter"); await rest(page); }
  await page.reload(); await rest(page); await page.keyboard.press("/");
  const rows = (await typed(page, "")).filter((hit) => hit.recent === "flush").length;
  await page.click('#hits [data-recent="flush"] .text'); await page.clock.fastForward(30);
  const mode = await page.evaluate(() => document.getElementById("regex").getAttribute("aria-pressed"));
  check(rows === 1 && mode === "true", `flush run plain, then as regex, shows ${rows} recent rows and comes back with the toggle ${mode === "true" ? "on" : "off"}`);
  quiet(page, "page-changes");
  await page.context().close();
  return "flush run plain, then as regex, shows one recent row that comes back with the toggle on";
}

// ---- titles ----
async function titles(browser) {
  for (const example of examples) {
    const page = await open(browser, example, SIZES[1], { still: true });
    await page.click("#claims");
    await page.clock.fastForward(30);
    const listed = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll("#hits [data-hit]")].map((row) => [row.dataset.hit, row.querySelector("b").textContent])));
    for (const claim of example.contract.claims || []) check(listed[claim.id] === claim.title, `${example.name}: the Claims list shows ${claim.id} as ${JSON.stringify(listed[claim.id])}, not by its title ${claim.title}`);
    const first = example.contract.claims[0];
    await page.click(`#hits [data-hit="${first.id}"]`);
    await rest(page);
    const heading = await page.evaluate(() => (document.querySelector("#card h2") || {}).textContent);
    check(heading === first.title, `${example.name}: the card of ${first.id} is headed ${JSON.stringify(heading)}, not ${first.title}`);
    quiet(page, example.name);
    await page.context().close();
  }
  const example = examples.find((one) => one.name === "self"), flat = JSON.parse(fs.readFileSync(example.source, "utf8"));
  const named = flat.nodes.find((node) => node.id === "checker"), holder = flat.nodes.find((node) => node.id === "reader");
  holder.purpose = `Rebuild from what {${named.id}} passes.`;
  const copy = { name: example.name + "-named", source: path.join(scratch, example.name + "-named.json"), built: path.join(scratch, example.name + "-named.html") };
  fs.writeFileSync(copy.source, JSON.stringify(flat));
  make(copy);
  const page = await open(browser, copy, SIZES[1], { still: true, at: `#level=${holder.level}&at=${holder.id}` });
  const text = await page.evaluate(() => document.getElementById("card").textContent);
  check(text.includes(`Rebuild from what ${named.label} passes.`), `${copy.name}: the card of ${holder.id} does not show ${named.label} as written mid-sentence`);
  quiet(page, copy.name);
  await page.context().close();
}

// ---- results ----
const typed = async (page, text) => { // TEXT typed into the open search, and each hit as the person reads it
  await page.fill("#query", "");
  await page.keyboard.insertText(text);
  await page.clock.fastForward(30);
  return page.evaluate(() => [...document.querySelectorAll("#hits .hit")].map((row) => ({
    id: row.dataset.hit || null, recent: row.dataset.recent || null, option: row.id, selected: row.getAttribute("aria-selected") === "true",
    name: [...row.querySelectorAll(".text > b mark")].map((mark) => mark.textContent),
    field: row.querySelector(".where i") ? row.querySelector(".where i").textContent : null,
    where: row.querySelector(".where") ? row.querySelector(".where").textContent : null,
    marks: [...row.querySelectorAll(".where mark")].map((mark) => mark.textContent),
    clock: !!row.querySelector(".clock svg"), plain: row.querySelector(".recent") ? row.querySelector(".recent").firstChild.textContent : null,
    bold: row.querySelector(".recent b") ? row.querySelector(".recent b").textContent : null,
  })));
};
const said = (page) => page.evaluate(() => { const none = document.querySelector("#hits .none"); return none ? { error: none.classList.contains("error"), title: none.querySelector("b").textContent, hint: none.querySelector("span").textContent } : null; });
const WORDS = { self: ["misread", "checker"], "page-changes": ["steering", "rule-text-is-data"] }; // a word only one node's purpose holds, and that node
async function results(browser) {
  const lines = [];
  for (const example of examples) {
    const page = await open(browser, example, SIZES[1], { still: true }), where = example.name;
    await page.keyboard.press("/");
    const [word, wants] = WORDS[example.name];
    const hit = (await typed(page, word)).find((one) => one.id === wants);
    check(hit && hit.field === "purpose" && hit.marks.map((mark) => mark.toLowerCase()).includes(word) && hit.where.split(/\s+/).length <= 16, `${where}: ${word} shows ${JSON.stringify(hit)}, not an excerpt of ${wants}'s purpose with the word marked`);
    const look = await page.evaluate((id) => { const row = document.querySelector(`#hits [data-hit="${id}"]`), mark = row.querySelector(".where mark");
      return { below: row.querySelector(".where").getBoundingClientRect().top >= row.querySelector(".text > b").getBoundingClientRect().bottom - 1, tint: getComputedStyle(mark).backgroundColor }; }, wants);
    check(look.below && !/^(transparent|rgba\(0, 0, 0, 0\))$/.test(look.tint), `${where}: ${wants}'s excerpt ${look.below ? "" : "shares the name's line"} ${look.tint}, not on its own line with the word tinted`);
    lines.push(`excerpt: ${where} ${word} shows "${hit.where}", on its own line, the word tinted`);
    const id = (await typed(page, wants.split("-").slice(0, 2).join("-"))).find((one) => one.id === wants);
    check(id && (id.name.length || id.field === "id"), `${where}: the id ${wants} shows ${JSON.stringify(id)}, naming no field`);
    lines.push(`field: ${where} the id's words show ${id.field ? `"${id.where}"` : "the name marked"}`);
    quiet(page, where);
    await page.context().close();
  }
  const page = await open(browser, examples.find((example) => example.name === "page-changes"), SIZES[1], { still: true });
  await page.keyboard.press("/");
  for (const [text, wants, letters] of [["page chec", "checker", ["page", "chec"]], ["vk", "keeper", ["v", "k"]], ["file wacther", "watcher", ["file", "watcher"]]]) {
    const hit = (await typed(page, text)).find((one) => one.id === wants);
    check(hit && JSON.stringify(hit.name.map((mark) => mark.toLowerCase())) === JSON.stringify(letters), `${text} marks ${hit ? JSON.stringify(hit.name) : "no hit"} in ${wants}, not ${JSON.stringify(letters)}`);
    lines.push(`marks: ${text} marks ${hit.name.join("|")}`);
  }
  const hits = await typed(page, "the page");
  check(hits.length >= 3 && hits[0].selected, `the page lists ${hits.length} hits, the first not chosen`);
  await page.keyboard.press("ArrowDown"); await page.keyboard.press("ArrowDown"); await page.keyboard.press("ArrowUp");
  const active = await page.evaluate(() => ({ named: document.getElementById("query").getAttribute("aria-activedescendant"), chosen: document.querySelector('#hits [aria-selected="true"]').id, id: document.querySelector('#hits [aria-selected="true"]').dataset.hit }));
  check(active.named === active.chosen && active.id === hits[1].id, `after Down, Down, Up the active option is ${active.named}, the chosen ${active.chosen} (${active.id}), not ${hits[1].id}`);
  await page.keyboard.press("Enter"); await rest(page);
  check((await view(page)).pinned === hits[1].id, `Enter on ${hits[1].id} does not pick it`);
  await page.keyboard.press("/"); await page.keyboard.press("Escape"); await rest(page);
  check(!(await page.evaluate(() => document.getElementById("palette").classList.contains("show"))), "Escape leaves the search open");
  lines.push(`keys: Down, Down, Up names ${active.named} active; Enter picks ${hits[1].id}; Escape closes`);
  await page.keyboard.press("/");
  check(!(await typed(page, "zzqxv wobbly")).length, "a query nothing matches lists hits");
  const none = await said(page);
  check(none && none.title.includes("zzqxv wobbly") && none.hint.length > 10, `a query nothing matches says ${JSON.stringify(none)}`);
  lines.push(`none: "${none.title}" ${none.hint}`);
  quiet(page, "page-changes");
  await page.context().close();
  const context = await browser.newContext({ viewport: { width: SIZES[1][0], height: SIZES[1][1] } }), timed = await context.newPage(); // no clock installed, so the page's own time is read
  await timed.goto("file://" + examples.find((example) => example.name === "page-changes").built);
  await timed.keyboard.press("/");
  const QUERIES = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures", "search-queries.json"), "utf8")).map((query) => query.query).concat(["the", "a page that the person opens", "zzqxv"]);
  const cdp = await context.newCDPSession(timed); // the main thread's own time, since a busy machine stretches wall time many fold
  await cdp.send("Performance.enable", { timeDomain: "threadTicks" });
  const spent = async () => (await cdp.send("Performance.getMetrics")).metrics.find((metric) => metric.name === "TaskDuration").value * 1000;
  const least = QUERIES.map(() => Infinity);
  for (let round = 0; round < 5 && least.some((took) => took > 50); round++) for (const [i, text] of QUERIES.entries()) {
    if (least[i] <= 50) continue;
    const before = await spent();
    await timed.evaluate((text) => { const box = document.getElementById("query"); box.value = text; box.dispatchEvent(new Event("input")); }, text);
    least[i] = Math.min(least[i], (await spent()) - before);
  }
  const slowest = Math.max(...least);
  await context.close();
  check(slowest <= 50, `the slowest query lists its hits in ${slowest.toFixed(1)} ms`);
  lines.push(`speed: the slowest of ${QUERIES.length} queries lists in ${slowest.toFixed(1)} ms of main thread time on page-changes`);
  for (const line of lines) console.log(line);
}

// ---- regex ----
async function regex(browser) {
  const lines = [], page = await open(browser, examples.find((example) => example.name === "page-changes"), SIZES[1], { still: true });
  const pressed = () => page.evaluate(() => document.getElementById("regex").getAttribute("aria-pressed"));
  const shade = () => page.evaluate(() => getComputedStyle(document.getElementById("regex")).backgroundColor);
  await page.keyboard.press("/");
  check(await page.evaluate(() => /alt\s*R\s*regex/i.test(document.getElementById("keys").textContent)), "the key line does not name Alt+R");
  const loose = await typed(page, "the checker"), off = await shade();
  await page.click("#regex");
  check(await pressed() === "true" && (await shade()) !== off, "the button does not turn the mode on, or looks the same pressed");
  await page.focus("#regex"); await page.keyboard.press("Enter");
  check(await pressed() === "false" && (await page.evaluate(() => document.getElementById("palette").classList.contains("show"))), "Enter on the focused button does not turn the mode off, or closes the search");
  await page.focus("#query"); await page.click("#regex");
  await page.keyboard.press("Alt+KeyR");
  check(await pressed() === "false", "Alt+R does not turn the mode off");
  await page.keyboard.press("Alt+KeyR");
  check(await pressed() === "true" && (await page.inputValue("#query")) === "the checker", "Alt+R does not turn the mode on, or it typed into the box");
  lines.push("toggle: the button and Alt+R turn the mode on and off, shown pressed");
  const holds = (hit, pattern) => hit.name.concat(hit.marks).some((mark) => pattern.test(mark));
  const strict = await typed(page, "the checker");
  check(strict.length && strict.every((hit) => holds(hit, /^the checker$/i)) && loose.some((hit) => !strict.some((one) => one.id === hit.id)), `the checker as a pattern lists ${strict.map((hit) => hit.id).join(",")}, not only records holding that text`);
  lines.push(`one pattern: the checker lists ${strict.length} records, each holding it with its space`);
  const loud = await typed(page, "THE CHECKER");
  check(JSON.stringify(loud.map((hit) => hit.id)) === JSON.stringify(strict.map((hit) => hit.id)), "case changes what the pattern finds");
  lines.push("case: THE CHECKER lists the same records");
  for (const text of ["the chekcer", "tvk"]) {
    check(!(await typed(page, text)).length && (await said(page)), `${text} finds records in the regular expression mode`);
  }
  lines.push("no slips or initials: the chekcer and tvk find nothing");
  const either = await typed(page, "watcher|flush");
  check(either.some((hit) => holds(hit, /^watcher$/i)) && either.some((hit) => holds(hit, /^flush$/i)) && either.every((hit) => holds(hit, /^(watcher|flush)$/i)), `watcher|flush lists ${JSON.stringify(either.map((hit) => [hit.id, hit.name, hit.marks]))}`);
  lines.push(`either: watcher|flush lists ${either.length} records, each marking one of the two`);
  check(!(await typed(page, "retr(y")).length, "a bad pattern lists hits");
  const bad = await said(page);
  check(bad && bad.error && bad.title === "Not a regular expression" && bad.hint.length > 3, `a bad pattern says ${JSON.stringify(bad)}`);
  const red = () => page.evaluate(() => { // the title's colour drawn on a canvas, so any colour form reads as red, green and blue
    const pen = document.createElement("canvas").getContext("2d");
    pen.fillStyle = getComputedStyle(document.querySelector("#hits .none b")).color; pen.fillRect(0, 0, 1, 1);
    const [r, g, b] = pen.getImageData(0, 0, 1, 1).data;
    return r - Math.max(g, b) > 60;
  });
  const light = await red();
  await page.emulateMedia({ colorScheme: "dark" });
  check(light && (await red()), `a bad pattern's title is ${light ? "" : "not "}red in the light scheme and ${light ? "not " : ""}in the dark one`);
  lines.push(`error: retr(y says ${bad.title}: ${bad.hint}, in red in both schemes`);
  quiet(page, "page-changes");
  await page.context().close();
  for (const line of lines) console.log(line);
}

// ---- ranking ----
async function ranking(browser) {
  const queries = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures", "ranking-queries.json"), "utf8")), pages = {};
  for (const example of examples) pages[example.name] = await open(browser, example, SIZES[1], { still: true });
  const reciprocal = (place) => place ? 1 / place : 0;
  let sum = 0, base = 0;
  for (const query of queries) {
    const hits = await searched(pages[query.example], query.query);
    await pages[query.example].keyboard.press("Escape");
    const place = hits.indexOf(query.wants) + 1;
    sum += reciprocal(place); base += reciprocal(query.base);
    console.log(`${query.query}: ${query.wants} at ${place || "none"}, base ${query.base || "none"}`);
  }
  for (const page of Object.values(pages)) await page.context().close();
  const mean = sum / queries.length, before = base / queries.length;
  console.log(`mean reciprocal rank ${mean.toFixed(3)} over ${queries.length} queries, base ${before.toFixed(3)}`);
  check(mean > before, `the mean reciprocal rank ${mean.toFixed(3)} is not above the base's ${before.toFixed(3)}`);
}

// ---- recent ----
async function recent(browser) {
  const lines = [], example = examples.find((one) => one.name === "page-changes");
  const QUERIES = ["the flush", "the checker", "the status", "the version keeper", "the wacther", "the exprot", "route-ack", "the page file", "the token"];
  const shown = async (page, text) => { await page.keyboard.press("/"); const hits = await typed(page, text); return hits.filter((hit) => hit.recent); };
  let page = await open(browser, example, SIZES[1], { still: true });
  for (const text of QUERIES) { await page.keyboard.press("/"); await typed(page, text); await page.keyboard.press("Enter"); await rest(page); }
  const kept = QUERIES.slice(1).reverse(), first = await shown(page, "");
  check(JSON.stringify(first.map((hit) => hit.recent)) === JSON.stringify(kept) && first.every((hit) => hit.clock), `the empty search lists ${JSON.stringify(first.map((hit) => hit.recent))}, not the last eight with a clock`);
  const order = await page.evaluate(() => [...document.querySelectorAll("#hits h3")].map((title) => title.textContent));
  check(order[0] === "Recent" && order[1] === "Questions", `the empty search lists ${order.join(", ")}, not Recent above the questions`);
  lines.push(`kept: the last 8 of 9 picked queries above the questions, each with a clock`);
  const typing = (await typed(page, "the")).filter((hit) => hit.recent);
  check(typing.length === kept.filter((text) => text.startsWith("the")).length && typing.every((hit) => hit.plain === "the" && hit.recent === "the" + hit.bold), `typing "the" shows ${JSON.stringify(typing)}`);
  const flat = await page.evaluate(() => [...document.querySelectorAll("#hits .recent")].map((part) => part.querySelector("b").getClientRects().length === 1 && part.getBoundingClientRect().height < 1.5 * part.querySelector("b").getBoundingClientRect().height));
  check(flat.length && flat.every(Boolean), "a recent query's typed part and bold rest sit on two lines");
  lines.push(`typing: "the" keeps ${typing.length}, the typed part plain and the rest bold on one line`);
  const top = (await typed(page, "the")).find((hit) => hit.selected);
  await page.keyboard.press("ArrowUp");
  const up = await page.evaluate(() => document.querySelector('#hits [aria-selected="true"]').dataset.recent || null);
  check(top && top.id && !top.recent && up, `typing "the" chooses ${JSON.stringify(top)}, and Up chooses ${up}, not the top record first and a recent query a move away`);
  lines.push(`choice: typing "the" chooses the record ${top.id}; Up reaches the recent ${up}`);
  await page.fill("#query", ""); await page.keyboard.insertText("");
  await page.focus(`#hits [data-recent="the status"] .forget`); await page.keyboard.press("Enter");
  check(await page.evaluate(() => document.getElementById("palette").classList.contains("show") && !document.querySelector('#hits [data-recent="the status"]')), "Enter on a focused remove button does not remove its query, or closes the search");
  await page.keyboard.press("Escape");
  await page.reload(); await rest(page);
  const left = await shown(page, "");
  check(left.length === 7 && !left.some((hit) => hit.recent === "the status"), `after removing the status and a reload the search lists ${JSON.stringify(left.map((hit) => hit.recent))}`);
  lines.push("remove: Enter on its focused remove button drops the status, gone after a reload");
  const elsewhere = path.join(scratch, "elsewhere.html"), other = await page.context().newPage(); // the same browser storage, another file
  fs.copyFileSync(example.built, elsewhere);
  await other.clock.install(); await other.goto("file://" + elsewhere); await rest(other);
  check(!(await shown(other, "")).length, "a page at another path lists the first page's recent queries");
  lines.push("apart: a page at another path in the same browser lists none");
  await page.context().close();
  const context = await browser.newContext({ viewport: { width: SIZES[1][0], height: SIZES[1][1] } });
  await context.addInitScript(() => Object.defineProperty(window, "localStorage", { get() { throw new DOMException("The operation is insecure.", "SecurityError"); } }));
  page = await context.newPage();
  await page.clock.install();
  await page.goto("file://" + example.built); await rest(page);
  await page.keyboard.press("/"); await typed(page, "the flush"); await page.keyboard.press("Enter"); await rest(page);
  const held = await shown(page, "");
  check(held.length === 1 && held[0].recent === "the flush", `with storage that throws the search lists ${JSON.stringify(held.map((hit) => hit.recent))}`);
  lines.push("no storage: the flush is kept for the tab");
  await context.close();
  for (const line of lines) console.log(line);
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
  const listed = question.answers.find((id) => (contract.scenarios || []).concat(contract.claims || []).some((record) => record.id === id));
  check(nodes.length || listed, `${example.name} ${question.id}: no answer is a node, a scenario or a claim to walk to`);
  if (!nodes.length || (listed && depth(nodes[0]) > 0)) {
    await page.click((contract.scenarios || []).some((record) => record.id === listed) ? "#scenarios" : "#claims");
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

// ---- card words ----
const REFERENCE = /\{([a-z0-9-]+)\}/g;
const kept = async (browser, example, id, level) => { // the page of EXAMPLE with ID's card kept open on LEVEL
  const page = await open(browser, example, SIZES[1], { at: `#level=${level}&at=${id}` });
  await settled(page);
  check(await page.evaluate(CARDED, id), `${example.name} ${id}: no card is kept open at #level=${level}&at=${id}`);
  return page;
};
const written = (record) => { // every text of a record a card draws as prose, with the record's own id taken out of what it names
  const texts = [];
  const walk = (value) => (typeof value === "string" ? texts.push(value) : value && typeof value === "object" && Object.values(value).forEach(walk));
  walk([record.purpose, record.label, record.statement, record.fault, record.info]);
  return texts;
};
const records = (example) => example.contract.levels.flatMap((level) => grouped(level).flatMap(([kind, group]) => group.map((record) => ({ kind, record, level: level.id }))));
const openers = (example) => Object.fromEntries(example.contract.levels.flatMap((level) => level.nodes.filter((node) => node.opens).map((node) => [node.opens, { id: node.id, level: level.id }])));
const spoken = (example, text) => { // TEXT as a card reads it: each named record by its label, in any case
  const labels = Object.fromEntries(records(example).map(({ record }) => [record.id, record.label]).concat(example.contract.levels.map((level) => [level.id, level.title])));
  return String(text).replace(REFERENCE, (whole, id) => labels[id] || whole).replace(/^(?:an?|the)\s+/i, "").toLowerCase();
};
async function nameChips(browser) {
  let crossed = 0;
  await Promise.all(examples.map(async (example) => {
    const ends = (list) => [ // a row the card builds from a record's own fields names each record it points to as a chip
      ...list.filter(({ kind }) => kind === "edge").slice(0, 1).map(({ record, level }) => ({ record, level, names: [record.from, record.to], row: "sentence" })),
      ...list.filter(({ record }) => record.opens).slice(0, 1).map(({ record, level }) => ({ record, level, names: [record.opens], row: "opens" })),
      ...list.filter(({ record }) => record.info && record.info.initial).slice(0, 1).map(({ record, level }) => ({ record, level, names: [record.info.initial], row: "initial" }))];
    const built = ends(records(example));
    check(built.length === 3, `${example.name} holds no edge, no opener or no area with an initial state`);
    for (const { record, level, names, row } of built) {
      const page = await kept(browser, example, record.id, level), found = new Set();
      for (let leaf = 0; leaf < 12; leaf++) {
        const seen = await page.evaluate((names) => ({ chips: names.filter((id) => document.querySelector(`#card dd .ref[data-ref="${id}"]`)), turn: (document.querySelector("#card .turn") || {}).textContent || "" }), names);
        seen.chips.forEach((id) => found.add(id));
        const [, to, of] = seen.turn.match(/(\d+) of (\d+)/) || [];
        if (found.size === names.length || !to || to === of) break;
        await page.evaluate(() => document.querySelector("#card .turn").click()); // the More rows press itself is the clear step's to check
        await rest(page);
      }
      const missed = names.filter((id) => !found.has(id));
      check(!missed.length, `${example.name} ${record.id}: its ${row} row names ${missed.join(", ")} with no chip`);
      quiet(page, `${example.name} ${record.id}`);
      await page.context().close();
    }
    const doors = openers(example), all = records(example);
    const pairs = all.flatMap(({ record, level }) => [...new Set(written(record).flatMap((text) => [...text.matchAll(REFERENCE)].map((match) => match[1])))]
      .filter((id) => id !== record.id && example.levelOf[id]).map((id) => ({ record, level, id, at: example.levelOf[id] === level ? id : doors[example.levelOf[id]] && doors[example.levelOf[id]].level === level ? doors[example.levelOf[id]].id : null }))
      .filter((pair) => pair.at));
    const same = pairs.filter((pair) => pair.at === pair.id), cross = pairs.filter((pair) => pair.at !== pair.id);
    check(same.length, `${example.name}: no card text names a record of its own level`);
    for (const [group, what] of [[same, "of its own level"], [cross, "of a level below"]]) {
      let tried = 0;
      for (const pair of group.slice(0, 8)) {
        const page = await kept(browser, example, pair.record.id, pair.level), chip = page.locator(`#card .ref[data-ref="${pair.id}"]`).first();
        if (!(await chip.count())) { await page.context().close(); continue; } // a row on a later page of the card
        check(await chip.evaluate((one) => getComputedStyle(one).backgroundColor !== "rgba(0, 0, 0, 0)"), `${example.name} ${pair.record.id}: the chip for ${pair.id} looks like the words around it`);
        await chip.hover();
        const marked = await page.evaluate(({ at, id }) => ({ at: [...document.querySelectorAll(`#stage [data-id="${at}"]`)].some((one) => one.classList.contains("named")), all: document.querySelectorAll("#stage .named").length, card: document.getElementById("card").dataset.for === id }), { at: pair.at, id: pair.record.id });
        check(marked.card, `${example.name} ${pair.record.id}: the card closed when the pointer rested on its chip for ${pair.id}`);
        check(marked.at, `${example.name} ${pair.record.id}: the chip for ${pair.id}, a record ${what}, marks ${marked.all ? "another record" : "nothing"} in the diagram, not ${pair.at}`);
        await page.mouse.move(2, SIZES[1][1] - 2, { steps: 2 });
        check(await page.evaluate(() => !document.querySelector("#stage .named")), `${example.name} ${pair.record.id}: the chip's mark stays once the pointer leaves it`);
        await chip.hover();
        await page.keyboard.press("Escape");
        await rest(page);
        check(await page.evaluate(() => !document.querySelector("#stage .named")), `${example.name} ${pair.record.id}: the chip's mark stays once Escape closes its card`);
        quiet(page, `${example.name} ${pair.record.id}`);
        await page.context().close();
        tried += 1;
        if (group === cross) crossed += 1;
        break;
      }
      check(tried || group === cross, `${example.name}: no kept card shows a chip for a record ${what} on its first page`);
    }
  }));
  check(crossed, "no example shows a chip for a record of a level below the card's");
}
async function glosses(browser) {
  await Promise.all(examples.map(async (example) => {
    const terms = example.contract.terms || [], sources = Object.fromEntries((example.contract.sources || []).map((one) => [one.id, one]));
    check(terms.length, `${example.name} holds no term`);
    const pattern = (term) => new RegExp(String.raw`(?<![\p{L}\p{N}./-])` + term.split(/\s+/).map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(String.raw`\s+`) + String.raw`(?:e?s)?(?![\p{L}\p{N}-]|[./][\p{L}\p{N}])`, "iu");
    const holder = records(example).find(({ record }) => record.purpose && terms.some((term) => pattern(term.term).test(record.purpose.replace(/`[^`]+`|\$[^$]+\$|\{[a-z0-9-]+\}/g, " "))));
    check(holder, `${example.name}: no purpose holds a term`);
    let page = await kept(browser, example, holder.record.id, holder.level);
    const shown = await page.evaluate(() => [...document.querySelectorAll("#card .term")].map((one) => ({ term: one.dataset.term, text: one.textContent })));
    check(shown.length, `${example.name} ${holder.record.id}: the card marks no term, though its purpose holds one`);
    const outside = await page.evaluate(() => [...document.querySelectorAll(".term, .ref, .badge.guess")].filter((one) => !one.closest("#card dl")).map((one) => one.textContent));
    check(!outside.length, `${example.name}: a label, a crumb or a card title marks ${outside.join(", ")} as a term, a chip or a guess, which belong to a card's rows`);
    for (const one of shown) {
      check(terms.some((term) => term.term === one.term) && pattern(one.term).test(one.text), `${example.name} ${holder.record.id}: "${one.text}" is marked as the term ${one.term}`);
      check(shown.filter((other) => other.term === one.term).length === 1, `${example.name} ${holder.record.id}: the term ${one.term} is marked more than once`);
    }
    await page.locator("#card .term").first().hover();
    await rest(page);
    const meaning = await page.evaluate(() => { const box = document.getElementById("gloss"); return box.classList.contains("show") && getComputedStyle(box).opacity > 0.5 ? box.textContent : ""; });
    const wanted = terms.find((term) => term.term === shown[0].term);
    check(meaning.toLowerCase().includes(spoken(example, wanted.meaning).slice(1)), `${example.name} ${holder.record.id}: the pointer on the term ${wanted.term} shows "${meaning}", not its meaning`);
    await page.mouse.move(2, SIZES[1][1] - 2, { steps: 2 });
    check(await page.evaluate(() => !document.getElementById("gloss").classList.contains("show")), `${example.name}: the term's meaning stays once the pointer leaves it`);
    await page.context().close();
    const cited = records(example).find(({ record }) => (record.evidence || []).length > 1) || records(example).find(({ record }) => record.evidence);
    check(cited, `${example.name}: no record cites a source`);
    page = await kept(browser, example, cited.record.id, cited.level);
    await page.click("#card .cite");
    await rest(page);
    const said = await page.evaluate(() => { const box = document.getElementById("gloss"); return box.classList.contains("show") ? box.textContent.toLowerCase() : ""; });
    for (const entry of cited.record.evidence) {
      const source = sources[entry.split(":")[0]];
      check(source && said.includes(source.path.toLowerCase()) && said.includes(spoken(example, source.says).slice(1)), `${example.name} ${cited.record.id}: a click on its sources mark does not show ${entry}'s path and what it says`);
    }
    const other = records(example).find(({ record, level }) => level === cited.level && record.id !== cited.record.id);
    await page.evaluate(({ level, id }) => { location.hash = `#level=${level}&at=${id}`; }, { level: other.level, id: other.record.id });
    await settled(page);
    check(await page.evaluate(() => !document.getElementById("gloss").classList.contains("show")), `${example.name} ${cited.record.id}: its sources stay shown once the kept card turns to ${other.record.id}`);
    await page.evaluate(({ level, id }) => { location.hash = `#level=${level}&at=${id}`; }, { level: cited.level, id: cited.record.id });
    await settled(page);
    await page.click("#card .cite");
    await rest(page);
    await page.keyboard.press("Escape");
    await rest(page);
    check(await page.evaluate(() => !document.getElementById("gloss").classList.contains("show")), `${example.name} ${cited.record.id}: its sources stay shown once Escape closes the card`);
    quiet(page, `${example.name} ${cited.record.id}`);
    await page.context().close();
  }));
  const copy = planted();
  for (const [at, form, said] of [[copy.nodes[0], "capitalised", copy.term[0].toUpperCase() + copy.term.slice(1)], [copy.nodes[1], "plural", copy.term + "s"]]) { // a term is found in any case and with a plural ending
    const page = await kept(browser, copy.example, at, copy.level);
    const mark = page.locator(`#card .term[data-term="${copy.term}"]`);
    check(await mark.count() === 1 && await mark.first().textContent() === said, `marked ${at}: the ${form} term ${said} is not marked as ${copy.term}`);
    if (await mark.count()) check(await mark.first().evaluate((one) => getComputedStyle(one).textDecorationStyle === "dotted"), `marked ${at}: the term ${said} has no dotted underline, so a reader cannot tell it holds a meaning`);
    if (form === "plural" && await mark.count()) {
      await mark.first().hover();
      await rest(page);
      const drawn = await page.evaluate(() => { const box = document.getElementById("gloss"); return { math: !!box.querySelector("math"), code: !!box.querySelector("code"), marks: /[`$]/.test(box.textContent) }; });
      check(drawn.math && drawn.code && !drawn.marks, `marked ${at}: the meaning of ${copy.term} draws ${drawn.math ? "" : "no formula "}${drawn.code ? "" : "no code "}${drawn.marks ? "a backtick or a dollar as text" : ""}`);
    }
    quiet(page, `marked ${at}`);
    await page.context().close();
  }
  const story = copy.example.contract.scenarios.find((one) => one.id === copy.story), shown = await open(browser, copy.example, SIZES[0], { at: `#scenario=${story.id}&step=0&level=${copy.example.levelOf[story.steps[0].at]}` });
  const loose = await shown.evaluate(() => [...document.querySelectorAll(".term, .ref, .badge.guess")].filter((one) => !one.closest("#card dl")).map((one) => one.textContent));
  check(!loose.length, `marked ${story.id}: the page outside a card, such as a step's note, marks ${loose.join(", ")} as a term, a chip or a guess, which belong to a card's rows`);
  quiet(shown, `marked ${story.id}`);
  await shown.context().close();
}
let marked = null;
const OUTSIDE = [[String.raw`\foo{x}`, "is outside the subset"], [String.raw`\frac{a`, "is never closed"], ["a}", "closes nothing"], ["x_1_2", "a second `_` on one base"],
  [String.raw`\frac{a}`, "lacks what it takes"], [String.raw`\text x`, "takes its words in braces"]]; // a formula outside the subset, and the words check-contract.py refuses it with
function planted() { // a copy of the first example whose cards hold a guess, a claim of each status, quotes, a fence and formulas
  if (marked) return marked;
  const flat = JSON.parse(fs.readFileSync(examples[0].source, "utf8")), first = flat.levels[0].id, nodes = flat.nodes.filter((node) => node.level === first);
  check(nodes.length >= 4, `${examples[0].name}'s first level holds under four nodes`);
  const holds = (flat.claims || []).find((one) => (one.status || "holds") === "holds"), open = (flat.claims || []).filter((one) => one.status !== "holds" && one.status);
  check(holds && open.length, `${examples[0].name} holds no claim that holds or none that is open`);
  const fails = { ...open[0], id: "planted-fails", status: "fails" };
  flat.claims.push(fails);
  const term = flat.terms[0], story = flat.scenarios[0];
  story.steps[0].note = `a ${term.term} of {${nodes[0].id}} (guess)`;
  term.meaning += String.raw` It weighs $x^2$ and runs \`make-page.py\`.`;
  nodes[0].purpose = `${term.term[0].toUpperCase()}${term.term.slice(1)} work: run \`make-page.py\` once a writer marks a step (guess).`;
  nodes[1].purpose = `Read the ${term.term}s in this file:\n\`\`\`yaml\nfirst:\n  second\n\`\`\``;
  nodes[2].purpose = String.raw`Keep each mark within $\sqrt{x^2 + y_1^2} \le \alpha \cdot \sqrt[3]{\log n}$ of its record.`;
  nodes[3].purpose = String.raw`Rank each hit by its words: $$\frac{1}{n}\sum_{i=1}^{n} w_i \ne \pi, \quad {a+b}^2 < \infty \text{ for } \Gamma$$`;
  const source = path.join(scratch, "marked.json"), wrong = path.join(scratch, "marked-wrong.json");
  fs.writeFileSync(source, JSON.stringify(flat));
  const refused = JSON.parse(JSON.stringify(flat));
  refused.nodes.find((node) => node.id === nodes[2].id).purpose = `Keep ${OUTSIDE.map(([tex]) => `$${tex}$`).join(", ")} apart.`;
  refused.nodes.find((node) => node.id === nodes[3].id).label = String.raw`Rank $x$ hits`;
  refused.nodes.find((node) => node.id === nodes[0].id).purpose = "Run `make-page.py once a writer marks a step.";
  fs.writeFileSync(wrong, JSON.stringify(refused));
  marked = { example: make({ name: "marked", source, built: path.join(scratch, "marked.html") }), wrong, term: term.term, story: story.id, nodes: nodes.slice(0, 4).map((node) => node.id), holds: holds.id, unknown: open.find((one) => one.status === "unknown").id, fails: fails.id, level: first };
  return marked;
}
const homeOf = (copy, claim) => (claim.on || []).map((id) => copy.example.levelOf[id]).find(Boolean) || copy.level;
async function badges(browser) {
  const copy = planted(), claims = Object.fromEntries(copy.example.contract.claims.map((one) => [one.id, one]));
  const badged = async (id, level) => { const page = await kept(browser, copy.example, id, level); const seen = await page.evaluate(() => [...document.querySelectorAll("#card .badge")].map((one) => (getComputedStyle(one).backgroundColor === "rgba(0, 0, 0, 0)" ? "unfilled " : "") + one.textContent.trim())); quiet(page, `marked ${id}`); await page.context().close(); return seen; };
  const guess = await badged(copy.nodes[0], copy.level);
  check(guess.includes("guess"), `a text holding (guess) shows the badges [${guess}], none naming the guess`);
  for (const state of ["unknown", "fails"]) {
    const seen = await badged(copy[state], homeOf(copy, claims[copy[state]]));
    check(seen.includes(state), `a claim whose status is ${state} shows the badges [${seen}]`);
  }
  const settled = await badged(copy.holds, homeOf(copy, claims[copy.holds]));
  check(!settled.length, `a claim that holds shows the badges [${settled}]`);
}
const FILLS = { holds: [140, 30, 0.08], unknown: [265, 40, 0.04], conflicting: [65, 30, 0.08], fails: [25, 25, 0.1] }; // the hue each status's fill keeps within a turn of, and its least chroma
const face = (claim) => ({ guarantee: "G", assumption: "A" })[claim.kind] + ({ holds: "✓", unknown: "?", conflicting: "!", fails: "✗" })[claim.status || "holds"] + ((claim.status || "holds") === "holds" && claim.fault ? "*" : ""); // a badge's text
function tallied() { // a copy of the first example whose first level's first node holds five claims that hold, one named on it twice, one with no status, one first on another level and one with a fault, one unknown, one conflicting and one that fails, each of its edges but the last one claim that fails, and its first area one claim
  const flat = JSON.parse(fs.readFileSync(examples[0].source, "utf8")), first = flat.levels[0].id, nodes = flat.nodes.filter((node) => node.level === first), away = flat.nodes.find((node) => node.level !== first), area = (flat.areas || []).find((one) => one.level === first), edges = flat.edges.filter((edge) => nodes.some((node) => node.id === edge.from));
  check(nodes.length >= 2 && edges.length >= 2 && away && area, `${examples[0].name}'s first level holds under two nodes, two edges or one area, or no node lies on another level`);
  const planted = (id, status, on, fault = status && status !== "holds") => ({ id, title: id, kind: "guarantee", ...(status ? { status } : {}), statement: "Each planted record keeps its count.", on, ...(fault ? { fault: "missing" } : {}) });
  flat.claims = (flat.claims || []).concat([planted("planted-holds-one", "holds", [nodes[0].id]), planted("planted-holds-two", "holds", [nodes[0].id, nodes[0].id]), planted("planted-away", "holds", [away.id, nodes[0].id]), planted("planted-area", "holds", [area.id]), planted("planted-holds-bare", null, [nodes[0].id]),
    planted("planted-holds-fault", "holds", [nodes[0].id], true), planted("planted-unknown", "unknown", [nodes[0].id]), planted("planted-conflicting", "conflicting", [nodes[0].id]), planted("planted-fails-one", "fails", [nodes[0].id]), planted("planted-fails", "fails", edges.slice(0, -1).map((edge) => edge.id))]);
  const source = path.join(scratch, "tallied.json");
  fs.writeFileSync(source, JSON.stringify(flat));
  const example = make({ name: "tallied", source, built: path.join(scratch, "tallied.html") }), want = {};
  for (const claim of example.contract.claims) for (const id of new Set(claim.on || [])) (want[id] = want[id] || []).push(claim);
  const placed = Object.fromEntries([...flat.nodes, ...(flat.areas || [])].map((one) => [one.id, one.level]).concat(flat.edges.map((edge) => [edge.id, flat.nodes.find((node) => node.id === edge.from).level])));
  const homes = Object.fromEntries(flat.claims.map((one) => [one.id, (one.on || []).map((id) => placed[id]).find(Boolean) || first]));
  check(homes["planted-away"] === away.level && away.level !== first, "the planted claim first on another level is seen on the first level");
  return { example, level: first, node: nodes[0].id, area: area.id, homes, want, titles: Object.fromEntries(example.contract.claims.map((one) => [one.id, one.title])) };
}
const badgesOf = (page) => page.evaluate(() => { // each node's and edge's badges as drawn: text, fill, ink, whether a reader sees them, and what they cover or stray from
  const box = (rect) => ({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom }), meets = (one, other) => one.left < other.right - 0.5 && other.left < one.right - 0.5 && one.top < other.bottom - 0.5 && other.top < one.bottom - 0.5;
  const words = (element) => [...element.childNodes].filter((part) => part.nodeType === 3 && part.textContent.trim()).map((part) => { const range = document.createRange(); range.selectNodeContents(part); return box(range.getBoundingClientRect()); });
  const pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true }), canvas = getComputedStyle(document.body).backgroundColor;
  pen.canvas.width = pen.canvas.height = 1;
  const pixel = (color, under) => { pen.clearRect(0, 0, 1, 1); pen.fillStyle = under; pen.fillRect(0, 0, 1, 1); pen.fillStyle = color; pen.fillRect(0, 0, 1, 1); return [...pen.getImageData(0, 0, 1, 1).data].slice(0, 3); };
  const out = {};
  for (const holder of document.querySelectorAll("#stage .node[data-id], #stage .label[data-edge], #stage .area[data-id]")) {
    const id = holder.dataset.id || holder.dataset.edge, tucked = holder.classList.contains("tucked"), node = holder.classList.contains("node"), held = node || holder.classList.contains("area");
    const frame = box(holder.getBoundingClientRect()), reach = held ? 0.5 : 16;
    const covered = node ? [...holder.querySelectorAll(":scope > b, :scope > small")].flatMap(words).concat([...holder.querySelectorAll(":scope > .open")].map((one) => box(one.getBoundingClientRect()))) : [];
    for (const one of holder.querySelectorAll(":scope > .claims > .claim, :scope > header > .claims > .claim")) {
      const style = getComputedStyle(one), fill = pixel(style.backgroundColor, canvas), rect = one.getBoundingClientRect();
      const strays = held ? rect.left < frame.left - reach || rect.right > frame.right + reach || rect.top < frame.top - reach || rect.bottom > frame.bottom + reach : Math.max(frame.left - rect.right, rect.left - frame.right) > reach || Math.max(frame.top - rect.bottom, rect.top - frame.bottom) > reach; // a node or an area holds its badges, a label's sit within reach of it
      (out[id] = out[id] || []).push({ kind: one.dataset.status, text: one.textContent, fill, ink: pixel(style.color, `rgb(${fill.join(",")})`), seen: one.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && rect.width > 0, tucked, strays: strays && `${[rect.left, rect.top, rect.right, rect.bottom].map(Math.round)} against ${Object.values(frame).map(Math.round)}`, covers: covered.some((part) => meets(box(rect), part)) });
    }
  }
  return out;
});
const lit = (rgb) => { const [r, g, b] = rgb.map((c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
async function countBadges(browser, copy) { // each node's, edge's and area's badges say each claim on it, its kind and what it holds, in its status's colour, a tucked label's included
  let tucked = 0, bare = { node: 0, edge: 0 };
  const level = copy.example.contract.levels.find((one) => one.id === copy.level);
  for (const scheme of ["light", "dark"]) for (const size of SIZES) {
    const page = await open(browser, copy.example, size, { scheme, at: `#level=${copy.level}` }), where = `${scheme} at ${size.join("x")}`, seen = await badgesOf(page), fills = {};
    for (const [kind, group] of [["node", level.nodes], ["edge", level.edges || []], ["area", level.areas || []]]) for (const record of group) {
      const want = (copy.want[record.id] || []).map(face), drawn = (seen[record.id] || []).map((badge) => badge.text);
      check(same(want, drawn), `${where}: ${kind} ${record.id} shows the badges [${drawn}], not [${want}]`);
      if (!want.length && kind !== "area") bare[kind] += 1;
      for (const badge of seen[record.id] || []) {
        check(badge.seen, `${where}: the ${badge.text} badge of ${kind} ${record.id} is hidden${badge.tucked ? " with its tucked label" : ""}`);
        if (badge.tucked) tucked += 1;
        check(!badge.strays, `${where}: the ${badge.text} badge of ${kind} ${record.id} sits ${kind === "edge" ? "more than 16 px from its label's place" : `outside its ${kind}`}: ${badge.strays}`);
        check(!badge.covers, `${where}: the ${badge.text} badge of node ${record.id} covers its name, its tag or its open button`);
        const fill = oklab(badge.fill), [at, by, least] = FILLS[badge.kind], ratio = (Math.max(lit(badge.fill), lit(badge.ink)) + 0.05) / (Math.min(lit(badge.fill), lit(badge.ink)) + 0.05);
        check(chroma(fill) >= least && turn(hue(fill), at) <= by, `${where}: the ${badge.text} badge of ${record.id} is filled at chroma ${chroma(fill).toFixed(3)} and hue ${hue(fill).toFixed(0)}, not ${badge.kind}'s colour`);
        check(ratio >= 4.5, `${where}: the ${badge.text} badge of ${record.id} shows its text at ${ratio.toFixed(2)}:1 on its fill`);
        fills[badge.kind] = fill;
      }
    }
    const kinds = Object.keys(fills);
    check(kinds.length === 4, `${where}: the level shows badges of only ${kinds.join(", ")}`);
    for (const [i, one] of kinds.entries()) for (const other of kinds.slice(i + 1)) check(apart(fills[one], fills[other]) >= 0.08, `${where}: the ${one} and ${other} badges' fills are ${apart(fills[one], fills[other]).toFixed(3)} apart in oklab`);
    quiet(page, where);
    await page.context().close();
  }
  check(bare.node && bare.edge, `the copy's first level shows no node or no edge without claims, so a bare record's lack of badges is untested`);
  check(tucked, `no edge whose label is tucked held a badge at any size, so a tucked label's badges are untested`);
}
async function countLists(browser, copy) { // the pointer on each badge shows its record's card listing the claims on it, a click on it opens its claim, and each chip opens its claim
  const listed = (page) => page.evaluate(() => {
    const card = document.getElementById("card"), rows = {};
    for (let leaf = 0; leaf < 12; leaf++) {
      for (const row of card.querySelectorAll("dl > div")) rows[row.querySelector("dt").textContent] = [...row.querySelectorAll(".ref")].map((chip) => chip.dataset.ref);
      const turn = card.querySelector("footer .turn");
      if (!turn) break;
      turn.click();
      if (/^1–/.test(card.querySelector("footer .turn").textContent)) break;
    }
    return rows;
  });
  const level = copy.example.contract.levels.find((one) => one.id === copy.level), home = `#level=${copy.level}`;
  let jittered = false, stilled = false;
  const shown = await open(browser, copy.example, SIZES[1], { at: home }), tucked = await shown.evaluate(() => [...document.querySelectorAll("#stage .label.tucked[data-edge]")].filter((one) => one.querySelector(".claims")).map((one) => one.dataset.edge));
  await shown.context().close();
  const edge = (level.edges || []).find((one) => copy.want[one.id] && !tucked.includes(one.id)), targets = [copy.node, edge.id, copy.area, ...tucked]; // every tucked label's badges, since a lit label moves to a free place
  check(tucked.length, `no edge whose label is tucked holds a badge at ${SIZES[1].join("x")}, so the pointer on a tucked label's badge is untested`);
  for (const id of targets) {
    const page = await open(browser, copy.example, SIZES[1], { at: home }), wanted = copy.want[id].map((claim) => claim.id);
    const badges = page.locator(`#stage [data-id="${id}"] > .claims > .claim, #stage [data-id="${id}"] > header > .claims > .claim, #stage [data-edge="${id}"] > .claims > .claim`);
    check(await badges.count() === wanted.length, `${id} shows ${await badges.count()} badges, not ${wanted.length}`);
    for (let i = 0; i < wanted.length; i++) {
      await page.mouse.move(2, SIZES[1][1] - 2);
      const box = await badges.nth(i).boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2); // straight onto the badge, since a card a path raises on the way may cover it
      await page.clock.fastForward(450);
      await page.waitForFunction(CARDED, id, { timeout: 8000 }).catch(async () => { const [x, y] = [box.x + box.width / 2, box.y + box.height / 2], under = await page.evaluate(([x, y]) => { const one = document.elementFromPoint(x, y); return `${one && one.className} of ${one && (one.closest("[data-id], [data-edge]") || {}).dataset}`; }, [x, y]); throw new Error(`the pointer on the ${i + 1}. badge of ${id} raises no card for it, over ${under}`); });
      const rows = await listed(page);
      check(same(rows.claims, wanted), `the card under the ${i + 1}. badge of ${id} lists [${rows.claims}] under claims, not [${wanted}]`);
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await rest(page);
      const [held, at] = await page.evaluate((claim) => [location.hash.includes("at=" + encodeURIComponent(claim)) && document.getElementById("card").classList.contains("kept") && document.getElementById("card").dataset.for === claim, new URLSearchParams(location.hash.slice(1)).get("level")], wanted[i]);
      check(held && at === copy.homes[wanted[i]], `a click on the ${i + 1}. badge of ${id} keeps ${held ? "" : "no "}card for ${wanted[i]} on the level ${at}, not ${copy.homes[wanted[i]]}`);
      await page.goto("file://" + copy.example.built + home);
      await settled(page);
    }
    for (const claim of wanted) {
      await page.goto("file://" + copy.example.built + `${home}&at=${id}`);
      await settled(page);
      const chip = page.locator(`#card .ref[data-ref="${claim}"]`);
      for (let leaf = 0; leaf < 12 && !(await chip.count()); leaf++) await page.locator("#card footer .turn").click();
      check(await chip.count(), `the kept card of ${id} shows no chip for ${claim}`);
      const spot = await chip.first().boundingBox(), clicked = [spot.x + spot.width / 2, spot.y + spot.height / 2];
      await page.mouse.click(...clicked);
      await settled(page);
      await page.waitForTimeout(200); // the pointer that clicked rests over the diagram the card left, long enough for a hover to raise a card
      await page.clock.fastForward(900);
      await settled(page);
      const [head, at] = await page.evaluate((claim) => { const card = document.getElementById("card"); return [card.classList.contains("show") && card.dataset.for === claim ? card.querySelector("h2").textContent : null, new URLSearchParams(location.hash.slice(1)).get("level")]; }, claim);
      check(head === copy.titles[claim], `a click on the chip for ${claim} in the card of ${id} shows the card ${head}, not one headed ${copy.titles[claim]}`);
      const there = copy.homes[claim]; // a claim is seen on the level of the first record it names
      check(at === there, `a click on the chip for ${claim} in the card of ${id} shows the level ${at}, not ${there}`);
      if (!jittered) jittered = await jitter(page, claim, clicked);
      if (!stilled && await page.evaluate(([x, y]) => { const one = document.elementFromPoint(x, y); return !!(one && one.closest("#stage [data-id], #stage [data-edge]")); }, clicked))
        stilled = await clickedResting(page, `${home}&at=${id}`, copy.example, claim, clicked); // a record the card uncovers, which a hover would raise
    }
    quiet(page, `the badges of ${id}`);
    await page.context().close();
  }
  check(stilled, "no chip has a record under it once its card leaves, so a click by a resting pointer is untested");
  const kept = await open(browser, copy.example, SIZES[1], { at: `${home}&at=${copy.node}` });
  const faded = await kept.evaluate((node) => [...document.querySelectorAll("#stage .claims")].map((group) => { // each badge group's opacity as drawn, its holders' multiplied in
    let shown = 1;
    for (let at = group; at && at.id !== "stage"; at = at.parentElement) shown *= Number(getComputedStyle(at).opacity);
    const holder = group.closest("[data-id], [data-edge]");
    return { id: holder.dataset.id || holder.dataset.edge, dim: !!group.closest(".dim"), shown, own: holder.dataset.id === node };
  }), copy.node);
  await kept.context().close();
  check(faded.some((one) => one.dim), `with the card of ${copy.node} kept no record holding badges is dimmed, so a dimmed record's badges are untested`);
  for (const one of faded) check(one.own ? one.shown === 1 : !one.dim || one.shown <= 0.75, `with the card of ${copy.node} kept the badges of ${one.dim ? "the dimmed " : ""}${one.id} show at opacity ${one.shown.toFixed(2)}`);
}
async function clickedResting(page, hash, example, claim, [x, y]) { // a hand resting on the chip since the page loaded clicks it unmoved, so no pointermove says where it is, then shakes, yet what the card uncovered raises no card
  await page.mouse.move(x, y);
  await page.goto("about:blank");
  await page.goto("file://" + example.built + hash);
  await settled(page);
  const chip = page.locator(`#card .ref[data-ref="${claim}"]`);
  for (let leaf = 0; leaf < 12 && !(await chip.count()); leaf++) await page.evaluate(() => document.querySelector("#card footer .turn").click()); // a click by script, since the pointer must not move
  const spot = await chip.first().boundingBox();
  check(spot && Math.abs(spot.x + spot.width / 2 - x) < 1 && Math.abs(spot.y + spot.height / 2 - y) < 1, `the chip for ${claim} stands elsewhere once its page loads again`);
  await page.mouse.down();
  await page.mouse.up();
  await settled(page);
  await page.mouse.move(Math.trunc(x) + 1, Math.trunc(y)); // a pixel from where the click landed, the page's click spot being whole pixels
  await page.clock.fastForward(900);
  await settled(page);
  check(await page.evaluate(CARDED, claim), `a pointer resting on the chip for ${claim} since its page loaded, clicking it and shaking 1 px, shows no card for ${claim}`);
  return true;
}
async function jitter(page, claim, [x, y]) { // a hand still on the chip it clicked shakes by a pixel or two and raises no card from what it comes over, yet a real move does
  const node = await page.evaluate(() => { const one = document.querySelector("#stage .node[data-id]"); return one && one.dataset.id; });
  check(node, `the level of ${claim} shows no node to come over`);
  const over = (dx) => page.evaluate(([x, y, dx, node]) => { // the pointer moved DX px from where it clicked, then coming over NODE, so only the distance tells
    dispatchEvent(new PointerEvent("pointermove", { clientX: x + dx, clientY: y, bubbles: true }));
    document.querySelector(`#stage [data-id="${node}"]`).dispatchEvent(new PointerEvent("pointerover", { clientX: x + dx, clientY: y, bubbles: true }));
  }, [x, y, dx, node]);
  await over(2);
  await page.clock.fastForward(900);
  await settled(page);
  check(await page.evaluate(CARDED, claim), `a pointer moved 2 px from the chip for ${claim} it clicked raised a card from what it came over`);
  await over(2.5);
  await page.clock.fastForward(900);
  await settled(page);
  check(await page.evaluate(CARDED, node), `a pointer moved 2.5 px from the chip for ${claim} it clicked raised no card for the node ${node} it came over`);
  return true;
}
async function counts(browser) {
  const copy = tallied(), lines = [];
  for (const [name, work] of [["count badges", countBadges], ["count lists", countLists]]) lines.push(await work(browser, copy).then(() => `${name}: PASS`, (error) => `${name}: FAIL, ${error.message.split("\n")[0]}`));
  lines.forEach((line) => console.log(line));
  check(lines.every((line) => line.endsWith(": PASS")), lines.find((line) => !line.endsWith(": PASS")));
}
async function note(browser) { // each step's note: a bar in the scenario mark's hue and a `Step <n>` heading, where no edge label has a border
  let read = 0;
  await each(examples.flatMap((example) => SIZES.map((size) => [example, size])), async ([example, size]) => {
    const page = await open(browser, example, size);
    for (const scenario of example.contract.scenarios || []) for (const [i, step] of scenario.steps.entries()) if (step.note) {
      await page.goto("file://" + example.built + "#scenario=" + scenario.id + "&step=" + i + "&level=" + example.levelOf[step.at]);
      await rest(page);
      const where = `${example.name} ${scenario.id} step ${i + 1} at ${size.join("x")}`;
      const seen = await page.evaluate(() => {
        const pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true }), canvas = getComputedStyle(document.body).backgroundColor;
        pen.canvas.width = pen.canvas.height = 1;
        const pixel = (color) => { pen.clearRect(0, 0, 1, 1); pen.fillStyle = canvas; pen.fillRect(0, 0, 1, 1); pen.fillStyle = color; pen.fillRect(0, 0, 1, 1); return [...pen.getImageData(0, 0, 1, 1).data].slice(0, 3); };
        const chip = document.getElementById("chip"), style = getComputedStyle(chip), probe = document.body.appendChild(document.createElement("div"));
        probe.style.color = "var(--mark)";
        const mark = pixel(getComputedStyle(probe).color), head = chip.firstElementChild;
        probe.remove();
        return { shown: chip.classList.contains("show"), bar: parseFloat(style.borderLeftWidth), color: pixel(style.borderLeftColor), mark, head: head ? head.textContent : "", ink: head ? pixel(getComputedStyle(head).color) : null,
          styled: [...document.querySelectorAll(".count")].filter((one) => !one.closest(".counts") && (getComputedStyle(one).boxShadow !== "none" || getComputedStyle(one).borderRadius !== "0px")).map((one) => one.parentElement.id || one.parentElement.className),
          bordered: [...document.querySelectorAll("#stage .label")].filter((label) => ["Top", "Right", "Bottom", "Left"].some((side) => parseFloat(getComputedStyle(label)[`border${side}Width`]) > 0)).map((label) => label.dataset.edge) };
      });
      const mark = hue(oklab(seen.mark));
      check(seen.shown, `${where}: the note is not shown`);
      check(seen.bar >= 3 && chroma(oklab(seen.color)) >= 0.1 && turn(hue(oklab(seen.color)), mark) <= 20, `${where}: the note's left bar is ${seen.bar} px at chroma ${chroma(oklab(seen.color)).toFixed(3)}, hue ${hue(oklab(seen.color)).toFixed(0)} against the mark's ${mark.toFixed(0)}`);
      check(seen.head === `Step ${i + 1}` && seen.ink && turn(hue(oklab(seen.ink)), mark) <= 20 && chroma(oklab(seen.ink)) >= 0.1, `${where}: the note opens with ${JSON.stringify(seen.head)}, not Step ${i + 1} in the mark's hue`);
      check(!seen.bordered.length, `${where}: the labels of ${seen.bordered.join(", ")} show a border`);
      check(!seen.styled.length, `${where}: a count outside the badges, in ${seen.styled.join(", ")}, takes a badge's ring or rounding`);
      read += 1;
    }
    quiet(page, `${example.name} at ${size.join("x")}`);
    await page.context().close();
  });
  check(read, "no example step holds a note");
  console.log(`${read} step notes at three sizes show a bar and a step heading in the mark's hue`);
}
async function formulas(browser) {
  const self = examples.find((example) => JSON.stringify(example.contract).includes("$$")), copy = planted();
  check(self, "no example holds a display formula");
  const read = async (example, id, level) => {
    const page = await kept(browser, example, id, level);
    const seen = await page.evaluate(() => {
      const card = document.getElementById("card"), box = (element) => element.getBoundingClientRect();
      return [...card.querySelectorAll("math")].map((math) => {
        const rect = box(math), inner = box(math.firstElementChild), around = math.closest("dd"), text = [...around.childNodes[0].childNodes].filter((node) => node.nodeType === 3 && node.textContent.trim());
        const lines = text.map((node) => { const range = document.createRange(); range.selectNodeContents(node); return [...range.getClientRects()]; }).flat();
        return {
          display: math.getAttribute("display"), shown: getComputedStyle(math).display, parts: [...math.querySelectorAll("*")].map((one) => one.localName), signs: math.textContent,
          upright: [...math.querySelectorAll('mi[mathvariant="normal"]')].map((one) => one.textContent), grouped: [...math.querySelectorAll("msup")].some((one) => one.firstElementChild.localName === "mrow"),
          beside: lines.some((line) => line.top < rect.bottom && rect.top < line.bottom), alone: lines.every((line) => line.bottom <= rect.top + 1 || line.top >= rect.bottom - 1),
          centered: Math.abs((inner.left + inner.right) / 2 - (rect.left + rect.right) / 2) < 2 && rect.width >= around.getBoundingClientRect().width - 2,
        };
      }).concat([{ tex: /\$|\\[a-z]/.test(card.querySelector("dl").textContent) }]);
    });
    quiet(page, `${example.name} ${id}`);
    await page.context().close();
    return seen;
  };
  const shape = (seen, where) => {
    check(!seen.pop().tex, `${where}: the card still shows TeX`);
    for (const one of seen) {
      if (one.display === "inline") check(one.beside && !one.shown.startsWith("block"), `${where}: an inline formula is drawn as ${one.shown}, ${one.beside ? "" : "off its sentence's line"}`);
      else check(one.display === "block" && one.shown.startsWith("block") && one.alone && one.centered, `${where}: a display formula is drawn as ${one.shown}, ${one.alone ? "" : "beside its text, "}${one.centered ? "centered" : "not centered"}`);
    }
    return seen;
  };
  const found = [];
  for (const record of records(self).filter(({ record }) => JSON.stringify(record).includes("$"))) found.push(...shape(await read(self, record.record.id, record.level), `${self.name} ${record.record.id}`));
  check(found.some((one) => one.display === "inline") && found.some((one) => one.display === "block"), `${self.name} draws ${found.length} formulas, not an inline and a display one`);
  const inline = shape(await read(copy.example, copy.nodes[2], copy.level), "marked inline"), display = shape(await read(copy.example, copy.nodes[3], copy.level), "marked display");
  check(inline.length === 1 && inline[0].display === "inline" && display.length === 1 && display[0].display === "block", "the planted formulas do not draw as one inline and one display formula");
  const parts = inline[0].parts.concat(display[0].parts), signs = inline[0].signs + display[0].signs;
  for (const part of ["mfrac", "msqrt", "mroot", "munderover", "msubsup", "msup", "msub", "mspace", "mtext"]) check(parts.includes(part), `the planted formulas draw no ${part}`);
  for (const sign of ["∑", "α", "π", "≤", "≠", "<", "∞", "log", "⋅", "Γ"]) check(signs.includes(sign), `the planted formulas draw no ${sign}`);
  check(!/undefined|null|None/.test(signs), `the planted formulas draw a missing part as text: ${signs}`);
  check(display[0].upright.includes("Γ") && display[0].grouped, `the planted display formula draws ${display[0].upright.includes("Γ") ? "" : "a capital Greek letter slanted"}${display[0].grouped ? "" : " a braced group's power on its last part alone"}`);
  const refused = python(path.join(ROOT, "scripts", "check-contract.py"), "check", copy.wrong);
  check(refused.status === 1, "check-contract.py accepts formulas outside the subset");
  for (const [tex, why] of OUTSIDE) check(refused.stdout.split("\n").some((line) => line.includes(`formula: \`${tex}\``) && line.includes(why)), `check-contract.py does not refuse the formula ${tex} as one that ${why}`);
  check(refused.stdout.includes("holds a formula;"), "check-contract.py accepts a label that holds a formula");
  check(refused.stdout.includes("opens a backtick it never closes"), "check-contract.py accepts a text whose backtick is never closed");
}
async function code(browser) {
  const copy = planted();
  const page = await kept(browser, copy.example, copy.nodes[0], copy.level);
  const inline = await page.evaluate(() => {
    const card = document.getElementById("card"), quote = card.querySelector("dd code"), line = quote && quote.getBoundingClientRect(), before = quote && quote.previousSibling;
    const range = document.createRange();
    if (before) range.selectNodeContents(before);
    return { found: !!quote && !quote.closest("pre"), text: quote ? quote.textContent : "", beside: !!before && [...range.getClientRects()].some((one) => one.top < line.bottom && line.top < one.bottom), ticks: card.querySelector("dl").textContent.includes("`") };
  });
  check(inline.found && inline.text === "make-page.py" && inline.beside, `a backtick span draws as ${inline.found ? `code "${inline.text}"${inline.beside ? "" : " off its sentence's line"}` : "no inline code"}`);
  check(!inline.ticks, "a card with inline code still shows a backtick");
  await page.context().close();
  const fenced = await kept(browser, copy.example, copy.nodes[1], copy.level);
  const block = await fenced.evaluate(() => {
    const card = document.getElementById("card"), pre = card.querySelector("dd pre"), text = pre && pre.previousSibling, range = document.createRange();
    if (text) range.selectNodeContents(text);
    const rect = pre && pre.getBoundingClientRect();
    return { found: !!pre, text: pre ? pre.textContent : "", space: pre ? getComputedStyle(pre).whiteSpace : "", alone: !!pre && [...range.getClientRects()].every((one) => one.bottom <= rect.top + 1), ticks: card.querySelector("dl").textContent.includes("`") };
  });
  check(block.found && block.text === "first:\n  second" && block.space.startsWith("pre") && block.alone, `a fence draws as ${block.found ? `a block holding ${JSON.stringify(block.text)} with white-space ${block.space}${block.alone ? "" : ", beside its text"}` : "no block"}`);
  check(!block.ticks, "a card with a fence still shows a backtick");
  quiet(fenced, "marked fence");
  await fenced.context().close();
}

async function tables(browser) {
  await Promise.all(examples.map(async (example) => {
    const held = records(example).find(({ record }) => JSON.stringify(record.info || {}).includes('"columns"'));
    check(held, `${example.name}: no card holds a table`);
    const page = await kept(browser, example, held.record.id, held.level);
    const shown = () => page.evaluate(() => [...document.querySelectorAll("#card table")].some((one) => one.getClientRects().length));
    for (let leaf = 0; leaf < 12 && !(await shown()) && (await page.locator("#card .turn").count()); leaf++) await page.click("#card .turn");
    const seen = await page.evaluate(() => {
      const table = [...document.querySelectorAll("#card table")].find((one) => one.getClientRects().length);
      if (!table) return null;
      const lines = (element) => { const style = getComputedStyle(element); return ["Top", "Right", "Bottom", "Left"].filter((side) => parseFloat(style[`border${side}Width`]) > 0 && style[`border${side}Style`] !== "none" && style[`border${side}Color`] !== "rgba(0, 0, 0, 0)").map((side) => `${element.localName} ${side.toLowerCase()}`); };
      const head = table.querySelector("th"), cell = table.querySelector("td");
      return { lines: [...new Set([table, ...table.querySelectorAll("thead, tbody, tr, th, td")].flatMap(lines))], heavier: parseInt(getComputedStyle(head).fontWeight, 10) >= 500, muted: getComputedStyle(head).color !== getComputedStyle(cell).color, rows: table.querySelectorAll("tbody tr").length };
    });
    check(seen, `${example.name} ${held.record.id}: the kept card draws no table`);
    check(!seen.lines.length, `${example.name} ${held.record.id}: the card's table draws lines on ${seen.lines.join(", ")}`);
    check(seen.heavier && seen.muted, `${example.name} ${held.record.id}: the table's header reads ${seen.muted ? "" : "in the cells' color"}${seen.heavier ? "" : " at a light weight"}, not apart from its rows`);
    quiet(page, `${example.name} ${held.record.id}`);
    await page.context().close();
  }));
}
// ---- wrap ----
const NOTES = [ // Korean descriptions of 150 characters or more, which wrap only between words
  "사람이 페이지에서 남긴 의견은 서버가 받아 대기열에 넣고, 세션이 의견을 읽어 파일을 고칠 때까지 기다립니다. 세션이 파일을 고치면 페이지는 바뀐 내용을 다시 불러와 보여 주며, 의견 옆에는 세션이 남긴 답글이 함께 나타납니다. 사람은 파일을 직접 열지 않고도 요청한 수정이 끝났는지 확인합니다.",
  "연결이 열리면 표시줄은 서버와 이어졌다는 사실과 아직 처리하지 않은 변경의 개수를 함께 보여 줍니다. 사람은 표시줄만 보고도 자신이 남긴 의견이 서버에 닿았는지, 세션이 아직 읽지 않았는지를 곧바로 알 수 있습니다. 개수가 영이 되면 세션이 모든 변경을 읽었다는 뜻입니다.",
  "사람이 문서의 한 부분에 의견을 달면 페이지는 그 부분의 위치와 의견의 내용을 하나로 묶어 기록합니다. 기록은 서버로 보내지기 전까지 브라우저 저장소에 남아 있으므로, 창을 닫았다가 다시 열어도 사라지지 않습니다. 서버가 기록을 받으면 브라우저 저장소의 사본은 곧바로 지워집니다.",
];
const LONGWORD = "Extraordinarilylongcompoundidentifierword"; // one word of 40 letters
const spread = ([selector, frame]) => { // per shown element: the lines its text takes, the first word split across two lines and the first word past its box or FRAME, such as a card that clips it
  const lines = (tops) => tops.sort((a, b) => a - b).filter((top, i, all) => !i || top - all[i - 1] > 6).length; // glyphs of one line differ in top by a pixel or two
  return [...document.querySelectorAll(selector)].filter((element) => element.getClientRects().length).map((element) => {
    const own = element.getBoundingClientRect(), outer = frame ? element.closest(frame).getBoundingClientRect() : own, tops = [], found = { text: element.textContent, split: "", out: "", wide: element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1 };
    const box = { left: Math.max(own.left, outer.left), right: Math.min(own.right, outer.right), top: Math.max(own.top, outer.top), bottom: Math.min(own.bottom, outer.bottom) };
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let text = walker.nextNode(); text; text = walker.nextNode()) for (const word of text.data.matchAll(/\S+/g)) {
      const range = document.createRange();
      range.setStart(text, word.index);
      range.setEnd(text, word.index + word[0].length);
      const rects = [...range.getClientRects()].filter((rect) => rect.width > 0.5);
      tops.push(...rects.map((rect) => rect.top));
      if (!found.split && lines(rects.map((rect) => rect.top)) > 1) found.split = word[0];
      if (!found.out && rects.some((rect) => rect.left < box.left - 0.5 || rect.right > box.right + 0.5 || rect.top < box.top - 0.5 || rect.bottom > box.bottom + 0.5)) found.out = word[0];
    }
    return { ...found, lines: lines(tops), inside: own.left >= 0 && own.top >= 0 && own.right <= innerWidth && own.bottom <= innerHeight };
  });
};
const unbroken = (seen, where) => seen.forEach((one) => {
  check(!one.split, `${where}: the word ${one.split} is split across two lines`);
  check(!one.out && !one.wide, `${where}: ${one.out ? "the word " + one.out : "the text"} reaches past its box or is cut off`);
});
async function wrap(browser) {
  const example = examples[0], flat = JSON.parse(fs.readFileSync(example.source, "utf8")), node = flat.nodes[0], scenario = flat.scenarios[0];
  NOTES.forEach((note) => check(note.length >= 150, `a planted note is ${note.length} characters, under 150`));
  scenario.steps.slice(0, NOTES.length).forEach((step, i) => { step.note = NOTES[i]; });
  node.purpose = NOTES[0];
  node.info = { ...(node.info || {}), failure: { columns: ["경우", "일어나는 일", "사람이 보는 것", "다시 시도하는 방법"], rows: [[NOTES[1].slice(0, 40), NOTES[2].slice(0, 60), NOTES[0].slice(0, 50), NOTES[1].slice(40, 90)]] } };
  node.label = `${node.label} ${LONGWORD}`;
  const copy = { name: example.name + "-wrap", source: path.join(scratch, example.name + "-wrap.json"), built: path.join(scratch, example.name + "-wrap.html") };
  fs.writeFileSync(copy.source, JSON.stringify(flat));
  make(copy);
  await Promise.all(SIZES.map(async (size) => {
    const where = `${copy.name} at ${size.join("x")}`;
    let page = await open(browser, copy, size, { still: true });
    await page.click("#scenarios");
    await page.click(`#hits [data-hit="${scenario.id}"]`);
    await rest(page);
    for (let i = 0; i < NOTES.length; i++) {
      if (i) { await page.keyboard.press("ArrowRight"); await rest(page); }
      const [chip] = await page.evaluate(spread, ["#chip.show > span", "#chip"]); // the note under its step heading
      check(chip && chip.text === NOTES[i], `${where} step ${i + 1}: the note shows ${chip ? chip.text.length + " of " + NOTES[i].length + " characters" : "nothing"}`);
      check(chip.lines >= 2 && chip.inside, `${where} step ${i + 1}: the note takes ${chip.lines} line${chip.lines === 1 ? "" : "s"}${chip.inside ? "" : " and reaches past the window"}`);
      unbroken([chip], `${where} step ${i + 1}'s note`);
    }
    quiet(page, where);
    await page.context().close();
    page = await open(browser, copy, size, { at: `#level=${node.level}&at=${node.id}` });
    await settled(page);
    check(await page.evaluate(CARDED, node.id), `${where}: no card is kept open for ${node.id}`);
    const label = await page.evaluate(spread, [`#stage .node[data-id="${node.id}"] b`, ".node"]);
    check(label.length === 1 && label[0].text === node.label, `${where}: node ${node.id} does not show its label`);
    unbroken(label, `${where}: node ${node.id}'s label`);
    const card = [], cells = [];
    for (let leaf = 0; leaf < 12; leaf++) { // each page of the kept card, turned by its More rows button as a person would
      const seen = await page.evaluate(spread, ["#card h2, #card p, #card dd, #card th, #card td", "#card"]);
      card.push(...seen);
      cells.push(...(await page.evaluate(spread, ["#card td", "#card"])));
      if (!(await page.locator("#card .turn").count()) || await page.evaluate(() => document.querySelector("#card .turn").disabled)) break;
      await page.click("#card .turn");
      await rest(page);
    }
    check(card.some((one) => one.text.includes(NOTES[0])), `${where}: the kept card of ${node.id} does not show its purpose`);
    check(cells.length >= 4, `${where}: the kept card of ${node.id} shows ${cells.length} of the planted table's 4 cells`);
    unbroken(card, `${where}: the kept card of ${node.id}`);
    quiet(page, where);
    await page.context().close();
  }));
}
// ---- layout ----
const GROUPS = ["card head", "card item", "card footer", "search hit", "search kind", "search keys", "tools", "scenario bar", "node", "area header"];
const PRINCIPLES = ["proximity", "common region", "alignment", "scale", "contrast"];
const FAULTS = { // one fault per principle, as a rule added to a page with a card kept
  proximity: "#card h2 { margin-bottom: 24px; }",
  "common region": "#card h2 { position: relative; left: -32px; }",
  alignment: "#card dt { margin-left: 4px; }",
  scale: "#card dl { row-gap: 7px; }",
  contrast: "#card dt { color: color-mix(in oklab, var(--popover) 80%, var(--foreground)); }",
};
// What the page shows breaks of each kept layout principle, measured on the ink a reader sees: each text's line boxes,
// each icon, and each part drawn with its own fill or border.
const principles = (page) => page.evaluate(() => {
  const SCALE = [0, 2, 4, 8, 12, 16, 24, 32];
  const found = { proximity: [], "common region": [], alignment: [], scale: [], contrast: [] }, counts = { proximity: 0, "common region": 0, alignment: 0, scale: 0, contrast: 0 }, groups = new Set();
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const shown = (element) => { const rect = element.getBoundingClientRect(), style = getComputedStyle(element); return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none"; };
  const named = (element) => element.id ? "#" + element.id : (element.closest("[id]") ? "#" + element.closest("[id]").id + " " : "") + element.tagName.toLowerCase() + (element.classList.length ? "." + [...element.classList].join(".") : "");
  const painted = (style) => style.backgroundColor !== "rgba(0, 0, 0, 0)" || ["Top", "Right", "Bottom", "Left"].some((side) => parseFloat(style[`border${side}Width`]) > 0 && style[`border${side}Style`] !== "none");
  const meet = (a, b) => ({ left: Math.max(a.left, b.left), top: Math.max(a.top, b.top), right: Math.min(a.right, b.right), bottom: Math.min(a.bottom, b.bottom) });
  const real = (box) => box.right - box.left > 0.5 && box.bottom - box.top > 0.5;
  const plain = (rect) => ({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom });
  const ink = (root) => { // the boxes a reader sees of ROOT, cut where an ellipsis or a scroll cuts them on purpose
    const boxes = [];
    const walk = (element, clip, top) => {
      if (!shown(element)) return;
      const style = getComputedStyle(element), rect = plain(element.getBoundingClientRect());
      if (element.tagName === "INPUT") { const middle = (rect.top + rect.bottom) / 2, line = parseFloat(style.lineHeight) / 2; boxes.push({ left: rect.left + parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft), right: rect.right - parseFloat(style.borderRightWidth) - parseFloat(style.paddingRight), top: middle - line, bottom: middle + line }); return; }
      if (element instanceof SVGElement || painted(style) || element.tagName === "TABLE") { const box = meet(rect, clip); if (real(box)) boxes.push(box); return; } // a table reads as one block, its cells held by its columns
      const cuts = style.textOverflow === "ellipsis" || /auto|scroll/.test(style.overflowY + style.overflowX);
      const inner = cuts ? meet(clip, rect) : clip;
      for (const child of element.childNodes) {
        if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
          const range = document.createRange();
          range.selectNodeContents(child);
          for (const line of range.getClientRects()) { const box = meet(plain(line), inner); if (real(box)) boxes.push(box); }
        } else if (child.nodeType === Node.ELEMENT_NODE) walk(child, inner, false);
      }
    };
    walk(root, { left: -1e6, top: -1e6, right: 1e6, bottom: 1e6 }, true);
    return boxes;
  };
  const gap = (a, b) => Math.max(0, a.left - b.right, b.left - a.right, a.top - b.bottom, b.top - a.bottom);
  const spread = (boxes) => { // the largest gap that still joins every box, the longest link of their shortest joining tree
    if (boxes.length < 2) return 0;
    const reach = boxes.map(() => Infinity), joined = boxes.map(() => false);
    let most = 0;
    reach[0] = 0;
    for (let turn = 0; turn < boxes.length; turn++) {
      let next = -1;
      for (let i = 0; i < boxes.length; i++) if (!joined[i] && (next < 0 || reach[i] < reach[next])) next = i;
      joined[next] = true;
      most = Math.max(most, reach[next]);
      for (let i = 0; i < boxes.length; i++) if (!joined[i]) reach[i] = Math.min(reach[i], gap(boxes[next], boxes[i]));
    }
    return most;
  };
  const apart = (a, b) => Math.min(...a.flatMap((one) => b.map((other) => gap(one, other))));
  const near = (kind, where, sets) => { // each group's inner spread is at most half its gap to the nearest group of the same set
    groups.add(kind);
    const inked = sets.map((parts) => parts.filter(Boolean).flatMap(ink)).filter((boxes) => boxes.length);
    inked.forEach((boxes, i) => {
      counts.proximity += 1;
      const inner = spread(boxes), outer = Math.min(Infinity, ...inked.filter((other, j) => j !== i).map((other) => apart(boxes, other)));
      if (outer < Infinity && inner > outer / 2 + 0.5) found.proximity.push(`${where} ${kind} ${i + 1}: ${inner.toFixed(1)} px inside, ${outer.toFixed(1)} px to the next group`);
    });
  };
  const framed = (frame, parts) => { // every part's ink inside its frame's border
    const rect = frame.getBoundingClientRect(), style = getComputedStyle(frame);
    const inside = { left: rect.left + parseFloat(style.borderLeftWidth) - 0.5, top: rect.top + parseFloat(style.borderTopWidth) - 0.5, right: rect.right - parseFloat(style.borderRightWidth) + 0.5, bottom: rect.bottom - parseFloat(style.borderBottomWidth) + 0.5 };
    for (const part of parts.filter(Boolean)) for (const box of ink(part)) {
      counts["common region"] += 1;
      const past = Math.max(inside.left - box.left, inside.top - box.top, box.right - inside.right, box.bottom - inside.bottom);
      if (past > 0) { found["common region"].push(`${named(part)} reaches ${past.toFixed(1)} px past ${named(frame)}`); return; }
    }
  };
  const lined = (where, edge, parts) => { // the parts that open a column share its start (or end) edge
    const at = parts.filter(Boolean).map((part) => ({ part, boxes: ink(part) })).filter((one) => one.boxes.length).map((one) => ({ part: one.part, x: edge === "start" ? Math.min(...one.boxes.map((box) => box.left)) : Math.max(...one.boxes.map((box) => box.right)) }));
    if (at.length < 2) return;
    counts.alignment += 1;
    const low = Math.min(...at.map((one) => one.x)), high = Math.max(...at.map((one) => one.x));
    if (high - low > 1) found.alignment.push(`${where}: ${at.map((one) => `${named(one.part)} at ${one.x.toFixed(1)}`).join(", ")} do not share one ${edge} edge`);
  };
  const SIDES = ["marginTop", "marginRight", "marginBottom", "marginLeft", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "rowGap", "columnGap"];
  const stepped = (roots) => { // every space of these parts is a step of the scale
    for (const element of roots.filter(Boolean).flatMap((root) => [root, ...$$("*", root)])) {
      if (!shown(element) || element instanceof SVGElement) continue;
      const style = getComputedStyle(element);
      for (const side of SIDES) {
        const value = parseFloat(style[side]);
        if (Number.isNaN(value) || value < 0 || (side.startsWith("margin") && String(element.computedStyleMap().get(side.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase()))) === "auto")) continue; // an auto margin pushes a part to the far side, no space of the scale
        counts.scale += 1;
        if (!SCALE.some((step) => Math.abs(step - value) < 0.05)) found.scale.push(`${named(element)} ${side.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase())} ${value} px`);
      }
    }
  };
  const pen = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  pen.canvas.width = pen.canvas.height = 1;
  const rgba = (color) => { pen.clearRect(0, 0, 1, 1); pen.fillStyle = "#000"; pen.fillStyle = color; pen.fillRect(0, 0, 1, 1); const [r, g, b, a] = pen.getImageData(0, 0, 1, 1).data; return [r, g, b, a / 255]; };
  const over = (top, under) => top.slice(0, 3).map((value, i) => value * top[3] + under[i] * (1 - top[3])).concat(1);
  const ground = (element) => { // the colour behind ELEMENT, its ancestors' fills laid over the page's
    const fills = [];
    for (let at = element; at; at = at.parentElement) fills.unshift(rgba(getComputedStyle(at).backgroundColor));
    return fills.reduce((under, fill) => over(fill, under), [255, 255, 255, 1]);
  };
  const light = (color) => { const [r, g, b] = color.slice(0, 3).map((value) => { value /= 255; return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const legible = (roots) => { // every text of these parts shows, at 4.5:1 or more on its ground
    for (const root of roots.filter(Boolean)) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let text = walker.nextNode(); text; text = walker.nextNode()) {
        const holder = text.parentElement;
        if (!text.textContent.trim() || holder.closest(".label.tucked:not(.shown), [hidden], script, style, .sep, #run .pause, #run .start")) continue;
        counts.contrast += 1;
        let fade = 1;
        for (let at = holder; at; at = at.parentElement) fade *= parseFloat(getComputedStyle(at).opacity);
        if (fade < 0.99 || !shown(holder)) { found.contrast.push(`${named(holder)} "${text.textContent.trim().slice(0, 24)}" is hidden or faded`); continue; }
        const under = ground(holder), ratio = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05), value = ratio(light(over(rgba(getComputedStyle(holder).color), under)), light(under));
        if (value < 4.5) found.contrast.push(`${named(holder)} "${text.textContent.trim().slice(0, 24)}" at ${value.toFixed(2)}:1`);
      }
    }
  };
  const card = document.getElementById("card"), palette = document.getElementById("palette"), play = document.getElementById("play");
  if (card.classList.contains("show")) {
    const items = $$("dl > div", card), foot = card.querySelector("footer");
    near("card head", "card", [[card.querySelector("h2"), ...$$(".tag", card)], [card.querySelector("dl")]]); // the footer is parted by its rule, which common region reads
    near("card item", "card", items.map((item) => [item]));
    near("card footer", "card", [[foot.querySelector(".turn")], ...$$(".hints > span", foot).map((hint) => [hint])]);
    if (!card.classList.contains("long")) framed(card, [...card.children]);
    lined("card", "start", [card.querySelector("h2"), card.querySelector(".tag"), ...$$("dt", card), foot.querySelector(".turn")]);
    stepped([card]); legible([card]);
  }
  if (palette.classList.contains("show")) {
    const kinds = [];
    for (const element of $$("#hits > *")) if (element.tagName === "H3" || !kinds.length) kinds.push([element]); else kinds[kinds.length - 1].push(element);
    near("search kind", "search", kinds.map((kind) => kind.flatMap((element) => element.classList.contains("hit") ? [...element.children] : [element])));
    near("search hit", "search", $$("#hits .hit").map((hit) => [...hit.children]));
    near("search keys", "search", $$("#keys > span").map((key) => [key]));
    framed(palette, [document.getElementById("query"), document.getElementById("keys")]);
    for (const hit of $$("#hits .hit")) framed(hit, [...hit.children]);
    lined("search", "start", [document.getElementById("query"), ...$$("#hits h3"), ...$$("#hits .hit .text > b")]);
    lined("search", "end", [document.getElementById("regex"), document.querySelector("#keys > span:last-child")]);
    stepped([palette]); legible([palette]);
  }
  near("tools", "bar", $$("#tools > .tool").map((tool) => [tool]));
  for (const bar of [document.getElementById("tools"), document.getElementById("crumbs")]) { framed(bar, [...bar.children]); stepped([bar]); legible([bar]); }
  if (Math.abs(document.getElementById("tools").getBoundingClientRect().top - document.getElementById("crumbs").getBoundingClientRect().top) > 1) found.alignment.push("the crumbs and the tools do not share one top edge");
  counts.alignment += 1;
  if (play.classList.contains("show")) {
    near("scenario bar", "bar", [["prev", "run", "next"].map((id) => document.getElementById(id)), [play.querySelector(".count"), play.querySelector(".title")], [play.querySelector(".dots")], [document.getElementById("onto")], [document.getElementById("again"), document.getElementById("onward")], [document.getElementById("stop")]]);
    framed(play, [...play.children]);
    stepped([play, document.getElementById("chip")]); legible([play, document.getElementById("chip").classList.contains("show") ? document.getElementById("chip") : null]);
  }
  const stage = document.getElementById("stage"), nodes = $$(".node", stage);
  if (nodes.length && !stage.querySelector(".dim") && !palette.classList.contains("show")) {
    near("node", "level", nodes.map((node) => [node]));
    for (const node of nodes) { framed(node, [...node.children]); lined(`node ${node.dataset.id}`, "start", [node.querySelector("b"), node.querySelector("small")]); }
    for (const area of $$(".area", stage)) {
      const box = area.getBoundingClientRect(), header = area.querySelector(":scope > header");
      const held = nodes.filter((node) => { const rect = node.getBoundingClientRect(); return rect.left >= box.left && rect.right <= box.right && rect.top >= box.top && rect.bottom <= box.bottom; });
      near("area header", `area ${area.dataset.id}`, [[header], ...held.map((node) => [node])]);
      framed(area, [header]);
      const first = held.filter((node) => Math.abs(node.getBoundingClientRect().left - Math.min(...held.map((one) => one.getBoundingClientRect().left))) < 0.5);
      lined(`area ${area.dataset.id}`, "start", [header.firstChild && header, ...first.slice(0, 1)]);
    }
    stepped([...nodes, ...$$(".area > header", stage), ...$$(".label", stage)]);
    legible([...nodes, ...$$(".area > header", stage), ...$$(".label", stage)]);
  }
  const roles = [["#card footer .hints", "#keys"], ["#card footer .hints > span", "#keys > span"]]; // one role drawn in two places
  for (const [one, other] of roles) {
    const a = document.querySelector(one), b = document.querySelector(other);
    if (!a || !b) continue;
    counts.scale += 1;
    if (getComputedStyle(a).columnGap !== getComputedStyle(b).columnGap) found.scale.push(`${one} is spaced ${getComputedStyle(a).columnGap}, ${other} ${getComputedStyle(b).columnGap}`);
  }
  return { found, counts, groups: [...groups] };
});

const ROOM = { gap: 16, along: 24, base: 11 }; // two runs of different edges under GAP px apart beside each other for over ALONG px read as one thick line
const crowded = (page) => page.evaluate(({ gap, along }) => { // the pairs of such runs the level shown draws, in window pixels
  const stage = document.getElementById("stage"), scale = +stage.dataset.scale, x0 = +stage.dataset.x, y0 = +stage.dataset.y;
  const runs = [...stage.querySelectorAll(".edge")].flatMap((edge) => {
    const steps = [...edge.querySelector("path.line").getAttribute("d").matchAll(/([MLQ])([^MLQ]*)/g)].map(([, verb, numbers]) => [verb, numbers.trim().split(/[\s,]+/).map(Number)]), found = [];
    let at = null;
    for (const [verb, numbers] of steps) {
      const end = numbers.slice(-2).map((value, i) => (i ? y0 : x0) + value * scale);
      if (verb === "L" && at && Math.abs(end[0] - at[0]) + Math.abs(end[1] - at[1]) > 0) found.push({ edge: edge.dataset.id, flat: Math.abs(end[1] - at[1]) < 0.5, from: at, to: end });
      at = end;
    }
    return found;
  });
  let pairs = 0;
  runs.forEach((one, i) => runs.slice(i + 1).forEach((other) => {
    if (one.edge === other.edge || one.flat !== other.flat) return;
    const [a, b] = one.flat ? [0, 1] : [1, 0], span = (run) => [Math.min(run.from[a], run.to[a]), Math.max(run.from[a], run.to[a])];
    const [low, high] = [span(one), span(other)], beside = Math.min(low[1], high[1]) - Math.max(low[0], high[0]);
    if (Math.abs(one.from[b] - other.from[b]) < gap && beside > along) pairs += 1;
  }));
  return pairs;
}, ROOM);
async function layout(browser) {
  const tally = { found: Object.fromEntries(PRINCIPLES.map((name) => [name, []])), counts: Object.fromEntries(PRINCIPLES.map((name) => [name, 0])), groups: new Set(), views: 0 };
  const add = (seen, where) => {
    tally.views += 1;
    for (const name of PRINCIPLES) { tally.counts[name] += seen.counts[name]; tally.found[name].push(...seen.found[name].map((line) => `${where}: ${line}`)); }
    seen.groups.forEach((group) => tally.groups.add(group));
  };
  const keep = async (page, example, target, size) => { // a card kept on TARGET, with the pointer off it
    await page.goto("file://" + example.built + "#level=" + target.level);
    await settled(page);
    const spot = await rested(page, target, size, `${example.name} ${target.id}`);
    await page.mouse.click(spot.x, spot.y);
    await rest(page);
    await page.mouse.move(2, size[1] - 2, { steps: 4 });
    await page.clock.fastForward(450);
    check(await page.evaluate((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.classList.contains("kept") && card.dataset.for === id; }, target.id), `${example.name}: no card is kept on ${target.id}`);
  };
  const size = SIZES[1];
  let pairs = 0;
  for (const example of examples) for (const scheme of ["light", "dark"]) {
    const page = await open(browser, example, size, { still: true, scheme });
    const where = `${example.name} ${scheme}`;
    for (const level of example.contract.levels) {
      await page.goto("file://" + example.built + "#level=" + level.id);
      await settled(page);
      await page.mouse.move(2, size[1] - 2);
      add(await principles(page), `${where} level ${level.id}`);
      if (example.name === "page-changes" && scheme === "light") pairs += await crowded(page);
    }
    for (const target of targets(example)) {
      await keep(page, example, target, size).catch(() => keep(page, example, target, size));
      add(await principles(page), `${where} card of ${target.id}`);
      await page.keyboard.press("Escape");
      await rest(page);
    }
    const words = [...new Set(example.contract.levels.flatMap((level) => level.nodes.map((node) => node.label.split(/\s+/).pop().toLowerCase())))];
    let kinds = 0;
    for (const word of words) {
      await page.goto("file://" + example.built);
      await settled(page);
      await searched(page, word.slice(0, 4));
      await rest(page);
      kinds = await page.evaluate(() => document.querySelectorAll("#hits h3").length);
      if (kinds >= 2) break;
    }
    check(kinds >= 2, `${where}: no query lists hits of two kinds`);
    add(await principles(page), `${where} search`);
    await page.keyboard.press("Escape");
    const scenario = (example.contract.scenarios || [])[0];
    check(scenario, `${where}: no scenario to play`);
    await page.goto("file://" + example.built + "#scenario=" + scenario.id + "&step=1&level=" + example.levelOf[scenario.steps[1] ? scenario.steps[1].at : scenario.steps[0].at]);
    await settled(page);
    await page.mouse.move(2, 2);
    check(await page.evaluate(() => document.getElementById("play").classList.contains("show")), `${where}: the scenario's bar did not show`);
    add(await principles(page), `${where} scenario ${scenario.id}`);
    quiet(page, where);
    await page.context().close();
  }
  const room = `${pairs} crowded parallel pairs (runs under ${ROOM.gap} px apart for over ${ROOM.along} px) on every level of page-changes at 1440, at most half of the ${ROOM.base} that 3dd6783c drew`;
  console.log(`parallel room: ${pairs <= ROOM.base / 2 ? "PASS" : "FAIL"}, ${room}`);
  check(pairs <= ROOM.base / 2, room);
  for (const group of GROUPS) check(tally.groups.has(group), `no view measured the group ${group}`);
  for (const name of PRINCIPLES) tally.found[name].slice(0, 12).forEach((line) => console.log(`${name}: ${line}`));
  for (const name of PRINCIPLES) check(!tally.found[name].length, `${name}: ${tally.found[name].length} faults, first ${tally.found[name][0]}`);
  // each principle finds the fault planted for it, so a measure that reads nothing cannot pass
  const example = examples[0], target = targets(example).find((one) => one.kind === "node");
  const page = await open(browser, example, size, { still: true });
  for (const name of PRINCIPLES) {
    await keep(page, example, target, size).catch(() => keep(page, example, target, size));
    const style = await page.addStyleTag({ content: FAULTS[name] });
    await rest(page); // a planted colour fades in under reduced motion, so it is read once its transition ends
    const seen = await principles(page);
    check(seen.found[name].length, `${name} misses the planted fault ${FAULTS[name]}`);
    await style.evaluate((element) => element.remove());
    await page.keyboard.press("Escape");
    await rest(page);
  }
  await page.context().close();
  for (const name of PRINCIPLES) console.log(`${name}: ${tally.counts[name]} measured over ${tally.views} views, light and dark, none off, and the planted fault found`);
  console.log(`groups measured: ${GROUPS.join(", ")}`);
}

// ---- fonts ----
const fitted = ([selector, frame]) => [...document.querySelectorAll(selector)].filter((element) => element.getClientRects().length).map((element) => { // per text: a word split across two lines, a word past its box or FRAME across, or its lines past FRAME down; a glyph's own box may stand a pixel over its line, which no reader sees
  const own = element.getBoundingClientRect(), outer = element.closest(frame).getBoundingClientRect(), left = Math.max(own.left, outer.left), right = Math.min(own.right, outer.right);
  const found = { text: element.textContent, split: "", out: own.top < outer.top - 0.5 || own.bottom > outer.bottom + 0.5 ? element.textContent : "", wide: element.scrollWidth > element.clientWidth + 1 };
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  for (let text = walker.nextNode(); text; text = walker.nextNode()) for (const word of text.data.matchAll(/\S+/g)) {
    const range = document.createRange();
    range.setStart(text, word.index);
    range.setEnd(text, word.index + word[0].length);
    const rects = [...range.getClientRects()].filter((rect) => rect.width > 0.5);
    if (!found.split && rects.some((rect) => Math.abs(rect.top - rects[0].top) > 6)) found.split = word[0];
    if (!found.out && rects.some((rect) => rect.left < left - 0.5 || rect.right > right + 0.5)) found.out = word[0];
  }
  return found;
});
const GROWN = [1, 2]; // each type size and line height of a copy's token sheet against the sheet's own: as shipped, then doubled as WCAG 1.4.4 resizes text
async function fonts(browser) {
  let read = 0;
  const sizes = [];
  for (const factor of GROWN) for (const example of examples) {
    const flat = JSON.parse(fs.readFileSync(example.source, "utf8")), name = `${example.name}-fonts-${factor}`, copy = { name, source: path.join(scratch, name + ".json"), built: path.join(scratch, name + ".html") };
    for (const area of flat.areas || []) area.label += " with every part it holds"; // a header wider than the nodes under it sets its area's width
    fs.writeFileSync(copy.source, JSON.stringify(flat));
    make(copy);
    const page = fs.readFileSync(copy.built, "utf8"), grown = page.replace(/(--(?:type|leading)-\d+): (\d+)px/g, (whole, token, px) => `${token}: ${Math.round(px * factor)}px`);
    const drawn = [...grown.matchAll(/--(?:type|leading)-\d+: \d+px/g)].map(([one]) => one).join(", ");
    check(drawn, `${copy.name}: the page holds no type size of the token sheet`);
    if (!sizes.includes(drawn)) sizes.push(drawn);
    fs.writeFileSync(copy.built, grown);
    await each(copy.contract.levels, async (level) => {
      const view = await open(browser, copy, SIZES[1], { still: true, at: "#level=" + level.id }), where = `${copy.name} level ${level.id}`;
      const seen = [...(await view.evaluate(fitted, ["#stage .node b, #stage .node small", ".node"])), ...(await view.evaluate(fitted, ["#stage .area > header", ".area"]))];
      check(seen.length >= level.nodes.length, `${where}: ${seen.length} labels, tags and headers shown for ${level.nodes.length} nodes`);
      unbroken(seen, where);
      const crowded = await view.evaluate(() => [...document.querySelectorAll("#stage .node")].filter((node) => { // a tag line running under the node's badges
        const tag = node.querySelector("small"), badges = node.querySelector(":scope > .claims");
        if (!tag || !badges || !badges.getClientRects().length) return false;
        const range = document.createRange();
        range.selectNodeContents(tag);
        return range.getBoundingClientRect().right > badges.getBoundingClientRect().left + 0.5;
      }).map((node) => node.dataset.id));
      check(!crowded.length, `${where}: the tag of ${crowded[0]} runs under its badges`);
      const cut = await view.evaluate(() => [...document.querySelectorAll("#stage .area > header .claims > .claim")].filter((claim) => { // a header badge shorter than its text
        const range = document.createRange();
        range.selectNodeContents(claim);
        return range.getBoundingClientRect().height > claim.getBoundingClientRect().height + 0.5;
      }).map((claim) => claim.closest(".area").dataset.id));
      check(!cut.length, `${where}: a badge of area ${cut[0]} is shorter than its text`);
      read += seen.length;
      quiet(view, where);
      await view.context().close();
    });
  }
  console.log(`${read} labels, tags and headers read at ${sizes.join(" and at ")}, none split or cut off`);
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
    const steps = { diagram, shapes, overlay, fit, clear, moves, changes, search, titles, results, regex, ranking, recent, tasks, sweep, names: nameChips, glosses, badges, counts, note, formulas, code, tables, layout, wrap, fonts };
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
