#!/usr/bin/env node
// Check every colour each example page of system and flow draws, and print `PASS <step>` or `FAIL <step>: <reasons>` per step, then
// PASS or FAIL.
//   tokens   each colour token of ../page-tokens.css stands under a comment citing a source its header lists.
//   cvd      the status tokens, and the group tokens, of each scheme are each 0.1 or more apart in OKLab, as seen and under protanopia,
//            deuteranopia and tritanopia simulated by Machado, Oliveira and Fernandes 2009 at severity 1, on linear sRGB.
//   literals no page holds a colour literal outside the tokens' own text.
//   <page> <width> <scheme>  once a level move ends, in a headless Chromium at 390 by 844 and 1200 by 800, light and dark, with the page as loaded, with the
//            search open on a query, and with a badge's card open: once with every token's colour swapped for one planted colour,
//            every colour drawn is that colour, so none comes from elsewhere; then with the tokens as written, every text is at 4.5:1
//            or more against what is behind it, and every badge, line and frame at 3:1 or more, a frame against both its sides. A
//            hairline drawn in the chrome's `--border` is not a frame of the drawing, what an opaque layer covers is not drawn, and a
//            part system dims while the reader keeps another record (`.dim`) is not measured.
//            Flow's diagram, which scrolls, is checked at each viewport-sized step of its scroll.
//
// usage: drive-page-colours.cjs
const fs = require("fs");
const path = require("path");
const { missing, launch } = require(path.join(__dirname, "..", "launch-browser.cjs"));

if (process.argv.length > 2) {
  console.error("usage: drive-page-colours.cjs");
  process.exit(2);
}
const PLUGIN = path.join(__dirname, "..", "..");
const TOKENS = path.join(PLUGIN, "lib", "page-tokens.css");
const SIZES = [[390, 844], [1200, 800]];
const PLANTED = "rgb(200, 40, 120)";
const pages = ["system", "flow"].flatMap((skill) => {
  const folder = path.join(PLUGIN, "skills", skill, "examples");
  return fs.existsSync(folder) ? fs.readdirSync(folder).sort().map((name) => path.join(folder, name, "page.html")).filter((file) => fs.existsSync(file)) : [];
});

