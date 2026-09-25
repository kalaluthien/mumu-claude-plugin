#!/usr/bin/env python3
"""Check every chart widget on a page against its own table; print one line per chart, then `pass` or `FAIL`.

usage: chart-check.py <page.html>
Renders the page in headless Chrome twice, with motion and with reduced motion (a player then
stands at its last table), reads each chart's drawn table, its scales (the svg's data-x and
data-y: domain low, high, range start, end) and its marks, and fails a chart on:
- a mark off its value through the scale: bar and stacked from zero (x at the scale of the
  sum before it, width to the sum with it), dot and scatter centres, line and spark points
  and paths, histogram bins from zero, box whisker, box and median, a heatmap cell's step
  of 5 from the lowest value to the highest, or an axis not spanning every step's data;
- a value with no mark, or a mark whose name lacks its cell's text;
- a mark the arrow keys do not reach from the first;
- no data table, or a summary (figcaption) that is not one sentence;
- facet panels on different scales.
Exit 0 pass, 1 FAIL, 2 when it could not run, saying why.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "chrome"))
import chrome  # noqa: E402

TOLERANCE = 0.02
STEPS = 5
FRAME = r"""<iframe id=f style="width:800px;height:800px;border:0"></iframe>
<script>
f.onload = function () {
  f.onload = null;
  setTimeout(function () {
    var d = f.contentDocument, out = [];
    var attrs = function (e) { var o = {}; Array.prototype.forEach.call(e.attributes, function (a) { o[a.name] = a.value; }); return o; };
    d.querySelectorAll('[data-widget="chart"]').forEach(function (fig) {
      var tables = Array.prototype.map.call(fig.querySelectorAll('details table'), function (t) {
        return { head: Array.prototype.map.call(t.tHead.rows[0].cells, function (c) { return c.textContent.trim(); }),
                 rows: Array.prototype.map.call(t.tBodies[0].rows, function (r) { return Array.prototype.map.call(r.cells, function (c) { return c.textContent.trim(); }); }) };
      });
      var marks = Array.prototype.slice.call(fig.querySelectorAll('.mark')), seen = [];
      var m = marks.filter(function (x) { return x.getAttribute('tabindex') === '0'; })[0];
      for (var i = 0; m && i < marks.length; i++) {
        m.focus();
        if (d.activeElement !== m) break;
        seen.push(m.dataset.key);
        m.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
        m = d.activeElement === m ? null : d.activeElement;
      }
      out.push({ kind: fig.dataset.chart, facet: fig.hasAttribute('data-facet'), at: +fig.dataset.at, tables: tables, seen: seen,
        summary: (fig.querySelector('figcaption') || { textContent: '' }).textContent.trim(),
        panels: Array.prototype.map.call(fig.querySelectorAll('.plot svg'), function (s) {
          return { x: s.dataset.x, y: s.dataset.y, v: s.dataset.v, marks: Array.prototype.map.call(s.querySelectorAll('.marks > *'), function (k) {
            var a = attrs(k);
            Array.prototype.forEach.call(k.children, function (c) { a[c.getAttribute('class')] = attrs(c); });
            return a;
          }) };
        }) });
    });
    document.body.dataset.r = JSON.stringify(out);
  }, 500);
};
f.src = location.hash.slice(1);
</script>"""


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


def check(chart):
    """The failures of one chart, as short strings."""
    out, kind = [], chart["kind"]
    if not chart["tables"] or not chart["tables"][0]["rows"]:
        return ["no data table"]
    if not re.fullmatch(r"[^.!?]+[.!?]", chart["summary"]):
        out.append(f"summary is not one sentence: {chart['summary']!r}")
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
        print("usage: chart-check.py <page.html>", file=sys.stderr)
        return 2
    page = pathlib.Path(sys.argv[1]).resolve()
    if not page.is_file() or not chrome.available():
        print(f"chart-check.py: no file {page} or no Chrome", file=sys.stderr)
        return 2
    failed = False
    for mode, flags in (("motion", ()), ("reduced", ("--force-prefers-reduced-motion",))):
        charts = chrome.render(FRAME, page, *flags)
        if charts is None:
            print(f"chart-check.py: could not read {page}", file=sys.stderr)
            return 2
        for n, chart in enumerate(charts, 1):
            out = check(chart)
            failed |= bool(out)
            marks = sum(len(p["marks"]) for p in chart["panels"])
            print(f"{mode} {n} {chart['kind']} marks {marks} keys {len(chart['seen'])} " + ("FAIL: " + "; ".join(out) if out else "pass"))
    print("FAIL" if failed else "pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
