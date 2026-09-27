#!/usr/bin/env python3
"""Check an Artifact page in headless Chrome, printing one line per check then `pass` or `FAIL`;
with --svg, write each figure as a standalone SVG instead.

usage: check.py <page.html> [--svg <out dir>]. Exit 0 pass or written, 1 FAIL or no figure, 2 could not run.
"""
import html
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REDUCED = "--force-prefers-reduced-motion"
TOLERANCE = 0.02
MIN_RUN = 3
CONTENTS = 4
FILES = 4  # a file-tree from this many files named, as the Mapping says
WORD = r"[A-Za-z]+(?:['’-][A-Za-z]+)*[.,:;!?]?"
ENGLISH = re.compile(rf"{WORD}(?:\s+{WORD}){{{MIN_RUN - 1},}}")
# a sentence ends at . ! or ? with no digit either side, so 4.00점 stays whole; its last one may have no mark
SENTENCE = re.compile(r"(?:[^.!?\n]|(?<=\d)[.!?]|[.!?](?=\d))+(?:(?<!\d)[.!?](?!\d)|$)")
SENTENCE_HEADING = re.compile(r"(니다|[아어여해예에세네지]요|다)[.!?]?$|[.!?]$")
LAYOUT = r"""<iframe id=f style="width:320px;height:800px;border:0"></iframe>
<script>
f.onload = function () {
  f.onload = null;
  var d = f.contentDocument, w = f.contentWindow;
  d.querySelectorAll('button,summary,input,select').forEach(function (c) { c.click(); });
  d.querySelectorAll('[data-chapter]').forEach(function (c) { c.hidden = false; });
  var anim = d.getAnimations().filter(function (a) { return a.playState === 'running'; }).length;
  setTimeout(function () {
    var e = d.documentElement, t = d.createTreeWalker(d.body, 4), n, z, s = [1 / 0, 1 / 0];
    while ((n = t.nextNode())) if (n.data.trim() && !/^(script|style|title)$/i.test(n.parentElement.tagName)) {
      z = /[\p{sc=Hangul}\p{sc=Han}]/u.test(n.data) ? 1 : 0;
      s[z] = Math.min(s[z], parseFloat(w.getComputedStyle(n.parentElement).fontSize));
    }
    var shown = 0, total = 0;
    d.querySelectorAll('[data-slide],[data-swipe]').forEach(function (p) {
      var li = p.querySelectorAll('.steps > li');
      total += li.length;
      shown += Array.prototype.filter.call(li, function (l) { return l.checkVisibility(); }).length;
    });
    var bad = 0;
    d.querySelectorAll('svg').forEach(function (g) {
      var box = g.getBoundingClientRect(), r = Array.prototype.map.call(g.querySelectorAll('text'), function (x) { return x.getBoundingClientRect(); })
        .filter(function (x) { return x.width && x.height; });
      r.forEach(function (a, i) {
        var hit = a.left < box.left - 1 || a.right > box.right + 1 || a.top < box.top - 1 || a.bottom > box.bottom + 1;
        r.forEach(function (b, j) { hit = hit || i != j && Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1; });
        bad += hit ? 1 : 0;
      });
    });
    var reduced = w.matchMedia('(prefers-reduced-motion: reduce)').matches;
    // the element reaching furthest right that no scroll box holds, named by its path
    var name = function (el) {
      return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + Array.prototype.map.call(el.classList, function (c) { return '.' + c; }).join('');
    };
    var held = function (el) {
      for (var a = el.parentElement; a && a !== d.body; a = a.parentElement)
        if (w.getComputedStyle(a).overflowX !== 'visible') return true;
      return false;
    };
    var far = null, right = -1 / 0;
    d.body.querySelectorAll('*').forEach(function (el) {
      var r = el.getBoundingClientRect().right;
      if (r >= right && !held(el)) { right = r; far = el; }
    });
    var path = [];
    for (var a = far; a && a !== d.body && path.length < 3; a = a.parentElement) path.unshift(name(a));
    document.body.dataset.r = JSON.stringify({ reduced: reduced, scroll: e.scrollWidth, client: e.clientWidth, latin: s[0], hangul: s[1],
      anim: anim, shown: shown, total: total, labels: bad, widest: path.join(' > ') });
  }, 500);
};
f.src = location.hash.slice(1);
</script>
"""
KOREAN = r"""<iframe id=f></iframe>
<script>
f.onload = function () {
  f.onload = null;
  setTimeout(function () {
    var d = f.contentDocument, w = f.contentWindow, groups = new Map(), out = [];
    var SKIP = 'script,style,template,noscript', CODE = 'code,pre,kbd,samp';
    // Mapping: a file named by path, or a flow drawn in text with arrows, outside any widget
    var PATH = /^[~.\w$-]*(\/[\w.*$-]*)*(\.[A-Za-z]\w{0,4}|\/)$/, ARROW = /[→⟶⇒➜➔▶]/g, BLOCK = 'pre,p,li,td,th,dd,figcaption';
    var block = function (el) {
      while (el.parentElement && !(el instanceof w.SVGElement) && !/^(button|label|option|summary)$/i.test(el.tagName)
             && w.getComputedStyle(el).display === 'inline') el = el.parentElement;
      return el;
    };
    var t = d.createTreeWalker(d.documentElement, 4), n, ascii = [], held = [];
    // a placeholder left in text or an attribute; an ASCII arrow in prose
    var HOLE = /\{\{[^}]*\}\}/g, PROSE = CODE + ',[data-widget]';
    d.querySelectorAll('*').forEach(function (el) {
      if (!el.closest(SKIP)) Array.prototype.forEach.call(el.attributes, function (a) { held = held.concat(a.value.match(HOLE) || []); });
    });
    while ((n = t.nextNode())) {
      var p = n.parentElement;
      if (!p || p.closest(SKIP) || !n.data.trim()) continue;
      held = held.concat(n.data.match(HOLE) || []);
      var at = n.data.replace(/\s+/g, ' ').search(/->|=>/);  // the arrow and a few words either side
      if (at >= 0 && !p.closest(PROSE)) ascii.push(n.data.replace(/\s+/g, ' ').slice(Math.max(0, at - 12), at + 14).trim());
      var b = block(p);
      if (!groups.has(b)) groups.set(b, []);
      groups.get(b).push(p.closest(CODE) ? '\n' : n.data);
    }
    // a table cell is data: a terse value there ends without a mark, so only its marked sentences are read
    var cells = [];
    groups.forEach(function (g, b) { (b.closest && b.closest('td,th') ? cells : out).push(g.join('')); });
    d.querySelectorAll('[alt],[aria-label],[title],[placeholder]').forEach(function (el) {
      ['alt', 'aria-label', 'title', 'placeholder'].forEach(function (a) { if (el.getAttribute(a)) out.push(el.getAttribute(a)); });
    });
    var heads = Array.prototype.map.call(d.querySelectorAll('h1,h2,h3,h4,h5,h6'), function (h) { return h.textContent.replace(/\s+/g, ' ').trim(); });
    var h2 = Array.prototype.slice.call(d.querySelectorAll('main h2')), nav = d.querySelector('main nav');
    if (nav && h2.length && !(nav.compareDocumentPosition(h2[0]) & 4)) nav = null;
    var links = nav ? Array.prototype.map.call(nav.querySelectorAll('a[href^="#"]'), function (a) { return a.getAttribute('href').slice(1); }) : [];
    var loose = function (sel) { return Array.prototype.filter.call(d.querySelectorAll(sel), function (e) { return !e.closest('[data-widget]'); }); };
    var arrows = function (e) { return (e.textContent.match(ARROW) || []).length >= 2; };
    var paths = loose('code').map(function (c) { return c.textContent.trim().replace(/:\d.*$/, ''); }).filter(function (p) { return PATH.test(p); });
    var flows = loose(BLOCK).filter(function (e) { return arrows(e) && !Array.prototype.some.call(e.querySelectorAll(BLOCK), arrows); })
      .map(function (e) { return e.textContent.replace(/\s+/g, ' ').trim().slice(0, 40); });
    document.body.dataset.r = JSON.stringify({ lang: d.documentElement.lang, text: out, headings: heads, ascii: ascii, cells: cells,
      held: held.filter(function (h, i) { return held.indexOf(h) === i; }), skin: !!d.querySelector('style#skin'),
      h1: !!d.querySelector('h1'), drawn: loose('svg').filter(function (g) { return !g.parentElement.closest('svg'); }).length,
      paths: paths.filter(function (p, i) { return paths.indexOf(p) === i; }), flows: flows,
      diagrams: Array.prototype.map.call(d.querySelectorAll('[data-widget="diagram"]'), function (e) { return e.dataset.diagram; }),
      h2: h2.length, linked: h2.filter(function (h) { return h.id && links.indexOf(h.id) >= 0; }).length, nav: !!d.querySelector('main nav'),
      broken: Array.prototype.map.call(d.querySelectorAll('a[href^="#"]'), function (a) { return a.getAttribute('href'); })
        .filter(function (h) { return h.length > 1 && !d.getElementById(decodeURIComponent(h.slice(1))); }),
      chapters: d.querySelectorAll('[data-chapter]').length,
      tables: Array.prototype.map.call(d.querySelectorAll('table'), function (t) {
        var text = function (c) { return c.textContent.replace(/\s+/g, ' ').trim(); };
        return [t.tHead && t.tHead.rows.length ? Array.prototype.map.call(t.tHead.rows[t.tHead.rows.length - 1].cells, text) : [],
          Array.prototype.map.call(t.tBodies.length ? t.tBodies[0].rows : [], function (r) { return Array.prototype.map.call(r.cells, text); })];
      }),
      loose: Array.prototype.filter.call(d.querySelectorAll('main h3'), function (h) { return !h.closest('[data-chapter]'); }).length });
  }, 300);
};
f.src = location.hash.slice(1);
</script>
"""
SVG = r"""<iframe id=f style="width:800px;height:800px;border:0"></iframe>
<script>
var PROPS = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
  'stroke-linejoin', 'stroke-opacity', 'opacity', 'marker-start', 'marker-end', 'font-family', 'font-size',
  'font-weight', 'font-style', 'text-anchor', 'dominant-baseline', 'paint-order', 'visibility', 'display'];
f.onload = function () {
  f.onload = null;
  setTimeout(function () {
    var d = f.contentDocument, w = f.contentWindow, out = [];
    var bg = w.getComputedStyle(d.body).backgroundColor;
    d.querySelectorAll('svg[role="img"], [data-widget="chart"] .plot svg').forEach(function (g) {
      var c = g.cloneNode(true), src = [g].concat(Array.from(g.querySelectorAll('*'))),
          dst = [c].concat(Array.from(c.querySelectorAll('*')));
      src.forEach(function (s, i) {
        var cs = w.getComputedStyle(s), up = i ? w.getComputedStyle(s.parentElement) : null, t = dst[i];
        PROPS.forEach(function (p) {
          var v = cs.getPropertyValue(p).replace(/url\("(#[^"]+)"\)/, 'url($1)');
          var same = up && up.getPropertyValue(p).replace(/url\("(#[^"]+)"\)/, 'url($1)') === v;
          if (p === 'opacity' ? v !== '1' : p === 'display' ? v === 'none' : !same) t.setAttribute(p, v);
        });
        t.removeAttribute('class'); t.removeAttribute('style'); t.removeAttribute('tabindex');
      });
      var box = g.getBoundingClientRect(), vb = g.viewBox.baseVal;
      c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      c.setAttribute('width', Math.round(vb && vb.width || box.width));
      c.setAttribute('height', Math.round(vb && vb.height || box.height));
      var r = d.createElementNS('http://www.w3.org/2000/svg', 'rect');
      r.setAttribute('x', vb ? vb.x : 0); r.setAttribute('y', vb ? vb.y : 0);
      r.setAttribute('width', '100%'); r.setAttribute('height', '100%'); r.setAttribute('fill', bg);
      c.insertBefore(r, c.firstChild);
      out.push(new XMLSerializer().serializeToString(c));
    });
    document.body.dataset.r = JSON.stringify(out);
  }, 300);
};
f.src = location.hash.slice(1);
</script>
"""
CHART = r"""<iframe id=f style="width:800px;height:800px;border:0"></iframe>
<script>
f.onload = function () {
  f.onload = null;
  setTimeout(function () {
    var d = f.contentDocument, out = [];
    var attrs = function (e) { var o = {}; Array.prototype.forEach.call(e.attributes, function (a) { o[a.name] = a.value; }); return o; };
    var collect = function (fig, moved) {
      var tables = Array.prototype.map.call(fig.querySelectorAll('details table'), function (t) {
        return { head: Array.prototype.map.call(t.tHead.rows[0].cells, function (c) { return c.textContent.trim(); }),
                 rows: Array.prototype.map.call(t.tBodies[0].rows, function (r) { return Array.prototype.map.call(r.cells, function (c) { return c.textContent.trim(); }); }) };
      });
      return { kind: fig.dataset.chart, at: +fig.dataset.at, tables: tables,
        slide: fig.hasAttribute('data-slide'), live: fig.classList.contains('live'), moved: moved,
        summary: (fig.querySelector('figcaption') || { textContent: '' }).textContent.trim(),
        panels: Array.prototype.map.call(fig.querySelectorAll('.plot svg'), function (s) {
          return { x: s.dataset.x, y: s.dataset.y, marks: Array.prototype.map.call(s.querySelectorAll('.marks > *'), attrs) };
        }) };
    };
    var figs = Array.prototype.slice.call(d.querySelectorAll('[data-widget="chart"]'));
    figs.forEach(function (fig) { out.push(collect(fig, false)); });
    var live = figs.filter(function (fig) { return fig.classList.contains('live'); });
    (function move(i) {  // step each slide to its last table with Next, then read it again
      if (i === live.length) { document.body.dataset.r = JSON.stringify(out); return; }
      var fig = live[i], next = fig.querySelectorAll('.controls button')[1], steps = fig.querySelectorAll('.steps > li');
      for (var k = 0; k < steps.length && !next.disabled; k++) next.click();
      setTimeout(function () { out.push(collect(fig, true)); move(i + 1); }, 300);
    })(0);
  }, 500);
};
f.src = location.hash.slice(1);
</script>"""


