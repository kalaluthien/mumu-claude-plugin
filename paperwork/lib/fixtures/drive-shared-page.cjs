#!/usr/bin/env node
// Drive the pages replay-shared-page.py builds on a copy of the plugin with a planted frame, in a headless Chromium at 1200 by 800 in
// the light scheme, and print `PASS <page>` or `FAIL <page>: <reason>` per page, then `PASS one bar` or `FAIL one bar: <reason>`.
// On each page the crumbs stand at the top left, each crumb planted; the light foreground token draws the body's text in the planted
// colour; the search bar is the last tool at the top right, titled as its box's placeholder `Search <records>`, and `/` opens the
// palette with the box focused; the page's query typed shows a hit's mark in the planted colour, and Enter shows the top record's card
// headed by the planted word. The search bar stands in one place on every page.
//
// usage: drive-shared-page.cjs <spec.json>
//   spec.json  {"pages": [<page.html>...], "queries": [<query of each page>...], "title": <word>, "mark": <colour>, "ink": <colour>}
const fs = require("fs");
const path = require("path");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));
const { check, until } = require(path.join(__dirname, "..", "check-step.cjs"));

const [file] = process.argv.slice(2);
if (!file || process.argv.length > 3 || !fs.existsSync(file)) {
  console.error("usage: drive-shared-page.cjs <spec.json>");
  process.exit(2);
}
const spec = JSON.parse(fs.readFileSync(file, "utf8"));

async function drive(browser, page, query) {
  const tab = await browser.newPage({ viewport: { width: 1200, height: 800 }, colorScheme: "light" }), faults = [];
  tab.on("pageerror", (error) => faults.push(String(error)));
  await tab.goto("file://" + page);
  await until(() => tab.evaluate(() => document.querySelector("#crumbs [data-level]") && document.getElementById("search")), 5000, "the crumbs and the search bar");
  const seen = await tab.evaluate(() => {
    const box = (element) => { const rect = element.getBoundingClientRect(); return { left: rect.left, top: rect.top, right: innerWidth - rect.right, height: rect.height, width: rect.width }; };
    const search = document.getElementById("search"), crumbs = document.getElementById("crumbs");
    return { crumbs: box(crumbs), planted: [...crumbs.querySelectorAll("[data-level]")].every((one) => one.dataset.planted === "crumb"), ink: getComputedStyle(document.body).color,
      bar: box(search), last: search.parentElement.id === "tools" && search === search.parentElement.lastElementChild, title: search.title, placeholder: document.getElementById("query").placeholder };
  });
  check(seen.crumbs.left <= 24 && seen.crumbs.top <= 24, `the crumbs stand at ${Math.round(seen.crumbs.left)}, ${Math.round(seen.crumbs.top)}, not at the top left`);
  check(seen.planted, "a crumb does not carry the planted change");
  check(seen.ink === spec.ink, `the body's text is ${seen.ink}, not the planted foreground ${spec.ink}`);
  check(seen.last && seen.bar.right <= 24 && seen.bar.top <= 24, "the search bar is not the last tool at the top right");
  check(/^Search [a-z, ]+$/.test(seen.placeholder) && seen.title === seen.placeholder, `the search box says ${JSON.stringify(seen.placeholder)} and its bar ${JSON.stringify(seen.title)}`);
  await tab.mouse.click(600, 790);
  await tab.keyboard.press("/");
  await until(() => tab.evaluate(() => document.getElementById("palette").classList.contains("show") && document.activeElement.id === "query"), 2000, "`/` to open the search");
  check(query, "the page names no record to search for");
  await tab.keyboard.type(query);
  const mark = await until(() => tab.evaluate(() => { const one = document.querySelector("#hits mark"); return one && getComputedStyle(one).backgroundColor; }), 2000, `a hit's mark for ${query}`);
  check(mark === spec.mark, `a hit's mark is filled ${mark}, not the planted ${spec.mark}`);
  await tab.keyboard.press("Enter");
  const head = await until(() => tab.evaluate(() => { const card = document.getElementById("card"); return card.classList.contains("show") && card.querySelector("h2") && card.querySelector("h2").textContent; }), 3000, "the picked record's card");
  check(head.startsWith(spec.title + " "), `the card is headed ${JSON.stringify(head)}, not by the planted word ${spec.title}`);
  check(!faults.length, `the page threw ${faults[0]}`);
  await tab.close();
  return seen.bar;
}

(async () => {
  if (missing()) { console.log(`FAIL browser: ${missing()}`); process.exit(1); }
  const browser = await launch(), bars = [];
  let failed = false;
  for (const [k, page] of spec.pages.entries()) {
    const name = path.basename(page);
    try { bars.push(await drive(browser, page, spec.queries[k])); console.log(`PASS ${name}`); } catch (error) { failed = true; console.log(`FAIL ${name}: ${error.message.split("\n")[0]}`); }
  }
  await browser.close();
  const apart = bars.filter((bar) => ["top", "right", "height", "width"].some((side) => Math.abs(bar[side] - bars[0][side]) > 0.5));
  if (bars.length !== spec.pages.length || apart.length) { failed = true; console.log(`FAIL one bar: the search bar stands at ${JSON.stringify(bars)}`); } else console.log("PASS one bar");
  process.exit(failed ? 1 : 0);
})();
