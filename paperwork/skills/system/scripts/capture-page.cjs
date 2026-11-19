#!/usr/bin/env node
// Record what a person sees on a built page, as the sample a fresh evaluator scores the page's look and its scenario
// play from: stills, frame sheets of each motion and one file of measures.
//
// usage: capture-page.cjs OUT [PAGE.html...]
// With no page it builds the page of each example contract with make-page.py. It drives each page only as a person
// does, by the pointer, the keys and an address, so a page of an earlier edition records the same way. Under OUT it
// writes `<page>/look/*.png`, `<page>/play/*.png` and `<page>/measures.json`, then prints one line per page and the
// seconds it took; exit 1 when a page cannot be opened, 2 on a call it cannot read.
//   look   the first level at 1024, 1440 and 1920 pixels wide, the fullest level, the pointer resting on a node
//          and on an edge, the longest card kept open, search with a query typed, the dark scheme, the pointer on a
//          node under reduced motion, and one sheet of frames of a level move, of the way back and of the move
//          under reduced motion.
//   play   each action that starts the first scenario, each of its steps at rest, a sheet of frames of a step along
//          an edge, of a step that changes level and of a step under reduced motion, what the space key starts, where
//          a button named `Step <n>` leads, the step after the last, and a step at 1024 pixels wide.
//   measures.json   per still: the smallest and the distinct sizes of the text shown, the share of the window the
//          diagram's records span and the share fixed chrome covers; per motion: each running animation's property,
//          duration, delay and easing; per hover: the wait until the card shows and the neighbours it covers; per
//          scenario step: the characters shown outside the diagram, and whether they cover the record the step names.
// The browser is the one ../../../lib/launch-browser.cjs starts.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const browsers = require(path.join(__dirname, "..", "..", "..", "lib", "launch-browser.cjs"));
const SMALL = [1024, 768], DESK = [1440, 900], WIDE = [1920, 1080];
const FRAMES = [40, 160, 300, 460, 640, 840, 1060, 1300];
const args = process.argv.slice(2);
if (!args.length || args.some((word) => word.startsWith("-")) || args.slice(1).some((file) => !fs.existsSync(file))) {
  const lines = fs.readFileSync(__filename, "utf8").split("\n").slice(1);
  console.error(lines.slice(0, lines.findIndex((line) => !line.startsWith("//"))).map((line) => line.replace(/^\/\/ ?/, "")).join("\n"));
  process.exit(2);
}

