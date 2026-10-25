import json, os, re, shutil
from html.parser import HTMLParser
from .build import CARDS, build, fill_refs
from .plan import Plan, PlanError
from .const import TEMPLATES
from .dom import VOID, parse, vis
from .text import emit_text
from .lint import lint, tag_balance

# ---------------------------------------------------------------- code-first HTML: snippets, outline, show, edit


def snippet(kind=None, src=None):
    """Print one markup snippet from assets/templates/units.html (<!--snip:KIND--> ... <!--/snip-->), or list the kinds."""
    path = src or os.path.join(TEMPLATES, 'units.html')
    s = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    snips = {m.group(1): m.group(2).strip('\n') for m in re.finditer(r'<!--\s*snip:([\w-]+)\s*-->(.*?)<!--\s*/snip\s*-->', s, re.DOTALL)}
    if not snips:
        print(f'no <!--snip:KIND--> markers in {path}')
        return 1
    if not kind:
        for k, v in snips.items():
            print(f'{k:14} {len(v):5} chars')
        return 0
    if kind not in snips:
        print(f'no snippet {kind}; kinds: {", ".join(snips)}')
        return 1
    print(snips[kind])
    return 0


class _Spans(HTMLParser):
    """Element spans (offsets into the source) with parent links; unclosed elements end where their parent ends."""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.t, self.out, self.stack = text, [], []
        self.ls = [0] + [m.end() for m in re.finditer('\n', text)]

    def _off(self):
        ln, col = self.getpos()
        return self.ls[ln - 1] + col

    def _rec(self, tag, attrs, closed):
        s = self._off()
        e = s + len(self.get_starttag_text())
        r = dict(tag=tag, attrs=dict(attrs), start=s, end=e if closed else None, line=self.getpos()[0], parent=self.stack[-1] if self.stack else None, i=len(self.out))
        self.out.append(r)
        if not closed:
            self.stack.append(r['i'])

    def handle_starttag(self, tag, attrs):
        self._rec(tag, attrs, tag in VOID)

    def handle_startendtag(self, tag, attrs):
        self._rec(tag, attrs, True)

    def handle_endtag(self, tag):
        s = self._off()
        e = self.t.find('>', s) + 1
        for k in range(len(self.stack) - 1, -1, -1):
            if self.out[self.stack[k]]['tag'] == tag:
                for j in self.stack[k + 1:]:
                    self.out[j]['end'] = s
                self.out[self.stack[k]]['end'] = e
                del self.stack[k:]
                return


def spans(text):
    p = _Spans(text)
    p.feed(text)
    p.close()
    for r in p.out:
        if r['end'] is None:
            r['end'] = len(text)
    return p.out


def unit_src(d, uid):
    """(path, file text, section span) of a unit's source: units/*.html or units.html."""
    files = [os.path.join(d, 'units', f) for f in sorted(os.listdir(os.path.join(d, 'units'))) if f.endswith('.html')] if os.path.isdir(os.path.join(d, 'units')) else [os.path.join(d, 'units.html')]
    for f in files:
        if not os.path.exists(f):
            continue
        t = open(f, encoding='utf-8').read()
        m = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', t, re.DOTALL)
        if m:
            return f, t, (m.start(1), m.end(1))
    raise PlanError(f'unit {uid} has no <section data-u="{uid}"> in units/*.html or units.html')


def _unit_spans(d, uid):
    """(path, text, spans inside the section, top-level spans); cards without an id get the id build gives them (c-UNIT-N)."""
    f, t, (a, b) = unit_src(d, uid)
    sp = [r for r in spans(t) if r['start'] >= a and r['end'] <= b]
    inside = {r['i'] for r in sp}
    n = 0
    for r in sp:
        r['id'] = r['attrs'].get('id')
        if r['attrs'].get('data-c') in CARDS:
            n += 1
            r['id'] = r['id'] or f'c-{uid}-{n}'
    top = [r for r in sp if r['parent'] not in inside]
    return f, t, sp, top


def _blocks(sp, top):
    """Outline blocks: top-level elements, descending into plain wrappers that hold components."""
    kids = {}
    for r in sp:
        kids.setdefault(r['parent'], []).append(r)
    out = []

    def go(rs, depth):
        for r in rs:
            plain = not r['attrs'].get('data-c') and not r['id'] and r['tag'] in ('div', 'section', 'details', 'ol', 'ul')
            sub = kids.get(r['i'], [])
            if plain and any(x['attrs'].get('data-c') or x['id'] for x in sub):
                out.append((depth, r, True))
                go(sub, depth + 1)
            else:
                out.append((depth, r, False))
    go(top, 0)
    return out


def _blk_text(t, r, plan=None):
    frag = t[r['start']:r['end']]
    return vis(parse(fill_refs(plan, frag) if plan else frag))


