#!/usr/bin/env node
// Replay the page drawing alone: copy the page-drawing folder, and nothing else of the playbook, to a scratch folder,
// serve its scripts from a stand-in that answers each route with the status and body recorded from the real server in
// fixtures/recorded-page-payloads.json, open each case's page in a headless Chromium and print one `PASS <case>` or
// `FAIL <case>: <why>` line per duty of the drawing, then PASS or FAIL.
//
// usage: run-drawing-alone.cjs [<case>]
// Cases: the badge, thread, reply and refused Accept drawn from the recorded page; the drawing's own diagram page; an
// anchor for every heading in Korean, same-named ones included; a thread's status when a quiet note sits between a
// comment and its answer, and after it; badges that follow a view shown by the url's hash; anchors and badges on a part
// the page rebuilds after load; a selection sent with one comment only, and with none once the reader clicks it away;
// derived anchors beside a marked one; a thread whose anchor is gone, listed apart and still open to a comment, its
// name kept from a later part of the same words; no badge on a part hidden or off the page.
// Playwright is loaded from TEAMWORK_PLAYWRIGHT, else /private/tmp/teamwork-playwright/node_modules/playwright-core,
// and the browser from TEAMWORK_CHROMIUM, else the newest headless shell Playwright installed.
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

const PLAYWRIGHT = process.env.TEAMWORK_PLAYWRIGHT || "/private/tmp/teamwork-playwright/node_modules/playwright-core";
const DRAWING = path.join(__dirname, "..", "page-drawing");
const RECORDED = path.join(__dirname, "..", "fixtures", "recorded-page-payloads.json");

function browserBinary() {
  if (process.env.TEAMWORK_CHROMIUM) return process.env.TEAMWORK_CHROMIUM;
  const cache = path.join(process.env.HOME, "Library/Caches/ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  return shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64/chrome-headless-shell") : path.join(cache, "chromium_headless_shell-*");
}

const BLOCK = /(<script type="application\/json" id="page-threads">)([\s\S]*?)(<\/script>)/;
const html = (body, threads = {}, head = "") => `<!doctype html><html><head><meta charset="utf-8">${head}</head><body>${body}
<script type="application/json" id="page-threads">${JSON.stringify({ threads })}</script>
</body></html>
`;
const stamp = (date) => new Date(date - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19);

