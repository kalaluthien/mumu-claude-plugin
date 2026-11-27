#!/usr/bin/env node
// Check every space and type size each example page of system and flow and the relay's starter page set, and print `PASS <step>`
// or `FAIL <step>: <reasons>` per step, then PASS or FAIL.
//   tokens   each space and type token of ../page-tokens.css stands under a comment citing a source its header lists.
//   literals no page's style sets a margin, padding, gap, font size or line height by a length of its own, outside the tokens' own
//            text and the relay's own overlay, which runs on any page and so sets its own.
//   <page> <width>  in a headless Chromium at 390 by 844 and 1200 by 800, with each space and type token set to a planted length,
//            as loaded, with the search open on a query, and with the card of its first node, found by search, open: every margin, padding and gap of each
//            element shown is 0 or a planted space, negated or not, every font size a planted type size times the page's own zoom
//            (`--grow`), and every line height set in px a planted line height, so none comes from elsewhere, the browser's own
//            defaults included. A keyword (`auto`, `normal`), a percentage and a line height with no unit are not lengths of
//            their own, and the relay's overlay is not measured.
//
// usage: drive-page-sizes.cjs
const fs = require("fs");
const path = require("path");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));

if (process.argv.length > 2) {
  console.error("usage: drive-page-sizes.cjs");
  process.exit(2);
}
const PLUGIN = path.join(__dirname, "..", "..");
const TOKENS = path.join(PLUGIN, "lib", "page-tokens.css");
const SIZES = [[390, 844], [1200, 800]];
const KINDS = { spacing: "space", type: "type", leading: "leading" }; // each token family by its name's head
const pages = ["system", "flow"].flatMap((skill) => {
  const folder = path.join(PLUGIN, "skills", skill, "examples");
  return fs.existsSync(folder) ? fs.readdirSync(folder).sort().map((name) => path.join(folder, name, "page.html")).filter((file) => fs.existsSync(file)) : [];
}).concat(path.join(PLUGIN, "skills", "system", "assets", "diagram-page.html"));

