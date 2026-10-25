"""Element checks: each attaches to an element (or a pair that appears together), so any combination is checked by what it contains."""
import html, re

OPTS = ('answer', 'rival', 'near-miss')
JUDGE = r'\b(?:bad|good|better|worse|wrong|right|correct|poor|best|worst|ideal|confusing|clear)\b'


def txt(h):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(h or '')))).strip()


def nums(t):
    return set(re.findall(r'\d+(?:[.,/]\d+)*', t or ''))


def proper(t):
    """Latin names: tokens with a digit or an inner capital, and capitalised words that do not open a sentence."""
    out = set()
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9'’-]*", t or ''):
        w = m.group(0)
        if re.search(r'\d', w) or re.search(r'[A-Z]', w[1:]):
            out.add(w)
        elif w[0].isupper():
            pre = t[:m.start()].rstrip()
            if pre and not re.search(r'[.!?:"“(\'‘]$', pre):
                out.add(w)
    return out


def words(t):
    """Content words of 2+ letters; a long word keeps a stem so particles and endings do not hide it."""
    out = []
    for w in re.findall(r'[^\W\d_]{2,}', t or ''):
        out.append(w[:-1] if len(w) >= 4 and not w.isascii() else w.lower())
    return out


def _num(s):
    try:
        if '/' in s:
            a, b = s.split('/', 1)
            return float(a) / float(b)
        return float(s.replace(',', ''))
    except (ValueError, ZeroDivisionError):
        return None


def derived(x, pool):
    """x is in the pool or one arithmetic step from two pool numbers."""
    v = _num(x)
    if v is None or x in pool:
        return True
    ps = [p for p in (_num(p) for p in pool) if p is not None]
    for a in ps:
        for b in ps:
            for r in (a + b, a - b, a * b, a / b if b else None):
                if r is not None and abs(r - v) < 1e-9:
                    return True
    return False


def els(spec, *names):
    return [(i, e) for i, e in enumerate(spec.get('elements') or []) if isinstance(e, dict) and e.get('el') in names]


def facts(spec):
    """The card's facts in citation order: setup, card exhibits, option exhibits."""
    out = []
    for _, e in els(spec, 'setup', 'exhibit'):
        out += [str(f) for f in e.get('facts') or []]
    for _, e in els(spec, *OPTS):
        if isinstance(e.get('exhibit'), dict):
            out += [str(f) for f in e['exhibit'].get('facts') or []]
    return out


def exhibit_text(x):
    if not isinstance(x, dict):
        return ''
    return txt(x.get('html')) + ' ' + str(x.get('alt') or '') + ' ' + kit_text(x.get('kit'))


def kit_text(n):
    if not isinstance(n, dict):
        return ''
    n = n.get('tree', n) if 'c' not in n else n
    return ' '.join([str(n.get('t') or '')] + [kit_text(k) for k in n.get('kids') or []])


def kit_marks(n, out=None):
    out = [] if out is None else out
    if isinstance(n, dict):
        n = n.get('tree', n) if 'c' not in n else n
        if 'n' in n:
            out.append(n['n'])
        for k in n.get('kids') or []:
            kit_marks(k, out)
    return out


def stem_text(spec):
    return ' '.join(txt(e.get('text')) for _, e in els(spec, 'stem'))


def setup_text(spec):
    return ' '.join(txt(e.get('text')) for _, e in els(spec, 'setup'))


def present(fact, pool):
    """A fact is shown when its numbers and Latin names are in the pool, or (without either) half its words are."""
    pn, pp = nums(pool), pool
    need_n, need_p = nums(fact), proper(' ' + fact)
    if need_n or need_p:
        return need_n <= pn and all(p in pp for p in need_p)
    ws = words(fact)
    low = pool.lower()
    return not ws or sum(1 for w in ws if w in low) * 2 >= len(ws)

# ---------------------------------------------------------------- checks: fn(spec, i, ctx) -> [(level, msg)]


def stem_self_contained(spec, i, ctx):
    rx = ctx['pack'].get('unseen_ref')
    shows = els(spec, 'exhibit') or any(isinstance(e.get('exhibit'), dict) for _, e in els(spec, *OPTS))
    t = txt(spec['elements'][i].get('text'))
    m = rx and not shows and re.search(rx, t)
    return [('error', f'the stem points at material the card does not show ("{m.group(0)}"); add an exhibit or quote it')] if m else []