// The connection's part, played from the recording: the page with its reply times and the drawing's scripts, a version
// that changes with the page, and each post answered as the real server answered it.
function standIn(page, scripts, recorded) {
  const answer = (route) => recorded.find((each) => each.method === "POST" && each.route === route && each.status < 400);
  const refusal = (route) => recorded.find((each) => each.method === "POST" && each.route === route && each.status >= 400);
  const state = { page, version: 1, posts: [], stamps: {}, comments: 0 };
  const server = http.createServer((request, response) => {
    const [, token, ...rest] = request.url.split("?")[0].split("/");
    const route = rest.join("/");
    const reply = (status, body, kind = "text/plain") => { response.writeHead(status, { "Content-Type": kind, "Cache-Control": "no-store" }); response.end(body); };
    if (token !== "stand-in") return reply(404, "");
    if (request.method === "GET" && route === "") {
      const times = state.page.includes("window.pageThreadsStamps") ? "" : `<script>window.pageThreadsStamps = ${JSON.stringify(state.stamps)};</script>`;
      const at = state.page.toLowerCase().lastIndexOf("</body>");
      return reply(200, state.page.slice(0, at) + times + scripts + state.page.slice(at), "text/html; charset=utf-8");
    }
    if (request.method === "GET" && route === "version") return reply(200, String(state.version));
    if (request.method !== "POST") return reply(404, "");
    let sent = "";
    request.on("data", (chunk) => { sent += chunk; });
    request.on("end", () => {
      const body = JSON.parse(sent);
      state.posts.push({ route, body });
      const given = route === "decide" && body.verdict === "accept" ? refusal(route) : answer(route);
      if (!given) return reply(404, "");
      if (route !== "comment") return reply(given.status, given.body);
      state.comments += 1;
      reply(given.status, String(Number(given.body) + state.comments - 1));
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({
    state, url: `http://127.0.0.1:${server.address().port}/stand-in/`, close: () => server.close(),
    write(change) {
      const match = state.page.match(BLOCK);
      const block = JSON.parse(match[2]);
      change(block.threads);
      for (const entry of Object.values(block.threads).flat()) if (entry.by === "sentinel" && !state.stamps[entry.id]) state.stamps[entry.id] = stamp(Date.now());
      state.page = state.page.replace(match[0], match[1] + JSON.stringify(block) + match[3]);
      state.version += 1;
    },
  })));
}

const anchors = (tab) => tab.evaluate(() => [...document.querySelectorAll("[data-thread-anchor]")].map((each) => each.dataset.threadAnchor));
const badges = (tab) => tab.evaluate(() => [...document.querySelectorAll("#page-threads-layer button")].map((each) => each.dataset.anchor));
const shows = async (tab, want) => {
  await tab.waitForFunction((status) => document.querySelector("#page-threads-panel .state")?.dataset.status === status, want, { timeout: 8000 }).catch(() => null);
  return tab.getAttribute("#page-threads-panel .state", "data-status");
};
const comments = (server) => server.state.posts.filter((each) => each.route === "comment").map((each) => each.body);
const send = async (tab, text) => {
  await tab.fill("#page-threads-panel textarea", text);
  await tab.evaluate(() => { document.querySelector("#page-threads-panel .sent").textContent = ""; });
  await tab.click("#page-threads-panel form button[type=submit]");
  await tab.waitForFunction(() => document.querySelector("#page-threads-panel .sent")?.textContent, null, { timeout: 5000 });
  return tab.textContent("#page-threads-panel .sent");
};

const CASES = {
  "recorded-thread": {
    page: (recorded) => recorded.find((each) => each.method === "GET" && each.route === "").body,
    async run(tab, server, recorded) {
      const drawn = await tab.evaluate(() => [...document.querySelectorAll("#page-threads-layer button")].map((each) => `${each.dataset.anchor} ${each.textContent}`));
      if (JSON.stringify(drawn) !== '["intro 💬 2"]') return `the recorded page drew badges ${JSON.stringify(drawn)}`;
      await tab.click("#page-threads-layer button");
      const thread = await tab.evaluate(() => [...document.querySelectorAll("#page-threads-panel li")].map((each) => `${each.dataset.by}:${each.querySelector(".text").textContent}`));
      const nested = await tab.evaluate(() => Boolean(document.querySelector('#page-threads-panel li[data-message="1"] ol li[data-message="1.1"]')));
      const time = await tab.textContent('#page-threads-panel li[data-message="1.1"] > .meta');
      if (JSON.stringify(thread) !== '["owner:propose a new intro","sentinel:A new intro"]' || !nested) return `the thread drew ${JSON.stringify(thread)}, the reply under its comment: ${nested}`;
      if (time.trim() !== "00:00") return `the reply shows "${time}", not the time the server recorded for it`;
      await tab.click('#page-threads-panel li[data-message="1.1"] .proposal button[data-verdict="accept"]');
      const refused = recorded.find((each) => each.route === "decide").body;
      await tab.waitForFunction(() => document.querySelector("#page-threads-panel .proposal .meta")?.textContent, null, { timeout: 5000 }).catch(() => null);
      const said = await tab.textContent("#page-threads-panel .proposal .meta");
      if (!refused || said !== refused) return `a refused Accept said "${said}", not the server's reason "${refused}"`;
      await tab.click("#page-threads-panel .undo");
      await tab.waitForFunction(() => document.querySelector("#page-threads-panel .sent")?.textContent, null, { timeout: 5000 }).catch(() => null);
      const undone = await tab.textContent("#page-threads-panel .sent");
      const sent = await send(tab, "a comment on the recorded page");
      const posted = comments(server);
      if (undone !== "undo sent" || sent !== "sent" || posted.length !== 1 || posted[0].anchor !== "intro" || posted[0].author !== "owner")
        return `Undo said "${undone}", a comment "${sent}", and the stand-in got ${JSON.stringify(posted)}`;
    },
  },
  "diagram-page": {
    page: (recorded, drawing) => drawing.page,
    async run(tab) {
      const found = await badges(tab);
      const node = await tab.evaluate(() => Object.keys(JSON.parse(document.getElementById("page-threads").textContent).threads)[0]);
      const nodes = await tab.evaluate(() => document.querySelectorAll("svg [data-thread-anchor]").length);
      if (!node || nodes < 2 || found.length < nodes || !found.includes(node)) return `the diagram page drew badges ${JSON.stringify(found)} for ${nodes} nodes`;
      await tab.click(`svg [data-thread-anchor="${node}"]`);
      const open = await tab.evaluate(() => [document.querySelector("#page-threads-panel")?.hidden, document.querySelectorAll("#page-threads-panel li li").length]);
      if (open[0] !== false || open[1] < 1) return `a click on node ${node} opened its thread: ${open[0] === false}, with ${open[1]} replies under a comment`;
    },
  },
  "korean-headings": {
    page: () => html("<h1>설치 방법</h1><p>a</p><h2>사용법</h2><p>b</p><h2>사용법</h2><p>c</p><h2>Résumé 요약</h2><p>d</p><h3>★</h3>"),
    async run(tab, server) {
      const found = await anchors(tab);
      const want = ["h-설치-방법", "h-사용법", "h-사용법-2", "h-résumé-요약", "h"];
      if (JSON.stringify(found) !== JSON.stringify(want)) return `5 headings gave anchors ${JSON.stringify(found)}`;
      if ((await badges(tab)).length !== 5) return `5 headings gave ${(await badges(tab)).length} badges`;
      await tab.evaluate(() => window.pageThreads.open("h-사용법-2"));
      const sent = await send(tab, "두 번째 사용법");
      const posted = comments(server).map((each) => each.anchor);
      if (sent !== "sent" || JSON.stringify(posted) !== '["h-사용법-2"]') return `a comment on the second same-named heading was ${sent} and posted to ${JSON.stringify(posted)}`;
    },
  },
  "status-order": {
    page: () => html('<h1 id="intro">Intro</h1>', { intro: [{ id: 1, by: "owner", text: "please rename", replies_to: null, at: stamp(Date.now() - 20000) },
      { id: 2, by: "guest", text: "a note", replies_to: null, at: stamp(Date.now() - 10000), quiet: true }] }),
    async run(tab, server) {
      await tab.evaluate(() => window.pageThreads.open("intro"));
      const waiting = await shows(tab, "waiting");
      const marked = await tab.textContent('#page-threads-panel li[data-message="2"] > .meta');
      server.write((threads) => threads.intro.push({ id: "1.1", by: "sentinel", text: "renamed", replies_to: 1 }));
      const answered = await shows(tab, "answered");
      await tab.waitForTimeout(1100);
      server.write((threads) => threads.intro.push({ id: 3, by: "guest", text: "a later note", replies_to: null, at: stamp(Date.now()), quiet: true }));
      const noted = await shows(tab, "quiet");
      server.write((threads) => threads.intro.push({ id: 4, by: "owner", text: "one more", replies_to: null, at: stamp(Date.now()) }));
      const again = await shows(tab, "waiting");
      const seen = [waiting, answered, noted, again].join(", ");
      if (seen !== "waiting, answered, quiet, waiting") return `a comment, a quiet note, the answer, a later quiet note and a new comment showed ${seen}`;
      if (!/noted/.test(marked || "")) return `the quiet note's own line says "${marked}"`;
    },
  },
  "hash-views": {
    page: () => html('<style>section { display: none } section:target { display: block }</style><nav><a href="#one">one</a> <a href="#two">two</a></nav>' +
      '<section id="one"><h2>One</h2><p>first view</p></section><section id="two"><h2>Two</h2><p>second view</p><p>more</p></section>'),
    async run(tab, server) {
      await tab.goto(server.url + "#one");
      await tab.waitForFunction(() => document.querySelectorAll("#page-threads-layer button").length === 1, null, { timeout: 5000 }).catch(() => null);
      const first = await badges(tab);
      await tab.evaluate(() => { location.hash = "#two"; });
      await tab.waitForFunction(() => document.querySelector("#page-threads-layer button")?.dataset.anchor === "two", null, { timeout: 5000 }).catch(() => null);
      const second = await badges(tab);
      const near = await tab.evaluate(() => {
        const box = document.getElementById("two").getBoundingClientRect();
        const badge = document.querySelector("#page-threads-layer button").getBoundingClientRect();
        return Math.abs(badge.top - box.top) < 30 && Math.abs(badge.left - box.right) < 30;
      }).catch(() => false);
      if (JSON.stringify([first, second]) !== '[["one"],["two"]]' || !near) return `view one drew ${JSON.stringify(first)}, view two ${JSON.stringify(second)}, the badge on its part ${near}`;
    },
  },
  "rebuilt-part": {
    page: () => html('<h1 id="top">Top</h1><main id="app"><h2>Old part</h2></main><script>setTimeout(() => { document.getElementById("app").innerHTML = "<h2>New part</h2><h2>Second new part</h2>"; }, 1500);</script>'),
    async run(tab) {
      await tab.waitForFunction(() => document.querySelectorAll("#page-threads-layer button").length === 3, null, { timeout: 8000 }).catch(() => null);
      const found = await badges(tab);
      if (JSON.stringify(found) !== '["top","h-new-part","h-second-new-part"]') return `after the page rebuilt a part the badges were ${JSON.stringify(found)}`;
    },
  },
  "selection-once": {
    page: () => html('<h1 id="intro">Intro words here</h1>'),
    async run(tab, server) {
      await tab.evaluate(() => {
        const range = document.createRange();
        range.selectNodeContents(document.querySelector("h1"));
        getSelection().removeAllRanges();
        getSelection().addRange(range);
        document.dispatchEvent(new MouseEvent("mouseup"));
        window.pageThreads.open("intro");
      });
      for (const text of ["about the selection", "about nothing selected"]) {
        await tab.waitForSelector("#page-threads-panel textarea");
        await tab.evaluate(() => getSelection().removeAllRanges());
        await tab.fill("#page-threads-panel textarea", text);
        await tab.click("#page-threads-panel form button[type=submit]");
        await tab.waitForFunction((sent) => [...document.querySelectorAll("#page-threads-panel li .text")].some((each) => each.textContent === sent), text, { timeout: 5000 });
      }
      const sent = comments(server).map((each) => each.selection);
      if (JSON.stringify(sent) !== '["Intro words here",null]') return `the two comments carried selections ${JSON.stringify(sent)}`;
    },
  },
  "marked-and-derived": {
    page: () => html('<h1>Guide</h1><h2 data-thread-anchor="h-setup">Install steps</h2><section id="use"><h2>Use</h2></section><h2>Notes</h2>',
      { "h-setup": [{ id: 1, by: "owner", text: "shorter", replies_to: null, at: stamp(Date.now()) }] }),
    async run(tab) {
      const found = await badges(tab);
      if (JSON.stringify(found) !== '["h-guide","h-setup","use","h-notes"]') return `a page with one marked heading drew badges ${JSON.stringify(found)}`;
    },
  },
  "lost-thread": {
    page: () => html("<h1>Guide</h1><h2>Install steps</h2>", { "h-setup": [{ id: 1, by: "owner", text: "shorter", replies_to: null, at: stamp(Date.now()) }] },
      "<script>window.built = true;</script>"),
    async run(tab, server) {
      const listed = await tab.evaluate(() => [document.getElementById("page-threads-gone").hidden, ...[...document.querySelectorAll("#page-threads-gone button")].map((each) => each.dataset.anchor)]);
      await tab.evaluate(() => { document.getElementById("page-threads-gone").open = true; });
      await tab.click("#page-threads-gone button");
      const shown = await tab.evaluate(() => [document.querySelector("#page-threads-panel .title")?.textContent, document.querySelectorAll("#page-threads-panel li .text").length]);
      await send(tab, "still here");
      const posted = comments(server).map((each) => each.anchor);
      if (JSON.stringify(listed) !== '[false,"h-setup"]' || !/h-setup.*no longer/.test(shown[0] || "") || shown[1] !== 1 || JSON.stringify(posted) !== '["h-setup"]')
        return `a thread under a heading since renamed was listed as ${JSON.stringify(listed)}, opened as ${JSON.stringify(shown)} and its comment posted to ${JSON.stringify(posted)}`;
    },
  },
  "removed-part": {
    page: () => html('<h1>Guide</h1><span hidden data-thread-gone data-thread-anchor="h-old-part"></span><h2>Old part</h2>',
      { "h-old-part": [{ id: 1, by: "owner", text: "remove this part", replies_to: null, at: stamp(Date.now()) }] }),
    async run(tab) {
      const listed = await tab.evaluate(() => [...document.querySelectorAll("#page-threads-gone button")].map((each) => each.dataset.anchor));
      const found = await badges(tab);
      await tab.evaluate(() => window.pageThreads.open("h-old-part"));
      const title = await tab.textContent("#page-threads-panel .title").catch(() => null);
      if (JSON.stringify([listed, found]) !== '[["h-old-part"],["h-guide","h-old-part-2"]]' || !/no longer/.test(title || ""))
        return `a removed part's thread was listed as ${JSON.stringify(listed)} beside badges ${JSON.stringify(found)} and opened as "${title}"`;
    },
  },
  "hidden-parts": {
    page: () => html('<h1 id="top">Top</h1><h2 id="unseen" style="visibility: hidden">Unseen</h2><h2 id="away" style="position: absolute; left: -9999px">Away</h2><h2 id="late" style="visibility: hidden">Late</h2>' +
      '<script>setTimeout(() => { document.getElementById("late").style.visibility = "visible"; }, 1500);</script>'),
    async run(tab) {
      const first = await badges(tab);
      await tab.waitForFunction(() => document.querySelectorAll("#page-threads-layer button").length === 2, null, { timeout: 8000 }).catch(() => null);
      const later = await badges(tab);
      if (JSON.stringify([first, later]) !== '[["top"],["top","late"]]') return `parts hidden or off the page drew badges ${JSON.stringify(first)}, then ${JSON.stringify(later)} once one was shown`;
    },
  },
  "selection-dropped": {
    page: () => html('<h1 id="intro">Intro words here</h1><p id="rest">Other text</p>'),
    async run(tab, server) {
      await tab.evaluate(() => {
        const range = document.createRange();
        range.selectNodeContents(document.querySelector("h1"));
        getSelection().removeAllRanges();
        getSelection().addRange(range);
        document.querySelector("h1").dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
      });
      await tab.click("#rest");
      await tab.evaluate(() => window.pageThreads.open("intro"));
      await send(tab, "after letting the selection go");
      const sent = comments(server).map((each) => each.selection);
      if (JSON.stringify(sent) !== "[null]") return `a comment sent after the reader clicked the selection away carried ${JSON.stringify(sent)}`;
    },
  },
};

async function main(args) {
  if (args.length > 1 || (args.length && !CASES[args[0]])) { console.error("usage: run-drawing-alone.cjs [<case>]"); return 2; }
  for (const needed of [PLAYWRIGHT, browserBinary(), RECORDED]) {
    if (!fs.existsSync(needed)) { console.log(`FAIL: nothing at ${needed}`); return 1; }
  }
  const recorded = JSON.parse(fs.readFileSync(RECORDED, "utf8"));
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "page-drawing-alone-"));
  fs.cpSync(DRAWING, scratch, { recursive: true });
  const names = fs.readdirSync(scratch).sort();
  const scripts = names.filter((name) => name.endsWith(".js")).map((name) => `<script>${fs.readFileSync(path.join(scratch, name), "utf8")}</script>`).join("");
  const pages = names.filter((name) => name.endsWith(".html"));
  if (!scripts || pages.length !== 1) { console.log(`FAIL: the drawing folder holds ${pages.length} pages and ${scripts ? "its" : "no"} scripts`); return 1; }
  const drawing = { page: fs.readFileSync(path.join(scratch, pages[0]), "utf8") };
  const chosen = Object.entries(CASES).filter(([name]) => !args.length || name === args[0]);
  const { chromium } = require(PLAYWRIGHT);
  const browser = await chromium.launch({ executablePath: browserBinary() });
  let failed = 0;
  try {
    for (const [name, each] of chosen) {
      const server = await standIn(each.page(recorded, drawing), scripts, recorded);
      const tab = await browser.newPage({ viewport: { width: 1280, height: 800 } });
      let why;
      try {
        await tab.goto(server.url);
        why = await each.run(tab, server, recorded);
      } catch (error) {
        why = `error: ${error.message.split("\n")[0]}`;
      }
      await tab.close();
      server.close();
      failed += why ? 1 : 0;
      console.log(why ? `FAIL ${name}: ${why}` : `PASS ${name}`);
    }
  } finally {
    await browser.close();
    fs.rmSync(scratch, { recursive: true, force: true });
  }
  console.log(failed ? `FAIL: ${failed} of ${chosen.length} cases` : "PASS");
  return failed ? 1 : 0;
}

main(process.argv.slice(2)).then((code) => process.exit(code), (error) => { console.log(`FAIL: ${error.message}`); process.exit(1); });
