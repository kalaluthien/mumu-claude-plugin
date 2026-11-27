#!/usr/bin/env node
// Plant claims on every kind of record in each example contract of system and flow, build each page, drive it in a headless Chromium
// at 1200 by 800, and print `PASS <example>` or `FAIL <example>: <reasons>` per example, then PASS or FAIL.
// Planted: one claim of each status, guarantees and assumptions in turn and one that holds with a fault, each on the first record of
// every kind the contract holds (level, area, node, task, edge, fragment, milestone), and one claim on every edge of the first level
// that has edges.
//   badges   on the record each claim's card leads to, one badge of it sits on that record, beside the record's own name.
//   faces    each badge says its kind by initial (G, A) and shape (a square corner, a pill), its status by glyph (✓ ? ! ✗) and its
//            status token's fill, its text drawn at least half the badge's height, and only a claim that holds with a fault carries
//            the mark `*`.
//   owners   no badge on any view sits on a record its claim is not on.
//   cards    for each planted claim, a click on a badge opens its claim's card, which lists each record the claim is on, and each listed record, clicked,
//            shows that record and its badge, on whichever of the card's pages names it.
//   edges    each badge of an edge sits inside its edge's label, shown or tucked, and the label is in sight.
//   list     the Claims button lists every claim once, under `Claims: <status>`, fails first, then conflicting, unknown and holds.
//
// usage: drive-claim-badges.cjs
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));

if (process.argv.length > 2) {
  console.error("usage: drive-claim-badges.cjs");
  process.exit(2);
}
const PLUGIN = path.join(__dirname, "..", "..");
const KINDS = ["levels", "areas", "nodes", "tasks", "edges", "fragments", "milestones"];
const ORDER = ["fails", "conflicting", "unknown", "holds"];
const PLANTED = [["planted-holds", "guarantee", "holds", null], ["planted-fault", "assumption", "holds", "no document states it"],
  ["planted-unknown", "guarantee", "unknown", "nothing read settles it"], ["planted-conflicting", "assumption", "conflicting", "two sources disagree"],
  ["planted-fails", "guarantee", "fails", "the record breaks it"]];
const GLYPHS = { holds: "✓", unknown: "?", conflicting: "!", fails: "✗" };

// The contract with the planted claims, and the claims it then holds.
function plant(contract) {
  const template = { ...contract.claims[0] }, firsts = KINDS.flatMap((kind) => (contract[kind] || []).slice(0, 1).map((record) => record.id));
  const level = (contract.levels || []).find((one) => (contract.edges || []).some((edge) => edge.level === one.id)) || (contract.levels || [])[0], nodes = new Map((contract.nodes || []).map((node) => [node.id, node]));
  const onLevel = (edge) => edge.level ? edge.level === level.id : nodes.has(edge.from) && (nodes.get(edge.from).level || level.id) === (nodes.get((contract.nodes || [])[0].id).level || level.id);
  const claim = (id, kind, status, fault, on) => ({ ...template, id, title: id, kind, statement: "The planted record keeps its planted state.", on,
    ...(status === "holds" ? {} : { status }), ...(fault ? { fault } : {}) });
  for (const key of ["status", "fault"]) delete template[key];
  const planted = [...PLANTED.map(([id, kind, status, fault]) => claim(id, kind, status, fault, firsts)),
    claim("planted-edges", "assumption", "holds", null, (contract.edges || []).filter(onLevel).map((edge) => edge.id))];
  return { ...contract, claims: [...contract.claims.map((one) => ({ ...one })), ...planted] };
}

