// What a runner's steps check and wait with: check throws its reason, same compares two values as JSON, until polls a
// probe every 100 ms until it gives a value or MS pass, sleep waits, python runs a script and keeps its output, and tags reads a
// skill's tag catalogue over the shared one, as its checker does.
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
const tags = (own) => JSON.parse(spawnSync("python3", ["-c", "import json, sys; sys.path.insert(0, sys.argv[1]); from contract_tags import catalogue; print(json.dumps(catalogue(sys.argv[2])))",
  __dirname, own], { encoding: "utf8" }).stdout);

module.exports = { check, same, until, sleep, python, tags };
