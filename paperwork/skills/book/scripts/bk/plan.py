import copy, json, os, re
from .const import BANDS, COMMON, DEFAULT_POLICY, KINDS, MARKS, FORBID_KEYS, POLICIES, Q_COUNT, ROLES, RULES, SCHEMA
from .dom import BG, contrast, oklch_to_lum, read_js
from .lang import final_sound, pack

# ---------------------------------------------------------------- plan model


class PlanError(Exception):
    pass


class Plan:
    def __init__(self, path):
        if not os.path.exists(path):
            raise PlanError(f'{path} not found; run `book.py init DIR` first')
        self.dir = os.path.dirname(os.path.abspath(path))
        try:
            self.d = d = json.load(open(path, encoding='utf-8'))
        except json.JSONDecodeError as e:
            raise PlanError(f'book.json is not valid JSON: {e}')
        if isinstance(d.get('patterns'), list) and 'forbid' not in d:  # v11 kept owner lint regexes under `patterns`; migrate once, in the file
            d['forbid'] = d.pop('patterns')
            json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        self.schema = []
        for key, req in SCHEMA.items():
            d.setdefault(key, [])
            for i, x in enumerate(d[key]):
                miss = [f for f in req if f not in x] if isinstance(x, dict) else list(req)
                if miss:
                    self.schema.append(f'{key}[{i}] lacks {", ".join(miss)}')
            d[key] = [x for x in d[key] if isinstance(x, dict) and all(f in x for f in req)]
        self.book = d.setdefault('book', {})
        pol = self.book.get('policies') or {}
        self.badpol = [f'{k}={v}' for k, v in pol.items() if k not in ('models', 'review', 'new_patterns') and (k not in POLICIES or v not in POLICIES[k])]
        self.pol = dict(DEFAULT_POLICY, **{k: v for k, v in pol.items() if k in POLICIES and v in POLICIES[k]})
        self.pack = pack(self.book.get('lang'))
        self.s = dict(self.pack['strings'], **(self.book.get('strings') or {}))
        self.units = d['units']
        self.live = [u for u in self.units if u.get('status') != 'planned']
        self.U = {u['id']: u for u in self.units}
        self.idx = {u['id']: i for i, u in enumerate(self.units)}
        self.parts = [p for p in self.book.get('parts') or [] if 'id' in p and 'name' in p]
        self.P = {p['id']: p for p in self.parts}
        self.C = {c['id']: c for c in d['concepts']}
        self.Q = {q['id']: q for q in d['questions']}
        self.L = {e['id']: e for e in d['lexicon']}
        self.H = {h['id']: h for h in d['homes']}
        self.project = d.get('project') or {}
        self.facts_decl = self.project.get('facts') or {}
        fp = os.path.join(self.dir, 'facts.json')
        self.facts = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
        self.bookjs = read_js(self.dir)
        n, self.num = 0, {}
        for u in self.units:
            if u['role'] == 'map':
                self.num[u['id']] = 0
            elif u['role'] == 'ref':
                self.num[u['id']] = None
            else:
                n += 1
                self.num[u['id']] = n
        self.defines = {u['id']: [c for c in self.C.values() if c['unit'] == u['id']] for u in self.units}
        self.closure = {q: self._closure(Q['needs']) for q, Q in self.Q.items()}
        self.serves = {u['id']: [q for q in self.Q if any(self.C[c]['unit'] == u['id'] for c in self.closure[q] if c in self.C)] for u in self.units}
        self.arrival = {}
        for q, cl in self.closure.items():
            homes = [self.idx[self.C[c]['unit']] for c in cl if c in self.C and self.C[c]['unit'] in self.idx]
            if homes:
                self.arrival[q] = self.units[max(homes)]['id']
        order = sorted(self.Q, key=lambda q: (self.idx.get(self.arrival.get(q), 10 ** 6), list(self.Q).index(q)))
        self.qnum = {q: i + 1 for i, q in enumerate(order)}
        self.bands = copy.deepcopy(BANDS[self.pol['length']])
        over = self.book.get('bands') or {}
        for role, o in over.items():
            if role != 'common':
                self.bands.setdefault(role, {}).update({k: tuple(v) if isinstance(v, list) else v for k, v in o.items()})
        self.common = dict(COMMON, **over.get('common', {}))
        self.maker = {}
        for u in self.units:
            for f in u.get('makes', []):
                self.maker.setdefault(f, u['id'])

    def _closure(self, needs):
        seen, stack = [], list(needs)
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.append(c)
            if c in self.C:
                stack.extend(self.C[c].get('needs', []))
        return seen

    def st(self, key, **kw):
        t = self.s.get(key, key)
        for k, v in kw.items():
            t = t.replace('{' + k + '}', str(v))
        return t

    def label(self, uid):
        n = self.num.get(uid)
        return self.U[uid]['title'] if n is None else self.st('ref', n=n, title=self.U[uid]['title'])


    def forms(self, c):
        """(form, final) pairs of a concept: its term and aliases; an alias may be {form, final}. A form ending in Hangul or a digit gets its final derived."""
        out = [(c['term'], c.get('final'))]
        for a in c.get('aliases', []):
            out.append((a.get('form'), a.get('final')) if isinstance(a, dict) else (a, None))
        return [(f, fi or final_sound(f, self.pack)) for f, fi in out if f]

