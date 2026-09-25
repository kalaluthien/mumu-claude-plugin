#!/usr/bin/env python3
"""Check an Artifact page in headless Chrome; print one line per check, then `pass` or `FAIL`.

usage: check.py <page.html>
- layout, in a 320 px frame, with motion and with reduced motion: after tapping each hint
  (an enabled [popovertarget]) open and shut and clicking each control once, it fails on a
  sideways scroll, text under 11 px (Hangul or Han under 12 px), an SVG label overlapping
  another or leaving its figure, a hint a tap leaves shut, or an uncaught error; the reduced
  run also on a running animation or a slide or swipe showing fewer captions than it has steps.
- korean: over every text node, the <title>, SVG <title> and <desc>, and each alt,
  aria-label, title and placeholder, skipping <code>, <pre>, <kbd> and <samp>, and joining a
  block across inline tags: fails on <html lang> other than "ko", a run of 3 or more English
  words, a sentence ending in a plain -다., or a heading that is a sentence.
- chart, with motion and with reduced motion (a slide then stands at its last table): each
  chart against its own table and scales (the svg's data-x and data-y: domain low, high,
  range start, end); fails on a mark off its value (bars from zero), a value with no mark or
  a mark whose name lacks its cell's text, a mark the arrow keys do not reach, a slide not
  starting at its first table or not reaching its last through Next, no data table, a summary that is not one sentence,
  or facet panels on different scales.
Exit 0 pass, 1 FAIL, 2 when it could not run, saying why.
"""
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REDUCED = "--force-prefers-reduced-motion"
TOLERANCE = 0.02
STEPS = 5
MIN_RUN = 3
WORD = r"[A-Za-z]+(?:['’-][A-Za-z]+)*[.,:;!?]?"
ENGLISH = re.compile(rf"{WORD}(?:\s+{WORD}){{{MIN_RUN - 1},}}")
SENTENCE = re.compile(r"[^.!?\n]*[.!?]")
PLAIN = re.compile(r"(?<!니)다\.$")
SENTENCE_HEADING = re.compile(r"(니다|[아어여해예에세네지]요|다)[.!?]?$|[.!?]$")
LAYOUT = r"""<iframe id=f style="width:320px;height:800px;border:0"></iframe>
<script>
f.onload = function () {
  f.onload = null;
  var d = f.contentDocument, w = f.contentWindow, hints = d.querySelectorAll('[popovertarget]:not(:disabled)'), opened = 0;
  hints.forEach(function (h) {
    var t = d.getElementById(h.getAttribute('popovertarget'));
    h.click();
    if (t && t.matches(':popover-open')) { opened++; h.click(); }
  });
  d.querySelectorAll('button,summary,input,select').forEach(function (c) { c.click(); });
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
    document.body.dataset.r = JSON.stringify({ reduced: reduced, scroll: e.scrollWidth, client: e.clientWidth, latin: s[0], hangul: s[1],
      anim: anim, shown: shown, total: total, labels: bad, opened: opened, hints: hints.length });
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
    var block = function (el) {
      while (el.parentElement && !(el instanceof w.SVGElement) && !/^(button|label|option|summary)$/i.test(el.tagName)
             && w.getComputedStyle(el).display === 'inline') el = el.parentElement;
      return el;
    };
    var t = d.createTreeWalker(d.documentElement, 4), n;
    while ((n = t.nextNode())) {
      var p = n.parentElement;
      if (!p || p.closest(SKIP) || !n.data.trim()) continue;
      var b = block(p);
      if (!groups.has(b)) groups.set(b, []);
      groups.get(b).push(p.closest(CODE) ? '\n' : n.data);
    }
    groups.forEach(function (g) { out.push(g.join('')); });
    d.querySelectorAll('[alt],[aria-label],[title],[placeholder]').forEach(function (el) {
      ['alt', 'aria-label', 'title', 'placeholder'].forEach(function (a) { if (el.getAttribute(a)) out.push(el.getAttribute(a)); });
    });
    var heads = Array.prototype.map.call(d.querySelectorAll('h1,h2,h3,h4,h5,h6'), function (h) { return h.textContent.replace(/\s+/g, ' ').trim(); });
    document.body.dataset.r = JSON.stringify({ lang: d.documentElement.lang, text: out, headings: heads });
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
      var marks = Array.prototype.slice.call(fig.querySelectorAll('.mark')), seen = [];
      var m = marks.filter(function (x) { return x.getAttribute('tabindex') === '0'; })[0];
      if (m) { m.focus(); m.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true })); m = d.activeElement; }
      for (var i = 0; m && i < marks.length; i++) {
        m.focus();
        if (d.activeElement !== m) break;
        seen.push(m.dataset.key);
        m.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
        m = d.activeElement === m ? null : d.activeElement;
      }
      return { kind: fig.dataset.chart, facet: fig.hasAttribute('data-facet'), at: +fig.dataset.at, tables: tables, seen: seen,
        slide: fig.hasAttribute('data-slide'), live: fig.classList.contains('live'), moved: moved,
        summary: (fig.querySelector('figcaption') || { textContent: '' }).textContent.trim(),
        panels: Array.prototype.map.call(fig.querySelectorAll('.plot svg'), function (s) {
          return { x: s.dataset.x, y: s.dataset.y, v: s.dataset.v, marks: Array.prototype.map.call(s.querySelectorAll('.marks > *'), function (k) {
            var a = attrs(k);
            Array.prototype.forEach.call(k.children, function (c) { a[c.getAttribute('class')] = attrs(c); });
            return a;
          }) };
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


def layout(r, error):
    """The run's line and whether it passed."""
    ok = (r["scroll"] == r["client"] and r["latin"] >= 11 and r["hangul"] >= 12 and r["labels"] == 0
          and r["opened"] == r["hints"] and not error and (not r["reduced"] or (r["anim"] == 0 and r["shown"] == r["total"])))
    line = (f"layout {'reduced' if r['reduced'] else 'motion'} {r['scroll']}/{r['client']} {r['latin']}px {r['hangul']}px "
            f"anim {r['anim']} steps {r['shown']}/{r['total']} labels {r['labels']} hints {r['opened']}/{r['hints']}"
            + (" error" if error else ""))
    return line + (" pass" if ok else " FAIL"), ok


