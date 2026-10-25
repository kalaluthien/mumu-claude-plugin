"""Element and pattern catalog: slots/U.json entries render into cards and figures at build; patterns are reference reading, never filled in.

A placeholder <!--card ID--> or <!--fig ID--> in a unit names an entry of BOOK/slots/U.json: {ID: {kind, label?, move, level, diff, elements: [{el, ...slots}]}}.
Elements live in assets/catalog/elements/<id>.json (BOOK/catalog/ first), patterns in assets/catalog/patterns/<id>.md.
"""
import collections, copy, datetime, functools, html, json, os, re, shutil
from .const import ASSETS, LIB
from .plan import PlanError
from . import pcheck

SKILL_CAT = os.path.join(ASSETS, 'catalog')
CARD_KINDS = ('ask', 'probe', 'task-sort', 'task-order', 'task-select', 'task-estimate', 'task-custom')
FIG_KINDS = ('fig', 'frames')
CARD_KEYS = {'kind', 'label', 'move', 'level', 'diff', 'variant_of', 'order', 'elements'}
FIG_KEYS = {'kind', 'label', 'tactic', 'fkind', 'enc', 'concept', 'caption', 'elements'}
PH = re.compile(r'<!--(card|fig) ([\w.-]+)-->')
TODO = 'TODO'

# ---------------------------------------------------------------- catalog files


def _cats(book=None):
    return ([os.path.join(book, 'catalog')] if book else []) + [SKILL_CAT]


def elements(book=None):
    """id -> element spec; a book's own element overrides the skill's."""
    out = {}
    for c in reversed(_cats(book)):
        for f in sorted(os.listdir(os.path.join(c, 'elements'))) if os.path.isdir(os.path.join(c, 'elements')) else []:
            if f.endswith('.json'):
                try:
                    e = json.load(open(os.path.join(c, 'elements', f), encoding='utf-8'))
                except json.JSONDecodeError as x:
                    raise PlanError(f'{os.path.join(c, "elements", f)} is not valid JSON: {x}')
                if not isinstance(e, dict):
                    raise PlanError(f'{os.path.join(c, "elements", f)} must hold a JSON object, found {type(e).__name__}')
                e['src'] = 'book' if c != SKILL_CAT else 'skill'
                out[e.get('id') or f[:-5]] = e
    if book:
        try:
            pcheck.load_book_checks(book)
        except Exception as x:  # book code that does not load is a plan problem, named
            raise PlanError(f'{book}/catalog/checks: {type(x).__name__}: {x}')
    return out


def read_pattern(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'#\s*([\w-]+):\s*(.*)', t)
    fam = re.search(r'^family:\s*(\w+)', t, re.MULTILINE)
    els = re.search(r'^elements:\s*(.*)$', t, re.MULTILINE)
    secs = dict((h.strip().lower(), b) for h, b in re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)', t, re.MULTILINE | re.DOTALL))
    return dict(id=m.group(1) if m else os.path.basename(path)[:-3], why=m.group(2).strip() if m else '', family=fam.group(1) if fam else '',
                elements=[x.strip() for x in els.group(1).split(',') if x.strip()] if els else [], path=path, text=t, sections=secs)


def patterns(book=None):
    out = {}
    for c in reversed(_cats(book)):
        pd = os.path.join(c, 'patterns')
        for f in sorted(os.listdir(pd)) if os.path.isdir(pd) else []:
            if f.endswith('.md'):
                p = read_pattern(os.path.join(pd, f))
                p['src'] = 'book' if c != SKILL_CAT else 'skill'
                out[p['id']] = p
    return out


def load_slots(d):
    """unit id -> {entry id -> spec} from BOOK/slots/*.json."""
    sd, out = os.path.join(d, 'slots'), {}
    for f in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
        if f.endswith('.json'):
            try:
                out[f[:-5]] = json.load(open(os.path.join(sd, f), encoding='utf-8'))
            except json.JSONDecodeError as x:
                raise PlanError(f'slots/{f} is not valid JSON: {x}')
    return out


