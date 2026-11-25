#!/usr/bin/env node
// Drive a page in a headless Chromium as a reader would, and print `PASS <mode>` or `FAIL <mode>: <reason>`.
//   own <page.html>             the page replay-page-parts.py writes: the first box carries a ✓1 and a !1 badge; the pointer resting on it
//                               shows its card with a chip per property; a click on the gap's chip shows the gap's card headed by its title;
//                               `/` opens search, where the second node's Korean alias and its name typed on a Korean layout each list it
//                               first, and Enter shows its card
//   system <page.html> <word>   a system page: the pointer resting on its first node shows a card whose heading starts with WORD, every badge
//                               group on the page carries `data-mark` WORD, and every hit `/` lists for a query carries it too
//
// usage: drive-page-parts.cjs own <page.html>
// usage: drive-page-parts.cjs system <page.html> <word>
const path = require("path");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));

const [mode, file, word] = process.argv.slice(2);
if (!(mode === "own" && file && !word || mode === "system" && file && word) || process.argv.length > 5) {
  console.error("usage: drive-page-parts.cjs own <page.html>\nusage: drive-page-parts.cjs system <page.html> <word>");
  process.exit(2);
}
const check = (condition, reason) => { if (!condition) throw new Error(reason); };
const heading = (page) => page.waitForFunction(() => document.querySelector("#card.show h2") && document.querySelector("#card.show h2").textContent, null, { timeout: 4000 })
  .then((handle) => handle.jsonValue()).catch(() => null);

async function own(page) {
  const badges = await page.$$eval('.box[data-id="intake"] .counts > .count', (all) => all.map((one) => one.textContent));
  check(badges.join(" ") === "✓1 !1", `the first box's badges read "${badges.join(" ")}"`);
  await page.hover('.box[data-id="intake"]');
  check(await heading(page) === "Intake", "resting on the first box showed no card headed Intake");
  const chips = await page.$$eval("#card .ref", (all) => all.map((one) => one.dataset.ref));
  check(chips.includes("checked") && chips.includes("no-retry"), `the card's chips are ${JSON.stringify(chips)}`);
  await page.click('#card .ref[data-ref="no-retry"]');
  check(await page.waitForFunction(() => document.querySelector("#card.show h2").textContent === "A failed intake is never retried", null, { timeout: 4000 }).catch(() => null),
    "a click on the gap's chip did not show the gap's card");
  for (const query of ["원장", "ㅣㄷㅇㅎㄷㄱ"]) {
    await page.mouse.move(1, 1);
    await page.keyboard.press("/");
    check(await page.waitForSelector("#palette.show", { timeout: 2000 }).catch(() => null), "`/` opened no search");
    await page.fill("#query", query);
    const first = await page.waitForFunction(() => { const hit = document.querySelector('#hits .hit[aria-selected="true"]'); return hit && hit.dataset.hit; }, null, { timeout: 2000 })
      .then((handle) => handle.jsonValue()).catch(() => null);
    check(first === "ledger", `the query ${query} listed ${first} first`);
    await page.keyboard.press("Enter");
    check(await heading(page) === "Ledger", `Enter on ${query} showed no card headed Ledger`);
  }
}

async function system(page) {
  await page.waitForSelector("#stage .node", { timeout: 4000 });
  await page.hover("#stage .node");
  const shown = await heading(page);
  check(shown && shown.startsWith(word), `the card's heading reads ${JSON.stringify(shown)}`);
  const groups = await page.$$eval(".counts", (all) => all.map((one) => one.dataset.mark || ""));
  check(groups.length && groups.every((one) => one === word), `of ${groups.length} badge groups, ${groups.filter((one) => one !== word).length} are not lib's`);
  await page.mouse.move(1, 1);
  await page.keyboard.press("/");
  check(await page.waitForSelector("#palette.show", { timeout: 2000 }).catch(() => null), "`/` opened no search");
  await page.fill("#query", "a");
  const hits = await page.waitForFunction(() => { const all = [...document.querySelectorAll("#hits .hit[data-hit]")]; return all.length && all.map((one) => one.dataset.mark || ""); }, null, { timeout: 2000 })
    .then((handle) => handle.jsonValue()).catch(() => null);
  check(hits && hits.every((one) => one === word), hits ? `of ${hits.length} hits, ${hits.filter((one) => one !== word).length} are not lib's` : "the query `a` listed no hit");
}

async function main() {
  if (missing()) return missing();
  const browser = await launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("file://" + path.resolve(file));
    await (mode === "own" ? own(page) : system(page));
    check(!errors.length, `the page threw ${errors[0]}`);
    return "";
  } finally {
    await browser.close();
  }
}

main().then((reason) => {
  console.log(reason ? `FAIL ${mode}: ${reason}` : `PASS ${mode}`);
  process.exit(reason ? 1 : 0);
}, (error) => {
  console.log(`FAIL ${mode}: ${error.message.split("\n")[0]}`);
  process.exit(1);
});
