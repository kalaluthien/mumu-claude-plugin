// What a runner's steps check and wait with: check throws its reason, same compares two values as JSON, until polls a
// probe every 100 ms until it gives a value or MS pass, sleep waits, and python runs a script and keeps its output.
const { spawnSync } = require("child_process");

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

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const python = (script, ...args) => spawnSync("python3", [script, ...args], { encoding: "utf8" });

module.exports = { check, same, until, sleep, python };