def facts_shown(spec, i, ctx):
    e = spec['elements'][i]
    pool = (stem_text(spec) + ' ' + setup_text(spec)) if e['el'] == 'setup' else exhibit_text(e)
    return [('error', f'fact "{f}" is not in the {e["el"]} the reader sees') for f in e.get('facts') or [] if not present(str(f), pool)]


def why_grounded(spec, i, ctx):
    e = spec['elements'][i]
    pool = ' '.join([stem_text(spec), setup_text(spec), ctx.get('known', '')] + facts(spec)
                    + [exhibit_text(x) for _, x in els(spec, 'exhibit')] + [txt(o.get('text')) + ' ' + exhibit_text(o.get('exhibit')) for _, o in els(spec, *OPTS)])
    why = txt(e.get('why'))
    pn = nums(pool)
    miss = [n for n in sorted(nums(why)) if not derived(n, pn)] + [p for p in sorted(proper(why)) if p not in pool]
    return [('warn', f'the why of "{txt(e.get("text"))[:30]}" rests on {", ".join(miss)}, which the card and the prose before it never gave')] if miss else []


def no_leak(spec, i, ctx):
    out, e = [], spec['elements'][i]
    if e['el'] == 'answer':
        a = txt(e.get('text')).lower().rstrip('.?')
        seen = stem_text(spec) + ' ' + ' '.join(str(x.get('alt') or '') for _, x in els(spec, 'exhibit'))
        if len(a) >= 6 and a in seen.lower():
            out.append(('warn', f'the answer "{a[:40]}" is written in the stem or an exhibit alt'))
    if e['el'] == 'option-exhibit':
        rx = ctx['pack'].get('judge') or JUDGE
        for _, o in els(spec, *OPTS):
            alt = str((o.get('exhibit') or {}).get('alt') or '')
            m = re.search(rx, alt, re.IGNORECASE)
            if m:
                out.append(('warn', f'option exhibit alt judges its option ("{m.group(0)}"); describe what it shows'))
    return out


def rival_real(spec, i, ctx):
    e, out = spec['elements'][i], []
    fs = facts(spec)
    rw = [txt(r.get('right_when')).lower() for _, r in els(spec, 'rival')]
    mine = txt(e.get('right_when')).lower()
    if not mine:
        out.append(('error', f'rival "{txt(e.get("text"))[:30]}" has no right_when: say when it would be right'))
    elif rw.count(mine) > 1:
        out.append(('error', f'rivals share right_when "{mine[:40]}"; each wrong option is right in its own situation'))
    rob = e.get('ruled_out_by')
    if not isinstance(rob, list) or not rob or any(not isinstance(k, int) or isinstance(k, bool) or not 0 <= k < len(fs) for k in rob):
        out.append(('error', f'rival "{txt(e.get("text"))[:30]}" ruled_out_by {rob} resolves to no fact of the card ({len(fs)} facts): a strawman'))
    return out


def near_miss_names(spec, i, ctx):
    e = spec['elements'][i]
    ws, why = words(str(e.get('missing') or '')), txt(e.get('why')).lower()
    return [] if ws and any(w in why for w in ws) else [('error', f'near-miss why never names the missing condition "{e.get("missing")}"')]


def differs_one(spec, i, ctx):
    out = []
    os_ = els(spec, *OPTS)
    no = [txt(o.get('text'))[:30] for _, o in os_ if not isinstance(o.get('exhibit'), dict)]
    if no:
        out.append(('error', f'option-exhibit: options without an exhibit: {", ".join(no)}'))
    props = [o['exhibit'].get('props') for _, o in os_ if isinstance(o.get('exhibit'), dict)]
    if props and all(isinstance(p, dict) for p in props):
        keys = set().union(*props)
        diff = {k for k in keys if len({repr(p.get(k)) for p in props}) > 1}
        want = spec['elements'][i].get('differs')
        if diff != {want}:
            out.append(('error', f'option exhibits differ in {sorted(diff) or "nothing"}, not only in {want}'))
    return out


def parts_match(spec, i, ctx):
    out = []
    ns = {m.get('n') for m in spec['elements'][i].get('marks') or [] if isinstance(m, dict)}
    shown = set()
    for _, x in els(spec, 'exhibit'):
        shown |= {int(n) for n in re.findall(r'data-n="(\d+)"', str(x.get('html') or ''))} | set(kit_marks(x.get('kit')))
    if shown != ns:
        out.append(('error', f'marks {sorted(ns)} differ from the numbered parts of the exhibit {sorted(shown)}'))
    om = [o.get('mark') for _, o in els(spec, *OPTS) if o.get('mark') is not None]
    bad = [m for m in om if m not in ns]
    if bad:
        out.append(('error', f'options name marks {bad} that the exhibit does not have'))
    elif om and om != sorted(om):
        out.append(('warn', 'options are not in mark order'))
    return out


