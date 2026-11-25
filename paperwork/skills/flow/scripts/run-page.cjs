#!/usr/bin/env node
// Build the page of each flow fixture, open it in a headless Chromium as file:// at 1440 by 900 pixels, and drive it as a
// person with a pointer and a keyboard would.
//
// usage: run-page.cjs [interaction] [plan]
// With no word it runs every step; it prints `PASS <step>` or `FAIL <step>: <reason>` per step with the step's seconds,
// then `PASS in <seconds> s` or `FAIL in <seconds> s` for the whole run, and exits 1 on a failure and 2 on a word it does
// not know.
//   interaction  on the first level of name-lookup.json: every node in one row across the top; every edge lower than the one
//                before it, its step number on its sender's line, its name above its arrow and its tag chip and badges below
//                it, then its code items and a pill per work row, a self-call a loop on its node's line with its parts starting
//                just right of it, the arrow joining its two nodes' lines and its name, code items and work pills between them;
//                each group's nodes in one fill and one 2 px border colour, the group's label inside each, the groups apart in
//                colour; each fragment's frame round all its edges, its kind written inside its top left corner, each guard
//                inside it; below the diagram a task list per group with work, its rows in step order, a click on the first
//                step's row bringing that arrow into view with its card; each milestone a dotted line across every node's line,
//                between the edges before and after it, its name on it; the pointer on a node's line and on an edge raising
//                that record's card, the edge's step and formula on it; `/` and an edge's name listing that edge first, and
//                Enter keeping its card; a click on the nested edge's ref mark drawing the level it opens with crumbs back, a
//                double-click on the edge doing the same, and the first crumb drawing the first level again; one anchor per
//                node, edge, task, fragment and milestone; a contract the checker refuses building no page; arrowheads pointing
//                at the receiver; on a crowded copy, a self-call's name inside its frame and the stage, a call's wide work
//                pills between its two lines, a frame 8 px or more inside the frame holding it on each side, a milestone listed
//                before the milestone it waits on drawn below it, and ten groups in eight colours taken in turn and again from
//                the first; no console error and no request.
//   plan         on the level of launch-plan.json: every node in one column down the left; each task a bar on one of its node's
//                lines, right of the nodes, no two overlapping, starting right of the end of every task and milestone it waits
//                on, by an edge or its `after`; each milestone's dotted line across every node's lane, right of the end of each
//                task it waits on; each arrow from the right end of its task to the left end of the one it leads to, its head
//                pointing in there, crossing no task, and between two lanes keeping to the band from one bar to the other; each
//                request arrow solid and each wait arrow dotted; the bold tasks and edges exactly the chain
//                `check-contract.py order` prints, as many bold tasks as it counts; the pointer on a task raising its card; no
//                console error and no request.
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const browsers = require(path.join(__dirname, "..", "..", "..", "lib", "launch-browser.cjs"));
const { check, same, python } = require(path.join(__dirname, "..", "..", "..", "lib", "check-step.cjs"));
const SIZE = [1440, 900];
const STEPS = ["interaction", "plan"];
const asked = process.argv.slice(2);
if (asked.some((word) => !STEPS.includes(word))) {
  console.error("usage: run-page.cjs " + STEPS.map((word) => `[${word}]`).join(" "));
  process.exit(2);
}

const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "flow-page-"));

function make(name) { // the page of one fixture contract, and its contract
  const fixture = { name, source: path.join(ROOT, "fixtures", name + ".json"), built: path.join(scratch, name + ".html") };
  const made = python(path.join(ROOT, "scripts", "make-page.py"), fixture.source, fixture.built);
  check(made.status === 0, `make-page.py refused ${name}: ${(made.stdout + made.stderr).split("\n")[0]}`);
  fixture.contract = JSON.parse(fs.readFileSync(fixture.source, "utf8"));
  return fixture;
}

async function open(browser, fixture, at = "") {
  const context = await browser.newContext({ viewport: { width: SIZE[0], height: SIZE[1] }, reducedMotion: "reduce", colorScheme: "light" });
  const page = await context.newPage();
  page.faults = [];
  page.asked = [];
  page.on("console", (message) => message.type() === "error" && page.faults.push(message.text()));
  page.on("pageerror", (error) => page.faults.push(String(error)));
  page.on("request", (request) => { if (!request.url().startsWith("file://" + fixture.built)) page.asked.push(request.url()); });
  await page.goto("file://" + fixture.built + at);
  return page;
}
const quiet = (page, where) => {
  check(!page.faults.length, `${where} wrote to the console: ${page.faults[0]}`);
  check(!page.asked.length, `${where} asked for ${page.asked[0]}`);
};
const carded = (page, id, where) => page.waitForFunction((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; }, id, { timeout: 5000 })
  .catch(() => { throw new Error(`${where}: no card for ${id} came`); });
const shownLevel = (page) => page.evaluate(() => [...document.querySelectorAll("#crumbs [aria-current]")].map((crumb) => crumb.dataset.level)[0]);