def outline(d, uid):
    f, t, sp, top = _unit_spans(d, uid)
    plan = Plan(os.path.join(d, 'book.json'))
    print(f'{os.path.relpath(f, d)} {uid}')
    a, b = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', t, re.DOTALL).span(1)
    ph = [(t.count('\n', 0, m.start()) + 1, m) for m in re.finditer(r'<!--(card|fig) ([\w.-]+)-->', t[a:b])]
    ph = [(t.count('\n', 0, a + m.start()) + 1, m) for _, m in ph]
    for depth, r, wrap in _blocks(sp, top):
        while ph and ph[0][0] <= r['line'] and depth == 0:  # slots entries (card new, card lift): edit them in slots/UNIT.json
            print(f'L{ph[0][0]} #{ph[0][1].group(2)} {ph[0][1].group(1)} (slots/{uid}.json)')
            ph.pop(0)
        a = r['attrs']
        kind = a.get('data-c') or r['tag']
        meta = '/'.join(x for x in (a.get('data-move'), a.get('data-level'), a.get('data-diff')) if x) or a.get('data-kind') or (('demo ' + a['data-demo']) if a.get('data-demo') else '')
        tx = _blk_text(t, r, plan)
        first = '' if wrap else tx[:50].replace('"', "'")
        print(f'{"  " * depth}L{r["line"]} #{r["id"] or "-"} {kind}{" " + meta if meta else ""} "{first}" {len(tx)}')
    for ln, m in ph:
        print(f'L{ln} #{m.group(2)} {m.group(1)} (slots/{uid}.json)')
    return 0


def select(sp, top, sel):
    """Spans a selector names: #id (cards also by their built id), a data-c kind, L120 (block starting on that line) or L120-L180."""
    m = re.fullmatch(r'L(\d+)(?:-L?(\d+))?', sel)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        pool = [r for _, r, wrap in _blocks(sp, top) if not wrap] if m.group(2) else [r for r in sp]
        hits = [r for r in pool if lo <= r['line'] <= hi]
        if not m.group(2):  # one line: the outermost element starting there
            hits = [r for r in hits if not any(h is not r and h['start'] <= r['start'] and r['end'] <= h['end'] for h in hits)][:1]
        return hits
    if sel.startswith('#'):
        return [r for r in sp if r['id'] == sel[1:]]
    hits = [r for r in sp if r['attrs'].get('data-c') == sel]
    return [r for r in hits if not any(h is not r and h['start'] < r['start'] and r['end'] <= h['end'] for h in hits)]


def show(d, uid, sel, as_html=False):
    f, t, sp, top = _unit_spans(d, uid)
    hits = select(sp, top, sel)
    if not hits:
        print(f'nothing matches {sel} in {uid}; run `make-book.py outline {uid}`')
        return 1
    plan = Plan(os.path.join(d, 'book.json'))
    lang = str(plan.book.get('lang', 'en'))
    for r in hits:
        frag = t[r['start']:r['end']]
        print(f'--- L{r["line"]} #{r["id"] or "-"} {r["attrs"].get("data-c") or r["tag"]}')
        if as_html:
            print(frag)
        else:
            emit_text(parse(fill_refs(plan, frag)), None, lang)
    return 0


def _lint_keys(d, uid):
    return {(f['level'], f['rule'], f['msg'], f['ev']) for f in lint(d, uid, quick=True)}


def _diff(a, b):
    ks = sorted(set(a) | set(b))
    return ', '.join(f'<{k}> {b.get(k, 0) - a.get(k, 0):+d}' for k in ks if a.get(k, 0) != b.get(k, 0))