def korean(page):
    out = []
    if page["lang"] != "ko":
        out.append(f'lang is "{page["lang"]}", not "ko"')
    for text in page["text"]:
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            out += [f"English: {m.group(0)}" for m in ENGLISH.finditer(line)]
            out += [f"plain ending: {s.strip()}" for s in SENTENCE.findall(line) if PLAIN.search(s.strip())]
    out += [f"sentence heading: {h}" for h in page["headings"] if SENTENCE_HEADING.search(h)]
    return out


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
    if not re.fullmatch(r"[^.!?]+[.!?]", chart["summary"]):
        out.append(f"summary is not one sentence: {chart['summary']!r}")
    last = len(chart["tables"]) - 1
    if chart["slide"] and (chart["moved"] or not chart["live"]) and chart["at"] != last:
        out.append(f"slide stands at table {chart['at'] + 1}, not its last, {last + 1}")
    if chart["slide"] and chart["live"] and not chart["moved"] and chart["at"] != 0:
        out.append(f"slide starts at table {chart['at'] + 1}, not its first")
    split = lambda row: (row[0], row[1], row[2:]) if chart["facet"] else (None, row[0], row[1:])
    tables = [[split(r) for r in t["rows"]] for t in chart["tables"]]
    rows = tables[chart["at"]]
    everything = [v for t in tables for _, _, cells in t for v in map(num, cells)]
    numeric = all(num(label) is not None for t in tables for _, label, _ in t)
    marks = {m["data-key"]: m for p in chart["panels"] for m in p["marks"] if "data-key" in m}
    named = [k for k in marks if not k.startswith("p")]  # every mark but a line's path
    if sorted(chart["seen"]) != sorted(named):
        out.append(f"keyboard reaches {len(set(chart['seen']))} of {len(named)} marks")
    panel_of = {}
    for p in chart["panels"]:
        for m in p["marks"]:
            panel_of[m.get("data-key")] = p
    if chart["facet"] and len({(p["x"], p["y"]) for p in chart["panels"]}) > 1:
        out.append("facet panels on different scales")
    position = {}
    for i, (group, label, cells) in enumerate(rows):
        position[i] = sum(1 for g, _, _ in rows[:i] if g == group)
    lo_v = min(everything)
    hi_v = max(everything)
    for i, (group, label, cells) in enumerate(rows):
        v = [num(c) for c in cells]
        keys = [f"r{i}"] if kind in ("scatter", "histogram", "box") else [f"r{i}c{j}" for j in range(len(v))]
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
        p = panel_of[keys[0]]
        bad = lambda what, got, want: out.append(f"{k} {what} {got} is not {want:.2f}")
        if kind in ("bar", "stacked", "dot", "box"):
            X, lo, hi = scale(p["x"])
            if kind in ("bar", "stacked") and not lo <= 0 <= hi:
                out.append(f"axis {lo}..{hi} does not start at zero")
            for j, k in enumerate(keys):
                m = marks[k]
                if kind == "bar":
                    want = (min(X(0), X(v[0])), abs(X(v[0]) - X(0)))
                    for what, got, w in (("x", m.get("x"), want[0]), ("width", m.get("width"), want[1])):
                        if not near(got, w):
                            bad(what, got, w)
                elif kind == "stacked":
                    a, b = X(sum(v[:j])), X(sum(v[:j + 1]))
                    for what, got, w in (("x", m.get("x"), a), ("width", m.get("width"), b - a)):
                        if not near(got, w):
                            bad(what, got, w)
                elif kind == "dot":
                    if not near(m.get("cx"), X(v[j])):
                        bad("cx", m.get("cx"), X(v[j]))
                else:
                    mn, q1, med, q3, mx = v
                    for what, got, w in (("whisker x1", m["whisker"].get("x1"), X(mn)), ("whisker x2", m["whisker"].get("x2"), X(mx)),
                                         ("box x", m["box"].get("x"), X(q1)), ("box width", m["box"].get("width"), X(q3) - X(q1)),
                                         ("median", m["median"].get("x1"), X(med))):
                        if not near(got, w):
                            bad(what, got, w)
        elif kind == "heatmap":
            lo, hi = map(float, p["v"].split())
            for j, k in enumerate(keys):
                want = 3 if hi == lo else min(STEPS, int((v[j] - lo) / (hi - lo) * STEPS) + 1)
                if f"s{want}" not in marks[k].get("class", "").split():
                    out.append(f"heatmap {k} value {cells[j]} is not in step s{want}: {marks[k].get('class')}")
            if (lo, hi) != (lo_v, hi_v):
                out.append(f"heatmap steps span {lo}..{hi}, not the data's {lo_v}..{hi_v}")
        else:
            X, xlo, xhi = scale(p["x"])
            Y, ylo, yhi = scale(p["y"])
            m = marks[keys[0]]
            if kind == "histogram":
                a, b = X(v[0]), X(v[1])
                if ylo > 0:
                    out.append(f"histogram counts start at {ylo}, not zero")
                for what, got, w in (("x", m.get("x"), a), ("width", m.get("width"), b - a),
                                     ("y", m.get("y"), Y(v[2])), ("height", m.get("height"), Y(0) - Y(v[2]))):
                    if not near(got, w):
                        bad(what, got, w)
            elif kind == "scatter":
                for what, got, w in (("cx", m.get("cx"), X(v[0])), ("cy", m.get("cy"), Y(v[1]))):
                    if not near(got, w):
                        bad(what, got, w)
            else:
                xv = num(label) if numeric else position[i]
                for j, k in enumerate(keys):
                    for what, got, w in (("cx", marks[k].get("cx"), X(xv)), ("cy", marks[k].get("cy"), Y(v[j]))):
                        if not near(got, w):
                            bad(what, got, w)
    if kind in ("line", "spark"):
        for p in chart["panels"]:
            for path in (m for m in p["marks"] if m.get("data-key", "").startswith("p")):
                j = path["data-key"][1:]
                pts = [(float(m["cx"]), float(m["cy"])) for m in p["marks"] if re.fullmatch(rf"r\d+c{j}", m.get("data-key", ""))]
                if path_points(path.get("d", "")) != pts:
                    out.append(f"line {path['data-key']} does not pass through its points")
    for p in chart["panels"]:
        for axis in ("x", "y"):
            if p.get(axis) and kind not in ("heatmap",):
                _, lo, hi = scale(p[axis])
                data = everything if axis == "y" or kind in ("bar", "stacked", "dot", "box") else None
                if kind == "scatter":
                    data = [num(c[0 if axis == "x" else 1]) for t in tables for _, _, c in t]
                elif kind == "histogram":
                    data = [num(x) for t in tables for _, _, c in t for x in (c[:2] if axis == "x" else c[2:])]
                elif kind == "stacked":
                    data = [sum(map(num, c)) for t in tables for _, _, c in t]
                elif axis == "x" and kind in ("line", "spark"):
                    data = [num(label) for t in tables for _, label, _ in t] if numeric else [0]
                if data and not lo - TOLERANCE <= min(data) and max(data) <= hi + TOLERANCE:
                    out.append(f"{axis} axis {lo}..{hi} does not span the data {min(data)}..{max(data)}")
    return out

def main():
    if len(sys.argv) != 2:
        print("usage: check.py <page.html>", file=sys.stderr)
        return 2
    page = pathlib.Path(sys.argv[1]).resolve()
    if not page.is_file() or not os.access(CHROME, os.X_OK):
        print(f"check.py: no file {page}" if not page.is_file() else f"check.py: no Chrome at {CHROME}", file=sys.stderr)
        return 2
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
    out = korean(runs[KOREAN, "motion"][0])
    failed |= bool(out)
    print("\n".join(f"korean {o} FAIL" for o in out) if out else "korean pass")
    for mode in ("motion", "reduced"):
        for n, one in enumerate(runs[CHART, mode][0], 1):
            out = chart(one)
            failed |= bool(out)
            marks = sum(len(p["marks"]) for p in one["panels"])
            print(f"chart {mode} {n} {one['kind']} marks {marks} keys {len(one['seen'])} " + ("FAIL: " + "; ".join(out) if out else "pass"))
    print("FAIL" if failed else "pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
