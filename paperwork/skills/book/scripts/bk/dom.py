import glob, html, math, os, re
from html.parser import HTMLParser

# ---------------------------------------------------------------- tiny DOM
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
BLOCKS = {'p', 'li', 'dd', 'dt', 'div', 'td', 'th', 'figcaption', 'h1', 'h2', 'h3', 'h4', 'summary', 'section', 'tr', 'ol', 'ul', 'figure', 'details', 'header', 'nav'}


SVG_CASE = {k.lower(): k for k in ('viewBox', 'preserveAspectRatio', 'textLength', 'lengthAdjust', 'markerWidth', 'markerHeight', 'refX', 'refY', 'patternUnits',
                                     'gradientUnits', 'attributeName', 'repeatCount', 'keyTimes', 'calcMode', 'stdDeviation', 'dominantBaseline')}


class Node:
    __slots__ = ('tag', 'attrs', 'kids', 'parent')

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.kids, self.parent = tag, dict(attrs or {}), [], parent

    def get(self, k, d=None):
        return self.attrs.get(k, d)

    def has(self, k):
        return k in self.attrs

    def walk(self):
        for k in self.kids:
            if isinstance(k, Node):
                yield k
                yield from k.walk()

    def find(self, pred):
        return [n for n in self.walk() if pred(n)]

    def first(self, pred):
        return next((n for n in self.walk() if pred(n)), None)

    def up(self, pred):
        p = self.parent
        while p is not None:
            if pred(p):
                return p
            p = p.parent
        return None

    def text(self, skip=lambda n: False):
        out = []
        for k in self.kids:
            if isinstance(k, str):
                out.append(k)
            elif not skip(k) and k.tag != '#comment':
                out.append(k.text(skip))
                if k.tag in BLOCKS:
                    out.append(' ')
        return ''.join(out)

    def html(self):
        if self.tag == '#comment':
            return f'<!--{self.attrs["text"]}-->'
        inner = ''.join((k if self.tag in ('script', 'style') else html.escape(k, quote=False)) if isinstance(k, str) else k.html() for k in self.kids)
        if self.tag == '#root':
            return inner
        a = ''.join(f' {SVG_CASE.get(k, k)}' if v is None else f' {SVG_CASE.get(k, k)}="{html.escape(v, quote=True)}"' for k, v in self.attrs.items())
        return f'<{self.tag}{a}>' if self.tag in VOID else f'<{self.tag}{a}>{inner}</{self.tag}>'


class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node('#root')

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        c = self.cur
        while c is not self.root and c.tag != tag:
            c = c.parent
        if c is not self.root:
            self.cur = c.parent

    def handle_data(self, d):
        self.cur.kids.append(d)

    def handle_comment(self, d):
        self.cur.kids.append(Node('#comment', {'text': d}, self.cur))


def parse(s):
    p = _P()
    p.feed(s)
    p.close()
    return p.root


def canon(s):
    """Tags, attributes and normalised text of a fragment: the comparison key for chrome."""
    root = parse(s) if isinstance(s, str) else s
    inmath = lambda n: n.up(lambda p: p is not n and p.has('data-m')) is not None
    nodes = [n for n in ([] if root.tag == '#root' else [root]) + list(root.walk()) if n.tag != '#comment' and not inmath(n)]
    tags = ' '.join(n.tag + '|' + ' '.join(f'{k}={v}' for k, v in sorted(n.attrs.items()) if k != 'data-tex') for n in nodes)
    tex = ' '.join(n.get('data-tex') if n.get('data-tex') is not None else n.text() for n in nodes if n.has('data-m'))
    return re.sub(r'\s+', ' ', tags + ' ' + root.text(lambda n: n.has('data-m')) + ' ' + tex).strip()


def is_c(n, *names):
    return n.get('data-c') in names


SKIP_VIS = lambda n: n.tag in ('svg', 'script', 'style') or n.has('data-m') or n.get('data-d') in ('nav', 'pn', 'head') or n.get('class') in ('blab', 'qn', 'tag')
NO_MATH = lambda n: n.tag in ('svg', 'script', 'style') or n.has('data-m')


def vis(n):
    return re.sub(r'\s+', ' ', n.text(SKIP_VIS)).strip()


def sentences(t):
    return [s.strip() for s in re.split(r'(?<=[.!?。？！])\s+', t) if len(s.strip()) > 2]


esc = lambda s: html.escape(str(s), quote=True)

# ---------------------------------------------------------------- color


def oklch_to_lum(s):
    m = re.match(r'oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)', s or '')
    if not m:
        return None
    L = float(m.group(1)) / (100 if m.group(2) else 1)
    C, h = float(m.group(3)), math.radians(float(m.group(4)))
    a, b = C * math.cos(h), C * math.sin(h)
    l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
    l, mm, ss = l_ ** 3, m_ ** 3, s_ ** 3
    rgb = (4.0767416621 * l - 3.3077115913 * mm + 0.2309699292 * ss, -1.2684380046 * l + 2.6097574011 * mm - 0.3413193965 * ss, -0.0041960863 * l - 0.7034186147 * mm + 1.7076147010 * ss)
    r, g, bl = (min(1.0, max(0.0, x)) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl


def contrast(y1, y2):
    return (max(y1, y2) + 0.05) / (min(y1, y2) + 0.05)


BG = {'light': oklch_to_lum('oklch(0.99 0.004 85)'), 'dark': oklch_to_lum('oklch(0.19 0.01 260)')}

# ---------------------------------------------------------------- HTML lint


def unit_blocks(sec):
    """Top-level components of a unit, in order."""
    return [n for n in sec.walk() if n.get('data-c') and not n.up(lambda p: p is not sec and p.get('data-c') is not None)]


TEXTISH = re.compile(r'\\(?:mathbb|mathrm|mathsf|mathit|mathcal|text|operatorname)\{[^{}]*\}')




def tex_of(n):
    return [x.get('data-tex') if x.get('data-tex') is not None else x.text() for x in n.find(lambda x: x.has('data-m'))]


def prose_blocks(sec):
    return sec.find(lambda n: n.tag in ('p', 'li', 'dd', 'td', 'figcaption') and not n.up(lambda p: p.tag == 'svg' or p.get('data-d') is not None) and not n.find(lambda x: x.tag in ('p', 'li')))


def opts(n):
    ol = n.first(lambda x: x.get('data-p') == 'opts')
    return [] if ol is None else [k for k in ol.kids if isinstance(k, Node) and k.tag == 'li']

# ---------------------------------------------------------------- demos



def read_js(d):
    """The book's script: book.js, then js/*.js in name order (one file per demo owner)."""
    parts = [os.path.join(d, 'book.js')] + sorted(glob.glob(os.path.join(d, 'js', '*.js')))
    return '\n'.join(open(f, encoding='utf-8').read() for f in parts if os.path.exists(f))