def edit(d, uid, patch):
    """Apply a JSON patch to one unit's source: all ops or none; backup in .work/, rebuild, print the unit's lint delta."""
    import datetime
    if not os.path.isfile(patch):
        print(f'patch file {patch} not found')
        return 1
    try:
        ops = json.load(open(patch, encoding='utf-8'))
    except (ValueError, OSError) as e:
        print(f'patch file {patch} is not valid JSON: {e}')
        return 1
    if isinstance(ops, dict):
        ops = ops.get('ops', [ops])
    if not isinstance(ops, list) or not all(isinstance(o, dict) for o in ops):
        print(f'patch file {patch} must hold an op object or a list of them')
        return 1
    f, t, (a, b) = unit_src(d, uid)
    # selector ops resolve against the file as it stands, then apply bottom-up; sub ops run after them, in order
    sp = [r for r in spans(t) if r['start'] >= a and r['end'] <= b]
    inside = {r['i'] for r in sp}
    nc = 0
    for r in sp:
        r['id'] = r['attrs'].get('id')
        if r['attrs'].get('data-c') in CARDS:
            nc += 1
            r['id'] = r['id'] or f'c-{uid}-{nc}'
    top = [r for r in sp if r['parent'] not in inside]
    edits, subs = [], []
    for k, op in enumerate(ops, 1):
        kind = op.get('op')
        if kind == 'sub':
            if 'old' not in op or 'new' not in op:
                print(f'op {k} sub needs old and new; nothing written')
                return 1
            subs.append((k, op))
            continue
        if kind not in ('replace', 'before', 'after', 'remove') or 'sel' not in op:
            print(f'op {k}: op must be replace, before, after, remove (with sel) or sub (with old, new); nothing written')
            return 1
        hits = select(sp, top, op['sel'])
        if len(hits) != 1:
            print(f'op {k} {kind}: selector {op["sel"]} matches {len(hits)} blocks in {uid}, needs exactly 1; nothing written')
            return 1
        h = op.get('html', '')
        if kind != 'remove' and not h:
            print(f'op {k} {kind}: html missing; nothing written')
            return 1
        r = hits[0]
        blk = f'#{r["id"]}' if r['id'] else f'L{r["line"]} <{r["tag"]}>'
        if kind != 'remove':
            net = tag_balance(h)[0]
            want = tag_balance(t[r['start']:r['end']])[0] if kind == 'replace' else {}
            if net != want and not (kind == 'replace' and want):  # a block already unbalanced may be repaired
                print(f'op {k} {kind}: the html changes the tag balance of block {blk} ({_diff(want, net)}); nothing written')
                return 1
        edits.append((k, kind, r['start'], r['end'], h))
    for x in edits:
        for y in edits:
            if x is not y and x[1] in ('replace', 'remove') and x[2] <= y[2] < x[3] and not (y[1] == 'before' and y[2] == x[2]):
                print(f'op {y[0]} touches the block op {x[0]} {x[1]}s; nothing written')
                return 1
    new = t
    for k, kind, st, en, h in sorted(edits, key=lambda e: (e[2] if e[1] != 'after' else e[3], e[0]), reverse=True):
        new = {'replace': lambda: new[:st] + h + new[en:], 'before': lambda: new[:st] + h + '\n' + new[st:],
               'after': lambda: new[:en] + '\n' + h + new[en:], 'remove': lambda: new[:st] + new[en:].lstrip('\n')}[kind]()
    for k, op in subs:
        a, b = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', new, re.DOTALL).span(1)
        n, want = new[a:b].count(op['old']), op.get('count', 1)
        if n != want:
            print(f'op {k} sub: "{op["old"][:50]}" occurs {n} times in {uid}, patch says {want}; nothing written')
            return 1
        if tag_balance(op['old'])[0] != tag_balance(op['new'])[0]:
            at = new[a:b].index(op['old']) + a
            cont = sorted((r for r in spans(new) if r['start'] <= at < r['end']), key=lambda r: r['end'] - r['start'])
            named = next((r for r in cont if r['attrs'].get('id') or r['attrs'].get('data-c')), None)
            r0 = named or (cont[0] if cont else None)
            blk = uid if r0 is None else f'#{r0["attrs"].get("id") or r0["attrs"].get("data-c")}' if named else f'L{r0["line"]} <{r0["tag"]}>'
            print(f'op {k} sub: changes the tag balance of block {blk} ({_diff(tag_balance(op["old"])[0], tag_balance(op["new"])[0])}); nothing written')
            return 1
        new = new[:a] + new[a:b].replace(op['old'], op['new']) + new[b:]
    if new == t:
        print('patch changes nothing; nothing written')
        return 1
    a1, b1 = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', t, re.DOTALL).span(1)
    a2, b2 = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', new, re.DOTALL).span(1)
    n0, n1 = tag_balance(t[a1:b1])[0], tag_balance(new[a2:b2])[0]
    if n0 != n1 and not n0:
        print(f'the result changes the tag balance of unit {uid} ({_diff(n0, n1)}); nothing written')
        return 1
    try:
        before = _lint_keys(d, uid) if os.path.exists(os.path.join(d, 'book.html')) else set()
    except PlanError:
        before = set()
    bk = os.path.join(d, '.work', 'backup')
    os.makedirs(bk, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    dst = os.path.join(bk, f'{os.path.basename(f)}.{stamp}')
    shutil.copy(f, dst)
    open(f, 'w', encoding='utf-8').write(new)
    build(d)
    after = _lint_keys(d, uid)
    print(f'{len(ops)} ops applied to {os.path.relpath(f, d)}; backup {os.path.relpath(dst, d)}; rebuilt')
    for sign, s_ in (('+', after - before), ('-', before - after)):
        for lv, rule, msg, ev in sorted(s_, key=lambda x: (x[1], x[2])):
            print(f'{sign} {lv:5} {rule:3} {msg}' + (f'  [{ev}]' if ev else ''))
    c = lambda rows, lv: sum(1 for x in rows if x[0] == lv)
    print(f'-- lint {uid}: {c(after, "error")} errors, {c(after, "warn")} warns ({len(after - before)} new, {len(before - after)} gone)')
    return 1 if c(after, 'error') else 0