// The space and type tokens, each [name, its family, the comment above it], and the source tags the header lists.
function tokens() {
  const text = fs.existsSync(TOKENS) ? fs.readFileSync(TOKENS, "utf8") : "", header = (text.match(/^\/\*[\s\S]*?\*\//) || [""])[0];
  const sources = new Set([...header.matchAll(/^\s*(?:Sources:\s*)?(\[[a-z-]+\])\s/gm)].map((match) => match[1]));
  const list = [];
  let comment = "";
  for (const match of text.slice(header.length).matchAll(/\/\*([\s\S]*?)\*\/|--([a-z]+)-([0-9]+)\s*:\s*([^;]+);/g)) {
    if (match[1] !== undefined) comment = match[1];
    else if (KINDS[match[2]]) list.push([`--${match[2]}-${match[3]}`, KINDS[match[2]], comment]);
  }
  return { text, sources, list };
}

function tokenSources({ sources, list }) {
  if (!fs.existsSync(TOKENS)) return ["lib/page-tokens.css is missing"];
  const found = Object.values(KINDS).filter((kind) => !list.some(([, family]) => family === kind)).map((kind) => `the tokens hold no ${kind} token`);
  for (const [name, , comment] of list) {
    const cited = comment.match(/\[[a-z-]+\]/g) || [];
    if (!cited.length) found.push(`${name} stands under no comment citing a source`);
    for (const tag of cited) if (!sources.has(tag)) found.push(`${name} cites ${tag}, which the header does not list`);
  }
  return found;
}

function literals(text) {
  const found = [];
  for (const page of pages) {
    const own = fs.readFileSync(page, "utf8").split(text.trim()).join("").replace(/<!-- relay runtime -->[\s\S]*?<!-- \/relay runtime -->/g, ""), name = path.relative(PLUGIN, page);
    const styled = [...own.matchAll(/<style[^>]*>([\s\S]*?)<\/style>|\sstyle="([^"]*)"/g)].map((match) => match[1] || match[2] || "").join("\n");
    const seen = [...styled.matchAll(/(?<![-\w])((?:margin|padding)(?:-[a-z]+)*|(?:row-|column-)?gap|font-size|font|line-height)\s*:\s*([^;{}"]*)/g)]
      .filter((match) => /(?<![\w-])-?\d*\.?\d+(?:px|r?em|ex|ch|pt|vw|vh)\b/.test(match[2].replace(/var\(--[a-z0-9-]+\)/g, ""))).map((match) => `${match[1]}: ${match[2].trim()}`);
    if (seen.length) found.push(`${name} sets ${[...new Set(seen)].slice(0, 5).join(", ")}`);
  }
  return found;
}

// In the page: each shown element's margin, padding, gap, font size and px line height that no planted token gives.
function measure(planted) {
  const near = (value, list) => list.some((one) => Math.abs(Math.abs(value) - one) < 0.02);
  const sides = ["margin-top", "margin-right", "margin-bottom", "margin-left", "padding-top", "padding-right", "padding-bottom", "padding-left", "row-gap", "column-gap"];
  const found = [];
  const name = (element) => element.tagName.toLowerCase() + (element.id ? "#" + element.id : "") + (typeof element.className === "string" && element.className ? "." + element.className.trim().split(/\s+/).join(".") : "");
  for (const element of [document.body, ...document.body.querySelectorAll("*")]) {
    if (element.closest("#relay-ui, script, style, template") || !element.checkVisibility({ visibilityProperty: true })) continue;
    const map = element.computedStyleMap(), length = (property) => { const value = map.get(property); return value && value.unit === "px" ? value.value : null; };
    for (const side of sides) {
      const value = length(side);
      if (value !== null && value !== 0 && !near(value, planted.space)) found.push(`${name(element)} has ${side} ${+value.toFixed(2)}px`);
    }
    const grow = parseFloat(getComputedStyle(element).getPropertyValue("--grow")) || 1, size = length("font-size");
    if (size !== null && !near(size, planted.type) && !near(size / grow, planted.type)) found.push(`${name(element)} has font-size ${+size.toFixed(2)}px`);
    const leading = length("line-height");
    if (leading !== null && !near(leading, planted.leading)) found.push(`${name(element)} has line-height ${+leading.toFixed(2)}px`);
  }
  return found;
}

// The label of the page's first node: its contract's, beside it, or its own data's.
function firstLabel(page) {
  const contract = path.join(path.dirname(page), "contract.json");
  if (fs.existsSync(contract)) return JSON.parse(fs.readFileSync(contract, "utf8")).nodes[0].label;
  const data = fs.readFileSync(page, "utf8").match(/<script type="application\/json" id="page-data">([\s\S]*?)<\/script>/);
  return data ? JSON.parse(data[1])["diagram-main"].nodes[0].label : "";
}

async function drive(browser, page, [width, height], overrides, planted) {
  const tab = await browser.newPage({ viewport: { width, height } }), faults = [], found = [];
  tab.on("pageerror", (error) => faults.push(String(error)));
  await tab.goto("file://" + page);
  await tab.waitForTimeout(500);
  await tab.addStyleTag({ content: overrides });
  await tab.waitForTimeout(100);
  const run = async () => found.push(...await tab.evaluate(measure, planted));
  await run();
  await tab.keyboard.press("/");
  await tab.keyboard.type("a");
  await tab.waitForTimeout(300);
  await run();
  await tab.keyboard.press("Escape");
  await tab.keyboard.press("/");
  await tab.keyboard.type(firstLabel(page));
  await tab.waitForTimeout(300);
  await tab.keyboard.press("Enter");
  await tab.waitForTimeout(500);
  await tab.waitForFunction(() => !document.getAnimations().some((one) => one.playState === "running" && one.effect && one.effect.getTiming().iterations !== Infinity), null, { timeout: 8000 }).catch(() => {});
  if (!(await tab.evaluate(() => document.getElementById("card") && document.getElementById("card").classList.contains("show")))) found.push(`Enter on the search for ${firstLabel(page)} shows no card`);
  await run();
  if (faults.length) found.push(`the page threw ${faults[0]}`);
  await tab.close();
  return [...new Set(found)];
}

(async () => {
  const read = tokens(), checks = [["tokens", tokenSources(read)], ["literals", literals(read.text)]];
  if (pages.length < 2) checks.push(["examples", ["no example page of system or flow"]]);
  let failed = false;
  for (const [step, reasons] of checks) { failed = failed || reasons.length > 0; console.log(reasons.length ? `FAIL ${step}: ${reasons.join("; ")}` : `PASS ${step}`); }
  if (missing()) { console.log(`FAIL browser: ${missing()}\nFAIL`); process.exit(1); }
  const planted = { space: [], type: [], leading: [] };
  const overrides = ":root, :root:root { " + read.list.map(([name, family], k) => { const value = 40 + 3 * k + 0.5; planted[family].push(value); return `${name}: ${value}px !important;`; }).join(" ") + " }";
  const browser = await launch();
  for (const page of pages) for (const size of SIZES) {
    const step = `${path.relative(PLUGIN, page)} ${size[0]}`;
    try {
      const reasons = await drive(browser, page, size, overrides, planted);
      failed = failed || reasons.length > 0;
      console.log(reasons.length ? `FAIL ${step}: ${reasons.length} — ${reasons.slice(0, 8).join("; ")}` : `PASS ${step}`);
    } catch (error) { failed = true; console.log(`FAIL ${step}: ${error.message.split("\n")[0]}`); }
  }
  await browser.close();
  console.log(failed ? "FAIL" : "PASS");
  process.exit(failed ? 1 : 0);
})();