def save_slots(d, uid, entries):
    os.makedirs(os.path.join(d, 'slots'), exist_ok=True)
    json.dump(entries, open(os.path.join(d, 'slots', uid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- render


def _get(ctx, path):
    v = ctx
    for k in path.split('.'):
        if isinstance(v, dict):
            v = v.get(k)
        elif isinstance(v, list) and k.isdigit() and int(k) < len(v):
            v = v[int(k)]
        else:
            return None
    return v


def fill(tpl, ctx, element_specs, kind):
    """Template: {slot}, {slot!a} (attribute-escaped), {a.b}, {slot@element} (sub-element), [slot: text] (if set), {#list}...{/list} (items merged into ctx)."""
    keep = []

    def stash(s):
        keep.append(s)
        return f'\x00{len(keep) - 1}\x00'

    def loop(m):
        items = _get(ctx, m.group(1)) or []
        return stash(''.join(fill(m.group(2), dict(ctx, **it) if isinstance(it, dict) else dict(ctx, **{'.': it}), element_specs, kind) for it in items))
    t = re.sub(r'\{#([\w.]+)\}(.*?)\{/\1\}', loop, tpl, flags=re.DOTALL)
    t = re.sub(r'\[([\w.]+): ([^\[\]]*)\]', lambda m: m.group(2) if _get(ctx, m.group(1)) not in (None, '', [], {}, False) else '', t)

    def val(m):
        v = _get(ctx, m.group(1))
        if m.group(2):
            return stash(render_el(m.group(2), v, element_specs, kind, sub=True) if v else '')
        if v is None or isinstance(v, bool):
            return ''
        s = ','.join(map(str, v)) if isinstance(v, list) else f'{v:g}' if isinstance(v, float) else str(v)
        return stash(html.escape(s, quote=True) if m.group(3) else s)
    t = re.sub(r'\{([\w.]+)(?:@([\w-]+))?(!a)?\}', val, t)
    return re.sub('\x00(\\d+)\x00', lambda m: keep[int(m.group(1))], t)


def kit_html(n):
    if not isinstance(n, dict):
        return ''
    if 'c' not in n:
        n = n.get('tree') or {}
    cls = ' '.join(['mk-' + str(n.get('c', 'box'))] + (['mk-hl'] if 'n' in n else []) + (['on'] if n.get('on') else []) + list(n.get('cls') or []))
    a = f' data-n="{n["n"]}"' if 'n' in n else ''
    return f'<div class="{html.escape(cls)}"{a}>{html.escape(str(n.get("t", "")))}' + ''.join(kit_html(k) for k in n.get('kids') or []) + '</div>'


def render_el(eid, ctx, element_specs, kind, sub=False):
    e = element_specs.get(eid) or {}
    tpl = e.get('render', '')
    if isinstance(tpl, dict):
        tpl = tpl.get(kind, tpl.get('*', ''))
    if tpl == '@kit':
        return kit_html(ctx) if sub else f'<div class="mk">{kit_html(ctx)}</div>'
    return fill(tpl, ctx if isinstance(ctx, dict) else {}, element_specs, kind)


def alt_of(spec):
    a = next((e for e in spec.get('elements') or [] if e.get('el') == 'alt'), None)
    return f'{a.get("kind", "")}: {a.get("encodes", "")}; {a.get("point", "")}' if a else ''


def render(cid, spec, element_specs):
    """The existing card or figure markup for one entry; build dresses it like a hand card."""
    k = spec.get('kind')
    zones = collections.defaultdict(list)
    for e in spec.get('elements') or []:
        el = element_specs.get(e.get('el')) or {}
        if el.get('zone', 'body') != 'none':
            zones[el.get('zone', 'body')].append(render_el(e['el'], e, element_specs, k))
    z = lambda n: ''.join(zones[n])
    a = lambda name, v: f' {name}="{html.escape(str(v), quote=True)}"' if v not in (None, '') else ''
    if k in FIG_KINDS:
        body = (f'<figure data-c="{k}"{a("id", cid)}{a("data-concept", spec.get("concept"))}{a("data-enc", spec.get("enc"))}{a("data-tactic", spec.get("tactic"))}{a("data-kind", spec.get("fkind"))}>'
                f'{z("body")}{z("tail")}<figcaption>{spec.get("caption", "")}</figcaption></figure>')
        alt = html.escape(alt_of(spec), quote=True)
        body = re.sub(r'<svg(?![^>]*aria-label)', f'<svg role="img" aria-label="{alt}"', body)
        return re.sub(r'<div class="mk">', f'<div class="mk" role="img" aria-label="{alt}">', body, count=1)
    meta = a('data-move', spec.get('move')) + a('data-level', spec.get('level')) + a('data-diff', spec.get('diff')) + a('data-variant-of', spec.get('variant_of'))
    if k in ('ask', 'probe'):
        return f'<div data-c="{k}"{a("id", cid)}{meta}>{z("q")}{z("body")}<ol data-p="opts"{a("data-order", spec.get("order"))}>{z("opts")}</ol>{z("tail")}</div>'
    w = next((e.get('widget') for e in spec.get('elements') or [] if e.get('el') == 'model'), None)
    return f'<div data-c="task"{a("id", cid)} data-kind="{k[5:]}"{a("data-widget", w)}{meta}>{z("q")}{z("body")}{z("items")}{z("opts")}{z("tail")}</div>'

# ---------------------------------------------------------------- validation (P1): what the format rules out


TYPES = {'html': str, 'str': str, 'int': int, 'num': (int, float), 'list': list, 'obj': dict, 'bool': bool, 'enum': str}


def _todo(x, path, out):
    if isinstance(x, str) and TODO in x:
        out.append(f'{path} is TODO')
    elif isinstance(x, dict):
        for k, v in x.items():
            _todo(v, f'{path}.{k}', out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _todo(v, f'{path}.{i}', out)


def check_slots(schema, x, path, element_specs, out):
    if not isinstance(x, dict):
        out.append(f'{path} must be an object')
        return
    for k in x:
        if k not in schema and k not in ('el',):
            out.append(f'{path} has unknown slot {k}; slots are {", ".join(schema)}')
    for k, sl in schema.items():
        v = x.get(k)
        if v is None:
            if sl.get('req'):
                out.append(f'{path} lacks {k}')
            continue
        if isinstance(v, str) and TODO in v:
            continue
        t = sl.get('type', 'str')
        if t.startswith('el:'):
            check_slots((element_specs.get(t[3:]) or {}).get('slots') or {}, v, f'{path}.{k}', element_specs, out)
            continue
        want = TYPES.get(t, str)
        if not isinstance(v, want) or (t in ('int', 'num') and isinstance(v, bool)):
            out.append(f'{path}.{k} must be {t}, got {type(v).__name__}')
        elif t == 'enum' and v not in sl.get('values', []):
            out.append(f'{path}.{k} must be one of {", ".join(sl["values"])}')
        elif t in ('html', 'str') and sl.get('req') and not v.strip():
            out.append(f'{path}.{k} is empty')
        elif t == 'list' and sl.get('of'):
            for i, it in enumerate(v):
                if it != TODO:
                    check_slots(sl['of'], it, f'{path}.{k}.{i}', element_specs, out)


COUNTS = {'ask': {'stem': (1, 1), 'answer': (1, 1)}, 'probe': {'stem': (1, 1), 'answer': (1, 1)}, 'task-sort': {'stem': (1, 1), 'items': (1, 1)},
          'task-order': {'stem': (1, 1), 'items': (1, 1)}, 'task-select': {'stem': (1, 1), 'items': (1, 1)}, 'task-estimate': {'stem': (1, 1), 'given': (1, 1)},
          'task-custom': {'stem': (1, 1), 'model': (1, 1)}, 'fig': {'alt': (1, 1)}, 'frames': {'alt': (1, 1), 'steps': (1, 1)}}


def validate_spec(cid, spec, element_specs):
    """P1 messages for one entry: kind, card keys, elements the kind can hold, slots present, typed and not TODO, element counts."""
    out = []
    if not isinstance(spec, dict):
        return [f'{cid} must be an object']
    k = spec.get('kind')
    if k not in CARD_KINDS + FIG_KINDS:
        return [f'{cid} kind {k} is not one of {", ".join(CARD_KINDS + FIG_KINDS)}']
    keys = FIG_KEYS if k in FIG_KINDS else CARD_KEYS
    out += [f'{cid} has unknown key {x}; keys are {", ".join(sorted(keys))}' for x in spec if x not in keys]
    out += [f'{cid} lacks {x}' for x in (('tactic', 'fkind', 'caption') if k in FIG_KINDS else ('move', 'level', 'diff')) if not spec.get(x)]
    _todo({x: v for x, v in spec.items() if x != 'elements'}, cid, out)
    els = spec.get('elements')
    if not isinstance(els, list) or not els:
        return out + [f'{cid} has no elements']
    n = collections.Counter()
    for i, e in enumerate(els):
        p = f'{cid}.elements.{i}'
        el = element_specs.get(e.get('el')) if isinstance(e, dict) else None
        if el is None:
            out.append(f'{p} names no known element ({e.get("el") if isinstance(e, dict) else e}); see `pattern list` and `element show`')
            continue
        n[e['el']] += 1
        if k not in el.get('kinds', []):
            out.append(f'{p}: a {k} cannot hold {e["el"]} (it goes in {", ".join(el.get("kinds", []))})')
        _todo(e, f'{p} {e["el"]}', out)
        check_slots(el.get('slots') or {}, e, f'{p} {e["el"]}', element_specs, out)
    for el, (lo, hi) in COUNTS[k].items():
        if not lo <= n[el] <= hi:
            out.append(f'{cid}: a {k} holds {lo if lo == hi else f"{lo}-{hi}"} {el}, found {n[el]}')
    if k in ('ask', 'probe') and not n['rival'] + n['near-miss']:
        out.append(f'{cid}: a {k} needs a rival or near-miss')
    return out


def _units(d):
    from .build import read_units
    return read_units(d)


def validate(d, element_specs=None, only=None):
    """[(unit, msg)] P1 over the book: placeholders without entries, orphan entries, entries of units that do not exist, and each entry's spec."""
    element_specs = element_specs or elements(d)
    slots, unit_texts, out = load_slots(d), _units(d), []
    for uid in sorted(set(slots) | {u for u, t in unit_texts.items() if PH.search(t)}):
        if only and uid != only:
            continue
        if uid not in unit_texts:
            out.append((uid, f'slots/{uid}.json names a unit with no section'))
            continue
        ent, placed = slots.get(uid) or {}, collections.Counter()
        for typ, cid in PH.findall(unit_texts[uid]):
            placed[cid] += 1
            if cid not in ent:
                out.append((uid, f'<!--{typ} {cid}--> has no entry in slots/{uid}.json'))
            elif (typ == 'fig') != (isinstance(ent[cid], dict) and ent[cid].get('kind') in FIG_KINDS):
                out.append((uid, f'<!--{typ} {cid}--> names a {ent[cid].get("kind") if isinstance(ent[cid], dict) else "?"} entry'))
        out += [(uid, f'{cid} is placed {c} times') for cid, c in placed.items() if c > 1]
        out += [(uid, f'slots/{uid}.json entry {cid} is placed nowhere; add <!--card {cid}--> or remove it') for cid in ent if cid not in placed]
        for cid, spec in ent.items():
            out += [(uid, m) for m in validate_spec(cid, spec, element_specs)]
    return out


def expand(d, uid, inner):
    """Build hook: render the unit's placeholders; any P1 message refuses the build."""
    if not PH.search(inner) and not os.path.exists(os.path.join(d, 'slots', uid + '.json')):
        return inner
    element_specs = elements(d)
    bad = validate(d, element_specs, uid)
    if bad:
        raise PlanError('P1 slots refuse the build:\n' + '\n'.join(f'  {u}: {m}' for u, m in bad[:20]) + (f'\n  … {len(bad) - 20} more' if len(bad) > 20 else ''))
    ent = load_slots(d).get(uid) or {}
    return PH.sub(lambda m: render(m.group(2), ent[m.group(2)], element_specs), inner)

# ---------------------------------------------------------------- lint (P1, P2)


def known_text(plan, src, pos):
    """What the reader has met before a placeholder: the unit prose before it, terms, canon and concept forms."""
    before = pcheck.txt(src[:pos])
    extra = [c.get('term', '') for c in plan.concept_by_id.values()] + [str(v) for v in ((plan.d.get('canon') or {}).get('values') or {}).values()]
    extra += [' '.join(map(str, t.values())) for t in plan.d.get('terms') or [] if isinstance(t, dict)]
    return before + ' ' + ' '.join(extra)


def lint_findings(d, plan, findings, unit=None):
    element_specs = elements(d)
    for uid, m in validate(d, element_specs, unit):
        findings.add('P1', 'error', uid, m)
    slots, unit_texts = load_slots(d), _units(d)
    for uid, ent in slots.items():
        if (unit and uid != unit) or uid not in unit_texts:
            continue
        for m in PH.finditer(unit_texts[uid]):
            spec = ent.get(m.group(2))
            if not isinstance(spec, dict):
                continue
            for cid, lv, i, msg in pcheck.run(spec, element_specs, plan.pack, known_text(plan, unit_texts[uid], m.start())):
                findings.add('P2', lv, uid, f'{m.group(2)} {cid}: {msg}')

# ---------------------------------------------------------------- mutate: every element check against its example


def _apply(spec, ops):
    s = copy.deepcopy(spec)
    for op in ops:
        path = (op.get('set') or op.get('del')).split('.')
        cur = s
        for k in path[:-1]:
            cur = cur[int(k)] if isinstance(cur, list) else cur.setdefault(k, {})
        last = path[-1]
        if 'del' in op:
            del cur[int(last) if isinstance(cur, list) else last]
        elif isinstance(cur, list):
            cur[int(last)] = op['to']
        else:
            cur[last] = op['to']
    return s


def element_cases(element_specs, pack, only=None):
    """[(element, check, label, ok)]: the example is clean (P1 and its own checks), and each check's breaks is caught by that check."""
    out = []
    for eid, el in sorted(element_specs.items()):
        if only and eid not in only:
            continue
        ex = el.get('example')
        if not ex:
            out.append((eid, '-', 'example missing', False))
            continue
        p1 = validate_spec(eid, ex, element_specs)
        mine = {c['id'] for c in el.get('checks') or []}
        fired = [(c, m) for c, lv, i, m in pcheck.run(ex, element_specs, pack) if c in mine and ex['elements'][i].get('el') == eid or lv == 'error']
        out.append((eid, 'clean', '; '.join(p1 + [f'{c}: {m}' for c, m in fired])[:160], not p1 and not fired))
        for c in el.get('checks') or []:
            if c['id'] not in pcheck.CHECKS:
                out.append((eid, c['id'], 'no such check in pcheck', False))
                continue
            try:
                hit = any(cc == c['id'] for cc, lv, i, m in pcheck.run(_apply(ex, c.get('breaks') or []), element_specs, pack))
            except (KeyError, IndexError, TypeError, ValueError) as x:
                out.append((eid, c['id'], f'breaks does not apply ({x})', False))
                continue
            out.append((eid, c['id'], 'caught' if hit else 'MISSED', hit))
    return out

# ---------------------------------------------------------------- writing: card new, fig new, card lift


def _stub(el):
    out = {'el': el['id']}
    for k, sl in (el.get('slots') or {}).items():
        if sl.get('req'):
            t = sl.get('type', 'str')
            item = {f: TODO for f, x in sl['of'].items() if x.get('req')} if sl.get('of') else TODO
            out[k] = [item] if t == 'list' else {TODO: TODO} if t == 'obj' else TODO
    return out


DEFAULT_ELEMENTS = {'ask': 'stem,answer,rival,rival', 'probe': 'stem,answer,rival,rival', 'task-sort': 'stem,items', 'task-order': 'stem,items', 'task-select': 'stem,items',
                    'task-estimate': 'stem,given', 'task-custom': 'stem,model', 'fig': 'alt', 'frames': 'scene,steps,alt'}


def _insert(d, uid, after, text):
    from .edit import _unit_spans, select
    f, t, sp, top = _unit_spans(d, uid)
    a, b = re.search(r'<section\s+data-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', t, re.DOTALL).span(1)
    ph = [m for m in PH.finditer(t, a, b) if '#' + m.group(2) == after]
    hits = ph or select(sp, top, after)
    if len(hits) != 1:
        raise PlanError(f'--after {after} matches {len(hits)} blocks in {uid}; run `make-book.py outline {uid}`')
    e = hits[0].end() if ph else hits[0]['end']
    _backup(d, f)
    open(f, 'w', encoding='utf-8').write(t[:e] + '\n' + text + t[e:])


def _backup(d, f):
    bk = os.path.join(d, '.work', 'backup')
    os.makedirs(bk, exist_ok=True)
    shutil.copy(f, os.path.join(bk, f'{os.path.basename(f)}.{datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")}'))


def new_entry(d, uid, after, kind, els, cid=None, label=None, tactic=None):
    """Insert a placeholder after block SEL and write a TODO stub; the writer fills slots, build refuses until no TODO is left."""
    element_specs = elements(d)
    if kind not in CARD_KINDS + FIG_KINDS:
        raise PlanError(f'--kind must be one of {", ".join(CARD_KINDS + FIG_KINDS)}')
    names = [x.strip() for x in (els or DEFAULT_ELEMENTS[kind]).split(',') if x.strip()]
    bad = [x for x in names if x not in element_specs]
    if bad:
        raise PlanError(f'unknown elements {", ".join(bad)}; see `make-book.py element show E` and `pattern list`')
    bad = [x for x in names if kind not in element_specs[x].get('kinds', [])]
    if bad:
        raise PlanError(f'a {kind} cannot hold {", ".join(bad)}; `make-book.py element show E` names the kinds each element goes in')
    slots = load_slots(d)
    ent = slots.get(uid) or {}
    fig = kind in FIG_KINDS
    if not cid:
        base = ('fig' if fig else kind.split('-')[0]) + '-' + re.sub(r'^u-', '', uid)
        cid = next(f'{base}-{i}' for i in range(1, 999) if f'{base}-{i}' not in ent)
    if cid in ent:
        raise PlanError(f'{cid} already has an entry in slots/{uid}.json')
    spec = {'kind': kind}
    if label:
        spec['label'] = label
    spec.update({'tactic': tactic or (kind if kind == 'frames' else TODO), 'fkind': TODO, 'caption': TODO} if fig else {'move': TODO, 'level': TODO, 'diff': TODO})
    spec['elements'] = [_stub(element_specs[x]) for x in names]
    _insert(d, uid, after, f'<!--{"fig" if fig else "card"} {cid}-->')
    ent[cid] = spec
    save_slots(d, uid, ent)
    print(f'<!--{"fig" if fig else "card"} {cid}--> after {after} in {uid}; stub in slots/{uid}.json: fill every TODO, then build')
    print('slots per element: `make-book.py element show E`; why and how to vary: `make-book.py pattern show P`')
    return 0


def _inner(n):
    return ''.join(html.escape(k, quote=False) if isinstance(k, str) else k.html() for k in n.kids).strip()


def _exhibit(n):
    x = {'alt': n.get('aria-label') or TODO}
    if n.get('class'):
        x['cls'] = n.get('class')
    x['html'] = _inner(n)
    x['facts'] = [TODO]
    return x


def lift_spec(node, uid=''):
    """A hand card as elements, recognised by its fragments; writer-only slots (belief, right_when, ruled_out_by, facts) are left TODO."""
    from .dom import Node
    c = node.get('data-c')
    kind = 'task-' + (node.get('data-kind') or 'custom') if c == 'task' else c
    spec = {'kind': kind}
    for a, k in (('data-move', 'move'), ('data-level', 'level'), ('data-diff', 'diff'), ('data-variant-of', 'variant_of')):
        if node.get(a):
            spec[k] = node.get(a)
    els, marks, raw = [], [], []
    flush = lambda: (els.append({'el': 'raw', 'html': ''.join(raw)}), raw.clear()) if ''.join(raw).strip() else raw.clear()
    for k in node.kids:
        if not isinstance(k, Node):
            raw.append(html.escape(k, quote=False))
            continue
        p, kc = k.get('data-p'), k.get('data-c')
        if p == 'q':
            flush(); els.append({'el': 'stem', 'text': _inner(k)})
        elif kc == 'exhibit':
            flush(); els.append(dict({'el': 'exhibit'}, **_exhibit(k)))
            marks += [(int(m.get('data-n')), pcheck.txt(m.html())[:40] or TODO) for m in k.find(lambda x: (x.get('data-n') or '').isdigit())]
        elif p == 'opts':
            flush()
            if k.get('data-order'):
                spec['order'] = k.get('data-order')
            oe = False
            for li in [x for x in k.kids if isinstance(x, Node) and x.tag == 'li']:
                o = {'el': 'answer' if li.has('data-ok') else 'rival'}
                why = li.first(lambda x: x.get('data-p') == 'why')
                ex = next((x for x in li.kids if isinstance(x, Node) and x.get('data-c') == 'exhibit'), None)
                if ex is not None:
                    o['exhibit'] = _exhibit(ex)
                    oe = True
                rest = [x for x in li.kids if x is not why and x is not ex]
                o['text'] = ''.join(html.escape(x, quote=False) if isinstance(x, str) else x.html() for x in rest).strip()
                o['why'] = _inner(why) if why is not None else TODO
                mk = re.match(r'\s*(\d+)\s*(?:번|\.|\))', pcheck.txt(o['text']))
                if marks and mk:  # an option that opens on a mark number names that mark
                    o['mark'] = int(mk.group(1))
                if o['el'] == 'rival':
                    o.update(belief=TODO, right_when=TODO, ruled_out_by=[TODO])
                els.append(o)
            if oe:
                els.insert(next(i for i, e in enumerate(els) if e['el'] in ('answer', 'rival')), {'el': 'option-exhibit', 'differs': TODO})
        elif p == 'items':
            flush()
            lis = [x for x in k.kids if isinstance(x, Node) and x.tag == 'li']
            it = {'el': 'items', 'list': []}
            if k.get('data-cats'):
                it['bins'] = k.get('data-cats').split(',')
            for li in lis:
                x = {'text': _inner(li), 'why': li.get('data-why') or TODO}
                if li.get('data-cat'):
                    x['bin'] = li.get('data-cat')
                if li.has('data-ok'):
                    x['ok'] = True
                it['list'].append(x)
            els.append(it)
        elif p == 'input':
            flush()
            g = {'el': 'given', 'ans': float(k.get('data-ans') or 0), 'tol': float(k.get('data-tol') or 0), 'unit': pcheck.txt(_inner(k)) or TODO}
            for q in ('lo', 'hi', 'why'):
                n2 = node.first(lambda x, q=q: x.get('data-p') == q and x.parent is node)
                g[q] = _inner(n2) if n2 is not None else TODO
            els.append(g)
        elif p in ('lo', 'hi', 'why') and kind == 'task-estimate':
            continue
        elif kind == 'task-custom' and node.get('data-widget') and node.get('data-widget') in (k.get('class') or '').split():
            flush(); els.append({'el': 'model', 'widget': node.get('data-widget'), 'model': k.get('data-want') or TODO, 'html': _inner(k), 'checks': [TODO]})
        else:
            raw.append(k.html())
    flush()
    if marks:
        i = next(i for i, e in enumerate(els) if e['el'] == 'exhibit') + 1
        els.insert(i, {'el': 'marks', 'marks': [{'n': n, 'target': t} for n, t in sorted(dict(marks).items())]})
    spec['elements'] = els
    return spec


def lift(d, uid, cid):
    """card lift U ID: the hand card becomes a slots entry and a placeholder; the rendered entry must equal the card in markup and text."""
    from .dom import canon, parse
    from .edit import _unit_spans, select
    f, t, sp, top = _unit_spans(d, uid)
    hits = select(sp, top, '#' + cid)
    if len(hits) != 1:
        raise PlanError(f'#{cid} matches {len(hits)} blocks in {uid}')
    r = hits[0]
    frag = t[r['start']:r['end']]
    node = next(k for k in parse(frag).kids if not isinstance(k, str))
    if node.get('data-c') not in ('ask', 'probe', 'task'):
        raise PlanError(f'#{cid} is a {node.get("data-c") or node.tag}, not a card')
    spec = lift_spec(node, uid)
    element_specs = elements(d)
    back = render(cid, spec, element_specs)
    if canon(back) != canon(frag if node.get('id') else frag.replace(f'data-c="{node.get("data-c")}"', f'data-c="{node.get("data-c")}" id="{cid}"', 1)):
        raise PlanError(f'#{cid}: the lifted entry does not render back to the same card; lift by hand or mark the odd part raw')
    slots = load_slots(d)
    ent = slots.get(uid) or {}
    if cid in ent:
        raise PlanError(f'{cid} already has an entry in slots/{uid}.json')
    ent[cid] = spec
    _backup(d, f)
    open(f, 'w', encoding='utf-8').write(t[:r['start']] + f'<!--card {cid}-->' + t[r['end']:])
    save_slots(d, uid, ent)
    todo = []
    _todo(spec, cid, todo)
    print(f'{cid} lifted into slots/{uid}.json ({", ".join(e["el"] for e in spec["elements"])}); renders back identical')
    print(f'{len(todo)} TODO slots before it builds: ' + '; '.join(todo[:8]) + (' …' if len(todo) > 8 else ''))
    return 0

# ---------------------------------------------------------------- reading: pattern list/show, element show


def pattern_list(family=None, book=None):
    pats = patterns(book)
    book_new = {p.get('id'): p for p in _new_patterns(book)} if book else {}
    for fam in ('problem', 'visual'):
        if family and fam != family:
            continue
        print(f'## {fam}')
        for p in sorted((p for p in pats.values() if p['family'] == fam), key=lambda p: p['id']):
            tag = ''
            if p['src'] == 'book':
                tag = ' [book' + (', local' if (book_new.get(p['id']) or {}).get('local') else ', unpromoted') + ']'
            print(f'- {p["id"]}: {p["why"]}  ({", ".join(p["elements"])}){tag}')
    return 0


def pattern_show(pid, book=None):
    p = patterns(book).get(pid)
    if not p:
        raise PlanError(f'no pattern {pid}; `make-book.py pattern list`')
    print(p['text'].rstrip())
    return 0


def element_show(eid, book=None):
    e = elements(book).get(eid)
    if not e:
        raise PlanError(f'no element {eid}; elements: {", ".join(sorted(elements(book)))}')
    print(f'# {eid}: {e.get("why", "")}\nzone {e.get("zone")}; kinds {", ".join(e.get("kinds", []))}')
    for k, sl in (e.get('slots') or {}).items():
        flags = ' '.join(x for x in ('req' if sl.get('req') else '', 'writer-only' if sl.get('writer') else '') if x)
        vals = f' [{"|".join(sl["values"])}]' if sl.get('values') else ''
        sub = f' {{{", ".join(sl["of"])}}}' if sl.get('of') else ''
        print(f'- {k}: {sl.get("type", "str")}{vals}{sub}{" " + flags if flags else ""}' + (f' — {sl["doc"]}' if sl.get('doc') else ''))
    print('checks: ' + (', '.join(dict.fromkeys(c['id'] for c in e.get('checks') or [])) or 'none'))
    ex = next((x for x in (e.get('example') or {}).get('elements', []) if x.get('el') == eid), None)
    if ex:
        print('example: ' + json.dumps(ex, ensure_ascii=False))
    return 0

# ---------------------------------------------------------------- plan and gates: new patterns


def _new_patterns(book):
    if not book or not os.path.exists(os.path.join(book, 'book.json')):
        return []
    j = json.load(open(os.path.join(book, 'book.json'), encoding='utf-8'))
    return [p for p in j.get('new_patterns') or [] if isinstance(p, dict)]


def plan_gaps(plan):
    """Why the skeleton gate refuses the plan's new_patterns (list of messages): too few per family, an id the catalog has, empty nearest or differs, unknown elements."""
    want = plan.book.get('policies', {}).get('new_patterns', 1) if isinstance(plan.book.get('policies'), dict) else 1
    want = want if isinstance(want, int) and not isinstance(want, bool) and want >= 0 else 1
    nps, out = plan.d.get('new_patterns') or [], []
    if want == 0 and not any(isinstance(x, dict) and x.get('node') == 'policies.new_patterns' and x.get('how') == 'user' for x in plan.d.get('decisions') or []):
        out.append('policies.new_patterns is 0 but no decisions entry records that the user chose it; add {"node": "policies.new_patterns", "chosen": 0, "how": "user"} after asking, or remove the policy (default 1 per family)')
        want = 1  # without the user's word the default holds
    cat, element_specs = patterns(), elements(plan.dir)
    for fam in ('problem', 'visual'):
        n = sum(1 for p in nps if isinstance(p, dict) and p.get('family') == fam)
        if n < want:
            out.append(f'{n} new {fam} pattern(s) in new_patterns, want {want}: what does a practitioner in this field do or see that no catalog pattern makes the reader do?')
    for p in nps:
        if not isinstance(p, dict) or not p.get('id'):
            out.append('a new_patterns entry needs id, family, why, elements, nearest, differs, units')
            continue
        if p['id'] in cat:
            out.append(f'new pattern {p["id"]} is already in the catalog; pick a new id or use the catalog one')
        for k in ('why', 'nearest', 'differs'):
            if not str(p.get(k) or '').strip():
                out.append(f'new pattern {p["id"]} has no {k}')
        if p.get('nearest') and p['nearest'] not in cat:
            out.append(f'new pattern {p["id"]}: nearest {p["nearest"]} is no catalog pattern')
        newe = set(p.get('new_elements') or [])
        unk = [e for e in p.get('elements') or [] if e not in element_specs and e not in newe]
        if not p.get('elements') or unk:
            out.append(f'new pattern {p["id"]} elements unknown or missing: {", ".join(unk) or "none listed"}')
    return out


def fig_labels(d, src):
    """Pattern labels of the figures a unit draws by hand: `data-pattern` on the figure or its svg (a Fig script passes `pattern=`), one label list per figure."""
    from .dom import parse
    if 'data-pattern' not in src and '<!--svg' not in src:
        return []

    def svg(m):
        f = os.path.join(d, 'figs', m.group(1) + '.svg')
        return open(f, encoding='utf-8').read() if os.path.exists(f) else ''
    src = re.sub(r'<!--svg ([\w.-]+)-->', svg, src)
    out = []
    for n in parse(src).find(lambda x: x.tag == 'figure' or (x.tag == 'svg' and not x.up(lambda p: p.tag == 'figure'))):
        lab = n.get('data-pattern') or next((x.get('data-pattern') for x in n.find(lambda y: y.tag == 'svg' and y.get('data-pattern'))), '')
        labs = [x for x in re.split(r'[,+ ]+', str(lab or '')) if x]
        if labs:
            out.append(labs)
    return out


def uses(d):
    """label -> number of entries in the book's slots, and of figures with a `data-pattern`, that name it."""
    c = collections.Counter()
    for ent in load_slots(d).values():
        for spec in ent.values():
            for lab in re.split(r'[,+ ]+', str((spec or {}).get('label') or '')):
                if lab:
                    c[lab] += 1
    for src in _units(d).values():
        for labs in fig_labels(d, src):
            c.update(labs)
    return c


def review_gaps(d):
    """Why the review gate refuses: a new pattern used fewer than twice, without its .md (why, examples, composition), or a new element failing schema or mutate."""
    out, u = [], uses(d)
    element_specs = elements(d)
    from .lang import pack
    j = json.load(open(os.path.join(d, 'book.json'), encoding='utf-8'))
    for p in _new_patterns(d):
        pid = p.get('id')
        if u[pid] < 2:
            out.append(f'new pattern {pid} is used {u[pid]} time(s) in slots labels; a pattern needs 2 uses in the book')
        f = os.path.join(d, 'catalog', 'patterns', f'{pid}.md')
        if not os.path.exists(f):
            out.append(f'new pattern {pid} has no catalog/patterns/{pid}.md')
        else:
            secs = read_pattern(f)['sections']
            miss = [s for s in ('why it works', 'examples', 'compose and vary') if not any(k.startswith(s) for k in secs)]
            if miss:
                out.append(f'catalog/patterns/{pid}.md lacks {", ".join(miss)}')
        for eid in p.get('new_elements') or []:
            if eid not in element_specs or element_specs[eid]['src'] != 'book':
                out.append(f'new element {eid} has no catalog/elements/{eid}.json')
                continue
            out += [f'new element {eid} {c}: {m}' for _, c, m, ok in element_cases(element_specs, pack(j.get('book', {}).get('lang')), {eid}) if not ok]
            if not element_specs[eid].get('checks'):
                out.append(f'new element {eid} has no check with breaks')
    return out


def unpromoted(d):
    """New patterns of the book that are neither in the skill catalog nor marked local."""
    cat = patterns()
    return [p['id'] for p in _new_patterns(d) if p.get('id') and p['id'] not in cat and not p.get('local')]


def domain_words(d):
    """The book's own nouns: concept forms, canon values and names, project name; promoted text outside Examples must not carry them."""
    j = json.load(open(os.path.join(d, 'book.json'), encoding='utf-8'))
    ws = set()
    for c in j.get('concepts') or []:
        ws |= {c.get('term'), c.get('en')} | {a.get('form') if isinstance(a, dict) else a for a in c.get('aliases') or []}
    cn = j.get('canon') or {}
    ws |= {str(v) for v in (cn.get('values') or {}).values()} | set(cn.get('names') or [])
    ws |= set(re.findall(r'[^\W\d_][\w-]{2,}', str((j.get('project') or {}).get('name') or '')))
    ws |= {w for c in j.get('concepts') or [] for w in re.findall(r'[A-Z][\w-]{2,}', str(c.get('en') or ''))}
    return {w for w in ws if isinstance(w, str) and len(w) >= 3}


def element_shape(eid, e):
    """Clean messages for an element JSON that a promote would copy: types and required keys, so no KeyError or AttributeError escapes."""
    if not isinstance(e, dict):
        return [f'element {eid} must be a JSON object']
    out = []
    for k in ('id', 'family', 'why', 'zone', 'render'):
        if not isinstance(e.get(k), str) or not e[k].strip():
            out.append(f'element {eid}: {k} must be a non-empty string')
    if isinstance(e.get('id'), str) and e['id'] != eid:
        out.append(f'element {eid}: id is {e["id"]}; id and file name must match')
    if e.get('family') not in ('problem', 'visual'):
        out.append(f'element {eid}: family must be problem or visual')
    if not isinstance(e.get('kinds'), list) or not e['kinds'] or not all(isinstance(k, str) for k in e['kinds']):
        out.append(f'element {eid}: kinds must be a list of kind names')
    sl = e.get('slots')
    if not isinstance(sl, dict):
        out.append(f'element {eid}: slots must be an object')
        sl = {}
    for k, x in sl.items():
        if not isinstance(x, dict):
            out.append(f'element {eid}: slot {k} must be an object')
            continue
        t = x.get('type', 'str')
        if not isinstance(t, str) or not (t in TYPES or t.startswith('el:')):
            out.append(f'element {eid}: slot {k} type {t!r} is none of {", ".join(TYPES)} or el:ID')
        if t == 'enum' and not (isinstance(x.get('values'), list) and x['values'] and all(isinstance(v, str) for v in x['values'])):
            out.append(f'element {eid}: enum slot {k} needs a list of values')
        for f in ('req', 'writer'):
            if f in x and not isinstance(x[f], bool):
                out.append(f'element {eid}: slot {k} {f} must be true or false')
        if 'of' in x and not (isinstance(x['of'], dict) and all(isinstance(v, dict) for v in x['of'].values())):
            out.append(f'element {eid}: slot {k} of must map slot names to slot objects')
    ck = e.get('checks')
    if not isinstance(ck, list):
        out.append(f'element {eid}: checks must be a list')
        ck = []
    for i, c in enumerate(ck):
        if not isinstance(c, dict) or not isinstance(c.get('id'), str) or not isinstance(c.get('breaks'), list) or not c['breaks'] \
                or not all(isinstance(b, dict) and isinstance(b.get('set'), str) and 'to' in b for b in c['breaks']):
            out.append(f'element {eid}: checks[{i}] needs an id and a non-empty breaks list of {{"set": path, "to": value}}')
    ex = e.get('example')
    if not isinstance(ex, dict) or not isinstance(ex.get('elements'), list):
        out.append(f'element {eid}: example must be an entry object with an elements list')
    return out


def book_check_gaps(d, eid, e):
    """A check the skill's pcheck lacks must come as code in BOOK/catalog/checks/ID.py: a `check(spec, i, ctx)` that returns [(level, message)] and keeps its own names."""
    import ast
    out = []
    for c in e.get('checks') or []:
        cid = c.get('id') if isinstance(c, dict) else None
        if not isinstance(cid, str) or cid in pcheck.CHECKS and cid not in pcheck.BOOK_CHECKS:
            continue
        f = os.path.join(d, 'catalog', 'checks', f'{cid}.py')
        if not os.path.exists(f):
            out.append(f'new element {eid}: check {cid} is not in pcheck and the book has no catalog/checks/{cid}.py to carry over; write it (def check(spec, i, ctx) -> [(level, message)]) or use an existing check')
            continue
        try:
            tree = ast.parse(open(f, encoding='utf-8').read())
        except SyntaxError as x:
            out.append(f'catalog/checks/{cid}.py: syntax error line {x.lineno}')
            continue
        top = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))] + [t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)]
        if 'check' not in top:
            out.append(f'catalog/checks/{cid}.py defines no check(spec, i, ctx)')
        clash = sorted(n for n in top if n != 'check' and hasattr(pcheck, n))
        if clash:
            out.append(f'catalog/checks/{cid}.py names {", ".join(clash)} that pcheck already has; rename them (promoted code shares pcheck\'s namespace)')
    return out