// ---- what the page shows, read through standard interfaces only ----
const seen = (page) => page.evaluate(() => {
  const shown = (element) => { const style = getComputedStyle(element), rect = element.getBoundingClientRect(); return style.visibility !== "hidden" && +style.opacity > 0.05 && rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.bottom > 0 && rect.left < innerWidth && rect.top < innerHeight; };
  const faded = (element) => { let all = 1; for (let one = element; one && one !== document.documentElement; one = one.parentElement) all *= +getComputedStyle(one).opacity; return all; };
  const sizes = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const holder = node.parentElement;
    if (!node.textContent.trim() || holder.closest("script, style") || !shown(holder) || faded(holder) < 0.05) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const rect = range.getClientRects()[0];
    if (!rect || rect.right < 0 || rect.bottom < 0 || rect.left > innerWidth || rect.top > innerHeight) continue;
    const scale = holder.offsetHeight ? holder.getBoundingClientRect().height / holder.offsetHeight : 1;
    sizes.push(Math.round(parseFloat(getComputedStyle(holder).fontSize) * scale * 10) / 10);
  }
  const records = [...document.querySelectorAll("[data-id]")].filter(shown).map((element) => element.getBoundingClientRect());
  const span = records.length ? { left: Math.min(...records.map((r) => r.left)), top: Math.min(...records.map((r) => r.top)), right: Math.max(...records.map((r) => r.right)), bottom: Math.max(...records.map((r) => r.bottom)) } : null;
  let chrome = 0;
  for (const element of document.body.querySelectorAll("*")) {
    if (getComputedStyle(element).position !== "fixed" || !shown(element) || element.querySelector("[data-id]") || element.closest("[data-id]")) continue;
    const rect = element.getBoundingClientRect();
    if (rect.width * rect.height < innerWidth * innerHeight * 0.8) chrome += (Math.min(rect.right, innerWidth) - Math.max(rect.left, 0)) * (Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0));
  }
  const round = (value) => Math.round(value * 100) / 100;
  return {
    smallestText: sizes.length ? Math.min(...sizes) : null, textSizes: [...new Set(sizes.map((size) => Math.round(size)))].sort((a, b) => a - b),
    textUnder11: sizes.filter((size) => size < 11).length, texts: sizes.length,
    recordsOutside: records.filter((r) => r.left < -1 || r.top < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1).length, records: records.length,
    spanWidth: span ? round((Math.min(span.right, innerWidth) - Math.max(span.left, 0)) / innerWidth) : 0, spanHeight: span ? round((Math.min(span.bottom, innerHeight) - Math.max(span.top, 0)) / innerHeight) : 0,
    chrome: round(chrome / (innerWidth * innerHeight)), scrolls: document.documentElement.scrollWidth > innerWidth + 1 || document.documentElement.scrollHeight > innerHeight + 1,
  };
});
const moving = (page) => page.evaluate(() => document.getAnimations().map((one) => {
  const timing = one.effect.getComputedTiming(), target = one.effect.target;
  const frames = one.effect.getKeyframes ? one.effect.getKeyframes() : [];
  const moves = frames.some((frame) => ["transform", "offsetDistance", "left", "top", "translate", "scale", "width", "height"].some((name) => name in frame));
  const eased = [timing.easing, ...frames.slice(0, -1).map((frame) => frame.easing)].find((easing) => easing && easing !== "linear"); // an animation's curve sits on its keyframes, a transition's on its timing
  return { on: target ? (target.id ? "#" + target.id : target.className && typeof target.className === "string" ? "." + target.className.split(" ")[0] : target.tagName.toLowerCase()) : "", what: one.transitionProperty || one.animationName || "", duration: Math.round(timing.duration), delay: Math.round(timing.delay), easing: eased || "linear", moves };
}));
const brief = (list) => { // one line per kind of animation, with how many elements run it
  const kinds = new Map();
  for (const one of list) { const key = [one.on, one.what, one.duration, one.delay, one.easing, one.moves].join("|"); kinds.set(key, { ...one, count: (kinds.get(key) || { count: 0 }).count + 1 }); }
  const all = [...kinds.values()];
  return { ends: Math.max(0, ...list.map((one) => one.delay + one.duration)), stages: [...new Set(list.map((one) => one.delay))].length, linear: list.filter((one) => one.easing === "linear" && one.duration > 0).length, moving: list.filter((one) => one.moves && one.duration > 0).length, fading: list.filter((one) => !one.moves && one.duration > 0).length, animations: all.slice(0, 24) };
};
const outside = (page, at) => page.evaluate((at) => { // the text a scenario step shows off the diagram's records, and what it covers
  const shown = (element) => { const style = getComputedStyle(element), rect = element.getBoundingClientRect(); return style.visibility !== "hidden" && +style.opacity > 0.05 && rect.width > 0 && rect.height > 0; };
  const target = document.querySelector(`[data-id="${at}"]`), line = target instanceof SVGElement ? target.querySelector("path") || target : null;
  const spots = !target ? [] : !line ? [target.getBoundingClientRect()] : Array.from({ length: 17 }, (_, k) => { // an edge is its line, never the box around it
    const point = line.getPointAtLength(line.getTotalLength() * k / 16).matrixTransform(line.getScreenCTM());
    return { left: point.x - 4, top: point.y - 4, right: point.x + 4, bottom: point.y + 4 };
  });
  let text = "", area = 0, covers = false;
  for (const element of document.body.querySelectorAll("*")) {
    if (getComputedStyle(element).position !== "fixed" || !shown(element) || element.querySelector("[data-id]") || element.closest("[data-id]")) continue;
    const rect = element.getBoundingClientRect();
    if (rect.width * rect.height >= innerWidth * innerHeight * 0.8 || (element.parentElement && getComputedStyle(element.parentElement).position === "fixed" && element.parentElement !== document.body)) continue;
    text += " " + element.innerText.replace(/\s+/g, " ").trim();
    area += rect.width * rect.height;
    if (spots.some((spot) => rect.left < spot.right && spot.left < rect.right && rect.top < spot.bottom && spot.top < rect.bottom)) covers = true;
  }
  return { text: text.trim(), characters: text.trim().length, share: Math.round(area / (innerWidth * innerHeight) * 1000) / 1000, coversItsRecord: covers, address: location.hash };
}, at);