def render(frame, page, *flags):
    """(the JSON the frame wrote for `page` or None, whether the page threw an uncaught error)."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(frame)
    try:
        r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--allow-file-access-from-files", "--dump-dom",
                            "--enable-logging=stderr", *flags, "--virtual-time-budget=3000", f"file://{f.name}#file://{page}"],
                           capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(f.name)
    m = re.search(r'data-r="([^"]*)"', r.stdout)
    return (json.loads(html.unescape(m.group(1))) if m else None), bool(re.search(r'CONSOLE.*"Uncaught', r.stderr))


SHOWN = "Array.prototype.map.call(document.querySelectorAll('[data-chapter]'), function (c) { return c.checkVisibility(); })"
CHAPTER_IDS = ("(function () { var c = Array.prototype.slice.call(document.querySelectorAll('[data-chapter]'));"
               " return Array.prototype.map.call(document.querySelectorAll('[data-chapter] [id]'), function (e) {"
               " return [e.id, c.indexOf(e.closest('[data-chapter]'))]; }); })()")
HOLDER = ("(function (a) { var t = document.getElementById(decodeURIComponent(a.hash.slice(1)));"
          " return t && t.closest('[data-chapter]') ? Array.prototype.indexOf.call(document.querySelectorAll('[data-chapter]'),"
          " t.closest('[data-chapter]')) : -1; })")

# each live swipe's [step reached, steps, its token inside its stage's box, or null with no token]
SWIPES = ("Array.prototype.map.call(document.querySelectorAll('[data-swipe].live'), function (r) {"
          " var t = r.querySelector('.token'), a = t && t.getBoundingClientRect(), b = r.querySelector('.stage').getBoundingClientRect();"
          " return [+r.dataset.at + 1, r.querySelectorAll('.steps > li').length,"
          " t ? a.left >= b.left - 1 && a.right <= b.right + 1 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1 : null]; })")

# [what was tried, the controls that changed nothing]: each filter and controls widget's control, then the reading aids;
# a control passes when its states differ: a slider at its min and max, each of a group's buttons from the others, a preset
# against the controls scrambled, the text box against no word, a reading-aid button against the page before it
CLICKS = r"""(async function () {
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var tried = 0, dead = [];
  // whether fn() holds within two seconds, for a transition that a loaded machine slows
  var until = async function (fn) { for (var i = 0; i < 40 && !fn(); i++) await wait(50); return fn(); };
  var shown = function (el) { return el.checkVisibility({ visibilityProperty: true }); };
  var look = function (el) {
    var cs = getComputedStyle(el), r = el.getBoundingClientRect();
    return [el.hidden, Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height), cs.fill, cs.stroke, cs.opacity,
      cs.transform, cs.display, cs.visibility, el.childElementCount ? '' : el.textContent];
  };
  var state = function (root) {
    if (root.dataset.widget === 'filter') {
      var list = document.getElementById(root.dataset.for);
      return JSON.stringify([list ? Array.prototype.map.call(list.querySelectorAll('tr, li, :scope > *'), function (e) { return e.hidden; }) : [],
        (root.querySelector('output') || {}).textContent]);
    }
    var els = [];
    root.querySelectorAll('.stage:not(.before), .stage:not(.before) *, output[data-calc]').forEach(function (e) { els.push(look(e)); });
    return JSON.stringify(els);
  };
  var click = async function (b) { b.click(); await wait(30); };
  var slide = async function (s, v) { s.value = v; s.dispatchEvent(new Event('input', { bubbles: true })); await wait(30); };
  var live = function (els) { return Array.prototype.filter.call(els, function (e) { return !e.matches(':disabled'); }); };
  var roots = document.querySelectorAll('[data-widget="filter"].live, [data-widget="controls"].live');
  for (var w = 0; w < roots.length; w++) {
    var root = roots[w], name = root.dataset.widget + ' ' + (1 + Array.prototype.slice.call(roots, 0, w).filter(function (r) { return r.dataset.widget === root.dataset.widget; }).length);
    var groups = root.querySelectorAll('[role="group"]');
    for (var g = 0; g < groups.length; g++) {
      var bs = live(groups[g].querySelectorAll('button')), seen = [];
      for (var i = 0; i < bs.length; i++) { await click(bs[i]); seen.push(state(root)); }
      bs.forEach(function (b, i) {
        tried++;
        if (seen.some(function (s, j) { return j !== i && s === seen[i]; })) dead.push(name + ' ' + groups[g].getAttribute('aria-label') + ' ' + b.textContent.trim() + ' changes nothing');
      });
      if (bs.length) await click(bs[0]);
    }
    var sliders = live(root.querySelectorAll('input[type="range"]'));
    for (var k = 0; k < sliders.length; k++) {
      var s = sliders[k], was = s.value;
      await slide(s, s.min || 0); var lo = state(root);
      await slide(s, s.max || 100); var hi = state(root);
      tried++;
      if (lo === hi) dead.push(name + ' slider ' + s.name + ' changes nothing');
      await slide(s, was);
    }
    var box = root.querySelector('input[type="search"]');
    if (box && !box.disabled) {
      var before = state(root);
      box.value = '␀␀'; box.dispatchEvent(new Event('input', { bubbles: true })); await wait(30);
      tried++;
      if (state(root) === before) dead.push(name + ' search box' + ' changes nothing');
      box.value = ''; box.dispatchEvent(new Event('input', { bubbles: true })); await wait(30);
    }
    var presets = live(root.querySelectorAll('[data-preset]'));
    for (var q = 0; q < presets.length; q++) {
      var changed = false;
      for (var end = 0; end < 2 && !changed; end++) {
        for (var k2 = 0; k2 < sliders.length; k2++) await slide(sliders[k2], end ? sliders[k2].max : sliders[k2].min);
        for (var g2 = 0; g2 < groups.length; g2++) { var gb = live(groups[g2].querySelectorAll('button')); if (gb.length) await click(gb[end ? 0 : gb.length - 1]); }
        var from = state(root);
        await click(presets[q]);
        changed = state(root) !== from;
      }
      tried++;
      if (!changed) dead.push(name + ' preset ' + presets[q].textContent.trim() + ' changes nothing');
    }
  }
  // the chapters as the page shows them, since browse unhid them all
  dispatchEvent(new HashChangeEvent('hashchange')); await wait(100);
  var nav = document.querySelector('main nav.drawer'), toggle = document.querySelector('.dock .contents');
  if (nav && toggle && shown(toggle)) {
    // a close an earlier step began may still be hiding it
    var closed = !(await until(function () { return !shown(nav); }));
    await click(toggle);
    var open = await until(function () { return shown(nav); });
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    var shut = await until(function () { return !shown(nav); });
    tried++;
    if (closed || !open || !shut) dead.push('contents button' + ' changes nothing');
  }
  // the top button shows once scrolled far, so at the foot of the page or of any chapter long enough
  var top = document.querySelector('.dock .top'), heads = document.querySelectorAll('[data-chapter] > h2[id]');
  for (var c = -1; top && c < heads.length && !shown(top); c++) {
    if (c >= 0) { location.hash = '#' + heads[c].id; await wait(200); }
    scrollTo(0, document.documentElement.scrollHeight); await wait(200);
  }
  if (top && shown(top)) {
    await click(top);
    tried++;
    if (!await until(function () { return scrollY <= 1; })) dead.push('top button' + ' changes nothing');
  }
  var back = document.querySelector('.dock .back');
  var link = Array.prototype.find.call(document.querySelectorAll('main a[href^="#"]'), function (a) {
    var t = document.getElementById(decodeURIComponent(a.hash.slice(1)));
    return t && a.hash !== location.hash && !a.closest('nav, .pager');
  });
  if (back && link) {
    var holder = link.closest('[data-chapter]');
    if (holder && !shown(link)) { location.hash = '#' + holder.querySelector('h2').id; await wait(200); }
    link.scrollIntoView(); await wait(200);
    var y = scrollY, hash = location.hash;
    link.click(); await wait(100);
    var flash = document.getElementById(decodeURIComponent(link.hash.slice(1))).getAnimations()
      .some(function (a) { return a.animationName === 'flash'; });
    tried++;
    if (!shown(back)) dead.push('back button not shown after a link');
    else {
      await click(back); await wait(300);
      if (Math.abs(scrollY - y) > 2 || location.hash !== hash) dead.push('back button returns to ' + Math.round(scrollY) + location.hash + ', not ' + Math.round(y) + hash);
    }
    tried++;
    if (!flash) dead.push(link.hash + ' does not flash its target');
  }
  return [tried, dead];
})()"""


def browse(page, paged):
    """(each live swipe's [step reached, steps, steps whose token lies outside its stage's view, or None with no token]
    once scrolled card by card to its end, a `paged` page's chapter_checks, CLICKS' result), in real time."""
    cmd_r, cmd_w = os.pipe()
    out_r, out_w = os.pipe()
    def fds():  # Chrome reads commands on fd 3 and answers on fd 4
        a, b = os.dup(cmd_r), os.dup(out_w)
        os.dup2(a, 3)
        os.dup2(b, 4)
    chrome = subprocess.Popen([CHROME, "--headless", "--remote-debugging-pipe", "--window-size=400,900",
                               f"--user-data-dir={tempfile.mkdtemp()}", "about:blank"], preexec_fn=fds, close_fds=False,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(cmd_r)
    os.close(out_w)
    buf, ids = b"", itertools.count(1)
    def send(method, session=None, **params):
        nonlocal buf
        n = next(ids)
        os.write(cmd_w, json.dumps({"id": n, "method": method, "params": params, **({"sessionId": session} if session else {})}).encode() + b"\0")
        while True:
            while b"\0" not in buf:
                buf += os.read(out_r, 65536)
            msg, buf = buf.split(b"\0", 1)
            msg = json.loads(msg)
            if msg.get("id") == n:
                return msg.get("result", {})
    try:
        target = send("Target.createTarget", url=f"file://{page}")["targetId"]
        session = send("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
        run = lambda js: send("Runtime.evaluate", session, expression=js, returnByValue=True, awaitPromise=True)["result"].get("value")
        time.sleep(1.5)
        chapters = paged and chapter_checks(page, run, lambda url: send("Page.navigate", session, url=url))
        run("document.querySelectorAll('[data-chapter]').forEach(function (c) { c.hidden = false; })")
        rows, out = run(SWIPES), {}
        for k in range(max((n for _, n, _ in rows), default=0)):
            run(f"document.querySelectorAll('[data-swipe].live .steps').forEach(function (s) {{"
                f" s.children[Math.min({k}, s.children.length - 1)].scrollIntoView({{inline: 'center', block: 'nearest'}}); }})")
            time.sleep(1)
            rows = run(SWIPES)
            for i, (_, n, seen) in enumerate(rows):
                if seen is not None:
                    out.setdefault(i, [])
                    if not seen and k < n:
                        out[i].append(k + 1)
        return [[at, n, out.get(i)] for i, (at, n, _) in enumerate(rows)], chapters, run(CLICKS)
    finally:
        chrome.kill()


def chapter_checks(page, run, navigate):
    """({check: [passed, tried]}, [failures]): each way to a chapter must show that chapter alone."""
    n = len(run(SHOWN))
    tally, out = {k: [0, 0] for k in ("load", "nav", "pager", "back")}, []
    def expect(check, want, what):
        tally[check][1] += 1
        for _ in range(20):
            got = run(SHOWN)
            if got == [i == want for i in range(n)]:
                tally[check][0] += 1
                return
            time.sleep(0.05)
        out.append(f"{what} shows chapters {[i + 1 for i, v in enumerate(got) if v]}, not {want + 1}")
    def load(fragment):
        navigate("about:blank")
        navigate(f"file://{page}{fragment}")
        for _ in range(40):
            if run("location.hash === " + json.dumps(fragment) + " && document.readyState === 'complete'"):
                break
            time.sleep(0.05)
    load("")
    expect("load", 0, "a load with no #id")
    for i, (link, at) in enumerate(run("Array.prototype.map.call(document.querySelectorAll('main nav a[href^=\"#\"]'),"
                                       f" function (a) {{ return [a.getAttribute('href'), {HOLDER}(a)]; }})")):
        if at >= 0:
            run(f"document.querySelectorAll('main nav a[href^=\"#\"]')[{i}].click()")
            expect("nav", at, f"nav link {link}")
    load("")
    for i in range(n - 1):
        run(f"document.querySelectorAll('[data-chapter]')[{i}].querySelector('.pager [rel=next]').click()")
        expect("pager", i + 1, f"next from chapter {i + 1}")
    run("history.back()")
    expect("back", n - 2, "back from the last chapter")
    for i in range(n - 1, 0, -1):
        run(f"(function (a) {{ a && a.click(); }})(document.querySelectorAll('[data-chapter]')[{i}].querySelector('.pager [rel=prev]'))")
        expect("pager", i - 1, f"previous from chapter {i + 1}")
    for eid, at in run(CHAPTER_IDS):
        load("#" + eid)
        expect("load", at, f"a load at #{eid}")
    return tally, out


def layout(r, error):
    """The run's line and whether it passed."""
    ok = (r["scroll"] == r["client"] and r["latin"] >= 11 and r["hangul"] >= 12 and r["labels"] == 0
          and not error and (not r["reduced"] or (r["anim"] == 0 and r["shown"] == r["total"])))
    line = (f"layout {'reduced' if r['reduced'] else 'motion'} {r['scroll']}/{r['client']} {r['latin']}px {r['hangul']}px "
            f"anim {r['anim']} steps {r['shown']}/{r['total']} labels {r['labels']}"
            + (" error" if error else ""))
    return line + (" pass" if ok else f" FAIL: widest {r['widest']}"), ok


