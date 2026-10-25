import json, os, re
from .plan import Plan, PlanError
from .dom import esc

# ---------------------------------------------------------------- rendered QA: shared in-page checks


LS_JS = """window.__ls=[];try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){if(!e.hadRecentInput&&e.value>0.001)window.__ls.push({v:e.value,nodes:(e.sources||[]).map(function(s){return s.node})})})}).observe({type:'layout-shift',buffered:true})}catch(e){}"""
CHECK_JS = r"""() => { if (window.__bc) return;
 const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', {willReadFrequently: true});
 const col = s => { cx.clearRect(0,0,1,1); cx.fillStyle = 'rgba(0,0,0,0)'; cx.fillStyle = s; cx.fillRect(0,0,1,1); const d = cx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2],d[3]/255]; };
 const over = (f, b) => [0,1,2].map(i => f[i]*f[3] + b[i]*(1-f[3])).concat([1]);
 const lum = c => { const v = c.slice(0,3).map(u => { u /= 255; return u <= .04045 ? u/12.92 : Math.pow((u+.055)/1.055, 2.4); }); return .2126*v[0] + .7152*v[1] + .0722*v[2]; };
 const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
 const bgOf = n => { const layers = []; for (let p = n; p && p.nodeType === 1; p = p.parentElement) { const c = col(getComputedStyle(p).backgroundColor); if (c[3] > 0) { layers.push(c); if (c[3] >= .99) break; } }
   let b = col(getComputedStyle(document.documentElement).backgroundColor); if (b[3] < .99) b = [255,255,255,1]; for (let i = layers.length-1; i >= 0; i--) b = over(layers[i], b); return b; };
 const shown = n => { const s = getComputedStyle(n); const r = n.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && (r.width > 0 || r.height > 0); };
 const scroller = (n, stop) => { for (let p = n.parentElement; p && p !== stop; p = p.parentElement) if (/auto|scroll/.test(getComputedStyle(p).overflowX)) return true; return false; };
 window.__bc = el => {
  const f = new Set(), vw = document.documentElement.clientWidth;
  const r = el.getBoundingClientRect();
  if (r.right > vw + 1 || r.left < -1) f.add('overflow-x');
  if (!/auto|scroll/.test(getComputedStyle(el).overflowX) && el.scrollWidth > el.clientWidth + 1 && el.tagName.toLowerCase() !== 'svg') f.add('overflow-x');
  for (const n of [el, ...el.querySelectorAll('*')]) {
   const tag = n.tagName.toLowerCase();
   if (n.closest('svg')) continue;
   if (!shown(n)) continue;
   const cs = getComputedStyle(n), nr = n.getBoundingClientRect();
   if ((nr.right > vw + 1 || nr.left < -1) && !scroller(n, el.parentElement)) f.add('overflow-x');
   const direct = [...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
   if (!direct || n.closest('[data-m],.katex')) continue;
   if (!n.closest('[data-expect="clipped"]') && ((/hidden|clip/.test(cs.overflowX) && n.scrollWidth > n.clientWidth + 1) || (/hidden|clip/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 1))) f.add('clipped-text');
   const fs = parseFloat(cs.fontSize); if (fs < 11) f.add('font<11px');
   const fg = col(cs.color), bg = bgOf(n), big = fs >= 24 || (fs >= 18.66 && +cs.fontWeight >= 700);
   if (+cs.opacity > 0 && !n.closest('[disabled],[aria-disabled="true"],[data-inactive]') && ratio(over(fg, bg), bg) < (big ? 3 : 4.5)) f.add('contrast<4.5');
  }
  const tgt = 'button,input:not([type=hidden]),select,textarea,[role=button],[role=slider],.grip,[data-p="opts"]>li,[data-node]';
  for (const b of [el, ...el.querySelectorAll(tgt)]) { if (!b.matches(tgt) || !shown(b)) continue; const br = b.getBoundingClientRect(); if (br.width < 24 || br.height < 24) f.add('touch<24px'); }
  const svgs = [...(el.matches('svg[viewBox]') ? [el] : []), ...el.querySelectorAll('svg[viewBox]')];
  for (const svg of svgs) { const sr = svg.getBoundingClientRect(); if (!shown(svg) || sr.width < 1 || sr.height < 1) continue; const vb = svg.viewBox.baseVal; const k = vb && vb.width ? sr.width / vb.width : 1; const sbg = bgOf(svg);
   for (const t of svg.querySelectorAll('text')) { if (!t.textContent.trim() || getComputedStyle(t).display === 'none') continue; let bb; try { bb = t.getBBox(); } catch (e) { continue; }
    if (vb && vb.width && (bb.x < vb.x-1 || bb.y < vb.y-1 || bb.x+bb.width > vb.x+vb.width+1 || bb.y+bb.height > vb.y+vb.height+1)) f.add('label-outside-viewBox');
    const ts = getComputedStyle(t); if (parseFloat(ts.fontSize) * k < 11) f.add('font<11px');
    const tr = t.getBoundingClientRect(), x = tr.left + tr.width/2, y = tr.top + tr.height/2; let bg = sbg;
    if (y > 0 && y < innerHeight && x > 0 && x < innerWidth) { const under = document.elementsFromPoint(x, y).find(e => e !== t && !t.contains(e) && svg.contains(e) && /^(rect|circle|ellipse|path|polygon)$/.test(e.tagName) && getComputedStyle(e).fill !== 'none');
     if (under) { const us = getComputedStyle(under), c = col(us.fill); c[3] *= (+us.fillOpacity) * (+us.opacity); bg = over(c, sbg); } }
    const fc = col(ts.fill); fc[3] *= (+ts.fillOpacity) * (+ts.opacity); if (fc[3] > 0 && ratio(over(fc, bg), bg) < (parseFloat(ts.fontSize) * k >= 24 ? 3 : 4.5)) f.add('contrast<4.5'); } }
  if ((window.__ls || []).some(e => e.nodes.some(nd => nd && nd !== el && el.contains(nd)))) f.add('layout-shift');
  return [...f];
 };
 window.__bid = el => { const kind = el.dataset.c || (el.dataset.demo ? 'demo' : el.tagName.toLowerCase()); if (el.id) return '#' + el.id; const a = el.parentElement && el.parentElement.closest('[id]:not(section)');
   const demo = el.dataset.demo ? '[data-demo=' + el.dataset.demo + ']' : ''; const sec = el.closest('section[data-u]'); const same = sec ? [...sec.querySelectorAll(el.dataset.c ? '[data-c="' + el.dataset.c + '"]' : el.dataset.demo ? '[data-demo]:not([data-c])' : el.tagName)] : [];
   return (a ? '#' + a.id + ' ' : '') + kind + demo + ':' + (same.indexOf(el) + 1); };
}"""
SHOT_DEFAULT = '[data-c="exhibit"], figure, [data-c="terms"], [data-demo]'
QUIET = '.bar,.float{display:none!important}'


