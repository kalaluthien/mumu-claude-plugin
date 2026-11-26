#!/usr/bin/env node
// Open one built page in a headless Chromium, as file://, and print the text it shows in each view.
//
// usage: list-page-texts.cjs PAGE.html
// It prints one JSON line per view, {"view", "text", "shown"}: each level, each node, edge and area with its
// overlay, each step of each scenario, each claim with its overlay, and the lists the Scenarios and
// Properties buttons open. `text` is the text the window draws and `shown` says whether the view's overlay or
// list came. It exits 1 with a `setup:` line when Playwright or its browser is missing, and 2 on another call.
// The browser is the one ../../../lib/launch-browser.cjs starts.
const path = require("path");

const browsers = require(path.join(__dirname, "..", "..", "..", "lib", "launch-browser.cjs"));
const asked = process.argv.slice(2);
if (asked.length !== 1 || asked[0].startsWith("-")) {
  console.error("usage: list-page-texts.cjs PAGE.html");
  process.exit(2);
}

async function main() {
  const built = "file://" + path.resolve(asked[0]);
  if (browsers.missing()) {
    console.log(`setup: ${browsers.missing()}`);
    return 1;
  }
  const browser = await browsers.launch().catch((error) => { console.log(`setup: ${error.message}`); return null; });
  if (!browser) return 1;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
    await page.clock.install(); // the page's timers run on a clock turned forward below, so a view is read where it comes to rest
    const rest = async () => {
      await page.evaluate(() => document.getAnimations().forEach((move) => { try { move.finish(); } catch (error) { /* one that never ends has no end to reach */ } }));
      await page.clock.fastForward(1000);
    };
    await page.goto(built);
    const contract = JSON.parse(await page.evaluate(() => document.getElementById("page-data").textContent));
    const views = [];
    for (const level of contract.levels) {
      views.push({ view: `level ${level.id}`, address: `#level=${level.id}` });
      for (const kind of ["areas", "nodes", "edges"]) for (const record of level[kind] || []) views.push({ view: `${kind} ${record.id}`, address: `#level=${level.id}&at=${record.id}`, card: record.id });
    }
    for (const scenario of contract.scenarios || []) scenario.steps.forEach((step, k) => views.push({ view: `scenario ${scenario.id} step ${k + 1}`, address: `#scenario=${scenario.id}&step=${k}`, step: k, note: !!step.note }));
    for (const claim of contract.claims || []) views.push({ view: `claim ${claim.id}`, address: `#at=${claim.id}`, card: claim.id });
    for (const button of ["scenarios", "claims"]) views.push({ view: `list of ${button}`, address: "", button });
    for (const one of views) {
      await page.goto("about:blank");
      await page.goto(built + one.address);
      await rest();
      if (one.button) {
        await page.click("#" + one.button);
        await rest();
      }
      const shown = await page.evaluate((view) => {
        if (document.body.dataset.busy !== "") return false;
        const card = document.getElementById("card");
        if (view.card) return card.classList.contains("show") && card.dataset.for === view.card;
        if (view.button) return document.querySelectorAll("#hits [data-hit]").length > 0;
        if ("step" in view) return +document.body.dataset.step === view.step && (!view.note || document.getElementById("chip").textContent.length > 0); // a step without a note shows no chip
        return true;
      }, one);
      console.log(JSON.stringify({ view: one.view, text: await page.evaluate(() => document.body.innerText), shown }));
    }
  } finally {
    await browser.close();
  }
  return 0;
}

main().then((code) => process.exit(code), (error) => { console.log(`setup: ${error.message.split("\n")[0]}`); process.exit(1); });