def carry_check(d, cid):
    """Append the book's check code to pcheck.py (before run) and register it; names the function _chk_<id>."""
    src = open(os.path.join(d, 'catalog', 'checks', f'{cid}.py'), encoding='utf-8').read()
    ident = '_chk_' + re.sub(r'\W', '_', cid)
    code = re.sub(r'^def check\(', f'def {ident}(', src, count=1, flags=re.MULTILINE)
    path = os.path.join(LIB, 'pcheck.py')
    t = open(path, encoding='utf-8').read()
    block = f"# --- promoted check {cid}\n{code.rstrip()}\nCHECKS['{cid}'] = {ident}\n# --- end promoted check {cid}\n\n\n"
    t = t.replace('\ndef run(spec, element_specs, pack', '\n' + block + 'def run(spec, element_specs, pack', 1)
    open(path, 'w', encoding='utf-8').write(t)


def promote(d, pid, variant_of=None):
    """Copy a book pattern (and its new elements) into the skill catalog, refusing what would not hold up there."""
    from .lang import pack
    src = os.path.join(d, 'catalog', 'patterns', f'{pid}.md')
    if not os.path.exists(src):
        raise PlanError(f'{src} not found; write the pattern file first')
    p = read_pattern(src)
    entry = next((x for x in _new_patterns(d) if x.get('id') == pid), {})
    element_specs, skillE = elements(d), elements()
    newe = [e for e in p['elements'] if e not in skillE]
    errs = []
    for eid in newe:
        if eid not in element_specs:
            errs.append(f'element {eid} is in neither catalog')
            continue
        shape = element_shape(eid, element_specs[eid])
        if shape:
            errs += shape
            continue
        errs += book_check_gaps(d, eid, element_specs[eid])
        if not element_specs[eid].get('checks'):
            errs.append(f'new element {eid} needs a check with breaks')
        if not any(m.startswith(f'new element {eid}: check') for m in errs):
            errs += [f'new element {eid} {c}: {m}' for _, c, m, ok in element_cases(element_specs, pack('en'), {eid}) if not ok]  # examples use the skill's generic English case
    same = [q['id'] for q in patterns().values() if set(q['elements']) == set(p['elements']) and q['id'] != pid]
    if same and not variant_of:
        errs.append(f'element set equals {", ".join(same)}; fold it in with --as-variant-of {same[0]}')
    dom = domain_words(d)
    body = re.sub(r'^## Examples\n.*?(?=^## |\Z)', '', p['text'], flags=re.MULTILINE | re.DOTALL)
    hit = sorted(w for w in dom if w in body)
    for eid in [e for e in newe if e in element_specs and isinstance(element_specs[e], dict)]:
        hit += sorted(w for w in dom if eid in element_specs and w in json.dumps({k: v for k, v in element_specs[eid].items() if k != 'example'}, ensure_ascii=False))
    if hit:
        errs.append(f'domain words outside Examples: {", ".join(sorted(set(hit))[:8])}; keep hints, checks and seed generic')
    seed = (p['sections'].get('seed') or '').strip().splitlines()
    if not seed or not seed[0].strip():
        errs.append('no ## Seed line')
    if errs:
        raise PlanError(f'promote {pid} refused:\n  ' + '\n  '.join(errs))
    if variant_of:
        dst = patterns()[variant_of]['path'] if variant_of in patterns() else None
        if not dst:
            raise PlanError(f'--as-variant-of {variant_of}: no such catalog pattern')
        t = open(dst, encoding='utf-8').read()
        note = f'- Variant {pid}: {p["why"]}' + (f' ({entry.get("differs")})' if entry.get('differs') else '')
        t = re.sub(r'(^## Compose and vary\n(?:.*?\n)*?)(?=^## |\Z)', lambda m: m.group(1) + note + '\n', t, count=1, flags=re.MULTILINE)
        open(dst, 'w', encoding='utf-8').write(t)
        print(f'{pid} folded into {variant_of} as a composition note')
    else:
        os.makedirs(os.path.join(SKILL_CAT, 'patterns'), exist_ok=True)
        shutil.copy(src, os.path.join(SKILL_CAT, 'patterns', f'{pid}.md'))
        print(f'{pid} copied to assets/catalog/patterns')
    for eid in newe:
        for c in element_specs[eid].get('checks') or []:
            if c['id'] not in pcheck.CHECKS or c['id'] in pcheck.BOOK_CHECKS:
                carry_check(d, c['id'])
                print(f'check {c["id"]} copied into pcheck')
        os.makedirs(os.path.join(SKILL_CAT, 'elements'), exist_ok=True)
        shutil.copy(os.path.join(d, 'catalog', 'elements', f'{eid}.json'), os.path.join(SKILL_CAT, 'elements', f'{eid}.json'))
        print(f'element {eid} copied to assets/catalog/elements')
    sp = os.path.join(ASSETS, 'seeds.md')
    row = f'| card-pattern | {seed[0].strip()} |'
    parent = next(iter((patterns()[variant_of]['sections'].get('seed') or '').strip().splitlines()), '').strip() if variant_of and variant_of in patterns() else None
    if row in open(sp, encoding='utf-8').read().splitlines() or parent == seed[0].strip():
        print('seed not appended: the same line is already in assets/seeds.md or is the parent pattern\'s')
    else:
        with open(sp, 'a', encoding='utf-8') as fh:
            fh.write(row + '\n')
        print('seed appended to assets/seeds.md (row card-pattern)')
    return 0