def _route(r):  # one network policy for every QA page: local files, and the web fonts the page links; nothing else leaves the disk
    u = r.request.url
    r.continue_() if u.startswith(('file:', 'data:', 'blob:', 'about:')) or r.request.resource_type in ('font', 'stylesheet') else r.abort()


def _page(br, w, scheme='light', errs=None, motion='no-preference'):
    """A QA page: viewport w x 900, colour scheme, motion preference, the network policy, the layout-shift probe; page and console errors go to errs."""
    pg = br.new_page(viewport={'width': w, 'height': 900}, color_scheme=scheme, reduced_motion=motion)
    if errs is not None:
        pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
        pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and errs.append(m.text[:160]))
    pg.route('**/*', _route)
    pg.add_init_script(LS_JS)
    return pg


def _free(pg, uid, solve=False):
    pg.evaluate("""([u, solve]) => { const s = document.querySelector('section[data-u="' + u + '"]'); if (!s) return false; s.classList.add('free');
      s.querySelectorAll('.gated').forEach(g => g.classList.remove('gated')); const lb = s.querySelector('.lockbar'); if (lb) lb.hidden = true;
      if (solve) s.querySelectorAll('[data-c="probe"],[data-c="ask"],[data-c="task"]').forEach(c => { try { if (c.__solve && !c.classList.contains('solved')) c.__solve() } catch (e) {} }); return true }""", [uid, solve])


