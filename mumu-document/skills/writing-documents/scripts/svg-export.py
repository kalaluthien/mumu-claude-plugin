#!/usr/bin/env python3
"""Export each figure of a page as a standalone SVG, for a GitHub body or a repository page.

usage: svg-export.py <page.html> <out dir>
Renders the page in headless Chrome (light scheme), takes each <svg role="img"> and each chart's svg, copies every
element's computed paint and type onto it as attributes (where it differs from its parent's), drops classes, adds the page's
background behind it, and writes <out dir>/<page stem>-<n>.svg, printing each path.
Exit 0 written, 1 when the page has no figure, 2 when it could not run, saying why.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

FRAME = r"""<iframe id=f style="width:800px;height:800px;border:0"></iframe>
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


def figures(page):
    """The page's figures as standalone SVG strings, or None when Chrome gave nothing back."""
    return check.render(FRAME, page, "--force-prefers-reduced-motion", "--blink-settings=preferredColorScheme=1")[0]


def main():
    if len(sys.argv) != 3:
        print("usage: svg-export.py <page.html> <out dir>", file=sys.stderr)
        return 2
    page, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2])
    if not page.is_file() or not os.access(check.CHROME, os.X_OK):
        print(f"svg-export.py: no file {page}" if not page.is_file() else f"svg-export.py: no Chrome at {check.CHROME}",
              file=sys.stderr)
        return 2
    svgs = figures(page)
    if svgs is None:
        print(f"svg-export.py: could not read {page}", file=sys.stderr)
        return 2
    if not svgs:
        print(f"no figure: {page} has no <svg role=\"img\"> or chart")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    for n, svg in enumerate(svgs, 1):
        path = out / f"{page.stem}-{n}.svg"
        path.write_text(svg)
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