# ---------------------------------------------------------------- brief and reviewer text


@functools.lru_cache(maxsize=1)
def _skill_ids():
    return frozenset(patterns())


def infer(node):
    """Heuristic label of a hand card from its markup."""
    from .dom import Node
    k = node.get('data-kind')
    if k:
        return {'sort': 'sort-bins', 'order': 'order', 'select': 'select-all', 'estimate': 'estimate', 'custom': 'compose'}.get(k, k)
    if any(isinstance(x, Node) and x.first(lambda y: y.get('data-c') == 'exhibit') for x in node.find(lambda y: y.tag == 'li')):
        return 'compare-designs'
    if node.first(lambda y: y.get('data-n')):
        return 'spot-defect'
    if node.first(lambda y: y.get('data-c') == 'exhibit'):
        return 'read-exhibit'
    mv = node.get('data-move')
    if mv == 'predict':
        lab = 'intervene' if node.first(lambda y: y.get('data-c') == 'frames') else 'scenario-decide'  # stepped frames are a variant of intervene
    else:
        lab = {'intervene': 'intervene', 'decide': 'scenario-decide', 'diagnose': 'read-exhibit', 'explain': 'explain-why', 'compute': 'estimate'}.get(mv, 'hand')
    return lab if lab == 'hand' or lab in _skill_ids() else ('read-exhibit' if 'read-exhibit' in _skill_ids() else 'hand')  # only labels the catalog has


