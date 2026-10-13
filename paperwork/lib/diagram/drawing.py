"""Drawing checks for a built zoom diagram, at 390 and 1200 px in light and dark (needs Playwright and the installed Chrome).

fits: no sideways page scroll; each partition drawn as one block; drawn text at least 9 px on a phone (the board
scrolls sideways inside its card rather than shrink further); on every level no node label wider than its node,
no edge label on a node, another label or another edge, no edge through a node it does not join, no two edges from different sources
sharing a stretch of line.
"""
import asyncio
import json
import pathlib

from playwright.async_api import async_playwright

MIN_PX = 9.0

LAYOUT = """async () => {
  const z = window.zd, root = document.getElementById('zd'), bad = [];
  const ids = [...root.querySelectorAll('[data-l]')].map(b => b.dataset.l);
  const R = e => ({x: +e.getAttribute('x'), y: +e.getAttribute('y'), w: +e.getAttribute('width'), h: +e.getAttribute('height')});
  const hit = (a, b, m) => a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m;
  const inside = (p, b, m) => p.x > b.x + m && p.x < b.x + b.w - m && p.y > b.y + m && p.y < b.y + b.h - m;
  for (const id of ids) {
    z.goto(id); await new Promise(r => setTimeout(r, 30));
    const nodes = [...root.querySelectorAll('.zd-canvas .node')].map(g => ({id: g.dataset.id, p: g.dataset.p || '', b: R(g.querySelector('.n-fill')), t: g.querySelector('.n-lab')}));
    const edges = [...root.querySelectorAll('.zd-canvas .edge')].map(g => {
      const [from, to] = g.dataset.key.split(':')[1].split('>'), path = g.querySelector('.e-hit'), L = path.getTotalLength(), pts = [];
      for (let s = 8; s < L - 8; s += 4) pts.push(path.getPointAtLength(s));
      const pl = g.querySelector('.e-plate');
      return {key: g.dataset.key, from, to, pts, plate: pl ? R(pl) : null};
    });
    for (const n of nodes) if (n.t.getBBox().width > n.b.w - 10) bad.push(`${id}: label of ${n.id} overflows its node`);
    for (const g of root.querySelectorAll('.zd-canvas .part')) {   // a partition draws as one block: no other partition's node inside it
      const bb = g.querySelector('.p-ink').getBBox(), p = {x: bb.x, y: bb.y, w: bb.width, h: bb.height};
      for (const n of nodes) if (n.p !== g.dataset.p && hit(p, n.b, -4)) bad.push(`${id}: ${n.id} sits inside partition ${g.dataset.p}; make each partition one block`);
    }
    for (const e of edges) {
      for (const n of nodes) {
        if (e.plate && hit(e.plate, n.b, 1)) bad.push(`${id}: label of ${e.key} touches node ${n.id}`);
        if (n.id !== e.from && n.id !== e.to && e.pts.some(p => inside(p, n.b, 3))) bad.push(`${id}: ${e.key} runs through ${n.id}`);
      }
      for (const f of edges) if (f.key > e.key && f.from !== e.from) {  // a fork from one source may share its trunk
        const near = p => nodes.some(n => hit({x: p.x, y: p.y, w: 0, h: 0}, n.b, 12));
        let run = 0, worst = 0;
        for (const p of e.pts) {
          const shared = !near(p) && f.pts.some(q => Math.hypot(p.x - q.x, p.y - q.y) < 3);
          run = shared ? run + 1 : 0; worst = Math.max(worst, run);
        }
        if (worst >= 5) bad.push(`${id}: ${e.key} and ${f.key} share a stretch of line`);
      }
      for (const f of edges) if (f !== e && e.plate) {
        if (f.plate && f.key > e.key && hit(e.plate, f.plate, 1)) bad.push(`${id}: labels of ${e.key} and ${f.key} overlap`);
        if (f.pts.some(p => inside(p, e.plate, 0.5))) bad.push(`${id}: label of ${e.key} sits on ${f.key}`);
      }
    }
  }
  z.goto(ids[0]);
  return [...new Set(bad)];
}"""

TEXT = """() => { let m = 99; document.querySelectorAll('svg text').forEach(t => {
  const s = t.ownerSVGElement, k = s.getBoundingClientRect().width / s.viewBox.baseVal.width;
  if (t.getBBox().width) m = Math.min(m, parseFloat(getComputedStyle(t).fontSize) * k); }); return m; }"""


async def _check(path, shots=None, font_css=None):
    url, problems = pathlib.Path(path).resolve().as_uri(), []
    css = pathlib.Path(font_css).read_text() if font_css else None
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        for width in (390, 1200):
            for scheme in ("light", "dark"):
                tag = f"{width}px {scheme}"
                page = await browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
                if css:   # offline machines: supply the sans face, since fits depends on it
                    await page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent=" + json.dumps(css) + ";document.head.appendChild(s);});")
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                await page.goto(url)
                await page.wait_for_timeout(400)
                await page.evaluate("document.fonts ? document.fonts.ready.then(() => 1) : 1")
                await page.wait_for_timeout(200)
                if await page.evaluate("document.documentElement.scrollWidth") > width:
                    problems.append(f"fits: {tag} scrolls sideways")
                if width < 900:
                    if (px := await page.evaluate(TEXT)) < MIN_PX:
                        problems.append(f"fits: {tag} text {px:.1f}px < {MIN_PX}")
                if shots:   # every level, for the critic's pass
                    pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
                    for lid in await page.evaluate("[...document.querySelectorAll('#zd [data-l]')].map(b => b.dataset.l)"):
                        await page.evaluate(f"window.zd.goto({json.dumps(lid)})")
                        await page.wait_for_timeout(450)
                        await page.screenshot(path=f"{shots}/{lid}-{width}-{scheme}.png", full_page=True)
                    await page.evaluate("window.zd.goto(window.zd.state.level)")
                problems += [f"fits: {tag} {x}" for x in await page.evaluate(LAYOUT)]
                problems += [f"error: {tag} {e}" for e in errors]
        await browser.close()
    return sorted(set(problems))


def check(path, shots=None, font_css=None):
    return asyncio.run(_check(path, shots, font_css))