def _step(pg, st, scope):
    op = st.get('op')
    loc = lambda sel: pg.locator(sel if sel.startswith('#') else f'{scope} {sel}').first
    if op == 'tap':
        loc(st['sel']).click(timeout=5000)
    elif op == 'drag':
        a = loc(st['sel']).bounding_box(timeout=5000)
        x0, y0 = a['x'] + a['width'] / 2, a['y'] + a['height'] / 2
        if isinstance(st.get('to'), list):
            x1, y1 = x0 + st['to'][0], y0 + st['to'][1]
        else:
            b = loc(st['to']).bounding_box(timeout=5000)
            x1, y1 = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
        pg.mouse.move(x0, y0)
        pg.mouse.down()
        pg.mouse.move(x1, y1, steps=12)
        pg.mouse.up()
    elif op == 'type':
        loc(st['sel']).fill(str(st.get('text', '')), timeout=5000)
    elif op == 'key':
        (loc(st['sel']).press if st.get('sel') else pg.keyboard.press)(st['key'])
    elif op == 'wait':
        pg.wait_for_timeout(min(int(st.get('ms', 300)), 5000))
    else:
        raise ValueError(f'unknown step op {op}; use tap, drag, type, key, wait')


def _sheet(br, out, uid, theme, rows):
    import base64
    cells = ''.join(f'<figure><img src="data:image/png;base64,{base64.b64encode(open(p, "rb").read()).decode()}"><figcaption>{esc(lab)}</figcaption></figure>' for p, lab in rows)
    pg = _page(br, 1400)
    pg.set_content('<style>body{margin:8px;font:12px sans-serif;background:#fff}main{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;align-items:start}'
                   'figure{margin:0;border:1px solid #ccc}img{display:block;width:100%;max-height:420px;object-fit:contain;object-position:top;background:#eee}'
                   f'figcaption{{padding:3px 4px;word-break:break-all}}</style><h3>{esc(uid)} {theme}</h3><main>{cells}</main>')
    dst = os.path.join(out, f'{uid}-{theme}-sheet.png')
    pg.screenshot(path=dst, full_page=True, timeout=60000)
    pg.close()
    return dst


SECTION_JS = """(e, scope) => { const sec = document.querySelector(scope);
  const hs = [...sec.querySelectorAll('h3')].filter(h => { const c = h.parentElement.closest('[data-c]'); return !c || !sec.contains(c) || c === sec });
  return hs.filter(h => h.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING).length }"""


