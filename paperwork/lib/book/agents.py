"""Generated briefs, task lists, round directives and gate approvals for make-book.py (brief, agents, note, round, approve).
"""
import collections, datetime, glob, json, os, re, shlex, sys

from .const import MAKE_BOOK, REFERENCES

REF = REFERENCES

ROUTES = {  # role -> stage, model, effort; book.json book.policies.models {role: {model, effort}} overrides
    'research-bulk': dict(stage='plan', model='haiku', effort='medium'),
    'research-explore': dict(stage='plan', model='sonnet', effort='medium'),
    'writer': dict(stage='write', model=None, effort=None),
    'review-facts': dict(stage='review', model='sonnet', effort='medium'),
    'review-conformance': dict(stage='review', model='sonnet', effort='high'),
    'review-intent': dict(stage='review', model='opus', effort='medium'),
    'review-coherence': dict(stage='review', model='opus', effort='high'),
    'test': dict(stage='any', model='sonnet', effort='medium'),
    'demo': dict(stage='write', model='sonnet', effort='medium'),
    'debug': dict(stage='any', model='opus', effort='medium'),
    'sources': dict(stage='review', model='haiku', effort='medium'),  # complete study-note fields (rule family E)
    'fixer': dict(stage='review', model='sonnet', effort='medium'),  # lint- and render-driven edits
}
FIX_CAPS = dict(sources=(12, 3), fixer=(25, 99))  # findings, units per task
TOPIC_TEXT = {'figures': 'figure and exhibit density', 'cards': 'card density', 'terms-box': 'terms boxes', 'models': 'deep models', 'demo': 'a demo request'}
WRITER_MAX, ROLE_MAX = 6000, 1500
BATCH_CHARS = 25000  # input chars per review task
LEFTOVER = 0.3  # a last task under this share of the cap merges into the one before
RULES = {  # printed once per brief
    'all': ['Write only in `{scratch}` and the files you own.', 'Directions arriving mid-run wait for the next round.',
            'Hand back at most 10 lines, in the form below.', 'Use the fewest tools that do the job; finish in at most 40 tool calls (read once, batch the reads), and when the budget ends hand back what is left.'],
    'writer': ['Put this round\'s edits in one `{scratch}patch.json` for `edit --patch`.',
               'Requirements come in this brief; a missing one goes in `open:`, not into a guess.'],
    'fix': ['Put every edit in the one patch.', 'Change only what a listed finding names.'],
    'review': ['Judge only from the inputs above; change no book file.'],
}
STAGES = ('plan', 'write', 'review', 'test', 'demo', 'debug', 'fix')
CARD_KINDS = ('probe', 'ask', 'task', 'ex', 'close')
BAND_KINDS = CARD_KINDS + ('worked', 'defn', 'terms', 'fig', 'frames', 'exhibit')


class AgentsError(Exception):
    pass


# ---------------------------------------------------------------- model access
def _book():
    from . import api
    return api


def topics():
    return tuple(_book().TOPICS)


def _plan(d):
    return _book().Plan(os.path.join(d, 'book.json'))


def plan_hash(plan):
    return _book().plan_hash(plan)


def _raw(d):
    return json.load(open(os.path.join(d, 'book.json'), encoding='utf-8'))


