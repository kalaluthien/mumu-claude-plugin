#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["playwright"]
# ///
"""Check a page at 390 and 1200 px in the installed Chrome, and save its full-page captures.

usage: check-page.py <page.html> [--shots DIR]

Exit 0 and a last line `ok` when, at both widths, the page does not scroll sideways, no element but one inside a
scroll box (`.scroll`, `pre`) runs past the right edge, no drawing needs a sideways scroll to be seen whole, no text is under 12 px, no text
in a drawing shows under 10 px tall or is cut at the drawing's edge, and no script throws.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

WIDTHS = (390, 1200)

PROBE = """() => {
  const bad = [], W = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth > W + 1) bad.push(`the page scrolls sideways (${document.documentElement.scrollWidth} px wide)`);
  for (const e of document.querySelectorAll('body *')) {
    if (e.closest('.scroll, pre, svg, textarea')) continue;
    const r = e.getBoundingClientRect();
    if (r.width && r.right > W + 1) bad.push(`<${e.tagName.toLowerCase()}${e.className ? '.' + e.className : ''}> runs ${Math.round(r.right - W)} px past the edge`);
    const t = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (t && parseFloat(getComputedStyle(e).fontSize) < 12) bad.push(`<${e.tagName.toLowerCase()}> text is under 12 px`);
  }
  for (const e of document.querySelectorAll('svg text')) {   // a drawing scaled down to the phone shrinks its text with it
    const h = e.getBoundingClientRect().height;
    if (h && h < 10 && e.textContent.trim()) bad.push(`text in a drawing shows under 10 px tall: "${e.textContent.trim().slice(0, 20)}"`);
    const r = e.getBoundingClientRect(), s = e.ownerSVGElement.getBoundingClientRect();
    if (r.width && (r.right > s.right + 1 || r.left < s.left - 1)) bad.push(`text in a drawing is cut at its edge: "${e.textContent.trim().slice(0, 20)}"`);
  }
  for (const svg of document.querySelectorAll('svg:not(svg svg)')) {   // a figure seen only by scrolling sideways is not seen whole
    for (let a = svg.parentElement; a && a !== document.body; a = a.parentElement)
      if (a.scrollWidth > a.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(a).overflowX)) { bad.push(`a drawing needs a sideways scroll (${Math.round(svg.getBoundingClientRect().width)} px in ${a.clientWidth} px)`); break; }
  }
  return [...new Set(bad)].slice(0, 20);
}"""


async def check(page_path, shots):
    problems = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        for w in WIDTHS:
            page = await browser.new_page(viewport={"width": w, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(page_path.resolve().as_uri())
            await page.wait_for_timeout(300)
            problems += [f"{w} px: {b}" for b in await page.evaluate(PROBE)]
            problems += [f"{w} px: a script throws: {e}" for e in errors]
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(shots / f"{page_path.stem}-{w}.png"), full_page=True)
            await page.close()
        await browser.close()
    return problems


def main(args):
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    shots = pathlib.Path(args[args.index("--shots") + 1]) if "--shots" in args else None
    problems = asyncio.run(check(pathlib.Path(args[0]), shots))
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
