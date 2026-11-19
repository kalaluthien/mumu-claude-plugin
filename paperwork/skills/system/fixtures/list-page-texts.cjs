#!/usr/bin/env node
// Open one built page in a headless Chromium, as file://, and print the text it shows in each view.
//
// usage: list-page-texts.cjs PAGE.html
// It prints one JSON line per view, {"view", "text", "shown"}: each level, each node, edge and area with its
// overlay, each step of each scenario, each property with its overlay, and the lists the Scenarios and
// Properties buttons open. `text` is the text the window draws and `shown` says whether the view's overlay or
// list came. It exits 1 with a `setup:` line when Playwright or its browser is missing, and 2 on another call.
// Playwright is loaded from /private/tmp/relay-playwright/node_modules/playwright-core and the browser is the
// newest headless shell Playwright installed, never an installed Google Chrome.
const fs = require("fs");
const os = require("os");
const path = require("path");

const PLAYWRIGHT = "/private/tmp/relay-playwright/node_modules/playwright-core";
const asked = process.argv.slice(2);
if (asked.length !== 1 || asked[0].startsWith("-")) {
  console.error("usage: list-page-texts.cjs PAGE.html");
  process.exit(2);
}

function browserBinary() {
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  return shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64/chrome-headless-shell") : null;
}

async function main() {
  const binary = browserBinary(), built = "file://" + path.resolve(asked[0]);
  if (!fs.existsSync(path.join(PLAYWRIGHT, "package.json")) || !binary || !fs.existsSync(binary)) {
    console.log("setup: install playwright-core into /private/tmp/relay-playwright and its chromium-headless-shell");
    return 1;
  }
  const browser = await require(PLAYWRIGHT).chromium.launch({ executablePath: binary });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
    await page.goto(built);
    const contract = JSON.parse(await page.evaluate(() => document.getElementById("page-data").textContent));
    const views = [];
    for (const level of contract.levels) {
      views.push({ view: `level ${level.id}`, address: `#level=${level.id}` });
      for (const kind of ["areas", "nodes", "edges"]) for (const record of level[kind] || []) views.push({ view: `${kind} ${record.id}`, address: `#level=${level.id}&at=${record.id}`, card: record.id });
    }
    for (const scenario of contract.scenarios || []) scenario.steps.forEach((step, k) => views.push({ view: `scenario ${scenario.id} step ${k + 1}`, address: `#scenario=${scenario.id}&step=${k}`, step: k, note: !!step.note }));
    for (const property of contract.properties || []) views.push({ view: `property ${property.id}`, address: `#at=${property.id}`, card: property.id });
    for (const button of ["scenarios", "properties"]) views.push({ view: `list of ${button}`, address: "", button });
    for (const one of views) {
      await page.goto("about:blank");
      await page.goto(built + one.address);
      await page.waitForFunction(() => document.body.dataset.busy === "", null, { timeout: 5000 });
      if (one.button) await page.click("#" + one.button);
      const shown = await page.waitForFunction((view) => {
        const card = document.getElementById("card");
        if (view.card) return card.classList.contains("show") && card.dataset.for === view.card;
        if (view.button) return document.querySelectorAll("#hits [data-hit]").length > 0;
        if ("step" in view) return +document.body.dataset.step === view.step && (!view.note || document.getElementById("chip").textContent.length > 0); // a step without a note shows no chip
        return true;
      }, one, { timeout: 3000 }).then(() => true, () => false);
      console.log(JSON.stringify({ view: one.view, text: await page.evaluate(() => document.body.innerText), shown }));
    }
  } finally {
    await browser.close();
  }
  return 0;
}

main().then((code) => process.exit(code), (error) => { console.log(`setup: ${error.message.split("\n")[0]}`); process.exit(1); });