def jong(c):
    """The final consonant's index of a Hangul syllable, else -1."""
    return (ord(c) - 0xAC00) % 28 if "가" <= c <= "힣" else -1


def plain(sentence):
    """Whether a sentence ends in a plain -다 (솔루션이다, 했다, 한다) or a noun form (했음, 필요함), not a noun (바다, 다음)."""
    s = sentence.rstrip(".!?").rstrip()
    if len(s) < 2:
        return False
    if s[-1] == "다":
        return s[-2] in "이없같많좋않싶" or jong(s[-2]) in (4, 20)  # ㄴ: 한다, 된다; ㅆ: 했다, 있다
    return s[-1] in "함됨" or s[-1] == "음" and jong(s[-2]) == 20  # 했음, 있음, not 마음


def korean(page):
    out = []
    if page["lang"] != "ko":
        out.append(f'lang is "{page["lang"]}", not "ko"')
    for text, cell in [(t, False) for t in page["text"]] + [(t, True) for t in page["cells"]]:
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            out += [f"English: {m.group(0)}" for m in ENGLISH.finditer(line)]
            out += [f"plain ending: {s.strip()}" for s in SENTENCE.findall(line) if plain(s.strip())
                    and not (cell and s.strip()[-1] not in ".!?")]
    out += [f"ASCII arrow: {t}" for t in page["ascii"]]
    out += [f"sentence heading: {h}" for h in page["headings"] if SENTENCE_HEADING.search(h)]
    return out