// ---- in the page ----
function badgeFacts() { // each badge in sight: its claim, its record, its owner's words beside it, its text, shape, fill and status fill
  const canvas = document.createElement("canvas"), context = canvas.getContext("2d", { willReadFrequently: true });
  canvas.width = canvas.height = 1;
  const rgba = (value) => { context.clearRect(0, 0, 1, 1); context.fillStyle = "rgba(0, 0, 0, 0)"; context.fillStyle = value; context.fillRect(0, 0, 1, 1); return [...context.getImageData(0, 0, 1, 1).data].join(","); };
  const root = getComputedStyle(document.documentElement);
  return [...document.querySelectorAll("button.claim")].filter((badge) => badge.checkVisibility({ visibilityProperty: true, opacityProperty: true }) && badge.getBoundingClientRect().width > 0).map((badge) => {
    const span = badge.closest("span.claims"), style = getComputedStyle(badge), box = badge.getBoundingClientRect();
    const crumb = span && span.parentElement && span.parentElement.id === "crumbs" ? span.previousElementSibling : null;
    const owner = crumb || (span && span.parentElement), range = document.createRange();
    range.selectNodeContents(badge);
    const drawn = range.getBoundingClientRect();
    const own = owner ? [...owner.childNodes].filter((node) => node !== span).map((node) => node.textContent).join(" ") : "";
    return { claim: badge.dataset.claim, record: span ? span.dataset.for : null, owner: own.replace(/\s+/g, " ").trim(), text: badge.textContent, label: badge.getAttribute("aria-label") || "",
      radius: Number.parseFloat(style.borderTopLeftRadius), height: box.height, textHeight: drawn.height, textWidth: drawn.width, fill: rgba(style.backgroundColor),
      token: rgba(root.getPropertyValue(`--status-${badge.dataset.status}`).trim() || "transparent") };
  });
}

const blocked = (error) => ((error.message.match(/[^\n]*intercepts pointer events/) || [error.message.split("\n")[0]])[0]).trim().slice(-200);

async function settle(tab) {
  await tab.waitForTimeout(250);
  await tab.waitForFunction(() => !document.getAnimations().some((one) => one.playState === "running" && one.effect && one.effect.getTiming().iterations !== Infinity) && !document.body.dataset.busy, null, { timeout: 8000 }).catch(() => {});
  await tab.waitForTimeout(150);
}

async function openClaim(tab, id) { // the claim's card, picked in the search by its keys, the pointer parked in a corner so no hover card takes its place
  await tab.keyboard.press("Escape");
  await tab.mouse.move(1, 799);
  await tab.evaluate(() => document.getElementById("search").click());
  await tab.waitForFunction(() => document.activeElement && document.activeElement.id === "query", null, { timeout: 2000 });
  await tab.keyboard.type(id);
  await tab.waitForSelector(`#hits [data-hit="${id}"]`, { timeout: 2000 });
  for (let k = 0; k < 20 && !await tab.evaluate((id) => !!document.querySelector(`#hits [data-hit="${id}"][aria-selected="true"]`), id); k++) await tab.keyboard.press("ArrowDown");
  await tab.keyboard.press("Enter");
  await settle(tab);
  return tab.waitForFunction((id) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === id; }, id, { timeout: 3000 }).then(() => true, () => false);
}

// The records the open card names, read on each of its pages; or, given ID, the page of the card that names ID turned to.
async function leaf(tab, id) {
  const refs = new Set();
  for (let k = 0; k < 12; k++) {
    const here = await tab.evaluate(() => [...document.querySelectorAll("#card .ref[data-ref]")].map((chip) => chip.dataset.ref));
    here.forEach((one) => refs.add(one));
    if (id && here.includes(id)) return true;
    const turn = await tab.$("#card .turn");
    if (!turn) break;
    await turn.click();
    await tab.waitForTimeout(120);
    if (!id && (await tab.evaluate(() => (document.querySelector("#card .turn") || {}).textContent || "")).startsWith("1–")) break;
  }
  return id ? false : [...refs];
}

