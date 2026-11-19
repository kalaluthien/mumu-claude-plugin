// Start the browser a page check drives: the newest headless shell Playwright installed, else the installed Google
// Chrome, run headless with a profile of its own, so a machine whose only browser is Chrome runs the checks too.
// Playwright itself is loaded from /private/tmp/relay-playwright/node_modules/playwright-core.
const fs = require("fs");
const os = require("os");
const path = require("path");

const PLAYWRIGHT = "/private/tmp/relay-playwright/node_modules/playwright-core";

function headlessShell() {
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  const shells = fs.existsSync(cache) ? fs.readdirSync(cache).filter((name) => name.startsWith("chromium_headless_shell-")).sort() : [];
  const binary = shells.length ? path.join(cache, shells[shells.length - 1], "chrome-headless-shell-mac-arm64/chrome-headless-shell") : null;
  return binary && fs.existsSync(binary) ? binary : null;
}

// What keeps a browser from starting before any is tried, or "".
const missing = () => fs.existsSync(path.join(PLAYWRIGHT, "package.json")) ? "" : "install playwright-core into /private/tmp/relay-playwright";

async function launch() {
  const binary = headlessShell();
  try {
    return await require(PLAYWRIGHT).chromium.launch(binary ? { executablePath: binary } : { channel: "chrome" });
  } catch (error) {
    throw new Error(error.message.split("\n")[0] + (binary ? "" : " (no headless shell, so the installed Google Chrome was tried)"));
  }
}

module.exports = { missing, launch };