def oklch_l(s):
    """OKLCH lightness 0-1 of a colour string, or None."""
    m = re.match(r'oklch\(\s*([\d.]+)(%?)', s or '')
    return float(m.group(1)) / (100 if m.group(2) else 1) if m else None


def fact_text(P, name):
    v = P.facts.get(name)
    if isinstance(v, dict):
        return v.get('text', str(v.get('value')))
    return None if v is None else str(v)

# ---------------------------------------------------------------- findings


class Findings(list):
    def add(self, rule, level, unit, msg, ev=''):
        if level:
            self.append(dict(rule=rule, level=level, unit=unit or '-', msg=msg, ev=str(ev)[:160]))


def settle(P, F, unit=None):
    """Drop warns allowed in decisions; scope to one unit."""
    allow = {(dc['allow'].get('rule'), dc['allow'].get('unit', '-')) for dc in P.d['decisions'] if isinstance(dc.get('allow'), dict)}
    out = Findings()
    for f in F:
        if f['level'] == 'warn' and ((f['rule'], f['unit']) in allow or (f['rule'], '*') in allow):
            continue
        if unit and f['unit'] not in (unit, '-'):
            continue
        out.append(f)
    return out

# ---------------------------------------------------------------- plan checks (B)


def check_plan(P):
    F = Findings()
    d, pol = P.d, P.pol
    for m in P.schema:
        F.add('B4', 'error', '-', 'schema: ' + m)
    for m in P.badpol:
        F.add('B4', 'error', '-', 'unknown policy ' + m)
    if not P.book.get('title'):
        F.add('B4', 'error', '-', 'book.title missing')
    for src in d.get('sources', []):
        if not src.get('id') or not src.get('name') or not src.get('forms') or src.get('unit') not in P.U:
            F.add('B4', 'error', '-', 'a source needs id, name, forms and a known unit', str(src.get('id')))
        for fx in src.get('forms', []):
            try:
                re.compile(fx)
            except re.error:
                F.add('B4', 'error', '-', 'source form does not compile', fx)
    forms = (P.pack.get('register') or {}).get('forms') or {}
    if P.book.get('register') and P.book['register'] not in forms:
        F.add('B4', 'error', '-', f'book.register names no form of lang/{P.pack["code"]}.json register.forms ({", ".join(forms) or "none"}); register checks would be off', P.book['register'])
    if not P.book.get('emphasis'):
        F.add('B4', 'error', '-', 'book.emphasis missing: record what the reader must be able to do beyond knowing (the Emphasis node of the interview)')
    cn = d.get('canon') or {}
    for k, rx in (cn.get('kinds') or {}).items():
        try:
            re.compile(rx)
        except re.error as e:
            F.add('B4', 'error', 'canon', f'canon.kinds.{k} regex invalid: {e}')
    for c in P.C.values():
        for a in [c] + [x for x in c.get('aliases', []) if isinstance(x, dict)]:
            form, fin = a.get('term') or a.get('form'), a.get('final')
            if form and fin and final_sound(form, P.pack) and fin != final_sound(form, P.pack):
                F.add('B4', 'error', c['id'], f'final {fin} contradicts the reading of {form} ({final_sound(form, P.pack)}); drop final where the pack derives it', form)
    ids = [x['id'] for k in ('units', 'concepts', 'questions', 'lexicon', 'homes', 'forbid') for x in d[k]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        F.add('B4', 'error', i, 'duplicate id')
    if not P.live:
        F.add('B4', 'error', '-', 'no unit to build')
    for u in P.units:
        if u['role'] not in ROLES:
            F.add('B4', 'error', u['id'], f'role must be one of {ROLES}')
        if u.get('status') not in (None, 'planned'):
            F.add('B4', 'error', u['id'], 'status may only be "planned"')
        if P.parts and u['role'] in ('core', 'capstone', 'catalog') and u.get('part') not in P.P:
            F.add('B4', 'error', u['id'], 'part missing or unknown')
        if re.search(r'[:?？：]', u['title']):
            F.add('B4', 'error', u['id'], 'title has a colon or question mark', u['title'])
    if pol['scale'] == 'book' and (not P.units or P.units[0]['role'] != 'map'):
        F.add('B4', 'error', '-', 'scale book needs the map unit first')
    if pol['scale'] == 'page' and len(P.live) != 1:
        F.add('B4', 'error', '-', f'scale page needs exactly one unit, found {len(P.live)}')
    for c in P.C.values():
        if c['unit'] not in P.U:
            F.add('B4', 'error', c['id'], 'concept home unit unknown', c['unit'])
        for n in c.get('needs', []):
            if n not in P.C:
                F.add('B4', 'error', c['id'], 'unknown need', n)
    syms = d['symbols']
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            if a['tex'] == b['tex']:
                sa, sb = set(a.get('scope') or []), set(b.get('scope') or [])
                if not sa or not sb or sa & sb:
                    F.add('B4', 'error', '-', f'symbol {a["tex"]} has two meanings in overlapping scopes', f'{a["meaning"]} / {b["meaning"]}')
    for p in d['forbid']:
        bad = set(p) - FORBID_KEYS
        if bad:
            F.add('B4', 'error', p['id'], f'unknown forbid keys {sorted(bad)}; use {sorted(FORBID_KEYS)}')
        if p.get('in', 'prose') not in ('prose', 'tex', 'label', 'all'):
            F.add('B4', 'error', p['id'], 'forbid `in` must be prose, tex, label or all')
        try:
            if not re.search(p['re'], p['example']):
                F.add('B4', 'error', p['id'], 'forbid entry does not match its example')
            if p.get('unless') and re.search(p['unless'], p['example']):
                F.add('B4', 'error', p['id'], 'forbid example is exempted by its own unless')
        except re.error as e:
            F.add('B4', 'error', p['id'], f'forbid regex invalid: {e}')
    for dc in d['decisions']:
        if isinstance(dc.get('allow'), dict) and dc['allow'].get('rule') not in RULES:
            F.add('B4', 'error', '-', 'allow names an unknown rule', dc['allow'])
    # B1 questions and selection
    lo, hi = Q_COUNT[pol['scale']]
    if not lo <= len(P.Q) <= hi:
        F.add('B1', 'error', '-', f'{len(P.Q)} questions; scale {pol["scale"]} wants {lo}-{hi}')
    for q in P.Q.values():
        if not q['needs']:
            F.add('B1', 'error', q['id'], 'question needs no concept')
        if not q['answer']:
            F.add('B1', 'error', q['id'], 'question has no one-sentence answer')
        for n in q['needs']:
            if n not in P.C:
                F.add('B1', 'error', q['id'], 'unknown need', n)
    sel = {'minimum': 'error', 'source': 'warn', 'survey': None}[pol['selection']]
    reach = {c for cl in P.closure.values() for c in cl}
    for c in P.C:
        if c not in reach:
            F.add('B1', sel, c, 'concept serves no question: cut it or add the question')
    for u in P.units:
        if u['role'] in ('core', 'capstone') and not P.serves[u['id']]:
            F.add('B1', sel, u['id'], 'unit serves no question')
    # B2 order and facts
    state = {}

    def cyc(c, path):
        if state.get(c) == 1:
            F.add('B2', 'error', c, 'concept needs form a cycle', ' > '.join(path + [c]))
            return
        if state.get(c) == 2 or c not in P.C:
            return
        state[c] = 1
        for n in P.C[c].get('needs', []):
            cyc(n, path + [c])
        state[c] = 2
    for c in P.C:
        cyc(c, [])
    for c in P.C.values():
        for n in c.get('needs', []):
            if n in P.C and P.idx.get(P.C[n]['unit'], -1) > P.idx.get(c['unit'], -1):
                F.add('B2', 'error', c['id'], f'needs {n}, which is homed later')
    if pol['structure'] != 'none':
        cores = [u for u in P.units if u['role'] == 'core']
        for u in P.units:
            for t in u.get('takes', []):
                m = P.maker.get(t)
                if m is None and t not in P.facts_decl:
                    F.add('B2', 'error', u['id'], 'takes a fact nobody makes and project.facts does not declare', t)
                elif m is not None and P.idx[m] >= P.idx[u['id']]:
                    F.add('B2', 'error', u['id'], f'takes {t} before {m} makes it')
        fin = P.project.get('final')
        if pol['structure'] == 'project':
            if not fin or fin not in P.maker:
                F.add('B2', 'error', '-', 'project final fact is never made', fin)
            lacking = sum(1 for u in cores if not u.get('makes'))
            if cores and lacking > len(cores) / 3:
                F.add('B2', 'warn', '-', f'{lacking} of {len(cores)} core units make no project fact')
    # B3 lexicon
    seen_m, seen_cm = {}, {}
    for e in P.L.values():
        if e['meaning'] in seen_m:
            F.add('B3', 'error', e['id'], 'two lexicon entries share a meaning', e['meaning'])
        seen_m[e['meaning']] = e['id']
        if e['mark'] not in MARKS:
            F.add('B3', 'error', e['id'], f'mark must be one of {MARKS}')
        key = (e['light'], e['mark'])
        if key in seen_cm:
            F.add('B3', 'error', e['id'], 'two lexicon entries share color and mark', seen_cm[key])
        seen_cm[key] = e['id']
        for th in ('light', 'dark'):
            y = oklch_to_lum(e.get(th) or e['light'])
            if y is None:
                F.add('B3', 'error', e['id'], f'{th} color is not oklch()')
            elif contrast(y, BG[th]) < P.common['contrast']:
                F.add('B3', 'warn', e['id'], f'{th} contrast {contrast(y, BG[th]):.2f} below {P.common["contrast"]}')
    lig = lambda e, th: oklch_l(e.get(th) or e['light'])
    ramps = {}
    for e in P.L.values():
        k = e.get('kind', 'semantic')
        if k not in KINDS:
            F.add('B3', 'error', e['id'], f'kind must be one of {KINDS}')
        elif k in ('sequential', 'diverging', 'cyclic'):
            ramps.setdefault((k, e.get('ramp') or e['id']), []).append(e)
    for (k, r), es in ramps.items():  # ordered ramps: steps are entries sharing `ramp`, in lexicon order
        for th in ('light', 'dark'):
            Ls = [lig(e, th) for e in es]
            if None in Ls or len(Ls) < 2:
                continue
            mids = [i for i, e in enumerate(es) if e.get('mid')]
            if k == 'sequential' and not (Ls == sorted(Ls) or Ls == sorted(Ls, reverse=True)):
                F.add('B3', 'error', r, f'sequential ramp {th} lightness is not monotone', ' '.join(f'{x:.2f}' for x in Ls))
            if k == 'diverging':
                if len(mids) != 1:
                    F.add('B3', 'error', r, 'a diverging ramp needs exactly one step with `mid` saying what the midpoint means')
                elif th == 'light' and Ls[mids[0]] < max(Ls):
                    F.add('B3', 'error', r, 'diverging midpoint is not the lightest step', f'{Ls[mids[0]]:.2f} < {max(Ls):.2f}')
                elif not (Ls[:mids[0] + 1] in (sorted(Ls[:mids[0] + 1]), sorted(Ls[:mids[0] + 1], reverse=True)) and Ls[mids[0]:] in (sorted(Ls[mids[0]:]), sorted(Ls[mids[0]:], reverse=True))):
                    F.add('B3', 'error', r, f'diverging ramp {th} lightness is not monotone on each side of the midpoint')
            if k == 'cyclic' and abs(Ls[0] - Ls[-1]) > 0.1:
                F.add('B3', 'warn', r, f'cyclic ramp {th}: first and last steps differ in lightness; a cycle closes on itself')
    es = list(P.L.values())
    for i, a in enumerate(es):  # hue alone fails colour-vision deficiency: entries that share a mark differ in lightness
        for b2 in es[i + 1:]:
            dl = [abs(lig(a, th) - lig(b2, th)) for th in ('light', 'dark') if lig(a, th) is not None and lig(b2, th) is not None]
            if a['mark'] == b2['mark'] and dl and min(dl) < P.common['cvd_dl']:
                F.add('B3', 'warn', a['id'], f'{a["id"]} and {b2["id"]} share mark {a["mark"]} and differ in lightness by {min(dl):.2f} (< {P.common["cvd_dl"]}); hue alone fails colour-vision deficiency: change lightness or mark', b2['id'])
    cat = sum(1 for e in P.L.values() if e.get('kind') == 'categorical')
    if cat > P.common['max_categorical']:
        F.add('B3', 'warn', '-', f'{cat} categorical lexicon entries; cap {P.common["max_categorical"]}')
    if not P.L:
        F.add('B3', 'error', '-', 'the lexicon is empty')
    avoid = {a: c['term'] for c in P.C.values() for a in c.get('avoid', [])}
    for x in list(P.C.values()) + list(P.Q.values()):
        for a, term in avoid.items():
            if a in ' '.join(str(x.get(k, '')) for k in ('gloss', 'text', 'answer', 'term')):
                F.add('B4', 'error', x['id'], f'"{a}" is an avoided synonym of {term}')
    if pol['scale'] == 'book' and not P.H and len(P.live) > 5:
        F.add('B3', 'warn', '-', 'no home figure declared')
    for h in P.H.values():
        if not h['regions']:
            F.add('B3', 'error', h['id'], 'home figure lists no regions to highlight')
    check_gates(P, F)
    return F


GATES = ('plan-check', 'skeleton', 'review', 'publish')
HASH_SKIP = ('gates', 'rounds', 'decisions', 'forbid')
TOPICS = ('figures', 'cards', 'terms-box', 'models')  # requirements the interview front-loads: round 1 needs a directive with each topic before the skeleton gate


def plan_hash(P):
    """Short hash of the approved plan: book.json without gates, rounds, decisions, forbid, policies.models and unit status."""
    d = P.d if hasattr(P, 'd') else P
    x = copy.deepcopy({k: v for k, v in d.items() if k not in HASH_SKIP and v not in ([], {}, None)})
    b = x.get('book') or {}
    if isinstance(b.get('policies'), dict):
        b['policies'].pop('models', None)
        b['policies'].pop('review', None)
    for u in x.get('units') or []:
        if isinstance(u, dict):
            u.pop('status', None)
    import hashlib
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]