def shot(d, uid, sel=None, widths=(390, 1200), schemes=('light', 'dark'), solve=False, steps=None, sheet=False, out=None, budget=300, section=None):
    """Screenshot the matched elements of one unit with in-page checks; one line per shot so only flagged images need opening."""
    import time
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright not installed (pip install playwright; playwright install chromium)')
        return 2
    plan = Plan(os.path.join(d, 'book.json'))
    if uid not in plan.unit_by_id:
        raise PlanError(f'unit {uid} is not in book.json')
    if not os.path.exists(os.path.join(d, 'book.html')):
        raise PlanError('book.html not found; run `make-book.py build` first')
    out = out or os.path.join(d, '.work', 'shots')
    # --out x.png names the file for a single shot; several shots go to the directory x/ instead
    out_file = out if out.lower().endswith('.png') and not os.path.isdir(out) else None
    if out_file:
        out = os.path.join(os.path.dirname(os.path.abspath(out_file)), '.shot-tmp')
    os.makedirs(out, exist_ok=True)
    failed, done = [], []
    st = json.load(open(steps, encoding='utf-8')) if steps else []
    url = 'file://' + os.path.abspath(os.path.join(d, 'book.html'))
    scope = f'section[data-u="{uid}"]'
    t0, flagged, n, sheets = time.time(), 0, 0, {}
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for w in widths:
            for theme in schemes:
                if time.time() - t0 > budget:
                    print(f'time budget {budget}s spent; stopped before {w} {theme}')
                    break
                errs = []
                pg = _page(br, w, theme, errs)
                try:
                    pg.goto(url, timeout=30000)
                    pg.evaluate('document.fonts ? document.fonts.ready.then(() => 1) : 1')
                except Exception as e:
                    print(f'page did not load at {w} {theme}: {e.__class__.__name__}')
                    failed.append(f'load {w} {theme}')
                    pg.close()
                    continue
                pg.add_style_tag(content=QUIET)
                if not pg.evaluate(f'!!document.querySelector(\'{scope}\')'):
                    pg.close()
                    raise PlanError(f'unit {uid} not in book.html; mark it live and build')
                _free(pg, uid, solve)
                for i, s_ in enumerate(st, 1):
                    try:
                        _step(pg, s_, scope)
                    except Exception as e:
                        print(f'step {i} {s_.get("op")} failed at {w} {theme}: {str(e).splitlines()[0][:160]}')
                    failed.append(f'step {i} {w} {theme}')
                pg.wait_for_timeout(250)
                pg.evaluate(CHECK_JS)
                els = pg.query_selector_all(f'{scope} :is({sel or SHOT_DEFAULT})') if not (sel or '').startswith('#') else pg.query_selector_all(sel)
                els = [e for e in els if e.evaluate('(e, s) => e.getBoundingClientRect().width > 0 && !(e.parentElement && e.parentElement.closest(s))', sel or SHOT_DEFAULT)]
                if section is not None:  # same sections as `text --section`: h3 headings outside every component
                    els = [e for e in els if e.evaluate(SECTION_JS, scope) in section]
                load_errs = list(errs)
                for e in load_errs:
                    print(f'page-error {w} {theme}: {e}')
                for el in els:
                    if time.time() - t0 > budget:
                        print(f'time budget {budget}s spent; {len(els)} elements, stopped early')
                        break
                    n += 1
                    k = len(errs)
                    try:
                        el.evaluate("e => { for (let x = e.closest('details'); x; x = x.parentElement && x.parentElement.closest('details')) x.open = true }")
                        el.scroll_into_view_if_needed(timeout=5000)
                        bid, flags = el.evaluate('e => [window.__bid(e), window.__bc(e)]')
                        box = el.bounding_box() or {'width': 0, 'height': 0}
                        name = re.sub(r'[^\w.-]+', '_', bid.strip('#')).strip('_')[:60]
                        p = os.path.join(out, f'{uid}-{w}-{theme}-{n:03d}-{name}.png')
                        if not (box['width'] and box['height']):
                            raise ValueError('element has no box')
                        # a viewport clip of the element's box, not el.screenshot (waits for "stable", which animated elements never reach)
                        # and not full_page: a full-page capture of a tall book never finishes for elements below ~16k px (GPU texture limit)
                        grow = box['height'] > 900
                        if grow:
                            pg.set_viewport_size({'width': w, 'height': min(int(box['height']) + 2, 8000)})
                            el.evaluate('e => e.scrollIntoView({block: "start"})')
                            box = el.bounding_box() or box
                        vh = pg.viewport_size['height']
                        y0 = max(box['y'], 0)
                        clip = {'x': max(box['x'], 0), 'y': y0, 'width': min(box['width'], w), 'height': min(box['height'], vh - y0)}
                        try:
                            pg.screenshot(path=p, clip=clip, timeout=15000, animations='disabled')
                        finally:
                            if grow:
                                pg.set_viewport_size({'width': w, 'height': 900})
                    except Exception as e:
                        print(f'- shot {n} failed at {w} {theme}: {str(e).splitlines()[0][:160]}')
                        failed.append(f'shot {n} {w} {theme}')
                        continue
                    done.append(p)
                    if box['height'] > 8000:
                        flags.append(f'cut at 8000px of {round(box["height"])}')
                    if load_errs or len(errs) > k:
                        flags.append('page-error')
                    flagged += bool(flags)
                    print(f'{p} {bid} {round(box["width"])}x{round(box["height"])} {w}px {theme} checks: {", ".join(flags) or "ok"}')
                    sheets.setdefault(theme, []).append((p, f'{bid} {w}px' + (' ! ' + ', '.join(flags) if flags else '')))
                pg.close()
        if sheet:
            for theme, rows in sheets.items():
                print(f'sheet {_sheet(br, out, uid, theme, rows)} ({len(rows)} shots)')
        br.close()
    if out_file:
        import shutil
        if len(done) == 1:
            shutil.move(done[0], out_file)
            print(f'wrote {out_file}')
        elif done:
            dst = out_file[:-4]
            os.makedirs(dst, exist_ok=True)
            for p in done:
                shutil.move(p, os.path.join(dst, os.path.basename(p)))
            print(f'{len(done)} shots, so --out became the directory {dst}/')
        shutil.rmtree(out, ignore_errors=True)
    if not n and not failed:
        print(f'selector matched nothing in {uid}: {sel or SHOT_DEFAULT}' + (f' (sections {sorted(section)})' if section is not None else ''))
        return 1
    if failed:
        print(f'failed ({len(failed)}): ' + '; '.join(failed))
    print(f'-- {n} shots, {len(failed)} failed, {flagged} flagged; open only flagged images')
    return 1 if flagged or failed else 0