def spread(d, uid, src):
    """'compare-designs 3 · hand 7 (~read-exhibit 4, ~sort-bins 3)' for a unit, and the top label's share."""
    from .dom import parse
    lab = collections.Counter()
    ent = load_slots(d).get(uid) or {}
    for typ, cid in PH.findall(src):
        if typ == 'card':
            lab[str((ent.get(cid) or {}).get('label') or 'unlabelled')] += 1
    for labs in fig_labels(d, src):
        lab.update(labs)
    hand = collections.Counter(infer(n) for n in parse(src).find(lambda n: n.get('data-c') in ('ask', 'task', 'probe')))
    n = sum(lab.values()) + sum(hand.values())
    top = (lab + hand).most_common(1)
    s = ' · '.join(f'{k} {v}' for k, v in lab.most_common())
    if hand:
        s += (' · ' if s else '') + f'hand {sum(hand.values())} (' + ', '.join(f'~{k} {v}' for k, v in hand.most_common()) + ')'
    return s or 'none', (top[0][1] / n if n else 0), (top[0][0] if top else '')


def writer_meta(d):
    """entry id -> reviewer lines: label, and each rival's belief, right_when and the facts it is ruled out by."""
    out = {}
    for ent in load_slots(d).values():
        for cid, spec in ent.items():
            if not isinstance(spec, dict):
                continue
            fs = pcheck.facts(spec)
            lines = [f'    label: {spec["label"]}'] if spec.get('label') else []
            for e in spec.get('elements') or []:
                if e.get('el') in ('rival', 'near-miss'):
                    rob = '; '.join(fs[k] for k in e.get('ruled_out_by') or [] if isinstance(k, int) and 0 <= k < len(fs))
                    lines.append(f'    rival "{pcheck.txt(e.get("text"))[:40]}": belief {e.get("belief", "-")}; right when {e.get("right_when", "-")}; ruled out by {rob or "-"}'
                             + (f'; missing {e["missing"]}' if e.get('missing') else ''))
            out[cid] = lines
    return out

