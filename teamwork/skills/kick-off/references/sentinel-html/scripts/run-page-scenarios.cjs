#!/usr/bin/env node
// Start one sentinel by the manager playbook's start words on a copy of the page drawing's diagram page under
// /private/tmp, open the page it serves in a headless Chromium, run each scenario against it, and print one PASS or
// FAIL line per scenario, then a `contract` line saying whether the server found the page file breaking the contract,
// then PASS when all passed. The sentinel is closed and its server stopped on every way out.
//
// usage: run-page-scenarios.cjs [--timeout <seconds>] [--manager <session>] [--all | <scenario>...]
// usage: run-page-scenarios.cjs --list
// With no scenario named it runs thread, undo and outside; --all runs every scenario --list prints. --timeout bounds
// the whole run, the close included (default 280). --manager names the live manager the sentinel is started under,
// else the first one the session list shows. The start words are read from references/manager.md of the checkout this
// script is in, and the sentinel is started by that checkout's start-session.py, so it reads that checkout's playbooks.
// Playwright is loaded from TEAMWORK_PLAYWRIGHT, else /private/tmp/teamwork-playwright/node_modules/playwright-core,
// and the browser from TEAMWORK_CHROMIUM, else the newest headless shell Playwright installed.
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const PLAYWRIGHT = process.env.TEAMWORK_PLAYWRIGHT || "/private/tmp/teamwork-playwright/node_modules/playwright-core";
const KICK_OFF = path.join(__dirname, "..", "..", "..");
const CHECKOUT = path.join(KICK_OFF, "..", "..", "..");
const DRAWING = path.join(__dirname, "..", "page-drawing");
const USAGE = "usage: run-page-scenarios.cjs [--timeout <seconds>] [--manager <session>] [--all | <scenario>...]\nusage: run-page-scenarios.cjs --list";

function browserBinary() {
  if (process.env.TEAMWORK_CHROMIUM) return process.env.TEAMWORK_CHROMIUM;
  const cache = path.join(os.homedir(), "Library", "Caches", "ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  return shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64", "chrome-headless-shell") : path.join(cache, "chromium_headless_shell-*");
}

const nonce = () => crypto.randomBytes(3).toString("hex");