const drawn = (page) => page.evaluate(() => { // what the shown level draws, as boxes in the stage's own pixels
  const stage = document.getElementById("stage").getBoundingClientRect();
  const box = (element) => { const at = element.getBoundingClientRect(); return { left: at.left - stage.left, right: at.right - stage.left, top: at.top - stage.top, bottom: at.bottom - stage.top }; };
  const all = (selector) => [...document.querySelectorAll(selector)];
  const nodes = Object.fromEntries(all("#stage .node").map((node) => {
    const style = getComputedStyle(node);
    return [node.dataset.id, { ...box(node), group: node.dataset.group, fill: style.backgroundColor, border: style.borderTopColor, width: style.borderTopWidth, label: node.querySelector(".group").textContent }];
  }));
  const lines = Object.fromEntries(all("#stage [data-for] > .lifeline").map((line) => [line.parentNode.dataset.for, { x: +line.getAttribute("x1"), top: +line.getAttribute("y1"), bottom: +line.getAttribute("y2") }]));
  const edges = Object.fromEntries(all("#stage g.edge").map((group) => {
    const id = group.dataset.for, arrow = group.querySelector(".arrow"), [tip, back] = group.querySelector(".head").getAttribute("points").split(" ").map((point) => +point.split(",")[0]), fill = [...group.querySelectorAll("path")].map((part) => getComputedStyle(part).fill).find((one) => one !== "none") || "none";
    const chips = document.querySelector(`#stage .edge-chips[data-for="${id}"]`), codes = document.querySelector(`#stage .edge-codes[data-for="${id}"]`), work = document.querySelector(`#stage .edge-work[data-for="${id}"]`);
    const disc = group.querySelector("circle.step"), number = group.querySelector("text.step-number");
    return [id, { tip, back, arrow: box(arrow), label: box(document.querySelector(`#stage .edge-label[data-id="${id}"]`)), text: document.querySelector(`#stage .edge-label[data-id="${id}"]`).firstChild.textContent,
      chips: box(chips), chip: chips.querySelector(".chip").textContent, badges: chips.querySelectorAll(".count").length,
      fill, codes: codes && { ...box(codes), text: codes.textContent }, work: work && { ...box(work), pills: [...work.querySelectorAll(".work-pill")].map((pill) => pill.textContent) }, step: disc && number && { x: +disc.getAttribute("cx"), y: +disc.getAttribute("cy"), text: number.textContent } }];
  }));
  const fragments = Object.fromEntries(all("#stage rect.fragment").map((frame) => {
    const id = frame.dataset.for, kind = document.querySelector(`#stage .fragment-kind[data-id="${id}"]`);
    return [id, { frame: box(frame), kind: box(kind), text: kind.textContent, guards: all(`#stage .guard[data-for="${id}"]`).map((guard) => ({ ...box(guard), text: guard.textContent })) }];
  }));
  const milestones = Object.fromEntries(all("#stage line.milestone").map((line) => {
    const id = line.dataset.for;
    return [id, { line: box(line), y: +line.getAttribute("y1"), dash: getComputedStyle(line).strokeDasharray, label: box(document.querySelector(`#stage .milestone-label[data-id="${id}"]`)), text: document.querySelector(`#stage .milestone-label[data-id="${id}"]`).textContent }];
  }));
  const anchors = all("#stage [data-id]").map((element) => element.dataset.id);
  const list = document.querySelector("#stage .work-list");
  const work = list && { ...box(list), sections: all("#stage .work-list section").map((section) => ({ group: section.dataset.group, title: section.querySelector("h2").textContent,
    rows: [...section.querySelectorAll(".work-row")].map((row) => ({ for: row.dataset.for, step: row.querySelector(".work-step").textContent, change: row.querySelector(".work-change").textContent, says: row.querySelector(".work-says").textContent })) })) };
  return { nodes, lines, edges, fragments, milestones, anchors, work };
});

