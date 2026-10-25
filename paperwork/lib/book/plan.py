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
            raise PlanError(f'{path} not found; run `make-book.py init DIR` first')
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
        self.unit_by_id = {u['id']: u for u in self.units}
        self.idx = {u['id']: i for i, u in enumerate(self.units)}
        self.parts = [p for p in self.book.get('parts') or [] if 'id' in p and 'name' in p]
        self.part_by_id = {p['id']: p for p in self.parts}
        self.concept_by_id = {c['id']: c for c in d['concepts']}
        self.question_by_id = {q['id']: q for q in d['questions']}
        self.lexicon_by_id = {e['id']: e for e in d['lexicon']}
        self.home_by_id = {h['id']: h for h in d['homes']}
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
        self.defines = {u['id']: [c for c in self.concept_by_id.values() if c['unit'] == u['id']] for u in self.units}
        self.closure = {q: self._closure(question['needs']) for q, question in self.question_by_id.items()}
        self.serves = {u['id']: [q for q in self.question_by_id if any(self.concept_by_id[c]['unit'] == u['id'] for c in self.closure[q] if c in self.concept_by_id)] for u in self.units}
        self.arrival = {}
        for q, cl in self.closure.items():
            homes = [self.idx[self.concept_by_id[c]['unit']] for c in cl if c in self.concept_by_id and self.concept_by_id[c]['unit'] in self.idx]
            if homes:
                self.arrival[q] = self.units[max(homes)]['id']
        order = sorted(self.question_by_id, key=lambda q: (self.idx.get(self.arrival.get(q), 10 ** 6), list(self.question_by_id).index(q)))
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
            if c in self.concept_by_id:
                stack.extend(self.concept_by_id[c].get('needs', []))
        return seen

    def st(self, key, **kw):
        t = self.s.get(key, key)
        for k, v in kw.items():
            t = t.replace('{' + k + '}', str(v))
        return t

    def label(self, uid):
        n = self.num.get(uid)
        return self.unit_by_id[uid]['title'] if n is None else self.st('ref', n=n, title=self.unit_by_id[uid]['title'])


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


def fact_text(plan, name):
    v = plan.facts.get(name)
    if isinstance(v, dict):
        return v.get('text', str(v.get('value')))
    return None if v is None else str(v)

# ---------------------------------------------------------------- findings


class Findings(list):
    def add(self, rule, level, unit, msg, ev=''):
        if level:
            self.append(dict(rule=rule, level=level, unit=unit or '-', msg=msg, ev=str(ev)[:160]))


def settle(plan, findings, unit=None):
    """Drop warns allowed in decisions; scope to one unit."""
    allow = {(dc['allow'].get('rule'), dc['allow'].get('unit', '-')) for dc in plan.d['decisions'] if isinstance(dc.get('allow'), dict)}
    out = Findings()
    for f in findings:
        if f['level'] == 'warn' and ((f['rule'], f['unit']) in allow or (f['rule'], '*') in allow):
            continue
        if unit and f['unit'] not in (unit, '-'):
            continue
        out.append(f)
    return out

# ---------------------------------------------------------------- plan checks (B)