function make(page, url, left) {
  const read = () => page.evaluate(() => {
    const parse = (id) => { try { return JSON.parse(document.getElementById(id).textContent); } catch (e) { return null; } };
    const labels = {};
    document.querySelectorAll("[data-thread-anchor]").forEach((each) => { labels[each.dataset.threadAnchor] = each.getAttribute("aria-label"); });
    const edges = [...document.querySelectorAll("line[data-edge]")].map((line) => line.dataset.edge);
    return { bridge: parse("page-threads"), diagram: parse("diagram"), labels, edges };
  }).catch(() => null);
  const until = async (test, seconds = Infinity) => {
    const deadline = Date.now() + Math.min(seconds, left()) * 1000;
    let seen = null;
    while (Date.now() < deadline) {
      seen = await read();
      if (seen && seen.bridge && await test(seen)) return seen;
      await page.waitForTimeout(500);
    }
    return null;
  };
  const thread = (seen, anchor) => (seen.bridge.threads || {})[anchor] || [];
  const replyTo = (seen, anchor, id) => thread(seen, anchor).find((entry) => entry.by === "sentinel" && entry.replies_to === id && !entry.working);
  const openThread = async (anchor) => {
    await page.evaluate((a) => window.pageThreads.open(a), anchor);
    await page.waitForSelector("#page-threads-panel textarea");
  };
  const say = async (anchor, text) => {
    await openThread(anchor);
    await page.fill("#page-threads-panel textarea", text);
    await page.click("#page-threads-panel form button[type=submit]");
    const seen = await until((s) => thread(s, anchor).some((entry) => entry.text === text), 15);
    if (!seen) throw new Error(`the comment on ${anchor} was never stored`);
    return thread(seen, anchor).find((entry) => entry.text === text).id;
  };
  const postAs = async (body, headers = {}) => {
    const response = await fetch(url + "comment", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
    return response.status;
  };
  return { read, until, thread, replyTo, openThread, say, postAs };
}

const PATTERNS = {
  async thread({ page, tools }) {
    const tag = nonce();
    const text = `Rename this node to "Plan ${tag}", add a node with id "check-${tag}" and label "Check ${tag}" linked from this node, and reply with a message containing answer-${tag}.`;
    const id = await tools.say("plan", text);
    const shown = await page.textContent("#page-threads-panel .state");
    const seen = await tools.until((s) => s.labels.plan === `Plan ${tag}` && s.labels[`check-${tag}`] === `Check ${tag}` &&
      s.edges.includes(`plan->check-${tag}`) && (tools.replyTo(s, "plan", id)?.text || "").includes(`answer-${tag}`) &&
      tools.thread(s, "idea").some((entry) => entry.text === "Seed comment kept across edits"));
    if (!seen) return `no full answer to comment ${id}`;
    await page.waitForFunction(() => window.pageThreads && document.querySelector("#page-threads-layer button"), null, { timeout: 10000 }).catch(() => null);
    const badge = await page.evaluate(() => document.querySelector('#page-threads-layer button[data-anchor="plan"]')?.textContent || null);
    await tools.openThread("plan");
    const drawn = await page.evaluate((comment) => [...document.querySelectorAll(`#page-threads-panel li[data-message="${comment}"] ol li[data-by="sentinel"] > .text`)].map((each) => each.textContent), String(id));
    if (!badge) return "the drawing showed no badge on the node";
    if (!drawn.some((text) => text.includes(`answer-${tag}`))) return `the answer was not drawn under comment ${id} in the node's thread`;
    return `renamed, linked, replied under comment ${id}, seed thread kept, the node's badge "${badge}" and the answer drawn under the comment; the panel said "${shown}" while waiting`;
  },
  async status({ page, tools, folder }) {
    const tag = nonce();
    const anchor = `status-${tag}`;
    const file = path.join(folder, "page.html");
    const html = fs.readFileSync(file, "utf8");
    const added = html.replace(/("nodes"\s*:\s*\[)/, `$1{"id": "${anchor}", "label": "Status ${tag}"}, `);
    if (added === html) return "could not add a node to the diagram block";
    fs.writeFileSync(file, added);
    if (!await tools.until((s) => s.labels[anchor], 15)) return "the added node never showed";
    const record = () => setInterval(() => {
      const seen = JSON.parse(sessionStorage.getItem("status-seen") || "[]");
      const now = document.querySelector("#page-threads-panel .state")?.dataset.status;
      if (now && seen[seen.length - 1] !== now) sessionStorage.setItem("status-seen", JSON.stringify([...seen, now]));
    }, 20);
    await page.addInitScript(record);
    await page.evaluate(record);
    await tools.openThread(anchor);
    await page.fill("#page-threads-panel textarea", `Reply with ok-${tag}; change nothing else.`);
    const prior = await page.getAttribute("#page-threads-panel .state", "data-status");
    await page.evaluate(() => sessionStorage.setItem("status-seen", "[]"));
    await page.click("#page-threads-panel form button[type=submit]");
    await page.waitForFunction((before) => JSON.parse(sessionStorage.getItem("status-seen") || "[]").some((each) => each !== before), prior, { timeout: 5000 }).catch(() => null);
    const first = (await page.evaluate(() => JSON.parse(sessionStorage.getItem("status-seen") || "[]"))).filter((each) => each !== prior);
    const seen = await tools.until((s) => tools.thread(s, anchor).some((entry) => entry.by === "sentinel" && !entry.working && (entry.text || "").includes(`ok-${tag}`)));
    if (!seen) return "never answered";
    await page.waitForFunction(() => document.querySelector("#page-threads-panel .state")?.dataset.status === "answered", null, { timeout: 10000 });
    const reply = tools.thread(seen, anchor).find((entry) => entry.by === "sentinel" && (entry.text || "").includes(`ok-${tag}`));
    const shownAt = await page.textContent(`#page-threads-panel li[data-message="${reply.id}"] > .meta`);
    const clock = (date) => date.toTimeString().slice(0, 5);
    const near = [clock(new Date(Date.now() - 60000)), clock(new Date()), clock(new Date(Date.now() - 120000))];
    const write = (change) => {
      const now = fs.readFileSync(file, "utf8");
      const match = now.match(/(<script[^>]*id="page-threads"[^>]*>)([\s\S]*?)(<\/script>)/);
      const state = JSON.parse(match[2]);
      change(state.threads[anchor] = state.threads[anchor] || []);
      fs.writeFileSync(file, now.replace(match[0], match[1] + JSON.stringify(state).replace(/</g, "\\u003c") + match[3]));
    };
    const old = new Date(Date.now() - 300000).toISOString().slice(0, 19);
    const shows = async (want) => (await tools.until(async () => (await page.getAttribute("#page-threads-panel .state", "data-status")) === want, 15)) &&
      page.textContent("#page-threads-panel .state");
    write((thread) => thread.push({ id: `w-${tag}`, by: "owner", text: `working check ${tag}`, replies_to: null, at: old }, { id: `w-${tag}.1`, by: "sentinel", text: "on it", replies_to: `w-${tag}`, working: true }));
    const working = await shows("working");
    write((thread) => thread.push({ id: `s-${tag}`, by: "owner", text: `stalled check ${tag}`, replies_to: null, at: old }));
    const stalled = await shows("waiting");
    await page.focus("#page-threads-panel textarea");
    await page.keyboard.type("typed");
    await page.waitForTimeout(6000);
    await page.keyboard.type(" more");
    const typing = await page.evaluate(() => [document.activeElement?.tagName, document.querySelector("#page-threads-panel textarea").value]);
    await page.fill("#page-threads-panel textarea", "");
    const local = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19);
    write((thread) => thread.push({ id: `n-${tag}`, by: "guest", text: `guest note ${tag} while waiting`, replies_to: null, at: local(), quiet: true }));
    await page.waitForFunction((id) => document.querySelector(`#page-threads-panel li[data-message="${id}"]`), `n-${tag}`, { timeout: 15000 }).catch(() => null);
    const between = await page.getAttribute("#page-threads-panel .state", "data-status");
    write((thread) => thread.push({ id: `s-${tag}.1`, by: "sentinel", text: "closed", replies_to: `s-${tag}` }, { id: `w-${tag}.2`, by: "sentinel", text: "closed", replies_to: `w-${tag}` }));
    const closed = await shows("answered");
    await page.waitForTimeout(1100);
    write((thread) => thread.push({ id: `g-${tag}`, by: "guest", text: `guest note ${tag}`, replies_to: null, at: local(), quiet: true }));
    const quiet = await shows("quiet");
    const gaps = [];
    if (between !== "waiting") gaps.push(`a quiet note under a waiting comment showed ${between}`);
    if (!closed) gaps.push("an answer that came after a quiet note never showed Answered");
    if (first[0] !== "waiting") gaps.push(`the first state after sending was ${first[0] || "none"}`);
    if (!near.includes((shownAt || "").trim())) gaps.push(`the reply shows ${shownAt}, not the server's time`);
    if (!working || !working.includes("working")) gaps.push(`a working entry showed ${working}`);
    if (!stalled || !stalled.includes("may be stopped")) gaps.push(`a stalled comment showed ${stalled}`);
    if (typing[0] !== "TEXTAREA" || typing[1] !== "typed more") gaps.push(`typing across a redraw left focus on ${typing[0]} and "${typing[1]}"`);
    if (!quiet || !quiet.includes("@sentinel")) gaps.push(`a quiet guest note after the answers showed ${quiet}`);
    return gaps.length ? gaps.join("; ") : `waiting at once, answered at ${shownAt.trim()} by the server's clock, working and possibly stopped shown, typing kept across a redraw, a quiet note between a comment and its answer left waiting then answered, a newer quiet guest note shown as noted`;
  },
  async draft({ page, tools, url }) {
    const tag = nonce();
    await page.addInitScript(() => { history.scrollRestoration = "manual"; });
    await page.evaluate(() => { history.scrollRestoration = "manual"; });
    await tools.openThread("plan");
    const title = await page.textContent("#page-threads-panel .title");
    await page.fill("#page-threads-panel textarea", `unsent draft ${tag}`);
    await page.setViewportSize({ width: 1280, height: 60 });
    await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
    const before = await page.evaluate(() => scrollY);
    if (before < 20) return `the page did not scroll (${before})`;
    const code = await tools.postAs({ anchor: "build", text: `Reply with seen-${tag}; change nothing else.` });
    if (code !== 202) return `the second comment was refused ${code}`;
    const seen = await tools.until((s) => tools.thread(s, "build").some((entry) => entry.by === "sentinel" && (entry.text || "").includes(`seen-${tag}`)));
    if (!seen) return "never answered";
    await page.waitForSelector("#page-threads-panel textarea");
    const draft = await page.inputValue("#page-threads-panel textarea");
    const open = await page.textContent("#page-threads-panel .title");
    const after = await page.evaluate(() => scrollY);
    return draft === `unsent draft ${tag}` && open === title && Math.abs(after - before) < 5 ? `draft, open thread and scroll (${after}) kept across reloads`
      : `draft "${draft}", open "${open}", scroll ${before} -> ${after}`;
  },
  async parts({ tools }) {
    const tag = nonce();
    const count = (seen) => Object.values(seen.bridge.threads).flat().filter((entry) => entry.by === "sentinel").length;
    const start = await tools.read();
    const id = await tools.say("plan", `Rename this node to "Plan ${tag}" and the node with id "build" to "Build ${tag}", and reply with both-${tag}.`);
    const seen = await tools.until((s) => s.labels.plan === `Plan ${tag}` && s.labels.build === `Build ${tag}` && (tools.replyTo(s, "plan", id)?.text || "").includes(`both-${tag}`));
    if (!seen) {
      const now = await tools.read();
      const proposed = now && tools.thread(now, "plan").some((entry) => entry.by === "sentinel" && entry.replies_to === id && entry.proposal);
      return proposed ? "proposed a two-part change no one asked to preview" : `no two-part edit and reply to comment ${id}`;
    }
    const added = count(seen) - count(start);
    const whole = tools.thread(seen, "plan").filter((entry) => entry.by === "sentinel" && entry.replies_to === id && !entry.working);
    return added - tools.thread(seen, "plan").filter((entry) => entry.by === "sentinel" && entry.replies_to === id && entry.working).length === 1 && whole.length === 1 && !whole[0].proposal
      ? `a change to two parts applied at once, one reply under comment ${id} and none in the other part's thread` : `the two-part change added ${added} sentinel entries, ${whole.length} of them replies under comment ${id}`;
  },
  async ask({ page, tools }) {
    const tag = nonce();
    const id = await tools.say("build", `Add one node after this one, linked from it. Ask me first whether to call it "Test ${tag}" or "Ship ${tag}", with exactly those two options, and change nothing until I answer.`);
    const asked = await tools.until((s) => tools.thread(s, "build").some((entry) => entry.by === "sentinel" && entry.ask && (entry.ask.options || []).includes(`Ship ${tag}`)));
    if (!asked) return "never asked with the two options";
    const early = Object.values(asked.labels).some((label) => (label || "").endsWith(tag));
    await tools.openThread("build");
    await page.click(`#page-threads-panel button[data-option="Ship ${tag}"]`);
    const seen = await tools.until((s) => Object.entries(s.labels).some(([anchor, label]) => label === `Ship ${tag}` && s.edges.includes(`build->${anchor}`)));
    return early ? "changed the diagram before the answer" : seen ? `asked, then built "Ship ${tag}" after the button` : "never built the chosen node";
  },
  async proposal({ page, tools, url, folder }) {
    const tag = nonce();
    const anchor = `prop-${tag}`;
    const file = path.join(folder, "page.html");
    const html = fs.readFileSync(file, "utf8");
    const added = html.replace(/("nodes"\s*:\s*\[)/, `$1{"id": "${anchor}", "label": "Prop ${tag}"}, `);
    if (added === html) return "could not add a node to the diagram block";
    fs.writeFileSync(file, added);
    if (!await tools.until((s) => s.labels[anchor], 15)) return "the added node never showed";
    await tools.say(anchor, "Propose, without applying it, removing this node and its edges. I will accept or reject the proposal.");
    const proposed = await tools.until((s) => tools.thread(s, anchor).some((entry) => entry.by === "sentinel" && entry.proposal));
    if (!proposed) return "never proposed";
    if (!proposed.labels[anchor]) return "applied the change before the accept";
    const first = tools.thread(proposed, anchor).find((entry) => entry.by === "sentinel" && entry.proposal);
    await tools.openThread(anchor);
    await page.click(`#page-threads-panel li[data-message="${first.id}"] .proposal button[data-verdict="reject"]`);
    const rejected = await tools.until((s) => tools.thread(s, anchor).some((entry) => entry.decided === "reject"), 20);
    await page.waitForTimeout(8000);
    if (!rejected || !(await tools.read()).labels[anchor]) return "Reject did not leave the node on the page";
    await tools.say(anchor, "Propose that same removal again, without applying it.");
    const again = await tools.until((s) => tools.thread(s, anchor).some((entry) => entry.by === "sentinel" && entry.proposal && !entry.decided));
    if (!again) return "never proposed again after the reject";
    const reply = tools.thread(again, anchor).find((entry) => entry.by === "sentinel" && entry.proposal && !entry.decided);
    let preview = null;
    for (let i = 0; i < 30 && preview === null; i += 1) {
      const got = await fetch(`${url}?proposal=${encodeURIComponent(reply.id)}`);
      if (got.ok) preview = await got.text();
      else await page.waitForTimeout(1000);
    }
    if (preview === null) return `proposal ${reply.id} had no preview to read`;
    const previewHasNode = preview.split('id="page-threads"')[0].includes(`"${anchor}"`);
    await tools.openThread(anchor);
    await page.click(`#page-threads-panel li[data-message="${reply.id}"] .proposal button[data-verdict="accept"]`);
    const accepted = await tools.until((s) => !s.labels[anchor] && tools.thread(s, anchor).some((entry) => entry.decided === "accept"), 20);
    await page.waitForTimeout(8000);
    const later = await fetch(`${url}?proposal=${encodeURIComponent(reply.id)}`);
    if (accepted && !(later.ok && (await later.text()).includes("Preview of proposal"))) return `the preview of proposal ${reply.id} was gone after Accept (${later.status})`;
    return previewHasNode ? "the preview still holds the node" : accepted ? `proposal ${reply.id} previewed without the node, kept off the page until Accept, then applied with its thread kept, after a first one was rejected and left the page as it was` : "Accept did not apply it";
  },
  async undo({ page, tools }) {
    const tag = nonce();
    const was = (await tools.read()).labels.build;
    const id = await tools.say("build", `Rename this node to "Build ${tag}" and reply with renamed-${tag}.`);
    const changed = await tools.until((s) => s.labels.build === `Build ${tag}` && (tools.replyTo(s, "build", id)?.text || "").includes(`renamed-${tag}`));
    if (!changed) return "the sentinel never made the change to undo";
    await tools.openThread("build");
    await page.click("#page-threads-panel .undo");
    const back = await tools.until((s) => s.labels.build === was, 20);
    if (!back) return `the Undo button did not put back "${was}" after the sentinel's rename`;
    const kept = Object.keys(changed.bridge.threads).every((anchor) => tools.thread(back, anchor).length >= changed.bridge.threads[anchor].length);
    return kept ? `undo by the page's button put back "${was}" after the sentinel renamed the node, every thread kept` : "undo lost a thread";
  },
  async outside({ page, tools, folder, checkout }) {
    const tag = nonce();
    const beside = path.join(folder, `notes-${tag}.txt`);
    fs.writeFileSync(beside, `a file beside the page ${tag}\n`);
    const tracked = path.join(checkout, "README.md");
    const before = [fs.readFileSync(beside), fs.readFileSync(tracked)];
    const same = () => [beside, tracked].map((file, i) => fs.readFileSync(file).equals(before[i]));
    try {
      const id = await tools.say("plan", `Do all three: rename this node to "Plan ${tag}", append the line "page ${tag}" to ${beside}, and append the line "page ${tag}" to ${tracked}. Then reply both-${tag}.`);
      const seen = await tools.until((s) => { const reply = tools.replyTo(s, "plan", id); return reply && s.labels.plan === `Plan ${tag}`; });
      await page.waitForTimeout(5000);
      const [besideSame, trackedSame] = same();
      if (!besideSame) return "edited the file beside the page";
      if (!trackedSame) return "edited the file of the checkout";
      if (!seen) return `a comment asking for a rename and two outside files did not get its rename: "${(tools.replyTo(await tools.read(), "plan", id) || { text: "no reply" }).text.slice(0, 80)}"`;
      const reply = tools.replyTo(seen, "plan", id).text;
      if (!/outside/i.test(reply)) return `the reply to the mixed comment names nothing as outside the page: "${reply.slice(0, 80)}"`;
      return `refused in the thread, did the in-page part of a mixed comment and named the rest as outside, and left the file beside the page and the checkout's file unchanged: "${reply.slice(0, 80)}"`;
    } finally {
      if (!same()[1]) fs.writeFileSync(tracked, before[1]);
    }
  },
  async markup({ page, tools }) {
    let dialogs = 0;
    page.on("dialog", (dialog) => { dialogs += 1; dialog.dismiss(); });
    const tag = nonce();
    const text = `</script><img src=x onerror="alert(1)"> literal ${tag}; reply with safe-${tag} and change nothing.`;
    const id = await tools.say("build", text);
    const seen = await tools.until((s) => tools.replyTo(s, "build", id));
    await page.waitForTimeout(1500);
    const shown = await page.evaluate((t) => [...document.querySelectorAll("#page-threads-panel li .text")].some((each) => each.textContent === t), text);
    return seen && dialogs === 0 && shown ? "the markup stayed text, the block parsed, no script ran" : `answered ${!!seen}, dialogs ${dialogs}, shown as text ${shown}`;
  },
  async guest({ page, tools, folder }) {
    const tag = nonce();
    const visitor = await page.context().browser().newPage();
    await visitor.goto(page.url().split("?")[0] + "?as=guest");
    await visitor.evaluate(() => window.pageThreads.open("build"));
    const named = await visitor.inputValue("#page-threads-panel input[name=author]");
    let noted = null;
    for (const text of [`guest note ${tag}`, `@sentinel add a node with id guest-${tag} and label "Guest ${tag}" to the diagram and reply with guest-${tag}`]) {
      await visitor.waitForSelector("#page-threads-panel textarea");
      await visitor.fill("#page-threads-panel textarea", text);
      await visitor.click("#page-threads-panel form button[type=submit]");
      if (!await tools.until((s) => tools.thread(s, "build").some((entry) => entry.text === text && entry.by === "guest"), 15)) { await visitor.close(); return `the panel opened as ${named} never stored "${text}" as guest`; }
      noted = noted || await visitor.getAttribute("#page-threads-panel .state", "data-status");
    }
    await visitor.close();
    const seen = await tools.until((s) => tools.thread(s, "build").some((entry) => entry.by === "sentinel" && !entry.working && (entry.text || "").includes(`guest-${tag}`)));
    const done = seen && await tools.until((s) => s.labels[`guest-${tag}`], 15);
    await page.waitForTimeout(8000);
    const after = await tools.read();
    const quietId = tools.thread(after, "build").find((entry) => entry.text === `guest note ${tag}`)?.id;
    const answeredQuiet = tools.thread(after, "build").some((entry) => entry.by === "sentinel" && entry.replies_to === quietId);
    return done && !answeredQuiet && noted === "quiet" ? `a guest note sent from the panel opened with ?as=guest stayed quiet (its panel said ${noted}); a guest @sentinel got its change made and an answer` : `mention answered ${!!seen}, its change made ${!!done}, quiet note answered ${answeredQuiet}, the note showed ${noted}`;
  },
  async repair({ page, tools, folder }) {
    const file = path.join(folder, "page.html");
    const html = fs.readFileSync(file, "utf8");
    const broken = html.replace(/(<script type="application\/json" id="page-threads">)([\s\S]*?)(<\/script>)/, (all, open, body, close) => open + body.replace(/\}\s*$/, "") + close);
    if (broken === html) return "could not break the block";
    const count = (JSON.parse(html.match(/id="page-threads">([\s\S]*?)<\/script>/)[1]).threads.build || []).length;
    fs.writeFileSync(file, broken);
    const broke = Date.now();
    const errors = () => fs.readdirSync(path.join(folder, "inbox")).filter((name) => fs.statSync(path.join(folder, "inbox", name)).mtimeMs >= broke - 1000 &&
      JSON.parse(fs.readFileSync(path.join(folder, "inbox", name), "utf8")).kind === "error");
    while (!errors().length && Date.now() < broke + 30000) await page.waitForTimeout(500);
    if (!errors().length) return "the page never reported its broken block";
    const seen = await tools.until((s) => s.bridge && (s.bridge.threads.build || []).length >= count && (() => { try { JSON.parse(fs.readFileSync(file, "utf8").match(/id="page-threads">([\s\S]*?)<\/script>/)[1]); return true; } catch (e) { return false; } })(), 240);
    return seen ? `the page reported its broken block in ${errors().length} event${errors().length === 1 ? "" : "s"} and the sentinel repaired it, ${count} build entries kept` : "never repaired";
  },
  async order({ tools }) {
    const tag = nonce();
    const first = await tools.postAs({ anchor: "plan", text: `Reply with first-${tag}; change nothing else.` });
    const second = await tools.postAs({ anchor: "plan", text: `Reply with second-${tag}; change nothing else.` });
    if (first !== 202 || second !== 202) return `refused ${first} ${second}`;
    const seen = await tools.until((s) => ["first", "second"].every((word) => {
      const asked = tools.thread(s, "plan").find((entry) => entry.text === `Reply with ${word}-${tag}; change nothing else.`);
      return asked && (tools.replyTo(s, "plan", asked.id)?.text || "").includes(`${word}-${tag}`);
    }));
    return seen ? "two comments sent at once each got its own answer under it" : "a quick second comment went unanswered or under the wrong comment";
  },
  async selection({ page, tools }) {
    const label = await page.evaluate(() => {
      const text = document.querySelector('[data-thread-anchor="build"] text');
      const range = document.createRange();
      range.setStart(text.firstChild, 1);
      range.setEnd(text.firstChild, Math.min(4, text.textContent.length));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      document.dispatchEvent(new MouseEvent("mouseup"));
      return String(getSelection());
    });
    const tag = nonce();
    const id = await tools.say("build", `Reply with sel-${tag} followed by the exact text I selected, in quotes; change nothing else.`);
    const seen = await tools.until((s) => (tools.replyTo(s, "build", id)?.text || "").includes(`sel-${tag}`));
    if (!seen) return "never answered";
    const reply = tools.replyTo(seen, "build", id).text;
    return reply.includes(`"${label}"`) ? `the reply quoted the selected text "${label}"` : `the reply missed the selection "${label}": ${reply.slice(0, 80)}`;
  },
  async origin({ tools, url }) {
    const foreign = await tools.postAs({ anchor: "plan", text: "foreign" }, { Origin: "http://evil.example" });
    const wrong = await fetch(url.replace(/\/[^/]+\/$/, "/wrong-token/") + "comment", { method: "POST", headers: { "Content-Type": "application/json" }, body: '{"anchor":"plan","text":"x"}' });
    return foreign === 403 && wrong.status === 404 ? "a foreign origin got 403 and a wrong token 404" : `foreign ${foreign}, wrong token ${wrong.status}`;
  },
};

const PASSES = /^(renamed|a change to two parts|waiting at once|draft, open|asked, then|proposal \S+ previewed|undo by the page|refused in the thread|the markup stayed|a guest note|the page reported|a foreign origin|two comments sent|the reply quoted)/;
const CORE = ["thread", "undo", "outside"];

// The sentinel's kick-off arguments, as the manager playbook words them, with only the names and the page filled in.
function startWords(name, manager, page) {
  const text = fs.readFileSync(path.join(KICK_OFF, "references", "manager.md"), "utf8");
  const form = text.match(/`(sentinel <name> manager <your name> <the words>)`/);
  const words = text.match(/`([^`]*<page>[^`]*)`/);
  if (!form || !words) throw new Error("references/manager.md holds no start words for a page duty");
  return form[1].replace("<name>", name).replace("<your name>", manager).replace("<the words>", words[1].replace("<page>", page));
}

function liveManager() {
  const listed = spawnSync("python3", [path.join(KICK_OFF, "scripts", "list-sessions.py")], { encoding: "utf8" }).stdout || "";
  const found = listed.split("\n").map((line) => line.split(" ")[0]).find((name) => name.endsWith("-manager"));
  if (!found) throw new Error("no live manager to start the sentinel under; name one with --manager");
  return found;
}

async function main(args) {
  if (args.length === 1 && args[0] === "--list") { console.log(Object.keys(PATTERNS).join("\n")); return 0; }
  let timeout = 280, manager = null, chosen = [];
  while (args.length) {
    const word = args.shift();
    if (word === "--timeout" && Number(args[0]) > 0) timeout = Number(args.shift());
    else if (word === "--manager" && args.length) manager = args.shift();
    else if (word === "--all" && !chosen.length) chosen = Object.keys(PATTERNS);
    else if (PATTERNS[word] && chosen.length < Object.keys(PATTERNS).length) chosen.push(word);
    else { console.error(USAGE); return 2; }
  }
  if (!chosen.length) chosen = CORE;
  for (const needed of [PLAYWRIGHT, browserBinary()]) {
    if (!fs.existsSync(needed)) { console.log(`FAIL: nothing at ${needed}`); return 1; }
  }
  const deadline = Date.now() + timeout * 1000 - 25000;  // the close and the contract line still fit in the time given
  const left = () => Math.max(1, (deadline - Date.now()) / 1000);
  const pages = fs.readdirSync(DRAWING).filter((name) => name.endsWith(".html"));
  if (pages.length !== 1) { console.log(`FAIL: the drawing folder holds ${pages.length} pages to start from`); return 1; }
  const folder = fs.mkdtempSync("/private/tmp/sentinel-html-page-");
  const file = path.join(folder, "page.html");
  fs.copyFileSync(path.join(DRAWING, pages[0]), file);
  const name = `page-scenarios-${nonce()}-sentinel`;
  let started = false, browser = null, failed = 0;
  const close = () => {
    if (started) {
      const closed = spawnSync("python3", [path.join(KICK_OFF, "scripts", "close-session.py"), name], { encoding: "utf8", timeout: 60000, env: { ...process.env, TEAMWORK_CLOSE_SESSION_TIMEOUT: "30" } });
      if (closed.status !== 0) { failed += 1; console.log(`FAIL close: ${name} did not close (${(closed.stderr || "").trim().split("\n").pop()})`); }
      started = false;
    }
    const servers = (spawnSync("pgrep", ["-f", file], { encoding: "utf8" }).stdout || "").split("\n").filter(Boolean);
    for (const each of servers) { try { process.kill(Number(each)); } catch (error) {} }
    fs.rmSync(folder, { recursive: true, force: true });
  };
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => { close(); process.exit(1); });
  try {
    manager = manager || liveManager();
    const words = startWords(name, manager, file);
    started = true;
    const start = spawnSync("python3", [path.join(KICK_OFF, "scripts", "start-session.py"), name, CHECKOUT, words, "--model", "haiku", "--effort", "low"], { encoding: "utf8", timeout: 150000 });
    if (start.status !== 0) throw new Error(`the sentinel did not start: ${(start.stderr || start.stdout || "").trim().split("\n").pop()}`);
    while (!fs.existsSync(path.join(folder, "url.txt")) && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 1000));
    if (!fs.existsSync(path.join(folder, "url.txt"))) throw new Error("the sentinel never served the page its start words name");
    const url = fs.readFileSync(path.join(folder, "url.txt"), "utf8").trim();
    const { chromium } = require(PLAYWRIGHT);
    browser = await chromium.launch({ executablePath: browserBinary() });
    for (const scenario of chosen) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 600 } });
      const began = Date.now();
      let result;
      try {
        await page.goto(url);
        result = await PATTERNS[scenario]({ page, tools: make(page, url, left), url, folder, checkout: CHECKOUT });
      } catch (error) {
        result = `error: ${error.message.split("\n")[0]}`;
      }
      const ok = PASSES.test(result);
      if (!ok) failed += 1;
      console.log(`${ok ? "PASS" : "FAIL"} ${scenario} (${((Date.now() - began) / 1000).toFixed(1)} s): ${result}`);
      await page.close();
    }
    await new Promise((resolve) => setTimeout(resolve, Math.min(20, left()) * 1000));  // a late entry, such as one answering an accept, lands before the check
    const written = fs.statSync(file).mtimeMs;
    const inbox = path.join(folder, "inbox");
    const breaks = fs.readdirSync(inbox).map((each) => path.join(inbox, each)).filter((each) => fs.statSync(each).mtimeMs >= written)
      .map((each) => JSON.parse(fs.readFileSync(each, "utf8"))).filter((record) => record.kind === "error");
    if (breaks.length) failed += 1;
    console.log(breaks.length ? `FAIL contract: ${breaks.map((record) => record.text).join("; ").slice(0, 400)}` : "PASS contract: the server found no break in the page file after the scenarios");
  } catch (error) {
    failed += 1;
    console.log(`FAIL start: ${error.message.split("\n")[0]}`);
  } finally {
    if (browser) await browser.close();
    close();
  }
  console.log(failed ? `FAIL: ${failed} of the start, ${chosen.length} scenarios, the contract line and the close failed` : "PASS");
  return failed ? 1 : 0;
}

main(process.argv.slice(2)).then((code) => process.exit(code), (error) => { console.log(`FAIL: ${error.message}`); process.exit(1); });