async function interaction(browser) {
  const refused = python(path.join(ROOT, "scripts", "make-page.py"), (() => { // a copy the checker refuses, with an edge from no node
    const copy = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures", "name-lookup.json"), "utf8"));
    copy.edges[0].from = "no-such-node";
    const file = path.join(scratch, "refused.json");
    fs.writeFileSync(file, JSON.stringify(copy));
    return file;
  })(), path.join(scratch, "refused.html"));
  check(refused.status === 1 && !fs.existsSync(path.join(scratch, "refused.html")), "make-page.py built a page from a contract the checker refuses");

  const fixture = make("name-lookup"), contract = fixture.contract, level = contract.levels[0];
  const edges = contract.edges.filter((edge) => edge.level === level.id), fragments = (contract.fragments || []).filter((one) => one.level === level.id);
  const milestones = (contract.milestones || []).filter((one) => one.level === level.id), nested = edges.find((edge) => edge.opens);
  const groups = new Set(level.nodes.map((id) => contract.nodes.find((node) => node.id === id).group));
  const tags = JSON.parse(fs.readFileSync(path.join(ROOT, "assets", "tags.json"), "utf8"));
  const owed = (edge) => ((edge.info || {}).work || { rows: [] }).rows;
  const groupLabel = (id) => contract.groups.find((group) => group.id === id).label;
  const codes = (edge) => (tags.edge[edge.tag] ? tags.edge[edge.tag].items : []).filter((item) => item.form === "code" && typeof (edge.info || {})[item.name] === "string" && edge.info[item.name] !== edge.label).map((item) => edge.info[item.name]).join(" · ");
  check(groups.size >= 2 && fragments.some((one) => one.kind === "loop") && fragments.some((one) => one.kind === "break") && milestones.length && nested
    && edges.some((edge) => edge.from === edge.to && owed(edge).length) && edges.some(codes) && new Set(edges.flatMap(owed).map((row) => row[0])).size >= 2,
    "the fixture's first level lacks two groups, a loop, a break, a milestone, a nested edge, a self-call with work, a code item or work for two groups");
  const page = await open(browser, fixture);
  const seen = await drawn(page);

  // nodes in one row, each group one colour with a 2px border and its label, the groups apart
  const nodes = level.nodes.map((id) => seen.nodes[id]);
  check(nodes.every(Boolean), "a node of the level is not drawn");
  check(nodes.every((node) => Math.abs(node.top - nodes[0].top) < 1), "the nodes are not in one row");
  check(nodes.every((node, k) => !k || node.left > nodes[k - 1].right), "the nodes are not side by side in the level's order");
  const colours = {};
  for (const id of level.nodes) {
    const node = seen.nodes[id], group = contract.groups.find((one) => one.id === node.group);
    check(node.width === "2px", `${id}'s border is ${node.width}, not 2px`);
    check(node.label === group.label, `${id} shows the group label "${node.label}", not "${group.label}"`);
    check(node.fill !== node.border, `${id}'s fill and border are one colour`);
    const colour = node.fill + " " + node.border;
    check(!colours[node.group] || colours[node.group] === colour, `the group ${node.group} is drawn in two colours`);
    colours[node.group] = colour;
  }
  check(new Set(Object.values(colours)).size === groups.size, "two groups share one colour");

  // edges top to bottom, name above, chips and badges below, arrow between its nodes' lines
  let above = -Infinity;
  for (const [k, edge] of edges.entries()) {
    const one = seen.edges[edge.id];
    check(one, `the edge ${edge.id} is not drawn`);
    check(one.step && one.step.text === String(k + 1), `${edge.id}'s step disc reads ${one.step ? one.step.text : "nothing"}, not ${k + 1}`);
    check(Math.abs(one.step.x - seen.lines[edge.from].x) < 2 && one.step.y >= one.arrow.top - 1 && one.step.y <= one.arrow.bottom + 1, `${edge.id}'s step disc is not on ${edge.from}'s line at its arrow`);
    check((one.codes ? one.codes.text : "") === codes(edge), `${edge.id} writes "${one.codes ? one.codes.text : ""}" under its arrow, not its code items "${codes(edge)}"`);
    check(!one.codes || one.codes.top >= one.chips.bottom - 1, `${edge.id}'s code items are not below its chip`);
    check(one.fill === "none", `a path of ${edge.id} is filled ${one.fill}`);
    const pills = owed(edge).map(([group, change]) => `${change} · ${groupLabel(group)}`);
    check(JSON.stringify(one.work ? one.work.pills : []) === JSON.stringify(pills), `${edge.id}'s work pills read ${JSON.stringify(one.work ? one.work.pills : [])}, not ${JSON.stringify(pills)}`);
    check(!one.work || one.work.top >= (one.codes || one.chips).bottom - 1, `${edge.id}'s work pills are not below its chip and code items`);
    check(one.text === edge.label, `${edge.id}'s name reads "${one.text}", not "${edge.label}"`);
    check(one.arrow.top > above, `${edge.id} is not lower than the edge before it`);
    above = one.arrow.bottom;
    check(one.label.bottom <= one.arrow.top + 1, `${edge.id}'s name is not above its arrow`);
    check(one.chips.top >= one.arrow.bottom - 1, `${edge.id}'s chip is not below its arrow`);
    check(one.chip === edge.tag.replace(/[A-Z]/g, (letter) => " " + letter.toLowerCase()), `${edge.id}'s chip reads "${one.chip}", not its tag ${edge.tag}`);
    const earned = new Set((contract.properties || []).filter((property) => (property.on || []).includes(edge.id)).map((property) => property.kind === "gap" ? "gap" : property.status || "holds")).size;
    check(one.badges === earned, `${edge.id} shows ${one.badges} badges, not ${earned}`);
    const toward = edge.from === edge.to ? -1 : Math.sign(seen.lines[edge.to].x - seen.lines[edge.from].x);
    check(Math.abs(one.tip - seen.lines[edge.to].x) < 2 && Math.sign(one.tip - one.back) === toward, `${edge.id}'s arrowhead does not point at ${edge.to}'s line from ${edge.from}'s side`);
    if (edge.from === edge.to) check(Math.abs(one.arrow.left - seen.lines[edge.from].x) < 2 && one.arrow.right - one.arrow.left >= 20 && one.arrow.bottom - one.arrow.top >= 8,
      `${edge.id}'s arrow is no loop leaving and coming back to ${edge.from}'s line`);
    if (edge.from === edge.to) check([one.label, one.chips, one.codes, one.work].filter(Boolean).every((part) => part.left >= one.arrow.right && part.left - one.arrow.right <= 16),
      `${edge.id}'s name, chip, code items or work pills do not start just right of its loop`);
    else {
      const xs = [seen.lines[edge.from].x, seen.lines[edge.to].x].sort((a, b) => a - b);
      check(Math.abs(one.arrow.left - xs[0]) < 12 && Math.abs(one.arrow.right - xs[1]) < 12, `${edge.id}'s arrow does not join ${edge.from}'s and ${edge.to}'s lines`);
    }
  }
  const between = (seen, edge) => { // the name, code items and work pills of a call between two lines stay between those lines
    const one = seen.edges[edge.id], xs = [seen.lines[edge.from].x, seen.lines[edge.to].x].sort((a, b) => a - b);
    return [one.label, one.codes, one.work].filter(Boolean).every((part) => part.left >= xs[0] - 1 && part.right <= xs[1] + 1);
  };
  for (const edge of edges.filter((one) => one.from !== one.to)) check(between(seen, edge), `${edge.id}'s name, code items or work pills reach past ${edge.from}'s or ${edge.to}'s line`);

  // each fragment's frame round its edges, its kind inside its top left corner and each guard inside the frame
  for (const fragment of fragments) {
    const one = seen.fragments[fragment.id];
    check(one, `the fragment ${fragment.id} is not drawn`);
    check(one.text === fragment.kind, `${fragment.id}'s frame reads "${one.text}", not ${fragment.kind}`);
    check(Math.abs(one.kind.left - one.frame.left) < 2 && Math.abs(one.kind.top - one.frame.top) < 2, `${fragment.id}'s kind is not in its top left corner`);
    const guards = fragment.operands.filter((operand) => operand.guard).map((operand) => `[${operand.guard}]`);
    check(JSON.stringify(one.guards.map((guard) => guard.text)) === JSON.stringify(guards), `${fragment.id} writes the guards ${JSON.stringify(one.guards.map((guard) => guard.text))}, not ${JSON.stringify(guards)}`);
    check(one.guards.every((guard) => guard.left >= one.frame.left && guard.right <= one.frame.right && guard.top >= one.frame.top && guard.bottom <= one.frame.bottom), `a guard of ${fragment.id} sits outside its frame`);
    for (const id of fragment.operands.flatMap((operand) => operand.edges)) {
      const edge = seen.edges[id];
      for (const part of [edge.arrow, edge.label, edge.chips, edge.codes].filter(Boolean))
        check(part.left >= one.frame.left && part.right <= one.frame.right && part.top >= one.frame.top && part.bottom <= one.frame.bottom, `${id} reaches outside the frame of ${fragment.id}`);
    }
  }

  // the task list below the diagram: per group with work, its rows in step order
  const tasks = contract.groups.map((group) => ({ group: group.id, title: group.label,
    rows: edges.flatMap((edge, k) => owed(edge).filter((row) => row[0] === group.id).map(([, change, says]) => ({ for: edge.id, step: String(k + 1), change, says }))) })).filter((one) => one.rows.length);
  check(seen.work && JSON.stringify(seen.work.sections) === JSON.stringify(tasks), `the task list reads ${JSON.stringify(seen.work && seen.work.sections)}, not ${JSON.stringify(tasks)}`);
  check(level.nodes.every((id) => seen.work.top > seen.lines[id].bottom), "the task list is not below the diagram");

  // each milestone a dotted line across every node's line, after the edges it names, its name on it
  for (const milestone of milestones) {
    const one = seen.milestones[milestone.id];
    check(one, `the milestone ${milestone.id} is not drawn`);
    check(one.dash !== "none" && one.dash !== "", `${milestone.id}'s line is not dotted`);
    check(level.nodes.every((id) => one.line.left < seen.lines[id].x && seen.lines[id].x < one.line.right && seen.lines[id].top < one.y && one.y < seen.lines[id].bottom), `${milestone.id} does not cross every node's line`);
    const order = edges.map((edge) => edge.id), last = Math.max(...milestone.after.map((id) => order.indexOf(id)));
    check(edges.every((edge, k) => k <= last ? Math.max(...[seen.edges[edge.id].chips, seen.edges[edge.id].codes, seen.edges[edge.id].work].filter(Boolean).map((part) => part.bottom)) < one.y : seen.edges[edge.id].label.top > one.y), `${milestone.id} is not between the edges before and after it`);
    check(one.text === milestone.label && one.label.bottom <= one.y + 2 && one.label.bottom >= one.y - 12, `${milestone.id}'s name is not on its line`);
  }

  // one anchor per drawn record, for the relay to take a comment on
  const records = [...level.nodes, ...edges.map((edge) => edge.id), ...fragments.map((one) => one.id), ...milestones.map((one) => one.id)];
  for (const id of records) check(seen.anchors.filter((one) => one === id).length === 1, `${id} has ${seen.anchors.filter((one) => one === id).length} anchors, not one`);

  // the pointer on a node's line and on an edge raises its card
  const node = level.nodes[level.nodes.length - 1], line = seen.lines[node], stage = await page.evaluate(() => { const at = document.getElementById("stage").getBoundingClientRect(); return { left: at.left, top: at.top }; });
  const gap = (seen.edges[edges[0].id].arrow.bottom + seen.edges[edges[1].id].label.top) / 2;
  await page.mouse.move(2, SIZE[1] - 2);
  await page.mouse.move(stage.left + line.x + 3, stage.top + gap, { steps: 4 });
  await carded(page, node, `the pointer on ${node}'s line`);
  const edge = edges[edges.length - 1], arrow = seen.edges[edge.id].arrow;
  await page.mouse.move(2, SIZE[1] - 2);
  await page.mouse.move(stage.left + (arrow.left + arrow.right) / 2, stage.top + (arrow.top + arrow.bottom) / 2, { steps: 4 });
  await carded(page, edge.id, `the pointer on ${edge.id}`);
  const formula = await page.evaluate(() => { const card = document.getElementById("card"); return { math: !!card.querySelector("math"), marks: card.textContent.includes("$"), step: (card.innerText.match(/^step\s+(\d+)$/m) || [])[1] }; });
  check(formula.step === String(edges.indexOf(edge) + 1), `${edge.id}'s card gives step ${formula.step}, not ${edges.indexOf(edge) + 1}`);
  check(formula.math && !formula.marks, `${edge.id}'s card draws ${formula.math ? "" : "no formula "}${formula.marks ? "a dollar as text" : ""}`);
  await page.mouse.move(2, SIZE[1] - 2);

  // a task-list row raises its edge's card with its arrow in view
  const row = tasks[0].rows[0]; // the first step's arrow, the farthest from the list
  await page.evaluate(() => { const box = document.getElementById("diagram"); box.scrollTop = box.scrollHeight; });
  await page.click(`#stage .work-list section[data-group="${tasks[0].group}"] .work-row:first-child`);
  await carded(page, row.for, `a click on the task-list row of step ${row.step}`);
  const shown = await page.evaluate((id) => { const at = document.querySelector(`#stage .edge-label[data-id="${id}"]`).getBoundingClientRect(); return at.top >= 0 && at.bottom <= innerHeight; }, row.for);
  check(shown, `a click on the task-list row of step ${row.step} leaves ${row.for}'s arrow out of view`);
  await page.keyboard.press("Escape");
  await page.evaluate(() => { document.getElementById("diagram").scrollTop = 0; });

  // `/` finds an edge by its name
  const sought = edges.find((one) => one.id !== edge.id && one.level === level.id);
  await page.keyboard.press("/");
  await page.keyboard.insertText(sought.label);
  const hits = await page.waitForFunction(() => { const rows = [...document.querySelectorAll("#hits [data-hit]")]; return rows.length && rows.map((row) => row.dataset.hit); }, null, { timeout: 5000 }).then((handle) => handle.jsonValue());
  check(hits[0] === sought.id, `"/" and "${sought.label}" listed ${hits[0]} first, not ${sought.id}`);
  await page.keyboard.press("Enter");
  await carded(page, sought.id, `Enter on the hit ${sought.id}`);
  await page.keyboard.press("Escape");

  // the nested edge opens its level, by its ref mark and by a double-click, with crumbs back
  await page.click(`#stage .edge-label[data-id="${nested.id}"] .opens-mark`);
  await page.waitForFunction((level) => document.querySelector(`#crumbs [aria-current][data-level="${level}"]`), nested.opens, { timeout: 5000 }).catch(() => { throw new Error(`a click on ${nested.id}'s ref mark did not draw ${nested.opens}`); });
  const inside = await drawn(page), wanted = contract.levels.find((one) => one.id === nested.opens);
  check(wanted.nodes.every((id) => inside.nodes[id]) && Object.keys(inside.nodes).length === wanted.nodes.length, `${nested.opens} does not draw its own nodes`);
  check(contract.edges.filter((one) => one.level === nested.opens).every((one) => inside.edges[one.id]), `${nested.opens} does not draw its own edges`);
  const crumbs = await page.evaluate(() => [...document.querySelectorAll("#crumbs [data-level]")].map((crumb) => crumb.dataset.level));
  check(crumbs.join(" ") === `${level.id} ${nested.opens}`, `the crumbs read ${crumbs.join(" ")}, not ${level.id} ${nested.opens}`);
  await page.click(`#crumbs [data-level="${level.id}"]`);
  await page.waitForFunction((level) => document.querySelector(`#crumbs [aria-current][data-level="${level}"]`), level.id, { timeout: 5000 }).catch(() => { throw new Error(`the crumb ${level.id} did not draw its level`); });
  const back = (await drawn(page)).edges[nested.id].arrow;
  await page.mouse.dblclick(stage.left + (back.left + back.right) / 2, stage.top + (back.top + back.bottom) / 2);
  await page.waitForFunction((level) => document.querySelector(`#crumbs [aria-current][data-level="${level}"]`), nested.opens, { timeout: 5000 }).catch(() => { throw new Error(`a double-click on ${nested.id} did not draw ${nested.opens}`); });
  check(await shownLevel(page) === nested.opens, `the double-click drew ${await shownLevel(page)}`);
  quiet(page, "the interaction page");
  await page.context().close();

  // a copy with a loop widened by its guard inside an opt, a self-call inside the break and one in no frame, each named at
  // length, and a milestone that waits on a milestone
  const crowded = JSON.parse(JSON.stringify(contract)), at = (id) => crowded.edges.findIndex((edge) => edge.id === id);
  const loop = crowded.fragments.find((one) => one.kind === "loop"), stop = crowded.fragments.find((one) => one.kind === "break");
  loop.operands[0].guard += ", and each shard answers in turn while the other one waits";
  crowded.fragments.push({ id: "if-sharded", level: level.id, kind: "opt", operands: [{ guard: "the names are sharded", edges: [crowded.edges[at(loop.operands[0].edges[0]) - 1].id, ...loop.operands[0].edges] }] });
  crowded.edges.splice(at(stop.operands[0].edges.slice(-1)[0]) + 1, 0, { id: "logs-failure", level: level.id, from: "name-store", to: "name-store", label: "log(both-shards-timed-out)", tag: "call" });
  stop.operands[0].edges.push("logs-failure");
  crowded.edges.splice(at(edges[edges.length - 1].id) + 1, 0, { id: "drops-record", level: level.id, from: "name-store", to: "name-store", label: "drop(the-cached-owner-record-once-the-whole-reply-has-gone-out-to-the-browser)", tag: "call" });
  crowded.milestones.unshift({ id: "reply-ready", level: level.id, label: "Reply ready", after: [milestones[0].id], purpose: "The reply is whole." });
  const resolves = crowded.edges[at("resolves-name")];
  resolves.info = { ...(resolves.info || {}), work: { columns: ["group", "change", "says"], rows: [["registry", "schema migration and index rebuild", "keep the owner of each name in one indexed table"]] } };
  for (let k = crowded.groups.length; k < 10; k++) { // past the eighth group the colours come round again
    crowded.groups.push({ id: `extra-${k}`, label: `Extra ${k}`, purpose: `Runs in place ${k}.` });
    crowded.nodes.push({ id: `extra-node-${k}`, group: `extra-${k}`, label: `Extra node ${k}`, tag: "service", purpose: `Stands by in place ${k}.`, evidence: ["runbook"], basis: "documented" });
    crowded.levels[0].nodes.push(`extra-node-${k}`);
  }
  const copied = { name: "crowded", source: path.join(scratch, "crowded.json"), built: path.join(scratch, "crowded.html"), contract: crowded };
  fs.writeFileSync(copied.source, JSON.stringify(crowded));
  const built = python(path.join(ROOT, "scripts", "make-page.py"), copied.source, copied.built);
  check(built.status === 0, `make-page.py refused the crowded copy: ${(built.stdout + built.stderr).split("\n")[0]}`);
  const crowdedPage = await open(browser, copied), packed = await drawn(crowdedPage);
  const width = await crowdedPage.evaluate(() => parseFloat(document.getElementById("stage").style.width));
  const framed = packed.edges["logs-failure"], frame = packed.fragments[stop.id].frame, loose = packed.edges["drops-record"];
  check([framed.label, framed.chips].every((part) => part.left >= frame.left && part.right <= frame.right), `logs-failure's name or chip reaches outside the frame of ${stop.id}`);
  check([loose.label, loose.chips].every((part) => part.right <= width), "drops-record's name or chip reaches past the stage");
  const inner = packed.fragments[loop.id].frame, outer = packed.fragments["if-sharded"].frame;
  check(inner.left - outer.left >= 7.5 && outer.right - inner.right >= 7.5, `the frame of ${loop.id} stands ${(inner.left - outer.left).toFixed(1)} and ${(outer.right - inner.right).toFixed(1)} px inside the frame of if-sharded, not 8 or more on each side`);
  check(between(packed, crowded.edges[at("resolves-name")]), "resolves-name's work pills reach past gateway's or name-service's line");
  const hues = crowded.groups.map((group) => { const node = Object.values(packed.nodes).find((one) => one.group === group.id); return node && node.fill + " " + node.border; });
  check(hues.every(Boolean) && hues.every((hue, k) => k < 8 ? hues.indexOf(hue) === k : hue === hues[k - 8]), `the ten groups are drawn ${JSON.stringify(hues)}, not eight colours taken in turn and again from the first`);
  const first = packed.milestones[milestones[0].id], later = packed.milestones["reply-ready"];
  check(later && packed.anchors.includes("reply-ready"), "the milestone that waits on a milestone is not drawn");
  const next = crowded.edges.filter((edge) => edge.level === level.id).find((edge, k, all) => k > all.findIndex((one) => one.id === milestones[0].after.slice(-1)[0]));
  check(later.y > first.y && later.y < packed.edges[next.id].label.top, "the milestone that waits on a milestone is not between that milestone and the next edge");
  quiet(crowdedPage, "the crowded copy's page");
  await crowdedPage.context().close();
  console.log(`${level.nodes.length} nodes, ${edges.length} edges, ${fragments.length} fragments and ${milestones.length} milestones read on ${level.id}; ${nested.opens} opened by its ref mark and by a double-click`);
}