# ---------------------------------------------------------------- render (optional)


RESOLVE_JS = """([kind, u, txt]) => { const s = document.querySelector('section[data-u="' + u + '"]'); if (!s) return '-';
  const pool = kind === 'labels' ? [...s.querySelectorAll('svg text')] : kind === 'unrendered' ? [...s.querySelectorAll('[data-m]')] : kind === 'overflow' ? [...s.querySelectorAll('[data-m="display"],.tw')] : [];
  const el = pool.find(e => (e.dataset && e.dataset.tex || e.textContent).trim().startsWith(txt.trim().slice(0, 25)));
  return el ? window.__bid(el.closest('figure,[data-c="exhibit"],[data-c="terms"],[data-c]') || el) : '-' }"""




PICK_JS = """() => { const C = '[data-c="probe"],[data-c="ask"],[data-c="task"]';
  const c = [...document.querySelectorAll(C)].find(x => x.id && x.__solve && !x.closest('.gated') && x.closest('section').querySelector('.gated'));
  const g = document.querySelector('.gated h3[id], h3.gated[id], .gated :is(' + C + ')[id], :is(' + C + ').gated[id]');
  const secs = [...document.querySelectorAll('main section[data-u]')];
  return {card: c ? c.id : null, gated: g ? g.id : null, sec: secs.length > 1 ? secs[1].id : null} }"""
SEEN_JS = """id => { const e = document.getElementById(id); if (!e) return false; const r = e.getBoundingClientRect();
  return r.height > 0 && getComputedStyle(e).display !== 'none' && r.top > -5 && r.top < innerHeight }"""
CALM_JS = """() => { const out = [], UI = JSON.parse(document.getElementById('ui').textContent);
  if (getComputedStyle(document.documentElement).scrollBehavior !== 'auto') out.push('smooth scroll under reduced motion');
  const moving = [...document.querySelectorAll('nav, .settle, button, [data-c], .bin')].find(e => getComputedStyle(e).transitionDuration.split(',').some(t => parseFloat(t) > 0.01));
  if (moving) out.push('transition under reduced motion: ' + (moving.dataset.c || moving.tagName.toLowerCase()));
  const f = document.querySelector('figure[data-c="frames"].play'); return {out, f: !!f, pause: UI.pause} }"""