def round_gaps(d):
    """TOPICS that no directive of the first round carries in its `topic` field."""
    rs = d.get('rounds') or []
    r0 = rs[0] if rs and isinstance(rs[0], dict) else {}
    have = set()
    for x in r0.get('directives') or []:
        if isinstance(x, dict):
            t = x.get('topic')
            have.update(t if isinstance(t, list) else [t])
    return [t for t in TOPICS if t not in have]


def pattern_gaps(P):
    from .catalog import plan_gaps
    return plan_gaps(P)


def check_gates(P, F):
    gates = P.d.get('gates') or {}
    if not isinstance(gates, dict):
        F.add('B5', 'error', '-', 'gates must be an object keyed by gate name')
        return
    for k, g in gates.items():
        if k not in GATES:
            F.add('B5', 'error', '-', f'unknown gate {k}; gates are {", ".join(GATES)}')
        elif not isinstance(g, dict) or g.get('approved_by') not in ('user', 'self') or not g.get('at'):
            F.add('B5', 'error', '-', f'gate {k} record needs approved_by (user or self) and at; record it with `book.py approve {k} --by user`')
    sk = gates.get('skeleton')
    if P.live and not isinstance(sk, dict):
        F.add('B5', 'error', '-', f'{len(P.live)} units are past planned but no skeleton gate is recorded; show the skeleton, then `book.py approve skeleton --by user`')
    if isinstance(sk, dict):
        gaps = round_gaps(P.d)
        np_ = pattern_gaps(P)
        for m in np_:  # a skeleton approved before new_patterns existed carries no `new_patterns` count: warn only
            F.add('B5', 'error' if 'new_patterns' in sk else 'warn', '-', m)
        if gaps:
            F.add('B5', 'error', '-', f'skeleton gate recorded but round 1 has no directive on {", ".join(gaps)}; ask in the interview and record each as `book.py note TEXT --topic T`')
    rec = [(g.get('at', ''), k, g) for k, g in gates.items() if isinstance(g, dict) and g.get('plan_hash')]
    if rec:
        at, k, g = max(rec, key=lambda r: str(r[0]))
        h = plan_hash(P)
        if g['plan_hash'] != h:
            F.add('B5', 'error', '-', f'plan changed after the {k} gate ({g["plan_hash"]} -> {h}) without a new record; show the change, then re-record the gate')
