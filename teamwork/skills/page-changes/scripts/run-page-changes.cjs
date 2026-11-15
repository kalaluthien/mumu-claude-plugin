#!/usr/bin/env node
// Run page-changes end to end in a headless Chromium on a copy of assets/diagram-page.html in a scratch folder:
// (a) opened as file://, a rename and a comment stay in window.pageChanges and Export downloads them;
// (b) served, a rename and a comment reach the queue and the server prints one pending line after the quiet window;
// (c) acting as the session, the script writes both into the page file and acks them, and the open page reloads by itself;
// (d) the server refuses a post without the token, from another origin or of an unknown kind, hides its records,
//     listens on 127.0.0.1 only, and keeps its url and id counter across a restart;
// (e) a page file cut off mid-write reloads no open page, a comment made while the server is down shows as not sent
//     and reaches the queue once the server is back, and a badge clicked right after a form edit opens its panel;
// (b), (c) and (d) also fail when the server writes the page file.
//
// usage: run-page-changes.cjs
//        run-page-changes.cjs --queue <folder>
//        run-page-changes.cjs --verify <folder>
// With no option it prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL, and exits 1 on a failure.
// --queue empties <folder>, serves a copy of the starter there, makes a rename and a comment as the person, leaves
// them pending, and prints `queued 2 changes for <folder>/page.html`, or `FAIL queue: <reason>` and exit 1.
// --verify serves <folder>/page.html again after a session applied and acked them, prints `PASS <check>` or
// `FAIL <check>: <reason>` per check, then PASS or FAIL, and exits 1 on a failure; it ignores stdin.
// Playwright is loaded from /private/tmp/page-changes-playwright/node_modules/playwright-core and the browser is the
// newest headless shell Playwright installed, never an installed Google Chrome.
const fs = require("fs");
const http = require("http");
const net = require("net");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawn, spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const PLAYWRIGHT = "/private/tmp/page-changes-playwright/node_modules/playwright-core";
const SERVER = path.join(ROOT, "scripts", "serve-page-changes.py");
const QUIET = 1.5;
const BLOCK = (id) => new RegExp(`(<script type="application/json" id="${id}">)([\\s\\S]*?)(</script>)`);

const MODE = process.argv[2];
const FOLDER = process.argv[3] && path.resolve(process.argv[3]);
if (process.argv.length > 4 || process.argv.length === 3 || (process.argv.length === 4 && !["--queue", "--verify"].includes(MODE))) {
  console.error("usage: run-page-changes.cjs [--queue <folder> | --verify <folder>]");
  process.exit(2);
}
const COMMENT = "Add a node Test after this one";

function browserBinary() {
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  return shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64/chrome-headless-shell") : null;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const check = (condition, reason) => { if (!condition) throw new Error(reason); };

async function until(probe, ms, what) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const value = await probe().catch(() => null);
    if (value) return value;
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${what}`);
}

function request(method, url, { headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const sent = http.request(url, { method, headers }, (response) => {
      let text = "";
      response.on("data", (chunk) => { text += chunk; });
      response.on("end", () => resolve({ status: response.statusCode, text }));
    });
    sent.on("error", reject);
    sent.end(body);
  });
}

const python = (script, ...args) => spawnSync("python3", [path.join(ROOT, "scripts", script), ...args], { encoding: "utf8" });

function startServer(page) {
  const child = spawn("python3", [SERVER, page, "--quiet", String(QUIET)], { stdio: ["ignore", "pipe", "pipe"] });
  const lines = [];
  readline.createInterface({ input: child.stdout }).on("line", (line) => lines.push(line));
  child.stderr.on("data", (chunk) => process.stderr.write(chunk));
  return { child, lines, stop: () => new Promise((resolve) => { if (child.exitCode !== null || child.signalCode) return resolve(); child.once("exit", resolve); child.kill(); }) };
}

async function rename(page, node, label) {
  page.once("dialog", (dialog) => dialog.accept(label));
  await page.dblclick(`g[data-id="${node}"]`);
  await until(async () => (await page.textContent(`g[data-id="${node}"] text`)) === label, 3000, `the label ${label}`);
}

async function comment(page, anchor, text) {
  await page.click(`#page-changes-ui .layer button[data-anchor="${anchor}"]`);
  await page.fill("#page-changes-ui aside textarea", text);
  await page.click("#page-changes-ui aside button[type=submit]");
  await until(async () => (await page.$$eval("#page-changes-ui aside li.waiting .text", (items) => items.map((item) => item.textContent))).includes(text),
    3000, "the comment shown as waiting");
}