// ---- the palette's arithmetic: OKLCH to linear sRGB, the simulated views and their OKLab distances ----
const MACHADO = {
  protanopia: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deuteranopia: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
  tritanopia: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
};
function linear([lightness, chroma, hue]) {
  const a = chroma * Math.cos(hue * Math.PI / 180), b = chroma * Math.sin(hue * Math.PI / 180);
  const l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3, s = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s].map((v) => Math.min(1, Math.max(0, v)));
}
function oklab([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b), s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
const simulated = (rgb, matrix) => matrix.map((row) => Math.min(1, Math.max(0, row.reduce((sum, weight, k) => sum + weight * rgb[k], 0))));

// The tokens of each scheme's block, each [name, value, the comment above it], and the source tags the header lists.
function tokens() {
  const text = fs.existsSync(TOKENS) ? fs.readFileSync(TOKENS, "utf8") : "", header = (text.match(/^\/\*[\s\S]*?\*\//) || [""])[0];
  const sources = new Set([...header.matchAll(/^\s*(?:Sources:\s*)?(\[[a-z-]+\])\s/gm)].map((match) => match[1]));
  const blocks = { light: text.slice(header.length).split("@media")[0], dark: text.split("prefers-color-scheme: dark")[1] || "" };
  const schemes = {};
  for (const [scheme, block] of Object.entries(blocks)) {
    let comment = "";
    schemes[scheme] = [];
    for (const match of block.matchAll(/\/\*([\s\S]*?)\*\/|(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
      if (match[1] !== undefined) comment = match[1];
      else schemes[scheme].push([match[2], match[3].trim(), comment]);
    }
  }
  return { text, sources, schemes };
}
const colourful = (value) => /oklch\(|var\(--|color-mix\(/.test(value);

function tokenSources({ sources, schemes }) {
  const found = [];
  if (!fs.existsSync(TOKENS)) return ["lib/page-tokens.css is missing"];
  if (!sources.size) found.push("the tokens' header lists no source");
  for (const [scheme, list] of Object.entries(schemes)) for (const [name, value, comment] of list.filter(([, value]) => colourful(value))) {
    const cited = comment.match(/\[[a-z-]+\]/g) || [];
    if (!cited.length) found.push(`${scheme} ${name} stands under no comment citing a source`);
    for (const tag of cited) if (!sources.has(tag)) found.push(`${scheme} ${name} cites ${tag}, which the header does not list`);
  }
  return found;
}

function apart({ schemes }) {
  const found = [];
  for (const [scheme, list] of Object.entries(schemes)) for (const set of ["status", "group"]) {
    const members = list.filter(([name]) => name.startsWith(`--${set}-`) && name !== "--status-glyph").map(([name, value]) => {
      const parts = (value.match(/^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)$/) || []).slice(1).map(Number);
      return [name, parts.length === 3 ? linear(parts) : null];
    });
    if (members.length < 2) found.push(`${scheme} holds ${members.length} ${set} token`);
    for (const [name, rgb] of members) if (!rgb) found.push(`${scheme} ${name} is no plain oklch()`);
    for (let a = 0; a < members.length; a++) for (let b = a + 1; b < members.length; b++) {
      if (!members[a][1] || !members[b][1]) continue;
      for (const [view, matrix] of [["as seen", null], ...Object.entries(MACHADO)]) {
        const [x, y] = [members[a][1], members[b][1]].map((rgb) => oklab(matrix ? simulated(rgb, matrix) : rgb));
        const distance = Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]);
        if (distance < 0.1) found.push(`${scheme} ${members[a][0]} and ${members[b][0]} are ${distance.toFixed(3)} apart ${view === "as seen" ? view : "under " + view}`);
      }
    }
  }
  return found;
}

const NAMED = "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen canvastext buttontext buttonface linktext highlight";
const NAMES = new Set(NAMED.split(" "));
function literals(text) {
  const found = [];
  for (const page of pages) {
    const own = fs.readFileSync(page, "utf8").split(text.trim()).join(""), name = path.relative(PLUGIN, page);
    const styled = [...own.matchAll(/<style[^>]*>([\s\S]*?)<\/style>|<script(?![^>]*application\/json)[^>]*>([\s\S]*?)<\/script>|\sstyle="([^"]*)"/g)].map((match) => match[1] || match[2] || match[3] || "").join("\n");
    const seen = [...styled.matchAll(/\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^)]*\)/g), ...styled.matchAll(/(?::\s*|["'])#[0-9a-fA-F]{3,8}\b(?![-\w])/g)].map((match) => match[0]);
    for (const match of styled.matchAll(/\b(?:color|background(?:-color)?|fill|stroke|border(?:-[a-z]+)*|outline(?:-color)?|box-shadow|text-shadow|caret-color|accent-color|stop-color)\s*:\s*([^;{}\n"']*)/g))
      seen.push(...match[1].toLowerCase().split(/[^a-z]+/).filter((word) => NAMES.has(word)));
    for (const match of styled.matchAll(/["'](?:fill|stroke|color)["']\s*,\s*["']([a-z]+)["']/g)) if (NAMES.has(match[1])) seen.push(match[1]);
    if (seen.length) found.push(`${name} holds ${[...new Set(seen)].slice(0, 5).join(", ")}`);
  }
  return found;
}

// ---- in the page: what is drawn, and the colour behind each point ----
function measure({ planted, mode }) {
  const canvas = document.createElement("canvas"), context = canvas.getContext("2d", { willReadFrequently: true }), cache = new Map();
  canvas.width = canvas.height = 1;
  const rgba = (value) => { // a computed colour as [r, g, b, a], each 0..1
    if (!cache.has(value)) {
      context.clearRect(0, 0, 1, 1); context.fillStyle = "rgba(0, 0, 0, 0)"; context.fillStyle = value; context.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = context.getImageData(0, 0, 1, 1).data;
      cache.set(value, [r / 255, g / 255, b / 255, a / 255]);
    }
    return cache.get(value);
  };
  const over = ([r, g, b, a], [br, bg, bb]) => [r * a + br * (1 - a), g * a + bg * (1 - a), b * a + bb * (1 - a), 1];
  const channel = (v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  const ratio = (x, y) => { const [low, high] = [luminance(x), luminance(y)].sort((a, b) => a - b); return (high + 0.05) / (low + 0.05); };
  const fade = (element) => { let alpha = 1; for (let one = element; one && one.nodeType === 1; one = one.parentElement) alpha *= Number(getComputedStyle(one).opacity); return alpha; };
  const svg = (element) => element instanceof SVGElement;
  const paint = (element) => { // what the element lays down under what it holds, as [r, g, b, a]
    const style = getComputedStyle(element);
    if (svg(element)) {
      if (!(element instanceof SVGGeometryElement) || element.tagName === "line" || style.fill === "none" || style.fill.startsWith("url")) return [0, 0, 0, 0];
      const [r, g, b, a] = rgba(style.fill);
      return [r, g, b, a * Number(style.fillOpacity) * fade(element)];
    }
    const [r, g, b, a] = rgba(style.backgroundColor);
    return [r, g, b, a * fade(element)];
  };
  const name = (element) => {
    const label = element.id ? "#" + element.id : (element.getAttribute("class") || "").split(" ").filter(Boolean).map((one) => "." + one).join("");
    const holder = element.closest("[data-id]");
    return `${element.tagName.toLowerCase()}${label}${holder ? `[${holder.dataset.id}]` : ""}${element.textContent.trim() ? ` "${element.textContent.trim().slice(0, 24)}"` : ""}`;
  };
  const hex = (colour) => "#" + colour.slice(0, 3).map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
  const inside = (x, y) => x >= 0 && y >= 0 && x < innerWidth && y < innerHeight;
  // The colour behind point x, y beneath the element, or null when an opaque layer that is not the element's covers it there.
  const behind = (element, x, y, own) => {
    const stack = document.elementsFromPoint(x, y), at = stack.indexOf(element);
    if (at < 0) return null;
    for (const above of stack.slice(0, at)) if (!element.contains(above) && paint(above)[3] > 0.05) return null;
    const scheme = matchMedia("(prefers-color-scheme: dark)").matches ? [0.07, 0.07, 0.07, 1] : [1, 1, 1, 1];
    return stack.slice(own ? at : at + 1).reverse().filter((one) => !element.contains(one) || one === element).reduce((under, one) => (one === element && !own) ? under : over(paint(one), under), scheme);
  };
  const border = rgba(getComputedStyle(document.body).getPropertyValue("--border").trim() || "transparent");
  const chrome = (value) => { const colour = rgba(value); return colour.every((v, k) => Math.abs(v - border[k]) < 0.02); };
  const shown = (element) => element.checkVisibility({ visibilityProperty: true }) && !element.closest("marker, defs") && fade(element) > 0.05;
  const all = [...document.querySelectorAll("body *")].filter((element) => element.closest("marker, defs") || shown(element));
  const found = [], measured = new Set();
  const say = (key, line) => { if (!measured.has(key)) { measured.add(key); found.push(line); } };

  if (mode === "planted") {
    const target = rgba(planted);
    const tested = (element, property, value) => {
      if (!value || value === "none" || value.startsWith("url") || value === "currentcolor") return;
      for (const colour of value.match(/(?:rgba?|oklab|oklch|lab|lch|color)\([^)]*\)|#[0-9a-f]{3,8}\b/gi) || [value]) {
        const [r, g, b, a] = rgba(colour);
        if (a * 255 < 6) continue;
        const slack = Math.max(0.02, 1.5 / (a * 255));
        if ([r, g, b].some((v, k) => Math.abs(v - target[k]) > slack)) say(`${name(element)} ${property}`, `${name(element)} draws ${property} ${colour}`);
      }
    };
    for (const element of all) {
      const style = getComputedStyle(element);
      if (svg(element)) {
        if ((element instanceof SVGGeometryElement && element.tagName !== "line") || element.tagName === "text") { tested(element, "fill", style.fill); if (Number.parseFloat(style.strokeWidth) > 0) tested(element, "stroke", style.stroke); }
        if (element.tagName === "text" || element.tagName === "tspan") tested(element, "fill", style.fill);
        continue;
      }
      if ([...element.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim())) tested(element, "color", style.color);
      tested(element, "background-color", style.backgroundColor);
      for (const side of ["Top", "Right", "Bottom", "Left"]) if (Number.parseFloat(style[`border${side}Width`]) > 0 && style[`border${side}Style`] !== "none") tested(element, "border colour", style[`border${side}Color`]);
      if (style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) tested(element, "outline", style.outlineColor);
      if (style.boxShadow !== "none") tested(element, "shadow", style.boxShadow);
      if (style.textDecorationLine !== "none") tested(element, "underline", style.textDecorationColor);
    }
    return found;
  }

  for (const element of all.filter((one) => shown(one) && !one.closest(".dim"))) {
    const style = getComputedStyle(element);
    // text, against what is behind it
    for (const node of [...element.childNodes].filter((one) => one.nodeType === 3 && one.textContent.trim())) {
      const range = document.createRange(); range.selectNodeContents(node);
      const box = [...range.getClientRects()].find((rect) => rect.width > 1 && rect.height > 1 && inside(rect.left + rect.width / 2, rect.top + rect.height / 2));
      if (!box) continue;
      const x = box.left + box.width / 2, y = box.top + box.height / 2, under = behind(element, x, y, true);
      if (!under) continue;
      const [r, g, b, a] = rgba(svg(element) ? style.fill : style.color), ink = over([r, g, b, a * fade(element)], under), seen = ratio(ink, under);
      if (seen < 4.5) say(`text ${name(element)}`, `text ${name(element)} at ${seen.toFixed(2)}:1, ${hex(ink)} on ${hex(under)}`);
    }
    // a badge, against what is behind it
    if (element.matches("button.claim")) {
      const box = element.getBoundingClientRect(), x = box.left + box.width / 2, y = box.top + box.height / 2;
      const under = inside(x, y) && behind(element, x, y, false);
      if (under) { const seen = ratio(over(paint(element), under), under); if (seen < 3) say(`badge ${name(element)}`, `badge ${name(element)} at ${seen.toFixed(2)}:1 on ${hex(under)}`); }
    }
    // a line, against what is behind it at the first point of it in sight
    if (element instanceof SVGGeometryElement && style.stroke !== "none" && !style.stroke.startsWith("url") && Number.parseFloat(style.strokeWidth) > 0 && rgba(style.stroke)[3] * Number(style.strokeOpacity) > 0.05 && !chrome(style.stroke)) {
      const length = element.getTotalLength(), matrix = element.getScreenCTM();
      for (const t of [0.5, 0.3, 0.7, 0.15, 0.85]) {
        const local = element.getPointAtLength(length * t), point = new DOMPoint(local.x, local.y).matrixTransform(matrix);
        const under = inside(point.x, point.y) && behind(element, point.x, point.y, false);
        if (!under) continue;
        const [r, g, b, a] = rgba(style.stroke), seen = ratio(over([r, g, b, a * Number(style.strokeOpacity) * fade(element)], under), under);
        if (seen < 3) say(`line ${name(element)}`, `line ${name(element)} at ${seen.toFixed(2)}:1 on ${hex(under)} at ${Math.round(point.x)}, ${Math.round(point.y)}`);
        break;
      }
    }
    // a frame, against the colour outside it and its own fill inside it
    if (!svg(element)) {
      const side = ["Left", "Top", "Right", "Bottom"].find((one) => Number.parseFloat(style[`border${one}Width`]) >= 1 && style[`border${one}Style`] !== "none" && rgba(style[`border${one}Color`])[3] > 0.05 && !chrome(style[`border${one}Color`]));
      if (side) {
        const box = element.getBoundingClientRect(), width = Number.parseFloat(style[`border${side}Width`]);
        const [x, y, dx, dy] = { Left: [box.left, box.top + box.height / 2, -1, 0], Right: [box.right, box.top + box.height / 2, 1, 0], Top: [box.left + box.width / 2, box.top, 0, -1], Bottom: [box.left + box.width / 2, box.bottom, 0, 1] }[side];
        const outside = inside(x + dx * 1.5, y + dy * 1.5) && behind(element, x + dx * 1.5, y + dy * 1.5, false);
        const within = inside(x - dx * (width + 1.5), y - dy * (width + 1.5)) && behind(element, x - dx * (width + 1.5), y - dy * (width + 1.5), true);
        if (outside && within) {
          const [r, g, b, a] = rgba(style[`border${side}Color`]), frame = over([r, g, b, a * fade(element)], outside);
          const seen = Math.min(ratio(frame, outside), ratio(over([r, g, b, a * fade(element)], within), within));
          if (seen < 3) say(`frame ${name(element)}`, `frame ${name(element)} at ${seen.toFixed(2)}:1`);
        }
      }
    }
  }
  return found;
}

async function drive(browser, page, [width, height], scheme, planted, overrides) {
  const tab = await browser.newPage({ viewport: { width, height }, colorScheme: scheme }), faults = [], found = [];
  tab.on("pageerror", (error) => faults.push(String(error)));
  await tab.goto("file://" + page);
  await tab.waitForTimeout(700);
  await tab.addStyleTag({ content: "* { pointer-events: auto !important; transition: none !important; animation: none !important; }" + (planted ? overrides : "") });
  const run = async () => found.push(...await tab.evaluate(measure, { planted: PLANTED, mode: planted ? "planted" : "ratios" }));
  const steps = await tab.evaluate(() => { const diagram = document.getElementById("diagram"); if (!diagram || getComputedStyle(diagram).overflow === "hidden") return [[0, 0]];
    const xs = [], ys = []; for (let x = 0; x < diagram.scrollWidth; x += diagram.clientWidth) xs.push(x); for (let y = 0; y < diagram.scrollHeight; y += diagram.clientHeight) ys.push(y);
    return xs.flatMap((x) => ys.map((y) => [x, y])); });
  for (const [x, y] of steps) { await tab.evaluate(([x, y]) => document.getElementById("diagram") && document.getElementById("diagram").scrollTo(x, y), [x, y]); await tab.waitForTimeout(50); await run(); }
  await tab.evaluate(() => document.getElementById("diagram") && document.getElementById("diagram").scrollTo(0, 0));
  await tab.keyboard.press("/");
  await tab.keyboard.type("a");
  await tab.waitForTimeout(300);
  await run();
  await tab.keyboard.press("Escape");
  await tab.waitForTimeout(200);
  const badge = await tab.evaluate(() => { const one = [...document.querySelectorAll("button.claim")].find((element) => { const box = element.getBoundingClientRect(); return box.width && box.left >= 0 && box.top >= 0 && box.right < innerWidth && box.bottom < innerHeight; });
    if (!one) return null; const box = one.getBoundingClientRect(); return [box.left + box.width / 2, box.top + box.height / 2]; });
  if (badge) {
    await tab.mouse.click(...badge);
    await tab.waitForTimeout(300);
    await tab.waitForFunction(() => !document.getAnimations().some((one) => one.playState === "running"), null, { timeout: 8000 }).catch(() => found.push("a level move still runs 8 s after a badge's click"));
    await tab.waitForTimeout(200);
    await run();
  }
  if (faults.length) found.push(`the page threw ${faults[0]}`);
  await tab.close();
  return [...new Set(found)];
}

(async () => {
  const read = tokens(), checks = [["tokens", tokenSources(read)], ["cvd", apart(read)], ["literals", literals(read.text)]];
  if (!pages.length) checks.push(["examples", ["no example page of system or flow"]]);
  let failed = false;
  for (const [step, reasons] of checks) { failed = failed || reasons.length > 0; console.log(reasons.length ? `FAIL ${step}: ${reasons.join("; ")}` : `PASS ${step}`); }
  if (missing()) { console.log(`FAIL browser: ${missing()}\nFAIL`); process.exit(1); }
  const overrides = ":root, :root:root { " + Object.values(read.schemes).flat().filter(([, value]) => colourful(value))
    .map(([name, value]) => `${name}: ${/^0 |^0px /.test(value) || /\dpx /.test(value) ? value.replace(/oklch\([^)]*\)/g, PLANTED) : PLANTED} !important;`).join(" ") + " }";
  const browser = await launch();
  for (const page of pages) for (const size of SIZES) for (const scheme of ["light", "dark"]) {
    const step = `${path.relative(PLUGIN, page)} ${size[0]} ${scheme}`;
    try {
      const reasons = [...(await drive(browser, page, size, scheme, true, overrides)).map((line) => `not a token: ${line}`), ...await drive(browser, page, size, scheme, false, overrides)];
      failed = failed || reasons.length > 0;
      console.log(reasons.length ? `FAIL ${step}: ${reasons.length} — ${reasons.slice(0, 8).join("; ")}` : `PASS ${step}`);
    } catch (error) { failed = true; console.log(`FAIL ${step}: ${error.message.split("\n")[0]}`); }
  }
  await browser.close();
  console.log(failed ? "FAIL" : "PASS");
  process.exit(failed ? 1 : 0);
})();
