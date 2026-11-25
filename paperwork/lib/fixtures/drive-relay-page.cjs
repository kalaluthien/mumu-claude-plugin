#!/usr/bin/env node
// Start a relay server by a command, then drive its page in a headless Chromium as a person and a session would: comment on an anchor,
// see the comment reach the queue and one pending line printed, write the page file and ack the comment, and see the open page reload
// with the queue empty. It prints `PASS relay loop` or `FAIL relay loop: <reason>`.
//
// usage: drive-relay-page.cjs <page.html> <anchor> <command>...
const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { spawn } = require("child_process");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));
const { sleep, check, until } = require(path.join(__dirname, "..", "check-step.cjs"));
const { request } = require(path.join(__dirname, "..", "send-request.cjs"));

const [pageFile, anchor, ...command] = process.argv.slice(2);
if (!pageFile || !anchor || !command.length) {
  console.error("usage: drive-relay-page.cjs <page.html> <anchor> <command>...");
  process.exit(2);
}
const COMMENT = "Say this idea in fewer words";

async function main() {
  if (missing()) return `${missing()}`;
  const server = spawn(command[0], command.slice(1), { stdio: ["ignore", "pipe", "pipe"] });
  const lines = [];
  readline.createInterface({ input: server.stdout }).on("line", (line) => lines.push(line));
  let errors = "";
  server.stderr.on("data", (chunk) => { errors += chunk; });
  const browser = await launch();
  try {
    const url = await until(async () => (lines.find((line) => line.startsWith("relay url: ")) || "").slice(11), 5000, `the server's url line${errors ? `; stderr: ${errors}` : ""}`);
    const page = await browser.newPage();
    await page.goto(url);
    await until(async () => /connected/.test(await page.textContent("#relay-ui .bar .state")), 5000, "the page to say it is connected");
    await page.click(`#relay-ui .layer button[data-anchor="${anchor}"]`);
    await page.fill("#relay-ui aside textarea", COMMENT);
    await page.click("#relay-ui aside button[type=submit]");
    const pending = await until(async () => {
      const queued = JSON.parse((await request("GET", url + "api/changes")).text);
      return queued.length === 1 && queued[0].target === anchor && queued[0].payload.text === COMMENT ? queued : null;
    }, 5000, "the comment in the queue");
    await until(async () => lines.filter((line) => line.startsWith("relay pending 1:")).length === 1, 5000, "one pending line");
    const origin = new URL(url).origin;
    const html = fs.readFileSync(pageFile, "utf8");
    check(html.includes("An idea<"), "the page file holds no `An idea` to edit");
    fs.writeFileSync(pageFile, html.replace("An idea<", "A short idea<"));
    const acked = await request("POST", url + "api/changes/ack", { headers: { Origin: origin, "Content-Type": "application/json" }, body: JSON.stringify({ ids: [pending[0].id] }) });
    check(acked.status === 200 && JSON.parse(acked.text).acked === 1, `the ack answered ${acked.status} ${acked.text}`);
    await until(async () => (await page.textContent(`[data-id="${anchor}"]`)) === "A short idea", 8000, "the open page to reload with the edit");
    check(JSON.parse((await request("GET", url + "api/changes")).text).length === 0, "the queue is not empty after the ack");
    return "";
  } finally {
    await browser.close();
    server.kill();
  }
}

main().then((reason) => {
  console.log(reason ? `FAIL relay loop: ${reason}` : "PASS relay loop");
  process.exit(reason ? 1 : 0);
}, (error) => {
  console.log(`FAIL relay loop: ${error.message.split("\n")[0]}`);
  process.exit(1);
});