def reader_state(br, url, w, scheme):
    """Reading-state checks a single page cannot make: solved cards survive a reload, the URL follows the current unit,
    a deep link into gated content opens it, and reduced motion stops transitions, smooth scroll and frame autoplay."""
    fails = []
    pg = _page(br, w, scheme)
    try:
        pg.goto(url, timeout=60000)
        pg.wait_for_timeout(700)
        pick = pg.evaluate(PICK_JS)
        if pick['card']:
            pg.evaluate('id => document.getElementById(id).__solve()', pick['card'])
            pg.reload(timeout=60000)
            pg.wait_for_timeout(700)
            if not pg.evaluate('id => document.getElementById(id).classList.contains("solved")', pick['card']):
                fails.append(('-', '#' + pick['card'], 'state', 'solved card not kept after reload'))
        if pick['sec']:
            pg.evaluate('id => scrollTo({top: document.getElementById(id).getBoundingClientRect().top + scrollY - 40, behavior: "instant"})', pick['sec'])
            pg.wait_for_timeout(300)
            if pg.evaluate('location.hash') != '#' + pick['sec']:
                fails.append(('-', '#' + pick['sec'], 'state', 'URL hash does not follow the current unit'))
    finally:
        pg.close()
    if pick.get('gated'):
        pg = _page(br, w, scheme)
        try:
            pg.goto(url + '#' + pick['gated'], timeout=60000)
            pg.wait_for_timeout(900)
            if not pg.evaluate(SEEN_JS, pick['gated']):
                fails.append(('-', '#' + pick['gated'], 'state', 'deep link into gated content does not show it'))
        finally:
            pg.close()
    pg = _page(br, w, scheme, motion='reduce')
    try:
        pg.goto(url, timeout=60000)
        pg.wait_for_timeout(500)
        r = pg.evaluate(CALM_JS)
        fails += [('-', '-', 'motion', m) for m in r['out']]
        if r['f']:
            pg.evaluate("document.querySelectorAll('.gated').forEach(g => g.classList.remove('gated')); document.querySelector('figure[data-c=\"frames\"].play').scrollIntoView({block: 'center'})")
            pg.wait_for_timeout(600)
            if pg.evaluate("p => [...document.querySelectorAll('figure[data-c=\"frames\"] .player button')].some(b => b.getAttribute('aria-label') === p)", r['pause']):
                fails.append(('-', 'frames', 'motion', 'frames autoplay under reduced motion'))
    finally:
        pg.close()
    return fails


def reader_check(d, w=390, scheme='light'):
    """Reader-page checks at one view (the #check run's interact and targets<24px, then reader_state); a list of (unit, element, check, text)."""
    from playwright.sync_api import sync_playwright
    url = 'file://' + os.path.abspath(os.path.join(d, 'book.html'))
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        errs = []
        pg = _page(br, w, scheme, errs)
        try:
            pg.goto(url + '#check', timeout=60000)
            pg.wait_for_selector('body[data-check]', timeout=30000, state='attached')
            res = json.loads(pg.get_attribute('body', 'data-check'))
        except Exception as e:
            res = {'interact': [f'-: no check result ({e.__class__.__name__})']}
        pg.close()
        fails = [('-', '-', 'page-error', e) for e in errs]
        fails += [(i.partition(': ')[0], '-', 'interact', i.partition(': ')[2]) for i in res.get('interact') or []]
        fails += [(t['u'], t['what'], 'targets<24px', t['size']) for t in res.get('targets') or [] if t['level'] == 'error']
        fails += reader_state(br, url, w, scheme)
        br.close()
    return fails