def check_plan(plan):
    findings = Findings()
    d, pol = plan.d, plan.pol
    for m in plan.schema:
        findings.add('B4', 'error', '-', 'schema: ' + m)
    for m in plan.badpol:
        findings.add('B4', 'error', '-', 'unknown policy ' + m)
    if not plan.book.get('title'):
        findings.add('B4', 'error', '-', 'book.title missing')
    for src in d.get('sources', []):
        if not src.get('id') or not src.get('name') or not src.get('forms') or src.get('unit') not in plan.unit_by_id:
            findings.add('B4', 'error', '-', 'a source needs id, name, forms and a known unit', str(src.get('id')))
        for fx in src.get('forms', []):
            try:
                re.compile(fx)
            except re.error:
                findings.add('B4', 'error', '-', 'source form does not compile', fx)
    forms = (plan.pack.get('register') or {}).get('forms') or {}
    if plan.book.get('register') and plan.book['register'] not in forms:
        findings.add('B4', 'error', '-', f'book.register names no form of assets/lang/{plan.pack["code"]}.json register.forms ({", ".join(forms) or "none"}); register checks would be off', plan.book['register'])
    if not plan.book.get('emphasis'):
        findings.add('B4', 'error', '-', 'book.emphasis missing: record what the reader must be able to do beyond knowing (the Emphasis node of the interview)')
    cn = d.get('canon') or {}
    for k, rx in (cn.get('kinds') or {}).items():
        try:
            re.compile(rx)
        except re.error as e:
            findings.add('B4', 'error', 'canon', f'canon.kinds.{k} regex invalid: {e}')
    for c in plan.concept_by_id.values():
        for a in [c] + [x for x in c.get('aliases', []) if isinstance(x, dict)]:
            form, fin = a.get('term') or a.get('form'), a.get('final')
            if form and fin and final_sound(form, plan.pack) and fin != final_sound(form, plan.pack):
                findings.add('B4', 'error', c['id'], f'final {fin} contradicts the reading of {form} ({final_sound(form, plan.pack)}); drop final where the pack derives it', form)
    ids = [x['id'] for k in ('units', 'concepts', 'questions', 'lexicon', 'homes', 'forbid') for x in d[k]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        findings.add('B4', 'error', i, 'duplicate id')
    if not plan.live:
        findings.add('B4', 'error', '-', 'no unit to build')
    for u in plan.units:
        if u['role'] not in ROLES:
            findings.add('B4', 'error', u['id'], f'role must be one of {ROLES}')
        if u.get('status') not in (None, 'planned'):
            findings.add('B4', 'error', u['id'], 'status may only be "planned"')
        if plan.parts and u['role'] in ('core', 'capstone', 'catalog') and u.get('part') not in plan.part_by_id:
            findings.add('B4', 'error', u['id'], 'part missing or unknown')
        if re.search(r'[:?？：]', u['title']):
            findings.add('B4', 'error', u['id'], 'title has a colon or question mark', u['title'])
    if pol['scale'] == 'book' and (not plan.units or plan.units[0]['role'] != 'map'):
        findings.add('B4', 'error', '-', 'scale book needs the map unit first')
    if pol['scale'] == 'page' and len(plan.live) != 1:
        findings.add('B4', 'error', '-', f'scale page needs exactly one unit, found {len(plan.live)}')
    for c in plan.concept_by_id.values():
        if c['unit'] not in plan.unit_by_id:
            findings.add('B4', 'error', c['id'], 'concept home unit unknown', c['unit'])
        for n in c.get('needs', []):
            if n not in plan.concept_by_id:
                findings.add('B4', 'error', c['id'], 'unknown need', n)
    syms = d['symbols']
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            if a['tex'] == b['tex']:
                sa, sb = set(a.get('scope') or []), set(b.get('scope') or [])
                if not sa or not sb or sa & sb:
                    findings.add('B4', 'error', '-', f'symbol {a["tex"]} has two meanings in overlapping scopes', f'{a["meaning"]} / {b["meaning"]}')
    for p in d['forbid']:
        bad = set(p) - FORBID_KEYS
        if bad:
            findings.add('B4', 'error', p['id'], f'unknown forbid keys {sorted(bad)}; use {sorted(FORBID_KEYS)}')
        if p.get('in', 'prose') not in ('prose', 'tex', 'label', 'all'):
            findings.add('B4', 'error', p['id'], 'forbid `in` must be prose, tex, label or all')
        try:
            if not re.search(p['re'], p['example']):
                findings.add('B4', 'error', p['id'], 'forbid entry does not match its example')
            if p.get('unless') and re.search(p['unless'], p['example']):
                findings.add('B4', 'error', p['id'], 'forbid example is exempted by its own unless')
        except re.error as e:
            findings.add('B4', 'error', p['id'], f'forbid regex invalid: {e}')
    for dc in d['decisions']:
        if isinstance(dc.get('allow'), dict) and dc['allow'].get('rule') not in RULES:
            findings.add('B4', 'error', '-', 'allow names an unknown rule', dc['allow'])
    # B1 questions and selection
    lo, hi = Q_COUNT[pol['scale']]
    if not lo <= len(plan.question_by_id) <= hi:
        findings.add('B1', 'error', '-', f'{len(plan.question_by_id)} questions; scale {pol["scale"]} wants {lo}-{hi}')
    for q in plan.question_by_id.values():
        if not q['needs']:
            findings.add('B1', 'error', q['id'], 'question needs no concept')
        if not q['answer']:
            findings.add('B1', 'error', q['id'], 'question has no one-sentence answer')
        for n in q['needs']:
            if n not in plan.concept_by_id:
                findings.add('B1', 'error', q['id'], 'unknown need', n)
    sel = {'minimum': 'error', 'source': 'warn', 'survey': None}[pol['selection']]
    reach = {c for cl in plan.closure.values() for c in cl}
    for c in plan.concept_by_id:
        if c not in reach:
            findings.add('B1', sel, c, 'concept serves no question: cut it or add the question')
    for u in plan.units:
        if u['role'] in ('core', 'capstone') and not plan.serves[u['id']]:
            findings.add('B1', sel, u['id'], 'unit serves no question')
    # B2 order and facts
    state = {}

    def cyc(c, path):
        if state.get(c) == 1:
            findings.add('B2', 'error', c, 'concept needs form a cycle', ' > '.join(path + [c]))
            return
        if state.get(c) == 2 or c not in plan.concept_by_id:
            return
        state[c] = 1
        for n in plan.concept_by_id[c].get('needs', []):
            cyc(n, path + [c])
        state[c] = 2
    for c in plan.concept_by_id:
        cyc(c, [])
    for c in plan.concept_by_id.values():
        for n in c.get('needs', []):
            if n in plan.concept_by_id and plan.idx.get(plan.concept_by_id[n]['unit'], -1) > plan.idx.get(c['unit'], -1):
                findings.add('B2', 'error', c['id'], f'needs {n}, which is homed later')
    if pol['structure'] != 'none':
        cores = [u for u in plan.units if u['role'] == 'core']
        for u in plan.units:
            for t in u.get('takes', []):
                m = plan.maker.get(t)
                if m is None and t not in plan.facts_decl:
                    findings.add('B2', 'error', u['id'], 'takes a fact nobody makes and project.facts does not declare', t)
                elif m is not None and plan.idx[m] >= plan.idx[u['id']]:
                    findings.add('B2', 'error', u['id'], f'takes {t} before {m} makes it')
        fin = plan.project.get('final')
        if pol['structure'] == 'project':
            if not fin or fin not in plan.maker:
                findings.add('B2', 'error', '-', 'project final fact is never made', fin)
            lacking = sum(1 for u in cores if not u.get('makes'))
            if cores and lacking > len(cores) / 3:
                findings.add('B2', 'warn', '-', f'{lacking} of {len(cores)} core units make no project fact')
    # B3 lexicon
    seen_m, seen_cm = {}, {}
    for e in plan.lexicon_by_id.values():
        if e['meaning'] in seen_m:
            findings.add('B3', 'error', e['id'], 'two lexicon entries share a meaning', e['meaning'])
        seen_m[e['meaning']] = e['id']
        if e['mark'] not in MARKS:
            findings.add('B3', 'error', e['id'], f'mark must be one of {MARKS}')
        key = (e['light'], e['mark'])
        if key in seen_cm:
            findings.add('B3', 'error', e['id'], 'two lexicon entries share color and mark', seen_cm[key])
        seen_cm[key] = e['id']
        for th in ('light', 'dark'):
            y = oklch_to_lum(e.get(th) or e['light'])
            if y is None:
                findings.add('B3', 'error', e['id'], f'{th} color is not oklch()')
            elif contrast(y, BG[th]) < plan.common['contrast']:
                findings.add('B3', 'warn', e['id'], f'{th} contrast {contrast(y, BG[th]):.2f} below {plan.common["contrast"]}')
    lig = lambda e, th: oklch_l(e.get(th) or e['light'])
    ramps = {}
    for e in plan.lexicon_by_id.values():
        k = e.get('kind', 'semantic')
        if k not in KINDS:
            findings.add('B3', 'error', e['id'], f'kind must be one of {KINDS}')
        elif k in ('sequential', 'diverging', 'cyclic'):
            ramps.setdefault((k, e.get('ramp') or e['id']), []).append(e)
    for (k, r), es in ramps.items():  # ordered ramps: steps are entries sharing `ramp`, in lexicon order
        for th in ('light', 'dark'):
            Ls = [lig(e, th) for e in es]
            if None in Ls or len(Ls) < 2:
                continue
            mids = [i for i, e in enumerate(es) if e.get('mid')]
            if k == 'sequential' and not (Ls == sorted(Ls) or Ls == sorted(Ls, reverse=True)):
                findings.add('B3', 'error', r, f'sequential ramp {th} lightness is not monotone', ' '.join(f'{x:.2f}' for x in Ls))
            if k == 'diverging':
                if len(mids) != 1:
                    findings.add('B3', 'error', r, 'a diverging ramp needs exactly one step with `mid` saying what the midpoint means')
                elif th == 'light' and Ls[mids[0]] < max(Ls):
                    findings.add('B3', 'error', r, 'diverging midpoint is not the lightest step', f'{Ls[mids[0]]:.2f} < {max(Ls):.2f}')
                elif not (Ls[:mids[0] + 1] in (sorted(Ls[:mids[0] + 1]), sorted(Ls[:mids[0] + 1], reverse=True)) and Ls[mids[0]:] in (sorted(Ls[mids[0]:]), sorted(Ls[mids[0]:], reverse=True))):
                    findings.add('B3', 'error', r, f'diverging ramp {th} lightness is not monotone on each side of the midpoint')
            if k == 'cyclic' and abs(Ls[0] - Ls[-1]) > 0.1:
                findings.add('B3', 'warn', r, f'cyclic ramp {th}: first and last steps differ in lightness; a cycle closes on itself')
    es = list(plan.lexicon_by_id.values())
    for i, a in enumerate(es):  # hue alone fails colour-vision deficiency: entries that share a mark differ in lightness
        for b2 in es[i + 1:]:
            dl = [abs(lig(a, th) - lig(b2, th)) for th in ('light', 'dark') if lig(a, th) is not None and lig(b2, th) is not None]
            if a['mark'] == b2['mark'] and dl and min(dl) < plan.common['cvd_dl']:
                findings.add('B3', 'warn', a['id'], f'{a["id"]} and {b2["id"]} share mark {a["mark"]} and differ in lightness by {min(dl):.2f} (< {plan.common["cvd_dl"]}); hue alone fails colour-vision deficiency: change lightness or mark', b2['id'])
    cat = sum(1 for e in plan.lexicon_by_id.values() if e.get('kind') == 'categorical')
    if cat > plan.common['max_categorical']:
        findings.add('B3', 'warn', '-', f'{cat} categorical lexicon entries; cap {plan.common["max_categorical"]}')
    if not plan.lexicon_by_id:
        findings.add('B3', 'error', '-', 'the lexicon is empty')
    avoid = {a: c['term'] for c in plan.concept_by_id.values() for a in c.get('avoid', [])}
    for x in list(plan.concept_by_id.values()) + list(plan.question_by_id.values()):
        for a, term in avoid.items():
            if a in ' '.join(str(x.get(k, '')) for k in ('gloss', 'text', 'answer', 'term')):
                findings.add('B4', 'error', x['id'], f'"{a}" is an avoided synonym of {term}')
    if pol['scale'] == 'book' and not plan.home_by_id and len(plan.live) > 5:
        findings.add('B3', 'warn', '-', 'no home figure declared')
    for h in plan.home_by_id.values():
        if not h['regions']:
            findings.add('B3', 'error', h['id'], 'home figure lists no regions to highlight')
    check_gates(plan, findings)
    return findings


GATES = ('plan-check', 'skeleton', 'review', 'publish')
HASH_SKIP = ('gates', 'rounds', 'decisions', 'forbid')
TOPICS = ('figures', 'cards', 'terms-box', 'models')  # requirements the interview front-loads: round 1 needs a directive with each topic before the skeleton gate


def plan_hash(plan):
    """Short hash of the approved plan: book.json without gates, rounds, decisions, forbid, policies.models and unit status."""
    d = plan.d if hasattr(plan, 'd') else plan
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


def pattern_gaps(plan):
    from .catalog import plan_gaps
    return plan_gaps(plan)


def check_gates(plan, findings):
    gates = plan.d.get('gates') or {}
    if not isinstance(gates, dict):
        findings.add('B5', 'error', '-', 'gates must be an object keyed by gate name')
        return
    for k, g in gates.items():
        if k not in GATES:
            findings.add('B5', 'error', '-', f'unknown gate {k}; gates are {", ".join(GATES)}')
        elif not isinstance(g, dict) or g.get('approved_by') not in ('user', 'self') or not g.get('at'):
            findings.add('B5', 'error', '-', f'gate {k} record needs approved_by (user or self) and at; record it with `make-book.py approve {k} --by user`')
    sk = gates.get('skeleton')
    if plan.live and not isinstance(sk, dict):
        findings.add('B5', 'error', '-', f'{len(plan.live)} units are past planned but no skeleton gate is recorded; show the skeleton, then `make-book.py approve skeleton --by user`')
    if isinstance(sk, dict):
        gaps = round_gaps(plan.d)
        np_ = pattern_gaps(plan)
        for m in np_:  # a skeleton approved before new_patterns existed carries no `new_patterns` count: warn only
            findings.add('B5', 'error' if 'new_patterns' in sk else 'warn', '-', m)
        if gaps:
            findings.add('B5', 'error', '-', f'skeleton gate recorded but round 1 has no directive on {", ".join(gaps)}; ask in the interview and record each as `make-book.py note TEXT --topic T`')
    rec = [(g.get('at', ''), k, g) for k, g in gates.items() if isinstance(g, dict) and g.get('plan_hash')]
    if rec:
        at, k, g = max(rec, key=lambda r: str(r[0]))
        h = plan_hash(plan)
        if g['plan_hash'] != h:
            findings.add('B5', 'error', '-', f'plan changed after the {k} gate ({g["plan_hash"]} -> {h}) without a new record; show the change, then re-record the gate')