const status = (page) => page.textContent("#page-changes-ui .bar .state");

async function fileStep(browser, pagePath) {
  const before = fs.readFileSync(pagePath, "utf8");
  const connected = python("connect-page.py", pagePath);
  check(connected.stdout.trim() === `updated ${pagePath}` && fs.readFileSync(pagePath, "utf8") === before,
    `connect-page.py changed the starter page or said "${connected.stdout.trim()}": assets/diagram-page.html lacks the current runtime`);
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`file://${pagePath}`);
  await rename(page, "plan", "Roadmap");
  await comment(page, "idea", "Say what the idea is");
  const changes = await page.evaluate(() => window.pageChanges);
  check(changes.length === 2, `window.pageChanges holds ${changes.length} changes, not 2`);
  const data = changes.find((change) => change.kind === "data");
  check(data && data.target === "diagram-main" && data.payload.path === "diagram-main"
    && data.payload.value.nodes.some((node) => node.id === "plan" && node.label === "Roadmap"), "the data change does not carry the renamed diagram");
  check(changes.some((change) => change.kind === "comment" && change.target === "idea" && change.payload.text === "Say what the idea is"), "the comment is not in window.pageChanges");
  const state = await status(page);
  check(/opened as file/.test(state) && /2 pending/.test(state), `the status bar says "${state}"`);
  const [download] = await Promise.all([page.waitForEvent("download"), page.click("#page-changes-ui .export")]);
  const exported = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
  check(download.suggestedFilename() === "changes.json" && exported.length === 2, "Export did not download both changes as changes.json");
  check(!errors.length, `the page threw: ${errors.join("; ")}`);
  const runtime = fs.readFileSync(path.join(ROOT, "assets", "page-runtime.js"), "utf8");
  const bare = {
    "no blocks": "",
    "broken blocks": '<script type="application/json" id="page-data">{not json</script><script type="application/json" id="page-threads">{"threads": []}</script>',
  };
  for (const [name, blocks] of Object.entries(bare)) {
    const barePath = path.join(path.dirname(pagePath), "bare.html");
    fs.writeFileSync(barePath, `<!doctype html><html><head><meta charset="utf-8"></head><body><p data-id="note">Note</p>${blocks}<script>${runtime}</script></body></html>`);
    await page.goto(`file://${barePath}`);
    await until(() => page.$('#page-changes-ui .layer button[data-anchor="note"]'), 3000, `a badge on a page with ${name}`);
    check(JSON.stringify(await page.evaluate(() => window.pageData)) === "{}" && !errors.length, `a page with ${name} threw or kept a page-data: ${errors.join("; ")}`);
    fs.rmSync(barePath);
  }
  await context.close();
}