async function drive(browser, page, contract) {
  const tab = await browser.newPage({ viewport: { width: 1200, height: 800 }, colorScheme: "light" }), faults = [];
  const found = { badges: [], faces: [], owners: [], cards: [], edges: [], list: [] };
  tab.on("pageerror", (error) => faults.push(String(error)));
  await tab.goto("file://" + page);
  await settle(tab);
  const claims = new Map(contract.claims.map((claim) => [claim.id, claim])), status = (claim) => claim.status || "holds";
  const records = new Map(KINDS.flatMap((kind) => (contract[kind] || []).map((record) => [record.id, { kind, record }])));
  const named = (id) => { const { record } = records.get(id) || {}; return record ? String(record.label || record.title || record.kind || id) : id; };
  const plain = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, "");
  const add = (step, line) => { if (!found[step].includes(line)) found[step].push(line); };
  const look = async () => { // every badge in sight, held to its face and owner
    const facts = await tab.evaluate(badgeFacts);
    for (const fact of facts) {
      const claim = claims.get(fact.claim);
      if (!claim) { add("owners", `a badge names ${fact.claim}, which is no claim`); continue; }
      if (!fact.record || !(claim.on || []).includes(fact.record)) add("owners", `a badge of ${fact.claim} sits on ${fact.record || "no record"}, which the claim is not on`);
      else if (!plain(fact.owner).includes(plain(named(fact.record)).slice(0, 12))) add("owners", `a badge of ${fact.claim} on ${fact.record} sits beside "${fact.owner.slice(0, 30)}", not its record's name`);
      const faulted = status(claim) === "holds" && !!claim.fault, want = { guarantee: "G", assumption: "A" }[claim.kind] + GLYPHS[status(claim)] + (faulted ? "*" : "");
      if (fact.text !== want) add("faces", `${fact.claim}'s badge reads ${JSON.stringify(fact.text)}, not ${want}`);
      else if (fact.textWidth <= 0 || fact.textHeight < fact.height / 2) add("faces", `${fact.claim}'s badge draws its text ${+fact.textHeight.toFixed(1)} px high in a badge ${+fact.height.toFixed(1)} px high`);
      if (!fact.label.includes(claim.kind) || !fact.label.includes(status(claim))) add("faces", `${fact.claim}'s badge is named ${JSON.stringify(fact.label)}`);
      if (claim.kind === "guarantee" ? fact.radius > 3 : fact.radius < fact.height / 2 - 0.5) add("faces", `${fact.claim}'s badge, a ${claim.kind}, has corners of ${fact.radius} px at ${fact.height} px high`);
      if (fact.fill !== fact.token) add("faces", `${fact.claim}'s badge is filled ${fact.fill}, not its status token's ${fact.token}`);
    }
    return facts;
  };
  // edges: every edge badge on the first view sits inside its label, which is in sight
  const edges = new Set((contract.edges || []).map((edge) => edge.id));
  const labels = await tab.evaluate((ids) => [...document.querySelectorAll("span.claims")].filter((span) => ids.includes(span.dataset.for)).map((span) => {
    const label = span.closest(".label, .edge-label"), box = span.getBoundingClientRect(), outer = label && label.getBoundingClientRect();
    return { edge: span.dataset.for, label: !!label, tucked: !!label && label.classList.contains("tucked"), seen: !!label && label.checkVisibility({ visibilityProperty: true, opacityProperty: true }),
      inside: !!outer && box.left >= outer.left - 2 && box.right <= outer.right + 2 && box.top >= outer.top - 2 && box.bottom <= outer.bottom + 2,
      sight: !!outer && outer.right > 0 && outer.bottom > 0 && outer.left < innerWidth && outer.top < innerHeight };
  }), [...edges]);
  const planted = claims.get("planted-edges");
  if (planted && planted.on.length && !labels.length) add("edges", "no edge of the first level shows a badge");
  for (const one of labels) {
    if (!one.label) add("edges", `${one.edge}'s badges sit outside any edge label`);
    else if (!one.inside || !one.seen) add("edges", `${one.edge}'s badges are ${one.seen ? "outside its" : "in a hidden"} ${one.tucked ? "tucked " : ""}label`);
  }
  await look();
  // cards and badges: each claim's card leads to each record it is on, where one badge of it sits and opens its card again
  for (const claim of contract.claims.filter((one) => one.id.startsWith("planted-"))) {
    if (!await openClaim(tab, claim.id)) { add("cards", `the search opens no card for ${claim.id}`); continue; }
    const listed = await leaf(tab);
    for (const id of claim.on || []) if (!listed.includes(id)) add("cards", `${claim.id}'s card does not list ${id}`);
    for (const id of claim.on || []) {
      if (!listed.includes(id)) continue;
      if (!await openClaim(tab, claim.id)) { add("cards", `the search opens no card for ${claim.id}`); break; }
      if (!await leaf(tab, id)) { add("cards", `${claim.id}'s card names ${id} on no page`); continue; }
      await tab.click(`#card .ref[data-ref="${id}"]`, { timeout: 3000 }).catch((error) => add("cards", `${claim.id}'s card's ${id} cannot be clicked: ${blocked(error)}`));
      await settle(tab);
      const facts = await look(), here = facts.filter((fact) => fact.claim === claim.id && fact.record === id);
      if (here.length !== 1) { add("badges", `${id} shows ${here.length} badges of ${claim.id} once ${claim.id}'s card leads to it`); continue; }
      const badge = await tab.$(`span.claims[data-for="${id}"] > button.claim[data-claim="${claim.id}"]:visible`);
      if (!badge) { add("badges", `${id}'s badge of ${claim.id} cannot be found to click`); continue; }
      await tab.keyboard.press("Escape");
      await badge.click({ timeout: 3000 }).catch((error) => add("cards", `${id}'s badge of ${claim.id} cannot be clicked: ${blocked(error)}`));
      await settle(tab);
      const opened = await tab.evaluate((claim) => { const card = document.getElementById("card"); return card.classList.contains("show") && card.dataset.for === claim; }, claim.id);
      if (!opened) add("cards", `a click on ${id}'s badge of ${claim.id} opens no card of ${claim.id}`);
    }
  }
  // list: one Claims list, grouped by status
  await tab.keyboard.press("Escape");
  await tab.evaluate(() => document.getElementById("claims").click());
  await tab.waitForTimeout(300);
  const rows = await tab.evaluate(() => [...document.querySelectorAll("#hits h3, #hits [data-hit]")].map((one) => one.tagName === "H3" ? ["group", one.textContent.trim()] : ["hit", one.dataset.hit]));
  const seen = new Map(), groups = [];
  let group = null;
  for (const [what, value] of rows) if (what === "group") { group = value; groups.push(value); } else seen.set(value, [...(seen.get(value) || []), group]);
  const want = ORDER.filter((one) => contract.claims.some((claim) => status(claim) === one)).map((one) => `Claims: ${one}`);
  if (JSON.stringify(groups.filter((one) => one.startsWith("Claims"))) !== JSON.stringify(want)) add("list", `the Claims list's groups are ${JSON.stringify(groups)}, not ${JSON.stringify(want)}`);
  for (const claim of contract.claims) {
    const under = seen.get(claim.id) || [];
    if (under.length !== 1 || under[0] !== `Claims: ${status(claim)}`) add("list", `${claim.id} is listed under ${JSON.stringify(under)}`);
  }
  if (faults.length) found.owners.push(`the page threw ${faults[0]}`);
  await tab.close();
  return found;
}