def mapping(page):
    """Each widget a Mapping row demands that the page lacks: a file-tree for the files it names, a use-case for a flow
    drawn in text."""
    out = []
    if len(page["paths"]) >= FILES and "file-tree" not in page["diagrams"]:
        out.append(f"no file-tree for {', '.join(page['paths'])}")
    if page["flows"] and "use-case" not in page["diagrams"]:
        out.append(f"no use-case for {page['flows'][0]!r}")
    if page["drawn"]:
        out.append(f"{page['drawn']} hand-drawn figure outside a widget")
    return out


BARE = re.compile(r"[+\-−–]?\d[\d,]*(\.\d+)?")
# a unit in a header: in brackets or after a slash, a symbol, or a unit word at its end
UNIT = re.compile(r"[(\[/%‰°₩$€¥£×]|(?<![A-Za-z])(ms|s|m|km|cm|mm|kg|g|KB|MB|GB|TB|px|pt|Hz|fps|rpm)$"
                  r"|(원|개|건|회|번|명|초|분|시간|일|주|달|년|배|점|위|장|줄|쪽|퍼센트)$")


def units(page):
    """Each table column, a chart's axes included, of bare numbers with no unit in its header or cells; the first column,
    the row label, is exempt."""
    out = []
    for n, (head, rows) in enumerate(page["tables"], 1):
        for j in range(1, max(map(len, rows), default=0)):
            cells = [r[j] for r in rows if j < len(r) and r[j]]
            if cells and all(BARE.fullmatch(c) for c in cells) and not (j < len(head) and UNIT.search(head[j])):
                out.append(f"table {n} column {head[j] if j < len(head) else j + 1!r} has bare numbers")
    return out