async function servedStep(browser, server, shared) {
  const line = await until(async () => server.lines.find((each) => each.startsWith("page-changes url: ")), 5000, "the url line");
  shared.url = line.slice("page-changes url: ".length);
  shared.origin = new URL(shared.url).origin;
  check(server.lines[0] === line, "the url line is not the first stdout line");
  check(fs.readFileSync(path.join(path.dirname(shared.pagePath), "url.txt"), "utf8").trim() === shared.url, "url.txt does not hold the url");
  const unwritten = fs.readFileSync(shared.pagePath);
  const page = shared.page = await (await browser.newContext()).newPage();
  page.on("pageerror", (error) => shared.errors.push(error.message));
  await page.goto(shared.url);
  await until(async () => /server connected/.test(await status(page)), 5000, "the status bar to say server connected");
  await rename(page, "idea", "Concept");
  await comment(page, "build", "Split this into build and test");
  const events = await until(async () => {
    const queue = JSON.parse((await request("GET", `${shared.url}api/changes`)).text);
    return queue.length >= 2 && queue;
  }, 3000, "two queued events");
  const early = server.lines.filter((each) => each.startsWith("page-changes pending")).length;
  check(early === 0, `the server printed ${early} pending lines before the quiet window ended`);
  check(events.length === 2 && events.some((event) => event.kind === "data" && event.target === "diagram-main")
    && events.some((event) => event.kind === "comment" && event.target === "build"), `the queue holds ${JSON.stringify(events)}`);
  check(events.every((event) => Number.isInteger(event.id) && /Z|\+00:00$/.test(event.ts)), "an event lacks an integer id or a UTC ts");
  shared.events = events;
  await sleep(QUIET * 1000 + 1500);
  const pending = server.lines.filter((each) => each.startsWith("page-changes pending"));
  check(pending.length === 1, `the server printed ${pending.length} pending lines, not 1`);
  check(/pending 2: 1 comment, 1 data/.test(pending[0]) && pending[0].includes(`curl -s ${shared.url}api/changes`)
    && pending[0].includes(`-H 'Origin: ${shared.origin}'`), `the pending line does not carry the counts and commands: ${pending[0]}`);
  check(/2 pending/.test(await status(page)), `the status bar says "${await status(page)}"`);
  check(fs.readFileSync(shared.pagePath).equals(unwritten), "the server wrote the page file while it queued changes");
}

function setPath(target, dotted, value) {
  const keys = dotted.split(".");
  const last = keys.pop();
  for (const each of keys) target = target[each] = target[each] && typeof target[each] === "object" ? target[each] : {};
  target[last] = value;
}

async function sessionStep(shared) {
  const { page, pagePath, events } = shared;
  await page.fill("#page-changes-ui aside textarea", "draft kept across the reload");
  await page.evaluate(() => { window.beforeReload = true; });
  let html = fs.readFileSync(pagePath, "utf8");
  const dataMatch = html.match(BLOCK("page-data"));
  const threadsMatch = html.match(BLOCK("page-threads"));
  const data = JSON.parse(dataMatch[2]);
  const threads = JSON.parse(threadsMatch[2]);
  const reply = "Split into Build and Test as asked";
  for (const event of events) {
    if (event.kind === "data") setPath(data, event.payload.path, event.payload.value);
    if (event.kind === "comment") {
      const thread = threads.threads[event.target] = threads.threads[event.target] || [];
      thread.push({ id: event.id, by: "person", text: event.payload.text, replies_to: null },
        { id: `${event.id}.1`, by: "session", text: reply, replies_to: event.id });
    }
  }
  const escaped = (value) => `\n${JSON.stringify(value, null, 1).replace(/</g, "\\u003c")}\n`;
  html = html.replace(dataMatch[0], dataMatch[1] + escaped(data) + dataMatch[3]);
  html = html.replace(BLOCK("page-threads"), (whole, open, body, close) => open + escaped(threads) + close);
  fs.writeFileSync(pagePath, html);
  await until(async () => (await page.evaluate(() => window.beforeReload)) === undefined, 5000, "the open page to reload by itself");
  await until(async () => (await page.textContent('g[data-id="idea"] text')) === "Concept", 5000, "the new label after the reload");
  await until(async () => (await page.$$eval('#page-changes-ui aside li[data-by="session"] .text', (items) => items.map((item) => item.textContent))).includes(reply),
    5000, "the session's reply in the panel");
  await until(async () => /server connected/.test(await status(page)), 5000, "the reloaded page to connect");
  // a session acks in a later tool call than its edit, so the ack reaches a page that has already reloaded
  await page.evaluate(() => { window.afterReload = true; });
  const acked = await request("POST", `${shared.url}api/changes/ack`, {
    headers: { Origin: shared.origin, "Content-Type": "application/json" },
    body: JSON.stringify({ ids: [...events.map((event) => event.id), 9999] }),
  });
  check(acked.status === 200 && JSON.parse(acked.text).acked === 2, `the ack answered ${acked.status} ${acked.text}`);
  await sleep(1000);
  check(fs.readFileSync(pagePath, "utf8") === html, "the server wrote the page file on the ack");
  await until(async () => /server connected/.test(await status(page)) && /0 pending/.test(await status(page)), 5000, "the status bar to say 0 pending");
  check(!(await page.$("#page-changes-ui aside li.waiting")), "the panel still shows a comment as waiting");
  check(await page.evaluate(() => window.afterReload), "the ack reloaded the page, though the page file did not change");
  check((await page.inputValue("#page-changes-ui aside textarea")) === "draft kept across the reload", "the draft did not survive the reload");
  const queue = JSON.parse((await request("GET", `${shared.url}api/changes`)).text);
  check(queue.length === 0, `the queue still holds ${queue.length} events`);
  const folder = path.dirname(pagePath);
  const applied = fs.readFileSync(path.join(folder, "changes", "applied.jsonl"), "utf8").trim().split("\n").map((each) => JSON.parse(each).id);
  check(events.every((event) => applied.includes(event.id)), `applied.jsonl holds ids ${applied}`);
  const versions = await until(async () => {
    const names = fs.readdirSync(path.join(folder, "history")).filter((name) => /^\d{8}T\d+-[0-9a-f]{12}\.html$/.test(name));
    return names.length >= 2 && names;
  }, 3000, "two versions in history/");
  check(versions.every((name) => !(fs.statSync(path.join(folder, "history", name)).mode & 0o222)), "a history copy is writable");
  const checked = python("check-page.py", pagePath);
  check(checked.stdout.trim() === "follows", `check-page.py printed: ${checked.stdout.trim()}`);
  check(!shared.errors.length, `the page threw: ${shared.errors.join("; ")}`);
}