def one_change(spec, i, ctx):
    e, out = spec['elements'][i], []
    if e['el'] == 'change':
        if re.search(r'[;；]', str(e.get('change') or '')):
            out.append(('error', 'change names more than one change; change one thing'))
        ls = [o.get('layer') for _, o in els(spec, *OPTS)]
        if None in ls:
            out.append(('error', 'with a change element every option carries layer (first-order, second-order, flip)'))
        elif len(set(ls)) < 2:
            out.append(('warn', 'all options state the same layer of the change'))
    elif e['el'] == 'steps':
        sc = els(spec, 'scene')
        objs = set(sc[0][1].get('objects') or []) if sc else None
        groups = (sc[0][1].get('groups') or {}) if sc else {}
        prev = None
        for k, st in enumerate(e.get('list') or [], 1):
            if not isinstance(st, dict):
                continue
            d = st.get('delta')
            if objs is not None and d not in objs and d not in groups:
                out.append(('error', f'frame {k} changes {d}, which the scene does not declare'))
            mem = set(groups.get(d) or [d])
            s = st.get('state') or {}
            if prev is not None:
                ch = {x for x in set(prev) | set(s) if prev.get(x) != s.get(x)}
                if ch - mem:
                    out.append(('error', f'frame {k} changes {sorted(ch)}; its delta names {d}: one change per frame'))
            prev = s
    elif e['el'] == 'pair':
        a, b = (e.get('before') or {}).get('state') or {}, (e.get('after') or {}).get('state') or {}
        ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
        if ch != {e.get('change')}:
            out.append(('error', f'before and after differ in {sorted(ch)}, not only in {e.get("change")}'))
    return out


def items_fit(spec, i, ctx):
    e, k, out = spec['elements'][i], spec.get('kind'), []
    li = [x for x in e.get('list') or [] if isinstance(x, dict)]
    if k == 'task-sort':
        bins = e.get('bins') or []
        if len(bins) < 2:
            out.append(('error', 'a sort needs two or more bins'))
        bad = [x.get('text') for x in li if x.get('bin') not in bins]
        if bad:
            out.append(('error', f'items in no declared bin: {", ".join(txt(b)[:20] for b in bad)}'))
        unused = [b for b in bins if b not in {x.get('bin') for x in li}]
        if unused:
            out.append(('error', f'bins with no item: {", ".join(unused)}'))
    elif k == 'task-order' and len(li) < 3:
        out.append(('error', 'an order task needs three or more items'))
    elif k == 'task-select':
        oks = [bool(x.get('ok')) for x in li]
        if all(oks) or not any(oks):
            out.append(('error', 'a select task needs right and wrong items'))
    return out


def given_shown(spec, i, ctx):
    e, out = spec['elements'][i], []
    pool = nums(stem_text(spec) + ' ' + setup_text(spec))
    for k, v in (e.get('given') or {}).items():
        if not nums(str(v)) <= pool:
            out.append(('error', f'given {k} = {v} is not stated in the stem'))
    if not isinstance(e.get('tol'), (int, float)) or e.get('tol') <= 0:
        out.append(('error', 'tol must be above 0: an estimate accepts a band'))
    return out


def model_checks(spec, i, ctx):
    return [] if spec['elements'][i].get('checks') else [('error', 'model lists no checks a correct build meets')]


def raw_use_element(spec, i, ctx):
    h = str(spec['elements'][i].get('html') or '')
    return [('warn', 'raw markup holds numbered marks or an exhibit; use the exhibit and marks elements so their checks run')] if re.search(r'data-n=|data-c="exhibit"', h) else []


def alt_complete(spec, i, ctx):
    e = spec['elements'][i]
    parts = [len(re.findall(r'\S+', str(e.get(k) or ''))) for k in ('kind', 'encodes', 'point')]
    need = ctx['pack'].get('alt_words', 5)
    if min(parts) < 2 or sum(parts) < need:
        return [('error', f'alt needs kind, what it encodes and its point, two words or more each ({parts})')]
    return []


