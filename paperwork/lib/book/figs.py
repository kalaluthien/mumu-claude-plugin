import json, math, os, re
from .dom import esc

# ---------------------------------------------------------------- figure helper


def _w(s, size):
    return sum(size * (1.0 if re.match(r'[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3\u4e00-\u9fff]', ch) else 0.32 if ch == ' ' else 0.62 if ch.isupper() else 0.55) for ch in s)


class Fig:
    """SVG builder that emits lexicon classes only, so F1 holds by construction.

    f = Fig('f-kl', 360, 160, enc=['p', 'excess'], alt='Bar chart of orders per dish; dish B holds half'); f.rect(10, 10, 50, 40, 'p', opacity=.2); f.text(10, 70, 'label'); f.save()
    `phone` is the rendered width on a phone (about 358 for a full-width figure, 150 for one frame); save() fails
    when a label leaves the viewBox or would render below `min_px`. `pan=True` keeps the figure at its own width on
    narrow screens, where the reader drags it sideways, so labels are checked at full size.
    `pattern='id'` labels the figure with a visual pattern (`data-pattern`), which the brief and the review gate's 2-use rule count.
    `alt` (required by save) names the kind, what it encodes and the point: 'Bar chart of orders per dish; dish B holds half'.
    Selectable diagram: `with f.node('id', 'what this node means'):` wraps the node's shapes; `f.edge('a', 'b')` draws
    a connector the shell highlights when either end is selected.
    """

    def __init__(self, fid, w, h, enc=(), size=12, phone=358, min_px=11, pan=False, alt=None, pattern=None):
        self.alt, self.pattern = alt, pattern
        self.id, self.w, self.h, self.enc, self.size, self.items, self.texts = fid, w, h, list(enc), size, [], []
        self.pan, self.scale, self.min_px = pan, 1.0 if pan else min(1.0, phone / w), min_px

    def _cls(self, enc, mode, dash, extra=''):
        if enc and enc not in self.enc:
            raise ValueError(f'{self.id}: lexicon entry {enc} not declared in enc')
        return ' '.join(x for x in ((f'lx-{enc}' if enc else ''), mode, 'dash' if dash else '', extra) if x)

    @staticmethod
    def _op(opacity):
        return f' fill-opacity="{opacity:g}"' if opacity is not None else ''

    def rect(self, x, y, w, h, enc=None, mode='fill', dash=False, rx=0, opacity=None):
        self.items.append(f'<rect class="{self._cls(enc, mode, dash)}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"' + (f' rx="{rx:g}"' if rx else '') + self._op(opacity) + '/>')

    def panel(self, x, y, w, h, rx=6, dash=False):
        """Neutral box in the page's panel and line colours."""
        self.items.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" fill="var(--panel)" stroke="var(--line)" stroke-width="1.2"' + (' stroke-dasharray="5 4"' if dash else '') + '/>')

    def box(self, x, y, w, h, label, enc=None, opacity=0.18, dash=False, size=None):
        """Labelled box: a soft lexicon fill with its outline, or a neutral panel; the label is centred and fit-checked."""
        if enc:
            self.rect(x, y, w, h, enc, 'fill', rx=5, opacity=opacity)
            self.rect(x, y, w, h, enc, 'line', dash, rx=5)
        else:
            self.panel(x, y, w, h, dash=dash)
        sz = size or self.size
        if _w(label, sz) > w - 6:
            raise ValueError(f'{self.id}: label "{label}" is wider than its box ({_w(label, sz):.0f} > {w - 6:g})')
        self.text(x + w / 2, y + h / 2 + sz * 0.36, label, 'middle', size=sz)

    def ring(self, x, y, w, h, pad=3):
        """Ink outline that marks the focused region of a home figure."""
        self.items.append(f'<rect x="{x - pad:g}" y="{y - pad:g}" width="{w + 2 * pad:g}" height="{h + 2 * pad:g}" rx="7" fill="none" stroke="var(--ink)" stroke-width="2"/>')

    def line(self, x1, y1, x2, y2, enc=None, dash=False):
        self.items.append(f'<line class="{self._cls(enc, "line", dash)}" x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"/>')

    def path(self, d, enc=None, mode='line', dash=False, opacity=None):
        self.items.append(f'<path class="{self._cls(enc, mode, dash)}" d="{d}"{self._op(opacity)}/>')

    def circle(self, cx, cy, r, enc=None, mode='fill', dash=False, opacity=None):
        self.items.append(f'<circle class="{self._cls(enc, mode, dash)}" cx="{cx:g}" cy="{cy:g}" r="{r:g}"{self._op(opacity)}/>')

    def arrow(self, x1, y1, x2, y2, enc=None, head=7):
        a = math.atan2(y2 - y1, x2 - x1)
        p = [(x2 - head * math.cos(a - s), y2 - head * math.sin(a - s)) for s in (0.45, -0.45)]
        self.line(x1, y1, x2, y2, enc)
        self.path(f'M{x2:.1f},{y2:.1f}L{p[0][0]:.1f},{p[0][1]:.1f}L{p[1][0]:.1f},{p[1][1]:.1f}Z', enc, 'fill')

    def text(self, x, y, s, anchor='start', cls='', size=None, enc=None, weight=None):
        size = size or self.size
        self.texts.append((x, y, s, anchor, size))
        c = ' '.join(x for x in ((self._cls(enc, 'fill', False) if enc else ''), cls) if x)
        attr = f' class="{c}"' if c else ''
        fs = '' if size == self.size else f' font-size="{size:g}"'
        fw = f' font-weight="{esc(str(weight))}"' if weight else ''
        self.items.append(f'<text{attr} x="{x:g}" y="{y:g}" text-anchor="{anchor}"{fs}{fw}>{esc(s)}</text>')

    class _Group:
        def __init__(self, fig, open_tag):
            self.fig, self.open_tag = fig, open_tag

        def __enter__(self):
            self.fig.items.append(self.open_tag)
            return self.fig

        def __exit__(self, *a):
            self.fig.items.append('</g>')

    def node(self, nid, note):
        """Group the shapes of one selectable node; `note` is shown below the figure when the reader taps it."""
        return Fig._Group(self, f'<g data-node="{esc(nid)}" data-note="{esc(note)}">')

    def edge(self, a, b, x1, y1, x2, y2, enc=None, arrow=True):
        """A connector between nodes a and b, highlighted when either is selected."""
        with Fig._Group(self, f'<g data-edge="{esc(a)} {esc(b)}">'):
            (self.arrow if arrow else self.line)(x1, y1, x2, y2, enc)

    def svg(self):
        for x, y, s, anchor, size in self.texts:
            w = _w(s, size)
            x0 = x - (w if anchor == 'end' else w / 2 if anchor == 'middle' else 0)
            if x0 < -0.5 or x0 + w > self.w + 0.5 or y - size < -0.5 or y > self.h + 0.5:
                raise ValueError(f'{self.id}: label "{s}" leaves the viewBox (needs {x0:.0f}..{x0 + w:.0f} of 0..{self.w})')
            if size * self.scale < self.min_px:
                raise ValueError(f'{self.id}: label "{s}" renders at {size * self.scale:.1f}px on a phone; relayout, split, or pass pan=True')
        pan = (' data-pan=""' if self.pan else '') + (f' data-pattern="{esc(self.pattern)}"' if self.pattern else '')  # pattern: the visual-pattern label (review gate counts it)
        return f'<svg viewBox="0 0 {self.w:g} {self.h:g}" role="img" aria-label="{esc(self.alt or "")}" font-size="{self.size:g}"{pan}>' + ''.join(self.items) + '</svg>'

    def save(self, d='figs'):
        if not (self.alt or '').strip() or self.alt.strip() == self.id:
            raise ValueError(f'{self.id}: pass alt naming the kind, what it encodes and the point (lint F8 counts its words)')
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, self.id + '.svg')
        open(p, 'w', encoding='utf-8').write(self.svg())
        return p


def fact(name, value, text=None, path='facts.json'):
    """Record a computed number for data-v spans and strips; returns the value so scripts can assert on it."""
    j = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    j[name] = {'value': value, 'text': text if text is not None else (f'{value:g}' if isinstance(value, (int, float)) else str(value))}
    json.dump(j, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return value