def shell(page):
    """What the page lacks of its shell: the skin, an h1, each {{...}} filled."""
    return ([] if page["skin"] else ['no <style id="skin">']) + ([] if page["h1"] else ["no h1"]) + [
        f"{h} left" for h in page["held"]]


def num(s):
    m = re.sub(r"[^\d.eE+-]", "", s.replace("−", "-").replace("–", "-"))
    try:
        return float(m)
    except ValueError:
        return None


def scale(spec):
    lo, hi, r0, r1 = map(float, spec.split())
    return lambda v: r0 + (v - lo) / (hi - lo) * (r1 - r0), lo, hi


def near(got, want):
    return got is not None and abs(float(got) - want) <= TOLERANCE


def path_points(d):
    return [(float(x), float(y)) for x, y in re.findall(r"[ML]\s*(-?[\d.]+)[ ,](-?[\d.]+)", d)]


def chart(chart):
    """The failures of one chart, as short strings."""
    out, kind = [], chart["kind"]
    if not chart["tables"] or not chart["tables"][0]["rows"]:
        return ["no data table"]
    said = [s for s in SENTENCE.findall(chart["summary"]) if s.strip()]
    if len(said) != 1 or not re.search(r"[.!?]$", said[0]):
        out.append(f"summary is not one sentence: {chart['summary']!r}")
    last = len(chart["tables"]) - 1
    if chart["slide"] and (chart["moved"] or not chart["live"]) and chart["at"] != last:
        out.append(f"slide stands at table {chart['at'] + 1}, not its last, {last + 1}")
    if chart["slide"] and chart["live"] and not chart["moved"] and chart["at"] != 0:
        out.append(f"slide starts at table {chart['at'] + 1}, not its first")
    tables = [[(r[0], r[1:]) for r in t["rows"]] for t in chart["tables"]]
    everything = [v for t in tables for _, cells in t for v in map(num, cells)]
    numeric = all(num(label) is not None for t in tables for label, _ in t)
    p = chart["panels"][0]
    marks = {m["data-key"]: m for m in p["marks"] if "data-key" in m}
    for i, (label, cells) in enumerate(tables[chart["at"]]):
        v = [num(c) for c in cells]
        keys = [f"r{i}c{j}" for j in range(len(v))]
        for k in keys:
            if k not in marks:
                out.append(f"row {i + 1} ({label}) has no mark {k}")
        if any(k not in marks for k in keys):
            continue
        for j, k in enumerate(keys):
            name = marks[k].get("aria-label", "")
            texts = cells if len(keys) == 1 else [cells[j]]
            if not all(t in name for t in texts):
                out.append(f"mark {k} name {name!r} lacks {texts}")
        def expect(k, *pairs):  # (what, the mark's value, the value its scale gives)
            out.extend(f"{k} {what} {got} is not {w:.2f}" for what, got, w in pairs if not near(got, w))
        X, lo, hi = scale(p["x"])
        if kind == "bar":
            if not lo <= 0 <= hi:
                out.append(f"axis {lo}..{hi} does not start at zero")
            m = marks[keys[0]]
            expect(keys[0], ("x", m.get("x"), min(X(0), X(v[0]))), ("width", m.get("width"), abs(X(v[0]) - X(0))))
        else:
            Y, _, _ = scale(p["y"])
            xv = num(label) if numeric else i
            for j, k in enumerate(keys):
                expect(k, ("cx", marks[k].get("cx"), X(xv)), ("cy", marks[k].get("cy"), Y(v[j])))
    for path in (m for m in p["marks"] if m.get("data-key", "").startswith("p")):
        j = path["data-key"][1:]
        pts = [(float(m["cx"]), float(m["cy"])) for m in p["marks"] if re.fullmatch(rf"r\d+c{j}", m.get("data-key", ""))]
        if path_points(path.get("d", "")) != pts:
            out.append(f"line {path['data-key']} does not pass through its points")
    for axis in ("x", "y"):
        if p.get(axis):
            _, lo, hi = scale(p[axis])
            data = everything
            if axis == "x" and kind == "line":
                data = [num(label) for t in tables for label, _ in t] if numeric else [0]
            if not (lo - TOLERANCE <= min(data) and max(data) <= hi + TOLERANCE):
                out.append(f"{axis} axis {lo}..{hi} does not span the data {min(data)}..{max(data)}")
    return out