def render(d, out=None, quick=False):
    """Book-wide #check at 390/1200 px, light/dark, plus the element checks shot uses; prints only failures (unit, element, check)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright not installed: open book.html#check at 390 and 1200 px, light and dark, and read body[data-check]')
        return 2
    out = out or os.path.join(d, 'shots')
    os.makedirs(out, exist_ok=True)
    url = 'file://' + os.path.abspath(os.path.join(d, 'book.html')) + '#check'
    bad, nwarn, combos = 0, 0, [(390, 'light')] if quick else [(w, sc) for w in (390, 1200) for sc in ('light', 'dark')]
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for w, scheme in combos:
            errors, warns = [], []
            pg = _page(br, w, scheme, errors)
            try:
                pg.goto(url, timeout=60000)
                pg.wait_for_selector('body[data-check]', timeout=30000, state='attached')
                res = json.loads(pg.get_attribute('body', 'data-check'))
            except Exception as e:
                res = {'error': f'no check result ({e.__class__.__name__})'}
            pg.evaluate(CHECK_JS)
            fails = []
            for e in errors:
                fails.append(('-', '-', 'page-error', e))
            if res.get('error'):
                fails.append(('-', '-', 'check', res['error']))
            if res.get('hscroll'):
                fails.append(('-', '-', 'overflow-x', 'page scrolls sideways'))
            for kind, check in (('overflow', 'overflow-x'), ('labels', 'label-outside-viewBox'), ('unrendered', 'math-unrendered'), ('interact', 'interact')):
                for item in res.get(kind) or []:
                    u, _, txt = item.partition(': ')
                    fails.append((u or '-', pg.evaluate(RESOLVE_JS, [kind, u, txt]) if (u and u != '-') else '-', check, txt))
            tg = {}  # targets: under 24px fails, under 44px warns; one line per unit and kind of control
            for t in res.get('targets') or []:
                tg.setdefault((t['u'], t['what'], t['level']), []).append(t['size'])
            for (u, what, lvl), sizes in tg.items():
                (fails if lvl == 'error' else warns).append((u, what, 'targets<24px' if lvl == 'error' else 'targets<44px', f'{len(sizes)} at {", ".join(sorted(set(sizes))[:3])}'))
            try:
                pg.screenshot(path=os.path.join(out, f'{w}-{scheme}.png'), full_page=pg.evaluate('document.documentElement.scrollHeight') < 12000, timeout=60000)
            except Exception:
                pass
            pg.close()
            pg = _page(br, w, scheme)  # element checks in the reader's view, every unit freed
            els = []
            try:
                pg.goto(url.split('#')[0], timeout=60000)
                pg.wait_for_timeout(500)
                pg.add_style_tag(content=QUIET)
                for u in pg.evaluate("[...document.querySelectorAll('main section[data-u]')].map(s => s.dataset.u)"):
                    _free(pg, u)
                pg.evaluate(CHECK_JS)
                els = pg.evaluate("""s => [...document.querySelectorAll('main section[data-u]')].flatMap(sec => [...sec.querySelectorAll(s)].filter(e => !(e.parentElement && e.parentElement.closest(s)))
                .map(e => { for (let x = e.closest('details'); x; x = x.parentElement && x.parentElement.closest('details')) x.open = true; if (!(e.getBoundingClientRect().width > 0)) return null;
                  e.scrollIntoView({block: 'start', behavior: 'instant'}); const f = window.__bc(e); return f.length ? [sec.dataset.u, window.__bid(e), f.join(', ')] : null }).filter(Boolean))""", SHOT_DEFAULT)
            except Exception as e:
                fails.append(('-', '-', 'element-checks', e.__class__.__name__))
            for u, bid, f in els:
                fails.append((u, bid, f, ''))
            try:
                fails += reader_state(br, url.split('#')[0], w, scheme)
            except Exception as e:
                fails.append(('-', '-', 'state', f'reader state checks failed ({e.__class__.__name__}: {str(e).splitlines()[0][:80]})'))
            for u, bid, check, txt in warns:
                print(f'warn {w}px {scheme} {u} {bid} {check}' + (f': {txt[:120]}' if txt else ''))
            nwarn += len(warns)
            for u, bid, check, txt in fails:
                print(f'fail {w}px {scheme} {u} {bid} {check}' + (f': {txt[:120]}' if txt else ''))
            bad += len(fails)
            pg.close()
        br.close()
    print(f'-- {bad} failures, {nwarn} warns over {len(combos)} views; fix loop: outline/show the block, edit --patch, shot --sel \'#id\'')
    return 1 if bad else 0