async function refusalStep(server, shared) {
  const { url, origin } = shared;
  const json = { "Content-Type": "application/json" };
  const good = JSON.stringify({ kind: "comment", target: "idea", payload: { text: "hello" } });
  const unwritten = fs.readFileSync(shared.pagePath);
  const cases = [
    ["POST without the token", "POST", `${origin}/api/changes`, { ...json, Origin: origin }, good, 404],
    ["POST with another token", "POST", `${origin}/wrong-token/api/changes`, { ...json, Origin: origin }, good, 404],
    ["POST from another origin", "POST", `${url}api/changes`, { ...json, Origin: "http://evil.example" }, good, 403],
    ["POST with no origin", "POST", `${url}api/changes`, json, good, 403],
    ["POST of an unknown kind", "POST", `${url}api/changes`, { ...json, Origin: origin }, JSON.stringify({ kind: "delete", target: "idea", payload: {} }), 400],
    ["POST of an empty comment", "POST", `${url}api/changes`, { ...json, Origin: origin }, JSON.stringify({ kind: "comment", target: "idea", payload: { text: " " } }), 400],
    ["POST to a bad target", "POST", `${url}api/changes`, { ...json, Origin: origin }, JSON.stringify({ kind: "data", target: "a b", payload: {} }), 400],
    ["POST that is not JSON", "POST", `${url}api/changes`, { "Content-Type": "text/plain", Origin: origin }, good, 400],
    ["GET url.txt", "GET", `${url}url.txt`, {}, undefined, 404],
    ["GET the queue file", "GET", `${url}changes/pending.jsonl`, {}, undefined, 404],
    ["GET a history copy", "GET", `${url}history/${fs.readdirSync(path.join(path.dirname(shared.pagePath), "history"))[0]}`, {}, undefined, 404],
    ["GET outside the token", "GET", `${origin}/`, {}, undefined, 404],
  ];
  for (const [name, method, target, headers, body, expected] of cases) {
    const answer = await request(method, target, { headers, body });
    check(answer.status === expected, `${name} answered ${answer.status}, not ${expected}`);
  }
  const port = Number(new URL(url).port);
  const others = Object.values(os.networkInterfaces()).flat().filter((each) => !each.internal).map((each) => each.address).concat("::1");
  for (const host of others) {
    const reached = await new Promise((resolve) => {
      const socket = net.connect({ host, port, timeout: 1000 }, () => { socket.destroy(); resolve(true); });
      socket.on("error", () => resolve(false));
      socket.on("timeout", () => { socket.destroy(); resolve(false); });
    });
    check(!reached, `the server answers on ${host}, not only on 127.0.0.1`);
  }
  await server.stop();
  const again = startServer(shared.pagePath);
  shared.server = again;
  const line = await until(async () => again.lines[0], 5000, "the url line after a restart");
  check(line === `page-changes url: ${url}`, `the restart printed "${line}", not the same url`);
  const added = await request("POST", `${url}api/changes`, { headers: { ...json, Origin: origin }, body: good });
  const highest = Math.max(...shared.events.map((event) => event.id));
  check(added.status === 202 && JSON.parse(added.text).id === highest + 1, `the first post after a restart answered ${added.status} ${added.text}, not id ${highest + 1}`);
  await sleep(1000);
  check(fs.readFileSync(shared.pagePath).equals(unwritten), "the server wrote the page file while it refused, restarted or queued");
}