async function capture(browser, file, out) {
  const html = fs.readFileSync(file, "utf8"), found = html.match(/<script type="application\/json" id="page-data">([\s\S]*?)<\/script>/);
  if (!found) throw new Error(`${file} holds no page data`);
  const contract = JSON.parse(found[1]), url = "file://" + path.resolve(file), measures = { page: path.resolve(file), stills: {}, motions: {}, hovers: {}, play: {} };
  for (const kind of ["look", "play"]) fs.mkdirSync(path.join(out, kind), { recursive: true });
  const levelOf = {}, kindOf = {};
  for (const level of contract.levels) for (const kind of ["nodes", "edges", "areas"]) for (const record of level[kind] || []) { levelOf[record.id] = level.id; kindOf[record.id] = kind; }
  const open = async (size, options = {}) => {
    const context = await browser.newContext({ viewport: { width: size[0], height: size[1] }, reducedMotion: options.still ? "reduce" : "no-preference", colorScheme: options.dark ? "dark" : "light" });
    const page = await context.newPage();
    await page.goto(url + (options.at || ""));
    await page.waitForTimeout(900);
    return page;
  };
  const still = async (page, name) => { await page.screenshot({ path: path.join(out, name + ".png") }); measures.stills[name] = await seen(page); };
  const visit = async (page, at) => { await page.goto(url + at); await page.waitForTimeout(1500); };
  const box = (page, id) => page.evaluate((id) => {
    const element = document.querySelector(`[data-id="${id}"]`);
    if (!element) return null;
    if (element instanceof SVGElement) { const line = element.querySelector("path") || element, long = line.getTotalLength(), spot = line.getPointAtLength(long / 2).matrixTransform(line.getScreenCTM()); return { x: spot.x, y: spot.y, left: spot.x - 4, top: spot.y - 4, right: spot.x + 4, bottom: spot.y + 4 }; }
    const rect = element.getBoundingClientRect();
    return { x: rect.left + Math.min(30, rect.width / 2), y: rect.bottom - Math.min(8, rect.height / 2), left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
  }, id);
  const card = (page) => page.evaluate(() => {
    const tip = [...document.querySelectorAll('[role="tooltip"], [role="dialog"][data-for]')].find((element) => +getComputedStyle(element).opacity > 0.5 && element.getBoundingClientRect().width > 0);
    if (!tip) return null;
    const rect = tip.getBoundingClientRect();
    return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, scrollsInside: tip.scrollHeight > tip.clientHeight + 1, characters: tip.innerText.length };
  });
  const rest = async (page, id, name) => { // the pointer comes to rest on a record
    const spot = await box(page, id);
    if (!spot) return null;
    await page.mouse.move(2, 2);
    await page.waitForTimeout(500);
    await page.mouse.move(spot.x, spot.y, { steps: 5 });
    const started = Date.now();
    let tip = null, waited = null;
    const entering = [];
    while (Date.now() - started < (waited === null ? 2500 : waited + 200)) {
      await page.waitForTimeout(40);
      entering.push(...(await moving(page)).filter((one) => /card|tip|pop|hover/i.test(one.on)));
      if (!tip && (tip = await card(page))) waited = Date.now() - started;
    }
    await page.waitForTimeout(500);
    tip = await card(page);
    const level = contract.levels.find((one) => one.id === levelOf[id]);
    const near = new Set((level.edges || []).filter((edge) => edge.from === id || edge.to === id).flatMap((edge) => [edge.from, edge.to]));
    const over = (rect) => tip && rect && rect.left < tip.right && tip.left < rect.right && rect.top < tip.bottom && tip.top < rect.bottom;
    let coveredNeighbours = 0, coveredOthers = 0;
    for (const node of level.nodes) if (node.id !== id) { const one = await box(page, node.id); if (over(one)) near.has(node.id) ? coveredNeighbours++ : coveredOthers++; }
    measures.hovers[name] = tip ? { record: id, shownAfterMs: waited, entrance: brief(entering.filter((one, i) => entering.findIndex((other) => JSON.stringify(other) === JSON.stringify(one)) === i)), coversItsRecord: !!over(spot), coveredNeighbours, coveredOtherNodes: coveredOthers, scrollsInside: tip.scrollsInside, characters: tip.characters, share: Math.round((tip.right - tip.left) * (tip.bottom - tip.top) / (page.viewportSize().width * page.viewportSize().height) * 1000) / 1000 } : { record: id, shownAfterMs: null };
    await still(page, name);
    return spot;
  };
  const sheet = async (page, name, act) => { // frames of one motion on one sheet, each under the milliseconds of the motion it shows
    const frames = [];
    await act();
    measures.motions[name] = brief(await moving(page));
    for (const due of FRAMES) { // the motion is held at each moment, since a loaded machine would take its first picture after the motion's first stage
      await page.evaluate((at) => document.getAnimations().forEach((one) => { one.pause(); one.currentTime = at; }), due);
      frames.push({ at: due, data: (await page.screenshot({ type: "jpeg", quality: 72 })).toString("base64") });
    }
    await page.evaluate(() => document.getAnimations().forEach((one) => one.play()));
    const size = page.viewportSize(), wide = 760, tall = Math.round(wide * size.height / size.width);
    const board = await page.context().newPage();
    await board.setViewportSize({ width: wide * 4 + 50, height: (tall + 34) * 2 + 20 });
    await board.setContent(`<body style="margin:10px;background:#888;display:grid;grid-template-columns:repeat(4,${wide}px);gap:10px;font:16px/24px sans-serif;color:#fff">${frames.map((frame) => `<figure style="margin:0"><figcaption>${frame.at} ms</figcaption><img width="${wide}" height="${tall}" src="data:image/jpeg;base64,${frame.data}"></figure>`).join("")}</body>`);
    await board.screenshot({ path: path.join(out, name + ".png") });
    await board.close();
    await page.waitForTimeout(600);
  };

  const first = contract.levels[0], fullest = [...contract.levels].sort((a, b) => b.nodes.length - a.nodes.length)[0];
  const nodes = contract.levels.flatMap((level) => level.nodes);
  const door = nodes.find((node) => node.opens && levelOf[node.id] === first.id) || nodes.find((node) => node.opens);
  const longest = [...nodes].sort((a, b) => JSON.stringify(b.info || {}).length - JSON.stringify(a.info || {}).length)[0];
  const ties = (id) => (first.edges || []).filter((edge) => edge.from === id || edge.to === id).length;
  const hub = [...first.nodes].sort((a, b) => ties(b.id) - ties(a.id))[0];
  const enter = async (page) => { const spot = await box(page, door.id); await page.mouse.move(2, 2); await page.waitForTimeout(300); await page.mouse.dblclick(spot.x, spot.y); };
  const jobs = [];
  const job = (run) => jobs.push(async () => { let page; try { await run((...given) => open(...given).then((opened) => (page = opened))); } finally { if (page) await page.context().close(); } });

  // ---- look ----
  job(async (start) => {
    const page = await start(DESK);
    await still(page, "look/1440-first-level");
    if (fullest.id !== first.id) { await visit(page, "#level=" + fullest.id); await still(page, "look/1440-fullest-level"); await visit(page, ""); }
    await rest(page, hub.id, "look/1440-pointer-on-node");
    if ((first.edges || []).length) await rest(page, first.edges[0].id, "look/1440-pointer-on-edge");
  });
  job(async (start) => {
    const page = await start(DESK, { at: "#level=" + levelOf[longest.id] });
    const kept = await rest(page, longest.id, "look/1440-longest-card");
    if (kept) { await page.mouse.click(kept.x, kept.y); await page.mouse.move(2, 2); await page.waitForTimeout(900); await still(page, "look/1440-longest-card-kept"); measures.hovers["look/1440-longest-card-kept"] = await card(page); await page.keyboard.press("Escape"); }
    await visit(page, "");
    await page.keyboard.press("/");
    await page.waitForTimeout(50);
    measures.motions["look/1440-search-opens"] = brief(await moving(page));
    await page.keyboard.type(hub.label.split(" ").pop().slice(0, 4), { delay: 30 });
    await page.waitForTimeout(700);
    await still(page, "look/1440-search");
  });
  if (door) {
    job(async (start) => {
      const page = await start(DESK, { at: "#level=" + levelOf[door.id] });
      await sheet(page, "look/1440-level-move-frames", () => enter(page));
      measures.motions["look/1440-level-move-frames"].arrivedAt = await page.evaluate(() => location.hash);
      await sheet(page, "look/1440-level-back-frames", () => page.keyboard.press("["));
    });
    job(async (start) => { const page = await start(DESK, { still: true, at: "#level=" + levelOf[door.id] }); await sheet(page, "look/1440-level-move-reduced-motion-frames", () => enter(page)); });
  }
  job(async (start) => rest(await start(DESK, { dark: true }), hub.id, "look/1440-dark-pointer-on-node"));
  job(async (start) => {
    const page = await start(DESK, { still: true });
    await rest(page, hub.id, "look/1440-reduced-motion-pointer-on-node");
    await page.keyboard.press("/");
    await page.waitForTimeout(50);
    measures.motions["look/1440-reduced-motion-search-opens"] = brief(await moving(page));
  });
  for (const [size, name] of [[WIDE, "1920"], [SMALL, "1024"]]) job(async (start) => {
    const page = await start(size);
    await still(page, `look/${name}-first-level`);
    await rest(page, hub.id, `look/${name}-pointer-on-node`);
    if (fullest.id !== first.id) { await visit(page, "#level=" + fullest.id); await still(page, `look/${name}-fullest-level`); }
  });

  // ---- play ----
  const scenario = (contract.scenarios || [])[0];
  if (scenario) {
    const steps = scenario.steps, play = measures.play, at = (one, i) => `#scenario=${one.id}&step=${i}&level=${levelOf[one.steps[i].at]}`;
    const reached = (page) => page.evaluate(() => { const given = new URLSearchParams(location.hash.slice(1)); return given.get("scenario") ? +(given.get("step") || 0) + 1 : null; });
    play.scenario = scenario.id; play.steps = steps.length; play.start = []; play.rest = [];
    job(async (start) => {
      const page = await start(DESK);
      await page.screenshot({ path: path.join(out, "play/start-0.png") });
      const entry = page.getByRole("button", { name: /scenario/i }).first();
      if (await entry.count()) {
        await entry.click(); await page.waitForTimeout(700);
        await page.screenshot({ path: path.join(out, "play/start-1.png") });
        play.start.push("press the button named Scenarios");
        if (!(await reached(page))) {
          const row = page.getByText(scenario.title, { exact: false }).first();
          if (await row.count()) { await row.click(); play.start.push("press the scenario's title"); await page.waitForTimeout(1200); await page.screenshot({ path: path.join(out, "play/start-2.png") }); }
        }
      }
      play.actionsToStart = (await reached(page)) ? play.start.length : null;
      await page.mouse.move(2, 2);
      await visit(page, at(scenario, 0));
      for (let i = 0; i < Math.min(steps.length, 8); i++) {
        if (i) { await page.keyboard.press("ArrowRight"); await page.waitForTimeout(1600); }
        await still(page, `play/step-${i + 1}-of-${steps.length}`);
        play.rest.push({ step: i + 1, names: steps[i].at, kind: kindOf[steps[i].at], note: steps[i].note || "", noteCharacters: await page.evaluate(() => { const chip = document.getElementById("chip"); return chip && chip.classList.contains("show") ? chip.textContent.length : 0; }), ...(await outside(page, steps[i].at)) });
      }
    });
    const edgeStep = steps.findIndex((step, i) => i > 0 && kindOf[step.at] === "edges" && levelOf[step.at] === levelOf[steps[i - 1].at]);
    const crossing = contract.scenarios.map((one) => [one, one.steps.findIndex((step, i) => i > 0 && levelOf[step.at] !== levelOf[one.steps[i - 1].at])]).find(([, i]) => i > 0);
    if (edgeStep > 0) job(async (start) => { const page = await start(DESK, { at: at(scenario, edgeStep - 1) }); await sheet(page, `play/step-${edgeStep + 1}-along-an-edge-frames`, () => page.keyboard.press("ArrowRight")); });
    if (edgeStep > 0) job(async (start) => { const page = await start(DESK, { still: true, at: at(scenario, edgeStep - 1) }); await sheet(page, `play/step-${edgeStep + 1}-reduced-motion-frames`, () => page.keyboard.press("ArrowRight")); });
    if (crossing) job(async (start) => {
      const [one, i] = crossing, page = await start(DESK, { at: at(one, i - 1) });
      await sheet(page, "play/step-to-another-level-frames", () => page.keyboard.press("ArrowRight"));
      await page.waitForTimeout(600);
      await still(page, "play/step-to-another-level-at-rest");
      play.stepToAnotherLevel = { scenario: one.id, step: i + 1, from: levelOf[one.steps[i - 1].at], to: levelOf[one.steps[i].at], ...(await outside(page, one.steps[i].at)) };
    });
    job(async (start) => {
      const page = await start(DESK, { at: at(scenario, 0) });
      await page.keyboard.press("ArrowRight"); await page.waitForTimeout(60); await page.keyboard.press("ArrowRight"); await page.waitForTimeout(1500);
      play.twoQuickKeysReachStep = await reached(page);
      const far = Math.min(steps.length, 4), control = page.getByRole("button", { name: new RegExp(`^step ${far}\\b`, "i") }).first();
      if (await control.count()) { await control.click(); await page.waitForTimeout(1500); play.buttonNamedStep = { pressed: far, reached: await reached(page) }; } else play.buttonNamedStep = null;
      play.buttonNamedPlayOrPause = (await page.getByRole("button", { name: /^(play|pause)\b/i }).count()) > 0;
    });
    job(async (start) => {
      const page = await start(DESK, { at: at(scenario, 0) });
      await page.keyboard.press(" ");
      play.stepEachSecondAfterSpace = [];
      for (let second = 1; second <= 6; second++) { await page.waitForTimeout(1000); play.stepEachSecondAfterSpace.push(await reached(page)); }
      await page.screenshot({ path: path.join(out, "play/six-seconds-after-space.png") });
      await page.keyboard.press(" ");
      await page.waitForTimeout(1300);
      play.stepAfterSecondSpace = [await reached(page)];
      await page.waitForTimeout(1300);
      play.stepAfterSecondSpace.push(await reached(page));
    });
    job(async (start) => {
      const page = await start(DESK, { at: at(scenario, steps.length - 1) });
      await page.keyboard.press("ArrowRight"); await page.waitForTimeout(1500);
      await still(page, "play/after-the-last-step");
      play.afterTheLastStep = await outside(page, steps[steps.length - 1].at);
    });
    for (const [size, name] of [[SMALL, "1024"]]) job(async (start) => {
      const i = Math.min(2, steps.length - 1), page = await start(size, { at: at(scenario, i) });
      await page.waitForTimeout(700);
      await still(page, `play/${name}-step-${i + 1}`);
      play[`at${name}`] = { ...(await outside(page, steps[i].at)), recordInWindow: await page.evaluate((id) => { const rect = document.querySelector(`[data-id="${id}"]`).getBoundingClientRect(); return rect.left >= 0 && rect.top >= 0 && rect.right <= innerWidth && rect.bottom <= innerHeight; }, steps[i].at) };
    });
  }
  // four at a time, so a frame sheet's timing is not starved
  let next = 0;
  await Promise.all([0, 1, 2, 3].map(async () => { while (next < jobs.length) await jobs[next++](); }));
  fs.writeFileSync(path.join(out, "measures.json"), JSON.stringify(measures, null, 1) + "\n");
  return fs.readdirSync(path.join(out, "look")).length + fs.readdirSync(path.join(out, "play")).length;
}

