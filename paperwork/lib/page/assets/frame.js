const THEME_KEY = "paperwork-theme";
const themeRoot = document.documentElement;
const systemDark = matchMedia("(prefers-color-scheme: dark)");

// A page opened from a file may be refused storage; the theme then lasts until it closes.
function savedTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch { return null; }
}
function saveTheme(theme) {
  try { localStorage.setItem(THEME_KEY, theme); } catch { /* the choice lasts until the page closes */ }
}
function systemTheme() {
  return systemDark.matches ? "dark" : "light";
}
// Runs in the head, so a saved dark theme never flashes light.
themeRoot.dataset.theme = savedTheme() || systemTheme();

function fallbackCopy(text) {
  const area = document.createElement("textarea");
  area.value = text;
  document.body.append(area);
  area.select();
  const done = document.execCommand("copy");
  area.remove();
  return done;
}

function startNavigation() {
  const nav = document.getElementById("frame-nav");
  const menu = document.getElementById("frame-menu");
  const links = [...nav.querySelectorAll("a")];
  const sections = links.map(link => document.getElementById(link.getAttribute("href").slice(1)));
  const showMenu = open => {
    nav.classList.toggle("open", open);
    menu.setAttribute("aria-expanded", open);
  };
  const markCurrent = () => {
    const current = sections.filter(section => section.getBoundingClientRect().top <= 96).pop() || sections[0];
    links.forEach((link, i) => {
      link.classList.toggle("selected", sections[i] === current);
      if (sections[i] === current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  };
  menu.addEventListener("click", () => showMenu(!nav.classList.contains("open")));
  links.forEach(link => link.addEventListener("click", () => showMenu(false)));
  addEventListener("keydown", event => { if (event.key === "Escape") showMenu(false); });
  addEventListener("scroll", markCurrent, {passive: true});
  markCurrent();
}

// copy returns the text the copy icon puts on the clipboard; reset puts the page back as it opened.
function start({copy, reset}) {
  const status = document.getElementById("frame-status");
  const say = message => {
    status.textContent = message;
    setTimeout(() => { if (status.textContent === message) status.textContent = ""; }, 3000);
  };
  document.getElementById("frame-copy").addEventListener("click", async () => {
    const text = copy();
    try { await navigator.clipboard.writeText(text); say("Copied"); }
    catch { say(fallbackCopy(text) ? "Copied" : "Copy failed: select the text instead"); }
  });
  document.getElementById("frame-reset").addEventListener("click", () => { reset(); say("Reset"); });
  document.getElementById("frame-theme").addEventListener("click", () => {
    themeRoot.dataset.theme = themeRoot.dataset.theme === "dark" ? "light" : "dark";
    saveTheme(themeRoot.dataset.theme);
  });
  systemDark.addEventListener("change", () => { if (!savedTheme()) themeRoot.dataset.theme = systemTheme(); });
  // Paper is light whatever the screen shows.
  addEventListener("beforeprint", () => { themeRoot.dataset.printed = themeRoot.dataset.theme; themeRoot.dataset.theme = "light"; });
  addEventListener("afterprint", () => { themeRoot.dataset.theme = themeRoot.dataset.printed; });
  startNavigation();
}