async function outageStep(shared) {
  const { page, pagePath } = shared;
  await until(async () => /server connected/.test(await status(page)), 5000, "the page to reconnect after the restart");
  await page.evaluate(() => { window.beforeCut = true; });
  const whole = fs.readFileSync(pagePath, "utf8");
  fs.writeFileSync(pagePath, whole.slice(0, whole.indexOf("<!-- /page-changes runtime -->")));
  await sleep(2500);
  check(await page.evaluate(() => window.beforeCut), "a page file cut off mid-write reloaded the open page");
  fs.writeFileSync(pagePath, whole);
  await shared.server.stop();
  await until(async () => /server not reachable/.test(await status(page)), 5000, "the status bar to say server not reachable");
  const text = "Keep this while the server is down";
  await page.click('#page-changes-ui .layer button[data-anchor="plan"]');
  await page.fill("#page-changes-ui aside textarea", text);
  await page.click("#page-changes-ui aside button[type=submit]");
  await until(async () => /1 not sent/.test(await status(page)), 3000, "the status bar to count 1 not sent");
  const note = await page.$$eval("#page-changes-ui aside li.waiting", (items) => items.map((item) => [item.querySelector(".text").textContent, item.querySelector(".meta").textContent]));
  check(note.some(([shown, meta]) => shown === text && meta === "not sent"), `the panel shows ${JSON.stringify(note)}`);
  check(await page.isVisible("#page-changes-ui .bar .export"), "no Export button while a change is not sent");
  shared.server = startServer(pagePath);
  await until(async () => {
    const queue = JSON.parse((await request("GET", `${shared.url}api/changes`).catch(() => ({ text: "[]" }))).text);
    return queue.some((event) => event.kind === "comment" && event.target === "plan" && event.payload.text === text);
  }, 8000, "the comment made while the server was down in the queue");
  await until(async () => !/not sent/.test(await status(page)), 3000, "the status bar to drop not sent");
  check(!(await page.isVisible("#page-changes-ui .bar .export")), "the Export button stays though every change was sent");
  // a form value recorded on blur redraws the badges, and the click that caused the blur must still open its panel
  await page.evaluate(() => {
    const field = document.createElement("input");
    field.id = "form-owner";
    field.addEventListener("change", () => window.recordChange("data", "form", { path: "form.owner", value: field.value }));
    document.body.prepend(field);
  });
  await page.click('#page-changes-ui aside .close');
  await page.fill("#form-owner", "Kim");
  await page.click('#page-changes-ui .layer button[data-anchor="idea"]');
  await until(async () => (await page.textContent("#page-changes-ui aside .title").catch(() => "")) === "idea" && await page.isVisible("#page-changes-ui aside"),
    3000, "the badge clicked right after a form edit to open its panel");
  const forms = await until(async () => {
    const queue = JSON.parse((await request("GET", `${shared.url}api/changes`)).text).filter((event) => event.target === "form");
    return queue.length && queue;
  }, 3000, "the form value in the queue");
  check(forms.length === 1 && forms[0].payload.value === "Kim", `the queue holds ${JSON.stringify(forms)} for the form`);
  check(!shared.errors.length, `the page threw: ${shared.errors.join("; ")}`);
}