async function main() {
  const started = Date.now();
  if (browsers.missing()) {
    console.log(`FAIL setup: ${browsers.missing()}`);
    return 1;
  }
  const out = path.resolve(args[0]);
  let pages = args.slice(1).map((file) => ({ name: path.basename(path.dirname(path.resolve(file))) || "page", file }));
  if (!pages.length) {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "system-capture-"));
    for (const name of fs.readdirSync(path.join(ROOT, "examples")).sort()) {
      const source = path.join(ROOT, "examples", name, "contract.json"), file = path.join(scratch, name + ".html");
      if (!fs.existsSync(source)) continue;
      const made = spawnSync("python3", [path.join(ROOT, "scripts", "make-page.py"), source, file], { encoding: "utf8" });
      if (made.status !== 0) { console.log(`FAIL ${name}: make-page.py refused it: ${(made.stderr || "").split("\n")[0]}`); return 1; }
      pages.push({ name, file });
    }
  }
  const browser = await browsers.launch().catch((error) => { console.log(`FAIL setup: ${error.message}`); return null; });
  if (!browser) return 1;
  let failed = 0;
  await Promise.all(pages.map(async (one) => {
    try { console.log(`${one.name}: ${await capture(browser, one.file, path.join(out, one.name))} pictures and measures.json in ${path.join(out, one.name)}`); }
    catch (error) { failed += 1; console.log(`FAIL ${one.name}: ${error.message.split("\n")[0]}`); }
  }));
  await browser.close();
  console.log(`${failed ? "FAIL" : "captured"} in ${((Date.now() - started) / 1000).toFixed(1)} s`);
  return failed ? 1 : 0;
}

main().then((code) => process.exit(code));