# ---------------------------------------------------------------- command line


def register(sub):
    s = sub.add_parser('pattern', help='catalog patterns: list, show, promote')
    s.add_argument('action', choices=('list', 'show', 'promote')); s.add_argument('id', nargs='?')
    s.add_argument('--family', choices=('problem', 'visual')); s.add_argument('--dir', dest='book'); s.add_argument('--as-variant-of', dest='variant_of')
    s = sub.add_parser('element', help='catalog elements: show slots, checks, example')
    s.add_argument('action', choices=('show',)); s.add_argument('id'); s.add_argument('--dir', dest='book')
    for name in ('card', 'fig'):
        s = sub.add_parser(name, help=f'{name} new: placeholder + slots stub' + ('; card lift U ID: a hand card into slots' if name == 'card' else ''))
        s.add_argument('action', choices=('new', 'lift') if name == 'card' else ('new',)); s.add_argument('pos', nargs='*', metavar='[DIR] [U ID]')
        s.add_argument('--dir', dest='dir_opt', metavar='DIR'); s.add_argument('--unit'); s.add_argument('--after'); s.add_argument('--kind'); s.add_argument('--elements'); s.add_argument('--id'); s.add_argument('--label')
        if name == 'fig':
            s.add_argument('--tactic')


def run(a):
    if a.cmd == 'pattern':
        if a.action == 'list':
            return pattern_list(a.family, a.book)
        if not a.id:
            raise PlanError(f'pattern {a.action} needs an id')
        if a.action == 'show':
            return pattern_show(a.id, a.book)
        if not a.book:
            raise PlanError('pattern promote needs --dir BOOK')
        return promote(a.book, a.id, a.variant_of)
    if a.cmd == 'element':
        return element_show(a.id, a.book)
    pos = list(a.pos)
    need = 2 if a.action == 'lift' else 0
    if len(pos) not in (need, need + 1):
        raise PlanError(f'{a.cmd} {a.action} takes ' + ('[DIR] U ID' if need else '[DIR] and --unit U --after SEL'))
    d = pos.pop(0) if len(pos) > need else None
    if d and a.dir_opt and os.path.abspath(d) != os.path.abspath(a.dir_opt):
        raise PlanError(f'two book directories given: {d} and --dir {a.dir_opt}')
    d = d or a.dir_opt or '.'
    if a.action == 'lift':
        return lift(d, pos[0], pos[1])
    if not a.unit or not a.after:
        raise PlanError(f'{a.cmd} new needs --unit U and --after SEL')
    kind = a.kind or ('fig' if a.cmd == 'fig' else 'ask')
    if (a.cmd == 'fig') != (kind in FIG_KINDS):
        raise PlanError(f'{a.cmd} new --kind must be one of {", ".join(FIG_KINDS if a.cmd == "fig" else CARD_KINDS)}')
    return new_entry(d, a.unit, a.after, kind, a.elements, a.id, a.label, getattr(a, 'tactic', None))