async function openBrowser() {
  const binary = browserBinary();
  if (!fs.existsSync(path.join(PLAYWRIGHT, "package.json")) || !binary || !fs.existsSync(binary)) {
    throw new Error("install playwright-core into /private/tmp/page-changes-playwright and its chromium-headless-shell");
  }
  return require(PLAYWRIGHT).chromium.launch({ executablePath: binary });
}

async function queueMode() {
  const pagePath = path.join(FOLDER, "page.html");
  let browser, server;
  try {
    fs.mkdirSync(FOLDER, { recursive: true });
    for (const name of ["page.html", "url.txt", "changes", "history"]) fs.rmSync(path.join(FOLDER, name), { recursive: true, force: true });
    fs.copyFileSync(path.join(ROOT, "assets", "diagram-page.html"), pagePath);
    browser = await openBrowser();
    server = startServer(pagePath);
    const line = await until(async () => server.lines.find((each) => each.startsWith("page-changes url: ")), 5000, "the url line");
    const url = line.slice("page-changes url: ".length);
    const page = await (await browser.newContext()).newPage();
    await page.goto(url);
    await until(async () => /server connected/.test(await status(page)), 5000, "the status bar to say server connected");
    await rename(page, "plan", "Plan B");
    await comment(page, "build", COMMENT);
    await until(async () => server.lines.find((each) => each.startsWith("page-changes pending")), (QUIET + 5) * 1000, "the pending line");
    const queue = JSON.parse((await request("GET", `${url}api/changes`)).text);
    check(queue.length === 2 && queue.filter((each) => each.kind === "data").length === 1 && queue.filter((each) => each.kind === "comment").length === 1,
      `the queue holds ${JSON.stringify(queue)}`);
    console.log(`queued 2 changes for ${pagePath}`);
    return 0;
  } catch (error) {
    console.log(`FAIL queue: ${error.message.split("\n")[0]}`);
    return 1;
  } finally {
    if (browser) await browser.close();
    if (server) await server.stop();
  }
}