def _save(d, j):
    p = os.path.join(d, 'book.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(p + '.tmp', p)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def routes(plan):
    over = (plan.d.get('policies') or {}).get('models') or (plan.book.get('policies') or {}).get('models') or {}
    out = {}
    for role, r in ROUTES.items():
        o = over.get(role) or {}
        out[role] = dict(r, model=o.get('model', r['model']), effort=o.get('effort', r['effort']))
    return out


def run_line(d, rest):
    """A command line that runs as printed from any directory."""
    q = shlex.quote
    return f'python3 {q(MAKE_BOOK)} {rest}' + (f' --dir {q(os.path.abspath(d))}' if d else '')


def scratch(d, aid):
    """Scratch path as make-book.py reads it: a `.work/` path resolves inside the book directory."""
    return f'.work/{aid}/'


# ---------------------------------------------------------------- criteria rows
def rows(name, ref=None):
    """{heading: [(id, text)]} from `| id | ... |` tables under ## headings of references/NAME; ids are lowercase kebab."""
    p = os.path.join(ref or REF, name)
    if not os.path.exists(p):
        raise AgentsError(f'references/{name} not found; the brief needs its rows')
    out, head = collections.OrderedDict(), None
    for line in open(p, encoding='utf-8'):
        m = re.match(r'##\s+(.+?)\s*$', line)
        if m:
            head = m.group(1)
            out.setdefault(head, [])
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')] if line.lstrip().startswith('|') else []
        if head and len(cells) >= 2:
            rid = cells[0].strip('`')
            if re.fullmatch(r'[a-z][a-z0-9]*(-[a-z0-9]+)+', rid):
                out[head].append((rid, ' | '.join(cells[1:])))
    return out


def lenses(ref=None):
    """{lens: {role, inputs, gate, rows, protocol}} from `## lens: NAME` sections of references/review.md."""
    p = os.path.join(ref or REF, 'review.md')
    if not os.path.exists(p):
        raise AgentsError('references/review.md not found; reviewer briefs need its lens sections')
    src = open(p, encoding='utf-8').read()
    out, rs = collections.OrderedDict(), rows('review.md', ref)
    pm = re.search(r'^##\s+protocol\s*\n(.*?)(?=^##\s|\Z)', src, re.DOTALL | re.MULTILINE)
    for m in re.finditer(r'^##\s+(lens:\s*(\S+))[^\n]*\n(.*?)(?=^##\s|\Z)', src, re.DOTALL | re.MULTILINE):
        name, body = m.group(2).strip(), m.group(3)
        head = body.split('\n|', 1)[0]
        role = next((r for r in ROUTES if r.startswith('review-') and re.search(r'`' + re.escape(r) + r'`', head)), 'review-conformance')
        im = re.search(r'Inputs?:([^\n]*)', head)
        g = re.search(r'\bat the `?([\w-]+)`? gate', head)
        out[name] = dict(role=role, inputs=re.findall(r'`([^`]+)`', im.group(1)) if im else [], gate=g.group(1) if g else 'review',
                         rows=rs.get(m.group(1).strip(), []), protocol=pm.group(1).strip() if pm else '', note=re.sub(r'^Role [^\n]*$', '', head, flags=re.MULTILINE).strip())
    if not out:
        raise AgentsError('references/review.md has no `## lens: NAME` sections')
    return out


def _resolve(text, wr):
    """Inline a `write.md#id` pointer with that row's text so a brief stands alone."""
    return re.sub(r'`?write\.md#([a-z0-9-]+)`?', lambda m: f'write.md {m.group(1)} ("{wr.get(m.group(1), "?")}")', text)


# ---------------------------------------------------------------- book facts
def _units_src(d):
    return _book().read_units(d)


def demos(d):
    """[(name, doc, units)] from the book's book.js."""
    return [(x['name'], x.get('doc', ''), x.get('units', [])) for x in _book().demo_index(d)]


def kit(d):
    """[(class, doc)] documented in a `/* kit: ... */` block of the book's book.js: one `.class  what it draws` per line."""
    jp = os.path.join(d, 'book.js')
    if not os.path.exists(jp):
        return []
    out = []
    for blk in re.findall(r'/\*\s*kit:(.*?)\*/', open(jp, encoding='utf-8').read(), re.DOTALL):
        for ln in blk.split('\n'):
            m = re.match(r'\s*\*?\s*(\.[\w-]+(?:[ ,]+\.[\w-]+)*)\s+(.*\S)', ln)
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def _cards(src):
    """[(kind, id, variant_of)] of card blocks in a unit source."""
    out = []
    for m in re.finditer(r'<(?:div|section|aside|details)\b([^>]*\bdata-c="(' + '|'.join(CARD_KINDS) + r')"[^>]*)>', src):
        a = m.group(1)
        i = re.search(r'\bid="([^"]+)"', a)
        v = re.search(r'\bdata-variant-of="([^"]+)"', a)
        out.append((m.group(2), i.group(1) if i else None, v.group(1) if v else None))
    return out


def _topic(x):
    return x.get('topic')


def _directives(j, uid=None, topic=None, closed_only=False):
    """Directives of every closed round in order (standing requirements stay); the open round only when none is closed."""
    rs = j.get('rounds') or []
    use = [r for r in rs if r.get('status') == 'closed'] or ([] if closed_only else rs[-1:])
    ds = [(r.get('n'), x) for r in use for x in r.get('directives', [])
          if (not x.get('units') or uid is None or uid in x['units']) and (topic is None or _topic(x) == topic)]
    return use, ds


def _cut(s, n):
    s = re.sub(r'\s+', ' ', str(s)).strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _band(b):
    return ', '.join(f'{k} {v[0]}-{v[1]}' if isinstance(v, (tuple, list)) else f'{k} {v}' for k, v in b.items())


def _handback(kind, aid, h, d):
    s = scratch(d, aid)
    if kind == 'writer':
        body = [f'HANDBACK {aid} plan:{h}', f'patch: {s}patch.json applied (or: not applied, why)',
                'files: <figure scripts, svgs, book.js demos you own>', 'model: <book.json changes as one JSON object, or none>',
                'lint: <errors>/<warns> for the unit after the patch', 'shots: <flagged checks left, or ok>', 'demo: <a demo change to request, or none>', 'open: <one question for the lead, or none>']
    elif kind == 'review':
        body = [f'HANDBACK {aid} plan:{h}', f'no: <count>; every no is one line in {s}no.tsv: unit TAB block id TAB row id TAB repair in the book language (quote in the repair)',
                'up to 8 no rows may also be listed here as: <row-id> <unit> "<quote>" -> <repair>', 'skill: <a finding that recurs in other books, with its detector, or none>']
    else:
        body = [f'HANDBACK {aid} plan:{h}', 'result: <one line>', 'evidence: <paths or lines>', 'open: <one question, or none>']
    return '```\n' + '\n'.join(body) + '\n```'


def _common(d, aid, h, kind):
    s = scratch(d, aid)
    rules = RULES['all'] + RULES.get(kind, [])
    return ['## Rules'] + ['- ' + r.format(scratch=s) for r in rules] + ['', '## Hand-back', _handback(kind, aid, h, d)]


def _code(lines):
    return ['```'] + lines + ['```']


# ---------------------------------------------------------------- briefs
def write_pointer():
    heads = _book().WRITE_SECTIONS
    if not os.path.exists(os.path.join(REF, 'write.md')):
        raise AgentsError('references/write.md not found; the writer brief points to it')
    return f'Read `{os.path.abspath(os.path.join(REF, "write.md"))}` sections {", ".join(heads)} once before the first draft; every row applies to this unit.'


def writer_brief(d, uid, aid=None, plan=None, j=None, level=0, revise=False):
    plan = plan or _plan(d)
    j = j or _raw(d)
    if uid not in plan.unit_by_id:
        raise AgentsError(f'unit {uid} is not in book.json')
    u, aid, h = plan.unit_by_id[uid], aid or f'w-{uid}', plan_hash(plan)
    b = _book()
    src = _units_src(d).get(uid, '')
    gl = (90, 60, 40)[level]
    s = scratch(d, aid)
    brief_lines = [f'# Writer brief: {uid} {u["title"]}' + (' (revise)' if revise else ''), f'Agent `{aid}`, role writer, plan hash `{h}`, scratch `{s}` in `{os.path.abspath(d)}`.', '', '## Unit']
    part = plan.part_by_id.get(u.get('part'), {}).get('name')
    brief_lines.append(f'- role {u["role"]}' + (f', part {part}' if part else '') + f', status {u.get("status", "written" if src else "new")}, book {plan.book.get("lang", "en")} / {plan.book.get("register", "-")}')
    brief_lines.append(f'- band: {_band(plan.bands.get(u["role"], {})) or "none"}')
    qs = plan.serves.get(uid, [])
    here = [q for q in qs if plan.arrival.get(q) == uid] or qs[:1]
    for q in here:
        brief_lines.append(f'- answers {q}: {_cut(plan.question_by_id[q]["text"], gl + 40)}')
    if len(qs) > len(here):
        brief_lines.append('- also feeds: ' + ', '.join(q for q in qs if q not in here))
    i = plan.idx[uid]
    prev = plan.units[i - 1]['id'] if i else '-'
    nxt = plan.units[i + 1]['id'] if i + 1 < len(plan.units) else '-'
    brief_lines.append(f'- place: after {prev}, before {nxt}; takes {", ".join(u.get("takes", [])) or "-"}; makes {", ".join(u.get("makes", [])) or "-"}')
    brief_lines += ['', '## Concepts', '| id | term | en | gloss | needs | avoid |', '|---|---|---|---|---|---|']
    links = []
    for c in plan.defines.get(uid, []):
        brief_lines.append(f'| {c["id"]} | {c["term"]} | {c.get("en", "")} | {_cut(c.get("gloss", ""), gl)} | {", ".join(c.get("needs", []))} | {", ".join(c.get("avoid", []))} |')
        links += [n for n in c.get('needs', []) if n in plan.concept_by_id and plan.concept_by_id[n]['unit'] != uid and n not in links]
    if links:
        brief_lines.append('- link with data-ref: ' + ', '.join(f'{n} {plan.concept_by_id[n]["term"]} ({plan.concept_by_id[n]["unit"]})' for n in links))
    facts = list(u.get('takes', [])) + list(u.get('makes', []))
    if facts:
        brief_lines += ['', '## Facts']
        for f in facts:
            v = b.fact_text(plan, f)
            brief_lines.append(f'- {"takes" if f in u.get("takes", []) else "makes"} `{f}`: {plan.facts_decl.get(f, "")} = {_cut(v, gl) if v is not None else "(not set)"}')
    canon = (j.get('canon') or {}).get('values') or {}
    used = {k: v for k, v in canon.items() if str(v) in src} or canon
    if used:
        brief_lines.append(f'- canon {"used" if src and used is not canon else "values"}: ' + ', '.join(f'{k}={v}' for k, v in list(used.items())[:12]))
    if plan.home_by_id:
        brief_lines.append('- homes: ' + '; '.join(f'{k}: {_cut(x["meaning"], 40)} [{", ".join(x["regions"])}]' for k, x in plan.home_by_id.items()))
    terms = [t for t in j.get('terms') or [] if t.get('avoid')]
    if terms:
        brief_lines.append('- terms: ' + '; '.join(f'{t["use"]} not {"/".join(t["avoid"])}' for t in terms[:12]))
    cards = _cards(src)
    kinds = collections.Counter(re.findall(r'data-c="([\w-]+)"', src))
    srcs = _units_src(d)
    pool = [cid for e in [x['id'] for x in plan.units[:i]] for k, cid, _ in _cards(srcs.get(e, '')) if cid and k in ('ask', 'task')]
    brief_lines += ['', '## Cards']
    qs_band = plan.bands.get(u['role'], {}).get('qs')
    n_q = sum(1 for k, _, _ in cards if k in ('ask', 'task'))
    brief_lines.append(f'- ask+task now {n_q}' + (f' (band {qs_band[0]}-{qs_band[1]})' if qs_band else '') + '; kinds present: ' + (', '.join(f'{k} {n}' for k, n in kinds.most_common() if k in BAND_KINDS) or 'none'))
    var = [v for _, _, v in cards if v]
    brief_lines.append(f'- review variants: {", ".join(var) or "none yet"}; earlier sources: {", ".join(pool[-6:]) or "none"}')
    from . import catalog
    sp, share, top = catalog.spread(d, uid, src)
    brief_lines.append(f'- patterns: {sp}' + (f'; {top} is {share:.0%} of the cards: vary the move (`pattern list`)' if share > 0.5 and top not in ('hand', 'unlabelled') else ''))
    newp = [p['id'] for p in j.get('new_patterns') or [] if isinstance(p, dict) and uid in (p.get('units') or [])]
    if newp:
        brief_lines.append(f'- this unit uses the book\'s new patterns: {", ".join(newp)} (catalog/patterns/ID.md in the book; label the entries)')
    ds = demos(d)
    if ds:
        mine = [x for x in ds if uid in x[2]]
        brief_lines += ['', '## Demos']
        brief_lines += [f'- {n}: {_cut(doc, gl)}' for n, doc, _ in mine]
        brief_lines.append(f'- {len(ds) - len(mine)} others; list: `{run_line(d, "demos")}`')
    use, dirs = _directives(j, uid)
    brief_lines += ['', '## Directives' + (f' (round {use[-1].get("n")}' + (', open)' if use[-1].get('status') != 'closed' else ')') if use else '')]
    brief_lines += [f'- r{n} [{_topic(x) or "-"}]{" (this unit)" if x.get("units") else ""} {x["text"]}' for n, x in dirs if _topic(x) != 'demo'] or ['- none']
    if revise:
        brief_lines += ['', '## Lint todos']
        findings = [f for f in b.settle(plan, b.lint(d, uid, quick=True), uid) if f['level'] in ('error', 'warn')]
        brief_lines += [f'- {f["level"]} {f["rule"]} {_cut(f["msg"], 110)}' for f in findings[:14]] or ['- none']
        if len(findings) > 14:
            brief_lines.append(f'- {len(findings) - 14} more: `{run_line(d, "lint --unit " + uid)}`')
        ks = kit(d)
        if ks:
            brief_lines += ['', '## Kit (book.js; reuse before adding parts)'] + [f'- `{c}` {_cut(t, 70)}' for c, t in ks[:20]]
    brief_lines += ['', '## Criteria', f'- {write_pointer()}']
    brief_lines += ['', '## Commands', 'Never read a whole unit or book.html; open only flagged shots.'] + _code([
        run_line(d, f'outline {uid}'), run_line(d, f"show {uid} '#ID'"), run_line(None, 'snippet --list'),
        run_line(None, 'pattern list --dir ' + shlex.quote(os.path.abspath(d))), run_line(None, 'pattern show P --dir ' + shlex.quote(os.path.abspath(d))), run_line(None, 'element show E'),
        run_line(d, f'card new --unit {uid} --after SEL --elements stem,exhibit,answer,rival,rival --label P'),
        run_line(d, f'text --unit {uid} --section N --only prose'), run_line(d, f'edit {uid} --patch {s}patch.json'),
        run_line(d, f'lint --unit {uid}'), run_line(d, f"shot {uid} --sel '#ID' --quick --out {s}shots")]) + ['']
    out = '\n'.join(brief_lines + _common(d, aid, h, 'writer'))
    if len(out) > WRITER_MAX and level < 2:
        return writer_brief(d, uid, aid, plan, j, level + 1, revise)
    return out


def _slices(tokens):
    """['u', 'v:2', 'v:4-6'] -> OrderedDict(unit -> None (whole) | [sections])."""
    out = collections.OrderedDict()
    for t in tokens:
        u, _, n = t.partition(':')
        if not n:
            out[u] = None
        elif out.get(u, []) is not None:
            a, _, z = n.partition('-')
            out.setdefault(u, []).extend(range(int(a), int(z or a) + 1))
    return out


def _inputs(d, x, sl, s):
    """Runnable input lines of a lens for unit slices."""
    out = []
    for c in x['inputs'] or ['text --unit U']:
        if c == 'book.json' or c.endswith('.json') and ' ' not in c:
            out.append(f'read {os.path.join(os.path.abspath(d), c)}')
            continue
        c = c.replace('S/', s)
        if re.search(r'(?<![\w-])U(?![\w-])', c):
            for u, secs in sl.items():
                cu = re.sub(r'(?<![\w-])U(?![\w-])', u, c)
                if secs:
                    spec = ','.join(_compress([f'{u}:{n}' for n in secs])).replace(u + ':', '')
                    cu = re.sub(r'^(shot \S+|text .*?--unit \S+)', r'\1 --section ' + spec, cu, count=1)
                out.append(run_line(d, cu))
        else:
            out.append(run_line(d, re.sub(r'(?<![\w-])IDS(?![\w-])', ','.join(sl), c)))
    return out


def lens_brief(d, lens, units, aid=None, plan=None):
    plan = plan or _plan(d)
    ls = lenses()
    if lens not in ls:
        raise AgentsError(f'lens {lens} not in references/review.md; lenses: {", ".join(ls)}')
    sl = _slices(units)
    bad = [x for x in sl if x not in plan.unit_by_id]
    if bad:
        raise AgentsError(f'units not in book.json: {", ".join(bad)}')
    x, h = ls[lens], plan_hash(plan)
    aid = aid or f'r-{lens}'
    s = scratch(d, aid)
    wr = {k: t for v in rows('write.md').values() for k, t in v}
    brief_lines = [f'# Review brief: lens {lens}', f'Agent `{aid}`, role {x["role"]}, plan hash `{h}`, scratch `{s}` in `{os.path.abspath(d)}`.', '', '## Units']
    brief_lines += [f'- {u} {plan.unit_by_id[u]["title"]} ({plan.unit_by_id[u]["role"]})' + (f', sections {", ".join(map(str, secs))}' if secs else '') for u, secs in sl.items()]
    brief_lines += ['', '## Inputs'] + _code(_inputs(d, x, sl, s))
    brief_lines += ['', '## Protocol', x['protocol']] + ([x['note']] if x['note'] else [])
    brief_lines += ['', '## Rows', '| id | yes when |', '|---|---|'] + [f'| {r} | {_resolve(t, wr)} |' for r, t in x['rows']]
    brief_lines += [''] + _common(d, aid, h, 'review')
    return '\n'.join(brief_lines)


def _lead(rule):
    return rule[0] == 'B' or rule == 'G1'


def no_rows(d):
    """Findings from the reviewers' `.work/r-*/no.tsv`: unit TAB block id TAB row id TAB repair; rule `no:ROW`."""
    out, seen = [], set()
    for p in sorted(glob.glob(os.path.join(d, '.work', 'r-*', 'no.tsv'))):
        for ln in open(p, encoding='utf-8'):
            c = [x.strip() for x in ln.rstrip('\n').split('\t')]
            if len(c) < 3 or not c[0] or c[0].startswith('#') or c[0].lower() == 'unit' or tuple(c[:3]) in seen:
                continue
            seen.add(tuple(c[:3]))
            out.append(dict(rule='no:' + c[2], unit=c[0], level='warn', msg=f'#{c[1]} {c[3] if len(c) > 3 else ""}'.strip(), ev=''))
    return out


def render_rows(path):
    """Findings from `render --quick` output: JSON rows (objects or [unit, block, check, text]) or the printed `fail ...` lines; rule `render:CHECK`."""
    if not os.path.isfile(path):
        raise AgentsError(f'render findings file {path} not found; save `render --quick` output there')
    txt = open(path, encoding='utf-8').read()
    raw = []
    try:
        j = json.loads(txt)
        for it in (j.get('fails') or j.get('failures') or [] if isinstance(j, dict) else j):
            if isinstance(it, dict):
                raw.append((it.get('unit', it.get('u', '-')), it.get('block', it.get('bid', it.get('id', '-'))), it.get('check', it.get('rule', '?')), it.get('msg', it.get('text', it.get('txt', '')))))
            elif isinstance(it, (list, tuple)) and len(it) >= 3:
                raw.append((it[0], it[1], it[2], it[3] if len(it) > 3 else ''))
    except ValueError:
        for ln in txt.split('\n'):
            m = re.match(r'fail\s+\d+px\s+\w+\s+(\S+)\s+(\S+)\s+([^\s:]+)(?::\s*(.*))?$', ln.strip())
            if m:
                raw.append(m.groups(''))
    out, seen = [], set()
    for u, bid, chk, t in raw:
        if (u, bid, chk) not in seen:
            seen.add((u, bid, chk))
            out.append(dict(rule='render:' + str(chk), unit=str(u), level='error', msg=f'{"#" + str(bid) + " " if bid not in ("-", "") else ""}{t}'.strip(), ev=''))
    return out


def _auto_render(d):
    return next((p for p in (os.path.join(d, '.work', 'render.json'), os.path.join(d, '.work', 'render.txt')) if os.path.isfile(p)), None)


def fix_findings(d, plan=None, units=None, render=None):
    """Lint findings (error, warn; decisions applied), the reviewers' no rows and render findings, grouped by unit; lead-level ones (B*, G1, no unit) under '-'."""
    plan = plan or _plan(d)
    b = _book()
    out = collections.defaultdict(list)
    extra = no_rows(d)
    rp = render or _auto_render(d)
    if rp:
        extra += render_rows(rp)
    for f in b.settle(plan, b.lint(d)) + extra:
        if f['level'] not in ('error', 'warn'):
            continue
        u = '-' if _lead(f['rule']) or f['unit'] not in plan.unit_by_id else f['unit']
        if units and u != '-' and u not in units:
            continue
        out[u].append(f)
    return out


def fix_brief(d, rules, units, aid=None, plan=None, render=None):
    plan = plan or _plan(d)
    h = plan_hash(plan)
    rules = set(rules)
    for uid in units:
        if uid not in plan.unit_by_id:
            raise AgentsError(f'unit {uid} is not in book.json')
    role = 'sources' if all(r[0] == 'E' for r in rules) else 'fixer'
    aid = aid or ('sr-' if role == 'sources' else 'fx-') + '-'.join(units)[:24]
    s = scratch(d, aid)
    findings = [f for u, fs in fix_findings(d, plan, units, render).items() if u != '-' for f in fs if f['rule'] in rules]
    findings.sort(key=lambda f: (plan.idx.get(f['unit'], 0), f['rule']))
    brief_lines = [f'# Fix brief: {",".join(sorted(rules))} in {",".join(units)}', f'Agent `{aid}`, role {role}, plan hash `{h}`, scratch `{s}` in `{os.path.abspath(d)}`.', '', '## Task']
    brief_lines.append('- Complete each flagged study note: source link (URL or DOI), locator, depth read (abstract, section, full text, summary-read; summary-read = only a fetch-tool summary was seen), sample size. Open the source; a field you cannot verify goes in `open:`, not into a guess.' if role == 'sources'
             else '- Fix each finding below with the smallest edit that clears it; rule text: `' + run_line(d, 'rules') + '`. `no:ROW` is a reviewer\'s judgment on that block (the repair is suggested; row text in references/review.md); `render:CHECK` is a rendered-page failure.')
    brief_lines += ['', f'## Findings ({len(findings)})']
    base = len('\n'.join(brief_lines))
    for k, f in enumerate(findings):
        ln = f'- {f["rule"]} {f["unit"]} {_cut(f["msg"], 130)}' + (f' | {_cut(f["ev"], 50)}' if f['ev'] else '')
        if base + len(ln) > WRITER_MAX - 2200:
            brief_lines.append(f'- {len(findings) - k} more: `{run_line(d, "lint --unit " + units[0])}`')
            break
        brief_lines.append(ln)
        base += len(ln) + 1
    u0 = units[0]
    brief_lines += ['', '## Commands'] + _code([run_line(d, f"show {u0} '#ID'"), run_line(d, f'text --unit {u0} --section N --only prose'),
                                      run_line(d, f'edit {u0} --patch {s}patch.json'), run_line(d, f'lint --unit {u0}')])
    rl = ['- ' + r.format(scratch=s) for r in RULES['all'] + RULES['writer'] + RULES['fix']]
    return '\n'.join(brief_lines + [''] + ['## Rules'] + rl + ['', '## Hand-back', _handback('writer', aid, h, d)])


def fix_batches(plan, by_unit, cap, ucap):
    """[(units, rules)]: units in plan order (a part together), each batch within cap findings and ucap units; a unit over cap splits by rule."""
    parts = list(plan.part_by_id)
    us = sorted((u for u in by_unit if by_unit[u]), key=lambda u: (parts.index(plan.unit_by_id[u]['part']) if plan.unit_by_id[u].get('part') in parts else -1, plan.idx[u]))
    out, cur, n = [], [], 0
    for u in us:
        c = collections.Counter(f['rule'] for f in by_unit[u])
        k = sum(c.values())
        if k > cap and len(c) > 1:
            if cur:
                out.append(cur)
                cur, n = [], 0
            piece, m = [], 0
            for r, v in c.items():
                if piece and m + v > cap:
                    out.append(([u], piece))
                    piece, m = [], 0
                piece.append(r)
                m += v
            out.append(([u], piece))
            continue
        if cur and (n + k > cap or len(cur) >= ucap):
            out.append(cur)
            cur, n = [], 0
        cur.append(u)
        n += k
    if cur:
        out.append(cur)
    return [x if isinstance(x, tuple) else (x, sorted({f['rule'] for u in x for f in by_unit[u]})) for x in out]


def role_brief(d, kind, what, aid=None, bulk=False, plan=None, uid=None):
    """test, debug, demo and research briefs."""
    plan = plan or _plan(d)
    h = plan_hash(plan)
    role = {'test': 'test', 'debug': 'debug', 'demo': 'demo'}.get(kind) or ('research-bulk' if bulk else 'research-explore')
    if uid and uid not in plan.unit_by_id:
        raise AgentsError(f'unit {uid} is not in book.json')
    aid = aid or {'test': 't-', 'debug': 'd-', 'demo': 'm-'}.get(kind, 'q-') + (uid + '-' if uid else '') + re.sub(r'[^\w]+', '-', (what or 'all').lower()).strip('-')[:20]
    s = scratch(d, aid)
    brief_lines = [f'# {kind.capitalize()} brief', f'Agent `{aid}`, role {role}, plan hash `{h}`, scratch `{s}` in `{os.path.abspath(d)}`.', '', '## Task', f'- {what}' + (f' (unit {uid})' if uid else '')]
    u = uid
    steps = f'{s}steps.json'
    shots = f'{s}shots'
    if kind == 'test':
        brief_lines += ['- Drive states as a reader would; open only images a check flags.', '', '## Checks'] + _code([run_line(d, 'render --quick')] + ([
            run_line(d, f'lint --unit {u}'), run_line(d, f'shot {u} --solve --sheet --quick --out {shots}'),
            run_line(d, f"shot {u} --sel '[data-demo]' --steps {steps} --out {shots}")] if uid else [run_line(d, 'lint')]))
        brief_lines.append(f'- `{steps}`: `[{{"op": "tap|drag|type|key|wait", "sel": "CSS", "to": "CSS or [dx, dy]", "text": "", "key": "", "ms": 300}}]`.')
    elif kind == 'debug':
        brief_lines += ['- Reproduce first, then fix in the owned file, then rerun the repro.', '', '## Repro'] + _code([run_line(d, 'render --quick')] + ([
            run_line(d, f'outline {u}'), run_line(d, f"show {u} '#ID'"),
            run_line(d, f"shot {u} --sel '#ID' --steps {steps} --quick --out {shots}"), run_line(d, f'lint --unit {u}')] if uid else [run_line(d, 'lint')]))
        brief_lines.append(f'- Owned: `{os.path.join(os.path.abspath(d), "book.js")}`, figure scripts, and the unit only through `edit --patch`.')
    elif kind == 'demo':
        _, reqs = _directives(j := _raw(d), topic='demo')
        reqs += [(r.get('n'), x) for r in (j.get('rounds') or []) if r.get('status') != 'closed' for x in r.get('directives', []) if _topic(x) == 'demo' and (r.get('n'), x) not in reqs]
        reqs = [(n, x) for n, x in reqs if not what or what in x['text'] or what in (x.get('units') or [])]
        brief_lines += ['', '## Requests'] + ([f'- r{n}{" " + ",".join(x["units"]) if x.get("units") else ""}: {x["text"]}' for n, x in reqs] or ['- none recorded; `note TEXT --topic demo` records one'])
        brief_lines += ['', '## Constraints', '- Colours from CSS variables; no `</` inside script strings; targets at least 24px; no layout shift on interaction.']
        names = [what] if what else [n for n, _, _ in demos(d)][:1]
        where = [uid] if uid else next((us for n, _, us in demos(d) if n in names), [])[:2]
        brief_lines += ['', '## Commands'] + _code([run_line(d, f'demos --name {n}') for n in names] + [run_line(d, f"shot {w} --sel '[data-demo={n}]' --steps {steps} --out {shots}") for n in names for w in where] + [run_line(d, 'render --quick')])
        brief_lines.append(f'- Owned: `{os.path.join(os.path.abspath(d), "book.js")}`.')
    elif what.startswith('Pattern scout'):
        brief_lines += [f'- Book language {plan.book.get("lang", "en")}; reader: {_cut(plan.book.get("reader", "-"), 120)}.', '', '## Catalog'] + _code([
            run_line(None, 'pattern list --dir ' + shlex.quote(os.path.abspath(d))), run_line(None, 'pattern show P --dir ' + shlex.quote(os.path.abspath(d)))])
        brief_lines.append('- Return one line per candidate: `id | problem or visual | nearest | differs | a real example (source URL)`. A candidate whose differs a nearest pattern could also say is dropped.')
    else:
        brief_lines += [f'- Book language {plan.book.get("lang", "en")}; reader: {_cut(plan.book.get("reader", "-"), 120)}.',
              '- Return one line per claim: `claim | source URL | grade (proved, strong, weak, contested) | depth read (abstract, section, full text, summary-read; summary-read = only a fetch-tool summary was seen)`.',
              '- Primary sources first; give the current status of each (retracted, superseded, version).']
    brief_lines += [''] + _common(d, aid, h, 'other')
    return '\n'.join(brief_lines)


def coverage(d, ref=None):
    """Row ids no generated brief reaches: write.md rows under a section the writer pointer does not name, review.md rows outside every lens brief."""
    global REF
    old, REF = REF, ref or REF
    try:
        plan = _plan(d)
        uid = next((u['id'] for u in plan.units if u['role'] == 'core'), plan.units[0]['id'])
        wb = writer_brief(d, uid, plan=plan)
        ptr = next((ln for ln in wb.split('\n') if 'write.md' in ln and 'sections' in ln), '')
        named = set(re.findall(r'[\w-]+', ptr.split('sections', 1)[-1].split('once', 1)[0]))
        miss = [r for head, rs in rows('write.md').items() for r, _ in rs if head not in named]
        ls = lenses()
        txt = '\n'.join(lens_brief(d, n, [uid], plan=plan) for n in ls)
        allr = [r for rs in rows('review.md').values() for r, _ in rs]
        return miss + [r for r in allr if not re.search(r'\|\s*' + re.escape(r) + r'\s*\|', txt)]
    finally:
        REF = old


def commands(d):
    """Every `python3 .../make-book.py ...` line the generated briefs and task lists print, for a parse check."""
    plan = _plan(d)
    uid = next((u['id'] for u in plan.units if u['role'] == 'core'), plan.units[0]['id'])
    txt = [writer_brief(d, uid, plan=plan, revise=True)] + [lens_brief(d, n, [uid], plan=plan) for n in lenses()]
    txt += [role_brief(d, k, 'x', plan=plan, uid=uid) for k in ('test', 'debug', 'demo', 'research')]
    txt += ['\n'.join(t.split('\t')[4] for t in tasks(d, st)) for st in ('plan', 'write', 'review', 'test', 'demo')]
    txt += [tasks(d, 'debug', symptom='x')[0].split('\t')[4]]
    txt += [fix_brief(d, ['E3', 'K10'], [uid], plan=plan)] + ['\n'.join(t.split('\t')[4] for t in tasks(d, 'fix') if t.split('\t')[1] != 'main')]
    return [ln.strip().strip('`') for t in txt for ln in t.split('\n') if ln.strip().strip('`').startswith('python3 ')]


# ---------------------------------------------------------------- task lists
def _sizes(d, plan, pool, views):
    b = _book()
    root = b.parse(open(os.path.join(d, 'book.html'), encoding='utf-8').read())
    return {v: b.text_slices(d, v, set(pool), root) for v in views}


def _view(c):
    m = re.match(r'text\b.*?(?:--only (\w+))?\s*$', c)
    return (m.group(1) or 'all') if m and c.startswith('text') else None


def _pack(units, whole=False, cap=BATCH_CHARS):
    """Fill tasks up to cap chars in book order: a unit goes whole when it fits, else by sections; whole=True never splits a unit."""
    groups, n, sizes = [[]], 0, [0]
    for u, secs in units:
        tot = sum(c for _, c in secs)
        if whole or n + tot <= cap or (n == 0 and tot <= cap):
            if groups[-1] and n + tot > cap:
                groups.append([])
                sizes.append(0)
                n = 0
            groups[-1].append(u)
            n += tot
            sizes[-1] = n
            continue
        parts = [k for k, c in secs if c]
        for k, c in secs:
            if not c:
                continue
            if groups[-1] and n + c > cap:
                groups.append([])
                sizes.append(0)
                n = 0
            groups[-1].append(f'{u}:{k}')
            n += c
            sizes[-1] = n
        for g in groups:  # a task that holds every section of a unit names the unit
            mine = [t for t in g if t.startswith(u + ':')]
            if len(mine) == len(parts) and mine:
                i = g.index(mine[0])
                g[:] = g[:i] + [u] + [t for t in g[i:] if t not in mine]
    if len(groups) > 1 and sizes[-1] < cap * LEFTOVER:  # a small leftover joins the previous task
        groups[-2] += groups.pop()
    return [_compress(g) for g in groups if g]


def _compress(g):
    """['u:0', 'u:1', 'u:2'] -> ['u:0-2']."""
    out = []
    for t in g:
        u, _, k = t.partition(':')
        m = re.match(r'(.+):(\d+)-(\d+)$', out[-1]) if out else None
        if k and m and m.group(1) == u and int(m.group(3)) + 1 == int(k):
            out[-1] = f'{u}:{m.group(2)}-{k}'
        elif k and out and out[-1] == f'{u}:{int(k) - 1}':
            out[-1] = f'{u}:{int(k) - 1}-{k}'
        else:
            out.append(t)
    return out


def review_groups(d, plan, x, pool, sizes):
    """Unit or unit:section tokens per task for one lens, sized by the lens's own text views."""
    views = [v for v in map(_view, x['inputs']) if v] or ['all']
    units = []
    for u in pool:
        secs = collections.Counter()
        for v in views:
            for n, _, _, c in sizes[{'all': None}.get(v, v)].get(u, []):
                secs[n] += c
        units.append((u, sorted(secs.items())))
    whole = any('IDS' in c for c in x['inputs'])  # a unit-wide command (blind solving) keeps units whole
    if x['role'] == 'review-coherence':  # one task per part, whole units, never sliced
        parts = collections.OrderedDict()
        for u, secs in units:
            parts.setdefault(plan.unit_by_id[u].get('part'), []).append(u)
        return list(parts.values())
    return _pack(units, whole)


def tasks(d, stage, units=None, symptom=None, render=None):
    plan = _plan(d)
    role_routes = routes(plan)
    srcs = _units_src(d)
    ids = units or None
    j = _raw(d)

    def line(aid, role, cmd):
        r = role_routes[role]
        return f'{aid}\t{role}\t{r["model"] or "main"}\t{r["effort"] or "-"}\t{run_line(d, cmd + " --as " + aid)}\t{scratch(d, aid)}'

    q = lambda t: shlex.quote(t)
    out = []
    if stage == 'plan':
        for qq in plan.question_by_id.values():
            out.append(line('q-' + re.sub(r'^q-', '', qq['id']), 'research-explore', f'brief --research {q(qq["text"])}'))
        for sx in j.get('sources') or []:
            out.append(line(f'b-src-{sx.get("id")}', 'research-bulk', f'brief --bulk --research {q("Verify source " + str(sx.get("name", sx.get("id"))) + ": where it lives, how to open it, one real entry per form")}'))
        cs = [c for c in plan.concept_by_id.values()]
        for k in range(0, len(cs), 12):
            grp = ', '.join(f'{c["term"]} ({c.get("en", "")})' for c in cs[k:k + 12])
            out.append(line(f'b-terms-{k // 12 + 1}', 'research-bulk', f'brief --bulk --research {q("Check each term against localized official docs and practitioner usage; give the used form and rivals: " + grp)}'))
        want = (plan.book.get('policies') or {}).get('new_patterns', 1)
        if want != 0:
            name = (j.get('project') or {}).get('name') or plan.book.get('title') or 'this book'
            out.append(line('b-pattern-scout', 'research-bulk', 'brief --bulk --research ' + q(
                f'Pattern scout for {name}: read the catalog (`pattern list`, `pattern show P` for the nearest ones), compare it with what practitioners of this book\'s field do or see at work, '
                'and propose at least 2 new problem patterns and at least 1 new visual pattern: id, family, nearest catalog pattern, differs (the move this one forces that the nearest cannot), one real example from the field')))
        try:
            for n, x in lenses().items():
                if x['gate'] in ('plan-check', 'skeleton'):
                    out.append(line(f'r-{n}', x['role'], f'brief --lens {n} --units {",".join(u["id"] for u in plan.units)}'))
        except AgentsError:
            pass
    elif stage == 'write':
        for u in ids or [x['id'] for x in plan.units if x.get('status') == 'planned' or x['id'] not in srcs]:
            out.append(line(f'w-{u}', 'writer', f'brief {u}'))
    elif stage == 'review':
        pool = ids or [x['id'] for x in plan.units if x['id'] in srcs]
        if not ids and plan.pol.get('review') == 'sample':  # the map, the capstone and one core unit per part
            seen = set()
            pool = [u for u in pool if plan.unit_by_id[u]['role'] in ('map', 'capstone')
                    or (plan.unit_by_id[u]['role'] == 'core' and plan.unit_by_id[u].get('part') not in seen and not seen.add(plan.unit_by_id[u].get('part')))]
        ls = {n: x for n, x in lenses().items() if x['gate'] == 'review'}
        views = {({'all': None}.get(v, v)) for x in ls.values() for v in (list(map(_view, x['inputs'])) or ['all']) if v} or {None}
        sizes = _sizes(d, plan, pool, views)
        for n, x in ls.items():
            for k, g in enumerate(review_groups(d, plan, x, pool, sizes), 1):
                out.append(line(f'r-{n}-{k}', x['role'], f'brief --lens {n} --units {",".join(g)}'))
    elif stage == 'test':
        for u in ids or [x['id'] for x in plan.units if x['id'] in srcs]:
            out.append(line(f't-{u}', 'test', f'brief {u} --test {q("render, lint, shots and interactive states")}'))
    elif stage == 'demo':
        _, reqs = _directives(j, topic='demo')
        reqs += [(r.get('n'), x) for r in (j.get('rounds') or []) if r.get('status') != 'closed' for x in r.get('directives', []) if _topic(x) == 'demo']
        names = sorted({m for _, x in reqs for m in re.findall(r'\b[\w-]+\b', x['text']) if m in {dd[0] for dd in demos(d)}})
        for nme in names or (['NAME'] if reqs else []):
            out.append(line(f'm-{nme}', 'demo', f'brief --demo {nme}'))
    elif stage == 'debug':
        if not symptom:
            raise AgentsError('agents debug needs --symptom TEXT')
        u = (ids or [None])[0]
        out.append(line('d-' + re.sub(r'[^\w]+', '-', symptom.lower()).strip('-')[:20], 'debug', (f'brief {u} ' if u else 'brief ') + f'--debug {q(symptom)}'))
    elif stage == 'fix':
        by = fix_findings(d, plan, ids, render)
        lead = by.pop('-', [])
        if lead:
            rl = sorted({f['rule'] for f in lead})
            out.append(f'lead-{"-".join(rl)}\tmain\tmain\t-\t{run_line(d, "lint")}\t{len(lead)} book-level findings ({",".join(rl)}): plan, build or chrome; the lead fixes them')
        for role, pick in (('sources', lambda r: r[0] == 'E'), ('fixer', lambda r: r[0] != 'E')):
            sub = {u: [f for f in fs if pick(f['rule'])] for u, fs in by.items()}
            for k, (us_, rs_) in enumerate(fix_batches(plan, sub, *FIX_CAPS[role]), 1):
                out.append(line(('sr-' if role == 'sources' else 'fx-') + str(k), role, f'brief --fix {",".join(rs_)} --units {",".join(us_)}' + (f' --render {q(render)}' if render else '')))
    return out


# ---------------------------------------------------------------- rounds and gates
def note(d, text, units=None, topic=None):
    j = _raw(d)
    rs = j.setdefault('rounds', [])
    if not rs or rs[-1].get('status') == 'closed':
        rs.append({'n': len(rs) + 1, 'status': 'open', 'opened': _now(), 'directives': []})
    x = {'text': text, 'at': _now()}
    if units:
        x['units'] = units
    if topic:
        x['topic'] = topic
    rs[-1]['directives'].append(x)
    _save(d, j)
    return f'round {rs[-1]["n"]}: directive {len(rs[-1]["directives"])} added'


def round_cmd(d, action):
    j = _raw(d)
    rs = j.get('rounds') or []
    if action == 'close':
        if not rs or rs[-1].get('status') == 'closed':
            raise AgentsError('no open round; `note` opens one')
        rs[-1].update(status='closed', closed=_now())
        _save(d, j)
        return f'round {rs[-1]["n"]} closed with {len(rs[-1]["directives"])} directives'
    return '\n'.join(f'round {r["n"]} {r.get("status")} {len(r.get("directives", []))} directives' for r in rs) or 'no rounds'


def approve(d, gate, by):
    plan = _plan(d)
    j = _raw(d)
    if gate == 'skeleton':
        missing = _book().round_gaps(j)
        if missing:
            raise AgentsError('skeleton refused: round 1 has no directive on ' + ', '.join(TOPIC_TEXT.get(t, t) for t in missing)
                              + '; record each with `note "..." --topic ' + missing[0] + '`')
    from . import catalog
    gaps = catalog.plan_gaps(plan) if gate == 'skeleton' else catalog.review_gaps(d) if gate == 'review' else []
    if gaps:
        raise AgentsError(f'{gate} refused: ' + '; '.join(gaps))
    h = plan_hash(plan)
    rec = {'approved_by': by, 'at': _now(), 'plan_hash': h}
    if gate == 'skeleton':
        rec['new_patterns'] = len(j.get('new_patterns') or [])
    if gate == 'publish':  # needs the review gate at this plan hash, lint without errors, and a published copy of this very build
        rv = (j.get('gates') or {}).get('review')
        if not rv or rv.get('plan_hash') != h:
            raise AgentsError('publish refused: no approved review gate at the current plan hash' + ('' if not rv else f' (approved at {rv.get("plan_hash")})') + '; review, then `approve review`')
        errs = [f for f in _book().settle(plan, _book().lint(d)) if f['level'] == 'error']
        if errs:
            raise AgentsError(f'publish refused: lint has {len(errs)} error(s), first {errs[0]["rule"]} {errs[0]["unit"]}: {_cut(errs[0]["msg"], 80)}')
        from . import publish
        try:
            ok = publish.current(d)
        except publish.PublishError as e:
            raise AgentsError(f'publish refused: {e}')
        if not ok:
            raise AgentsError('publish refused: no record in publish.json matches the current build; publish it (publish-book.py) first')
        rec.update(targets=ok, sha=publish.sha(os.path.join(d, 'book.html')))
        left = catalog.unpromoted(d)
        if left:
            print(f'warning: book patterns not promoted or marked local: {", ".join(left)}; see SKILL.md How to Fix', file=sys.stderr)
    j.setdefault('gates', {})[gate] = rec
    _save(d, j)
    return f'{gate} approved by {by} at plan hash {h}'


# ---------------------------------------------------------------- command line
def register(sub):
    b = _book()
    s = sub.add_parser('brief', help='generated brief for one agent')
    s.add_argument('pos', nargs='*', metavar='[DIR] [UNIT]')
    s.add_argument('--dir', dest='dir_opt', metavar='DIR')
    s.add_argument('--lens'); s.add_argument('--units'); s.add_argument('--test'); s.add_argument('--debug'); s.add_argument('--demo', nargs='?', const='')
    s.add_argument('--research'); s.add_argument('--bulk', action='store_true'); s.add_argument('--revise', action='store_true'); s.add_argument('--fix'); s.add_argument('--render'); s.add_argument('--as', dest='as_id')
    s.set_defaults(func=run)
    s = sub.add_parser('agents', help='task list for a stage: agents [DIR] STAGE or agents STAGE [DIR]')
    s.add_argument('pos', nargs='*', metavar='[DIR] STAGE'); s.add_argument('--dir', dest='dir_opt', metavar='DIR')
    s.add_argument('--units'); s.add_argument('--symptom', help='debug only'); s.add_argument('--render', help='fix only: file with render --quick output')
    s.set_defaults(func=run)
    s = b.dir_args(sub.add_parser('note', help='directive for the open round'))
    s.add_argument('text'); s.add_argument('--units'); s.add_argument('--topic', choices=topics() + ('demo',))
    s.set_defaults(func=run)
    s = sub.add_parser('round', help='list rounds or close the open one')
    s.add_argument('pos', nargs='*', metavar='[DIR] [show|close]'); s.add_argument('--dir', dest='dir_opt', metavar='DIR')
    s.set_defaults(func=run)
    s = b.dir_args(sub.add_parser('approve', help='record a gate approval'))
    s.add_argument('gate', choices=b.GATES); s.add_argument('--by', required=True, choices=('user', 'self'))
    s.set_defaults(func=run)


def _free_pos(a):
    """Split brief/round positionals into the book directory and the rest."""
    d, rest = a.dir_opt, list(a.pos)
    if a.cmd == 'agents':  # DIR and STAGE in either order
        st = [x for x in rest if x in STAGES]
        if len(st) != 1 or len(rest) > 2:
            raise AgentsError(f'agents needs one STAGE ({"|".join(STAGES)}) and at most one DIR')
        rest.remove(st[0])
        if rest and d and os.path.abspath(rest[0]) != os.path.abspath(d):
            raise AgentsError(f'two book directories given: {rest[0]} and --dir {d}')
        return d or (rest[0] if rest else '.'), st[0]
    words = ('show', 'close') if a.cmd == 'round' else ()
    if len(rest) > 2:
        raise AgentsError(f'{a.cmd} takes at most [DIR] and one more positional')
    if len(rest) == 2:
        d2, rest = rest[0], rest[1:]
    elif rest and rest[0] not in words and os.path.isfile(os.path.join(rest[0], 'book.json')) and not (os.path.isfile(os.path.join(d or '.', 'book.json')) and rest[0] in _plan(d or '.').unit_by_id):
        d2, rest = rest[0], []
    else:
        d2 = None
    if d and d2 and os.path.abspath(d) != os.path.abspath(d2):
        raise AgentsError(f'two book directories given: {d2} and --dir {d}')
    return d or d2 or '.', (rest[0] if rest else None)


def run(a):
    """Handler for the commands register() adds; returns an exit code."""
    try:
        if hasattr(a, 'pos'):
            a.dir, arg = _free_pos(a)
        us = a.units.split(',') if getattr(a, 'units', None) else None
        d = a.dir
        if a.cmd == 'brief':
            if a.lens:
                if not us:
                    raise AgentsError('--lens needs --units')
                print(lens_brief(d, a.lens, us, a.as_id))
            elif a.test is not None:
                print(role_brief(d, 'test', a.test, a.as_id, uid=arg))
            elif a.debug is not None:
                print(role_brief(d, 'debug', a.debug, a.as_id, uid=arg))
            elif a.demo is not None:
                print(role_brief(d, 'demo', a.demo, a.as_id, uid=arg))
            elif a.research:
                print(role_brief(d, 'research', a.research, a.as_id, a.bulk))
            elif a.fix:
                if not us:
                    raise AgentsError('--fix needs --units')
                out = fix_brief(d, a.fix.split(','), us, a.as_id, render=a.render)
                print(out)
                if len(out) > WRITER_MAX:
                    print(f'warn: brief is {len(out)} chars, over {WRITER_MAX}', file=sys.stderr)
            elif arg:
                out = writer_brief(d, arg, a.as_id, revise=a.revise)
                print(out)
                if len(out) > WRITER_MAX:
                    print(f'warn: brief is {len(out)} chars, over {WRITER_MAX}', file=sys.stderr)
            else:
                raise AgentsError('brief needs UNIT, --lens, --test, --debug, --demo or --research')
        elif a.cmd == 'agents':
            if a.symptom and arg != 'debug':
                raise AgentsError('--symptom belongs to `agents debug` only')
            if a.render and arg != 'fix':
                raise AgentsError('--render belongs to `agents fix` only')
            print('\n'.join(tasks(d, arg, us, a.symptom, a.render)) or 'no tasks')
        elif a.cmd == 'note':
            print(note(d, a.text, us, a.topic))
        elif a.cmd == 'round':
            print(round_cmd(d, arg or 'show'))
        elif a.cmd == 'approve':
            print(approve(d, a.gate, a.by))
        return 0
    except (AgentsError, _book().PlanError) as e:
        print(f'error: {e}', file=sys.stderr)
        return 2