def export(page, out):
    """Write each figure of `page` to <out>/<page stem>-<n>.svg in the light scheme, printing each path."""
    svgs = render(SVG, page, REDUCED, "--blink-settings=preferredColorScheme=1")[0]
    if svgs is None:
        print(f"check.py: could not read {page}", file=sys.stderr)
        return 2
    if not svgs:
        print(f"no figure: {page} has no <svg role=\"img\"> or chart")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    for n, svg in enumerate(svgs, 1):
        (out / f"{page.stem}-{n}.svg").write_text(svg)
        print(out / f"{page.stem}-{n}.svg")
    return 0


def empty(source):
    """Whether the page shows no text: nothing but its head, styles, scripts, comments and tags."""
    body = re.sub(r"<(head|title|style|script|template)\b.*?</\1>|<!--.*?-->|<[^>]*>", " ", source, flags=re.S | re.I)
    return not html.unescape(body).strip()


def main():
    if len(sys.argv) not in (2, 4) or len(sys.argv) == 4 and sys.argv[2] != "--svg":
        print("usage: check.py <page.html> [--svg <out dir>]", file=sys.stderr)
        return 2
    page = pathlib.Path(sys.argv[1]).resolve()
    if not page.is_file() or not os.access(CHROME, os.X_OK):
        print(f"check.py: no file {page}" if not page.is_file() else f"check.py: no Chrome at {CHROME}", file=sys.stderr)
        return 2
    if len(sys.argv) == 4:
        return export(page, pathlib.Path(sys.argv[3]))
    if empty(page.read_text(errors="replace")):
        print("empty")
        print("FAIL")
        return 1
    runs = {(frame, mode): render(frame, page, *flags) for frame in (LAYOUT, KOREAN, CHART)
            for mode, flags in (("motion", ()), ("reduced", (REDUCED,))) if frame != KOREAN or mode == "motion"}
    if any(r is None for r, _ in runs.values()):
        print(f"check.py: could not read {page}", file=sys.stderr)
        return 2
    failed = False
    for mode in ("motion", "reduced"):
        line, ok = layout(*runs[LAYOUT, mode])
        failed |= not ok
        print(line)
    out = shell(runs[KOREAN, "motion"][0])
    failed |= bool(out)
    print("shell " + ("FAIL: " + "; ".join(out) if out else "pass"))
    out = korean(runs[KOREAN, "motion"][0])
    failed |= bool(out)
    print("\n".join(f"korean {o} FAIL" for o in out) if out else "korean pass")
    k = runs[KOREAN, "motion"][0]
    ok = k["linked"] == k["h2"] if k["h2"] >= CONTENTS or k["chapters"] else not k["nav"]
    failed |= not ok
    print(f"contents {k['h2']} h2 {k['linked']} linked" + (" nav" if k["nav"] else "") + (" pass" if ok else " FAIL"))
    out = mapping(k)
    failed |= bool(out)
    print(f"mapping {len(k['paths'])} files {len(k['flows'])} flows " + ("FAIL: " + "; ".join(out) if out else "pass"))
    out = units(k)
    failed |= bool(out)
    print(f"units {len(k['tables'])} tables " + ("FAIL: " + "; ".join(out) if out else "pass"))
    for link in k["broken"]:
        failed = True
        print(f"links {link} has no target FAIL")
    paged = k["chapters"] > 0 or (k["h2"] and k["loose"])
    swipes, chapters, (tried, dead) = browse(page, k["chapters"] > 1)
    if paged:
        tally, out = chapters or ({}, [])
        if k["loose"]:
            out.append(f"{k['loose']} h3 outside a chapter")
        if k["chapters"] == 1:
            out.append("one chapter")
        failed |= bool(out)
        print(f"chapters {k['chapters']} " + "".join(f"{c} {p}/{t} " for c, (p, t) in tally.items())
              + ("FAIL: " + "; ".join(out) if out else "pass"))
    for mode in ("motion", "reduced"):
        for n, one in enumerate(runs[CHART, mode][0], 1):
            out = chart(one)
            failed |= bool(out)
            marks = sum(len(p["marks"]) for p in one["panels"])
            print(f"chart {mode} {n} {one['kind']} marks {marks} " + ("FAIL: " + "; ".join(out) if out else "pass"))
    for i, (at, n, out) in enumerate(swipes, 1):
        failed |= at != n or bool(out)
        print(f"swipe {i} step {at}/{n} " + ("pass" if at == n else "FAIL"))
        if out is not None:
            print(f"swipe {i} token in view {n - len(out)}/{n} " + ("FAIL: steps " + ", ".join(map(str, out)) if out else "pass"))
    if tried:
        failed |= bool(dead)
        print(f"clicks {tried - len(dead)}/{tried} " + ("FAIL: " + "; ".join(dead) if dead else "pass"))
    print("FAIL" if failed else "pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