(async () => {
  if (missing()) { console.log(`FAIL browser: ${missing()}\nFAIL`); process.exit(1); }
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "claim-badges-")), browser = await launch();
  let failed = false, examples = 0;
  for (const skill of ["system", "flow"]) {
    const folder = path.join(PLUGIN, "skills", skill, "examples");
    for (const name of fs.existsSync(folder) ? fs.readdirSync(folder).sort() : []) {
      const file = path.join(folder, name, "contract.json");
      if (!fs.existsSync(file)) continue;
      examples++;
      const step = `${skill} ${name}`, contract = plant(JSON.parse(fs.readFileSync(file, "utf8")));
      const planted = path.join(scratch, `${skill}-${name}.json`), page = path.join(scratch, `${skill}-${name}.html`);
      fs.writeFileSync(planted, JSON.stringify(contract, null, 1));
      const built = spawnSync("python3", [path.join(PLUGIN, "skills", skill, "scripts", "make-page.py"), planted, page], { encoding: "utf8" });
      if (built.status !== 0) { failed = true; console.log(`FAIL ${step}: make-page.py refused the planted claims: ${(built.stdout + built.stderr).trim().split("\n").slice(-3).join(" ")}`); continue; }
      try {
        const found = await drive(browser, page, contract), reasons = Object.entries(found).filter(([, lines]) => lines.length).map(([part, lines]) => `${part}: ${lines.slice(0, 4).join("; ")}${lines.length > 4 ? ` and ${lines.length - 4} more` : ""}`);
        failed = failed || reasons.length > 0;
        console.log(reasons.length ? `FAIL ${step}: ${reasons.join(" | ")}` : `PASS ${step}`);
      } catch (error) { failed = true; console.log(`FAIL ${step}: ${error.message.split("\n")[0]}`); }
    }
  }
  await browser.close();
  fs.rmSync(scratch, { recursive: true, force: true });
  if (!examples) { failed = true; console.log("FAIL examples: no example contract of system or flow"); }
  console.log(failed ? "FAIL" : "PASS");
  process.exit(failed ? 1 : 0);
})();
