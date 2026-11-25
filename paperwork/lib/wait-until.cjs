// The waits and the check a relay run shares: sleep, a check that throws its reason, and until, which polls a probe
// every 100 ms until it gives a value or MS pass.
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

module.exports = { sleep, check, until };