async function plan(browser) {
  const fixture = make("launch-plan"), contract = fixture.contract, level = contract.levels.find((one) => one.kind === "plan");
  const ordered = python(path.join(ROOT, "scripts", "check-contract.py"), "order", fixture.source);
  const printed = ordered.stdout.split("\n").find((line) => line.startsWith(`critical-path ${level.id} `));
  check(ordered.status === 0 && printed, `check-contract.py order printed no critical path for ${level.id}`);
  const counted = +printed.split(" ")[2], chain = printed.split(": ")[1].split(" ");
  const tasks = contract.tasks.filter((task) => task.level === level.id), edges = contract.edges.filter((edge) => edge.level === level.id);
  const milestones = (contract.milestones || []).filter((one) => one.level === level.id);
  const page = await open(browser, fixture, `#level=${level.id}`);
  const seen = await page.evaluate(() => {
    const stage = document.getElementById("stage").getBoundingClientRect();
    const box = (element) => { const at = element.getBoundingClientRect(); return { left: at.left - stage.left, right: at.right - stage.left, top: at.top - stage.top, bottom: at.bottom - stage.top }; };
    const nodes = Object.fromEntries([...document.querySelectorAll("#stage .node")].map((node) => [node.dataset.id, box(node)]));
    const lines = {};
    for (const line of document.querySelectorAll("#stage [data-for] > .lifeline")) (lines[line.parentNode.dataset.for] = lines[line.parentNode.dataset.for] || []).push(+line.getAttribute("y1"));
    const bars = Object.fromEntries([...document.querySelectorAll("#stage .task")].map((bar) => {
      const style = getComputedStyle(bar);
      return [bar.dataset.id, { ...box(bar), bold: +style.fontWeight >= 700 && parseFloat(style.borderTopWidth) >= 3 }];
    }));
    const arrows = Object.fromEntries([...document.querySelectorAll("#stage g.edge")].map((group) => {
      const arrow = group.querySelector(".arrow"), style = getComputedStyle(arrow), length = arrow.getTotalLength();
      const points = Array.from({ length: Math.ceil(length / 2) + 1 }, (_, k) => { const at = arrow.getPointAtLength(Math.min(k * 2, length)); return [at.x, at.y]; });
      const head = group.querySelector(".head").getAttribute("points").split(" ").map((point) => point.split(",").map(Number));
      return [group.dataset.for, { dash: style.strokeDasharray, bold: parseFloat(style.strokeWidth) >= 3, points, head }];
    }));
    const marks = Object.fromEntries([...document.querySelectorAll("#stage line.milestone")].map((line) => [line.dataset.for, { x: +line.getAttribute("x1"), top: +line.getAttribute("y1"), bottom: +line.getAttribute("y2"), dash: getComputedStyle(line).strokeDasharray }]));
    return { nodes, lines, bars, arrows, marks };
  });

  // the nodes in one column down the left, each task on one of its node's lines, right of them
  const nodes = level.nodes.map((id) => seen.nodes[id]);
  check(nodes.every(Boolean), "a node of the level is not drawn");
  check(nodes.every((node, k) => Math.abs(node.left - nodes[0].left) < 1 && (!k || node.top >= nodes[k - 1].bottom)), "the nodes are not in one column down the left");
  const edgeOfNodes = Math.max(...nodes.map((node) => node.right));
  for (const task of tasks) {
    const bar = seen.bars[task.id];
    check(bar, `the task ${task.id} is not drawn`);
    check(bar.left > edgeOfNodes, `${task.id} is not right of the nodes`);
    check((seen.lines[task.node] || []).some((y) => Math.abs(y - (bar.top + bar.bottom) / 2) < 1.5), `${task.id} is not on a line of ${task.node}`);
  }
  const apart = (a, b) => a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top;
  for (const [k, task] of tasks.entries()) for (const other of tasks.slice(k + 1)) check(apart(seen.bars[task.id], seen.bars[other.id]), `${task.id} and ${other.id} overlap`);

  // each task right of the end of what it waits on; each milestone right of what it waits on
  const ends = (id) => seen.bars[id] ? seen.bars[id].right : seen.marks[id].x;
  const starts = (id) => seen.bars[id] ? seen.bars[id].left : seen.marks[id].x;
  const waits = [...edges.map((edge) => [edge.from, edge.to]), ...[...tasks, ...milestones].flatMap((record) => (record.after || []).map((earlier) => [earlier, record.id]))];
  for (const [earlier, later] of waits) check(starts(later) > ends(earlier), `${later} does not start right of the end of ${earlier}`);
  for (const milestone of milestones) {
    const mark = seen.marks[milestone.id];
    check(mark && mark.dash !== "none", `${milestone.id} is not a dotted line`);
    check(mark.top <= nodes[0].top && mark.bottom >= nodes[nodes.length - 1].bottom, `${milestone.id}'s line runs from ${mark.top} to ${mark.bottom}, not across every node's lane`);
  }

  // requests solid, waits dotted, and the bold ones exactly the printed chain
  for (const edge of edges) {
    const arrow = seen.arrows[edge.id];
    check(arrow, `the edge ${edge.id} is not drawn`);
    if (edge.tag === "request") check(arrow.dash === "none", `the request ${edge.id} is not solid`);
    if (edge.tag === "wait") check(arrow.dash !== "none", `the wait ${edge.id} is not dotted`);
    const from = seen.bars[edge.from], to = seen.bars[edge.to], start = arrow.points[0], end = arrow.points[arrow.points.length - 1], tip = arrow.head[0];
    const near = ([x, y], at, height) => Math.abs(x - at) < 1.5 && Math.abs(y - height) < 1.5;
    check(near(start, from.right, (from.top + from.bottom) / 2) && near(end, to.left, (to.top + to.bottom) / 2), `${edge.id}'s arrow does not run from the right end of ${edge.from} to the left end of ${edge.to}`);
    check(near(tip, to.left, (to.top + to.bottom) / 2) && arrow.head.slice(1).every(([x]) => x < tip[0]), `${edge.id}'s arrowhead does not point into the left end of ${edge.to}`);
    check(arrow.points.every(([x, y]) => Object.values(seen.bars).every((bar) => x <= bar.left + 1 || x >= bar.right - 1 || y <= bar.top + 1 || y >= bar.bottom - 1)), `${edge.id}'s arrow crosses a task`);
    const lanes = [contract.tasks.find((one) => one.id === edge.from).node, contract.tasks.find((one) => one.id === edge.to).node], band = [Math.min(from.top, to.top), Math.max(from.bottom, to.bottom)];
    if (lanes[0] !== lanes[1]) check(arrow.points.every(([, y]) => y >= band[0] - 1 && y <= band[1] + 1), `${edge.id}'s arrow leaves the band from ${edge.from}'s lane to ${edge.to}'s`);
    const linked = chain.indexOf(edge.to) >= 1 && chain[chain.indexOf(edge.to) - 1] === edge.from;
    check(arrow.bold === linked, `${edge.id} is ${arrow.bold ? "" : "not "}bold, though it is ${linked ? "" : "not "}on the printed chain`);
  }
  const bold = tasks.filter((task) => seen.bars[task.id].bold).map((task) => task.id);
  const wanted = chain.filter((id) => tasks.some((task) => task.id === id));
  check(same(bold, wanted.slice().sort((a, b) => tasks.findIndex((task) => task.id === a) - tasks.findIndex((task) => task.id === b))), `the bold tasks are ${bold.join(" ")}, not the chain's ${wanted.join(" ")}`);
  check(bold.length === counted, `${bold.length} tasks are bold, not the ${counted} the order call counts`);

  // the pointer on a task raises its card
  const task = tasks[tasks.length - 1], bar = seen.bars[task.id];
  await page.evaluate(([x, y]) => document.getElementById("diagram").scrollTo(x, y), [Math.max(0, bar.left - 200), 0]);
  const stage = await page.evaluate(() => { const at = document.getElementById("stage").getBoundingClientRect(); return { left: at.left, top: at.top }; });
  await page.mouse.move(2, SIZE[1] - 2);
  await page.mouse.move(stage.left + (bar.left + bar.right) / 2, stage.top + (bar.top + bar.bottom) / 2, { steps: 4 });
  await carded(page, task.id, `the pointer on ${task.id}`);
  quiet(page, "the plan page");
  await page.context().close();
  console.log(`${tasks.length} tasks, ${edges.length} edges and ${milestones.length} milestones read on ${level.id}; ${bold.length} tasks bold: ${chain.join(" ")}`);
}

async function main() {
  if (browsers.missing()) {
    console.log(`FAIL setup: ${browsers.missing()}`);
    return 1;
  }
  let failed = 0, browser = null;
  try {
    browser = await browsers.launch();
    const steps = { interaction, plan };
    for (const name of asked.length ? asked : STEPS) {
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