def axes(spec, i, ctx):
    e, out = spec['elements'][i], []
    if e['el'] == 'axes':
        labels = txt(re.sub(r'<(?!/?text\b)[^>]+>', ' ', str(e.get('svg') or '')))
        for ax in ('x', 'y'):
            a = e.get(ax) or {}
            if not str(a.get('unit') or '').strip():
                out.append(('error', f'axis {ax} has no unit (write "count", "%" or the measure)'))
            if a.get('label') and str(a['label']) not in labels:
                out.append(('warn', f'axis {ax} label "{a["label"]}" is not drawn in the svg'))
    else:
        if len(e.get('list') or []) < 2:
            out.append(('error', 'panels need two or more cases'))
        if not str(e.get('domain') or '').strip():
            out.append(('error', 'panels need one shared domain'))
    return out


def direct_labels(spec, i, ctx):
    e, out = spec['elements'][i], []
    names = [str(s.get('name')) for s in e.get('list') or [] if isinstance(s, dict)]
    if e.get('legend') and len(names) <= 5:
        out.append(('warn', f'a legend for {len(names)} series; label each series where it is drawn'))
    if not e.get('legend'):
        drawn = ' '.join(txt(re.sub(r'<(?!/?text\b)[^>]+>', ' ', str(a.get('svg') or ''))) for _, a in els(spec, 'axes'))
        miss = [n for n in names if n not in drawn]
        if miss:
            out.append(('warn', f'series {", ".join(miss)} not labelled in the plot'))
    return out


def kit_marks_unique(spec, i, ctx):
    ms = kit_marks(spec['elements'][i].get('tree'))
    d = sorted({m for m in ms if ms.count(m) > 1})
    return [('error', f'kit marks repeat: {d}')] if d else []


def graph_edges(spec, i, ctx):
    e, out = spec['elements'][i], []
    ids = {n.get('id') for n in e.get('nodes') or [] if isinstance(n, dict)}
    for x in e.get('edges') or []:
        if x.get('from') not in ids or x.get('to') not in ids:
            out.append(('error', f'edge {x.get("from")} -> {x.get("to")} names a node the graph lacks'))
        if e.get('state') and not str(x.get('event') or '').strip():
            out.append(('error', f'state edge {x.get("from")} -> {x.get("to")} names no event'))
    return out


def demo_measures(spec, i, ctx):
    e = spec['elements'][i]
    return [] if e.get('controls') and e.get('measures') else [('error', 'a demo names its controls and what the reader measures')]


CHECKS = {'stem-self-contained': stem_self_contained, 'facts-shown': facts_shown, 'why-grounded': why_grounded, 'no-leak': no_leak, 'rival-real': rival_real,
          'near-miss-names': near_miss_names, 'differs-one': differs_one, 'parts-match': parts_match, 'one-change': one_change, 'items-fit': items_fit,
          'given-shown': given_shown, 'model-checks': model_checks, 'raw-use-element': raw_use_element, 'alt-complete': alt_complete, 'axes': axes,
          'direct-labels': direct_labels, 'kit-marks': kit_marks_unique, 'graph-edges': graph_edges, 'demo-measures': demo_measures}


BOOK_CHECKS = set()  # ids loaded from a book's catalog/checks/ (not yet promoted)


def load_book_checks(book):
    """Register BOOK/catalog/checks/ID.py (a `check(spec, i, ctx)` function) as check ID, so a book's new element can carry its own check."""
    import importlib.util, os
    d = os.path.join(book, 'catalog', 'checks')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        cid = f[:-3]
        if not f.endswith('.py') or (cid in CHECKS and cid not in BOOK_CHECKS):
            continue
        sp = importlib.util.spec_from_file_location('bookcheck_' + cid.replace('-', '_'), os.path.join(d, f))
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        if not callable(getattr(m, 'check', None)):
            raise ValueError(f'{f} defines no check(spec, i, ctx)')
        CHECKS[cid] = m.check
        BOOK_CHECKS.add(cid)


def run(spec, element_specs, pack, known=''):
    """[(check id, level, element index, msg)] for every element of a card or figure spec that the catalog knows."""
    ctx, out, seen = {'pack': pack or {}, 'known': known}, [], set()
    for i, e in enumerate(spec.get('elements') or []):
        el = element_specs.get(e.get('el')) if isinstance(e, dict) else None
        for c in (el or {}).get('checks') or []:
            fn = CHECKS.get(c['id'])
            if fn is None or (c['id'], i) in seen:
                continue
            seen.add((c['id'], i))
            for lv, msg in fn(spec, i, ctx):
                out.append((c['id'], lv, i, msg))
    return out