async function verifyMode() {
  const pagePath = path.join(FOLDER, "page.html");
  let browser, server, failed = 0;
  const run = async (name, step) => {
    try { await step(); console.log(`PASS ${name}`); } catch (error) { failed += 1; console.log(`FAIL ${name}: ${error.message.split("\n")[0]}`); }
  };
  try {
    browser = await openBrowser();
    server = startServer(pagePath);
    const line = await until(async () => server.lines.find((each) => each.startsWith("page-changes url: ")), 5000, "the url line");
    const url = line.slice("page-changes url: ".length);
    const page = await (await browser.newContext()).newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(url);
    await until(async () => /server connected/.test(await status(page)), 5000, "the status bar to say server connected");
    const html = fs.readFileSync(pagePath, "utf8");
    const diagram = JSON.parse(html.match(BLOCK("page-data"))[2])["diagram-main"] || { nodes: [], edges: [] };
    const threads = JSON.parse(html.match(BLOCK("page-threads"))[2]).threads || {};
    const nodes = diagram.nodes || [];
    await run("rename", async () => {
      const plan = nodes.find((node) => node.id === "plan");
      check(plan && plan.label === "Plan B", `node plan is labelled ${plan && plan.label}`);
    });
    await run("new node", async () => {
      const added = nodes.find((node) => node.label === "Test");
      check(added, "no node is labelled Test");
      check((diagram.edges || []).some((edge) => edge[0] === "build" && edge[1] === added.id), `no edge from build to ${added.id}`);
    });
    await run("labels drawn", async () => {
      const labels = await page.$$eval("#diagram-canvas g[data-id] text", (items) => items.map((item) => item.textContent));
      check(labels.includes("Plan B") && labels.includes("Test"), `the page draws ${JSON.stringify(labels)}`);
    });
    await run("thread", async () => {
      const thread = Array.isArray(threads.build) ? threads.build : [];
      const asked = thread.find((entry) => entry.by === "person" && entry.text === COMMENT);
      check(asked, "the thread under build lacks the person's comment");
      const replies = thread.filter((entry) => entry.by === "session" && String(entry.replies_to) === String(asked.id));
      check(replies.length, `no session entry replies to ${asked.id}`);
      await page.click('#page-changes-ui .layer button[data-anchor="build"]');
      const shown = await until(async () => {
        const texts = await page.$$eval('#page-changes-ui aside li[data-by="session"] .text', (items) => items.map((item) => item.textContent));
        return replies.some((reply) => texts.includes(reply.text));
      }, 3000, "the reply in the panel");
      check(shown, "the panel does not show the reply");
    });
    await run("queue empty", async () => {
      const queue = JSON.parse((await request("GET", `${url}api/changes`)).text);
      check(queue.length === 0, `the queue still holds ${queue.length} changes`);
    });
    await run("applied", async () => {
      const applied = fs.readFileSync(path.join(FOLDER, "changes", "applied.jsonl"), "utf8").trim().split("\n").filter(Boolean).map((each) => JSON.parse(each));
      check(applied.some((each) => each.kind === "data") && applied.some((each) => each.kind === "comment"), `applied.jsonl holds ${applied.map((each) => each.id)}`);
    });
    await run("follows", async () => {
      const checked = python("check-page.py", pagePath);
      check(checked.stdout.trim() === "follows", `check-page.py printed: ${checked.stdout.trim()}`);
    });
    await run("runtime", async () => {
      const runtime = fs.readFileSync(path.join(ROOT, "assets", "page-runtime.js"), "utf8").trim();
      const open = html.indexOf("<!-- page-changes runtime -->");
      const close = html.indexOf("<!-- /page-changes runtime -->");
      check(open >= 0 && close > open && html.slice(open, close).includes(runtime), "page.html lacks the runtime between its markers");
    });
    await run("page errors", async () => check(!errors.length, `the page threw: ${errors.join("; ")}`));
  } catch (error) {
    failed += 1;
    console.log(`FAIL setup: ${error.message.split("\n")[0]}`);
  } finally {
    if (browser) await browser.close();
    if (server) await server.stop();
  }
  console.log(failed ? "FAIL" : "PASS");
  return failed ? 1 : 0;
}

async function main() {
  if (MODE === "--queue") return queueMode();
  if (MODE === "--verify") return verifyMode();
  const binary = browserBinary();
  if (!fs.existsSync(path.join(PLAYWRIGHT, "package.json")) || !binary || !fs.existsSync(binary)) {
    console.log(`FAIL setup: install playwright-core into /private/tmp/page-changes-playwright and its chromium-headless-shell`);
    return 1;
  }
  const { chromium } = require(PLAYWRIGHT);
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "page-changes-"));
  const shared = { pagePath: path.join(folder, "page.html"), errors: [] };
  fs.copyFileSync(path.join(ROOT, "assets", "diagram-page.html"), shared.pagePath);
  const browser = await chromium.launch({ executablePath: binary });
  shared.server = startServer(shared.pagePath);
  const steps = [
    ["a file", () => fileStep(browser, shared.pagePath)],
    ["b served", () => servedStep(browser, shared.server, shared)],
    ["c session", () => sessionStep(shared)],
    ["d refusals", () => refusalStep(shared.server, shared)],
    ["e outage", () => outageStep(shared)],
  ];
  let failed = 0;
  for (const [name, run] of steps) {
    try {
      await run();
      console.log(`PASS ${name}`);
    } catch (error) {
      failed += 1;
      console.log(`FAIL ${name}: ${error.message.split("\n")[0]}`);
    }
  }
  await browser.close();
  await shared.server.stop();
  fs.rmSync(folder, { recursive: true, force: true });
  console.log(failed ? "FAIL" : "PASS");
  return failed ? 1 : 0;
}

main().then((code) => process.exit(code), (error) => { console.log(`FAIL ${error.message}`); console.log("FAIL"); process.exit(1); });
