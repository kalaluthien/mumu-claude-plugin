import collections, json, os, re, shlex, shutil, sys, tempfile
from .const import ASSETS, MAKE_BOOK, REFERENCES, TEMPLATES
from .lang import LANG_DIR, pack
from .dom import NO_MATH, parse, sentences
from .plan import Plan, PlanError, plan_hash, round_gaps
from .build import build
from .edit import unit_src
from .lint import lint, report

# ---------------------------------------------------------------- mutation tests


def _sub(path, old, new, count=1):
    s = open(path, encoding='utf-8').read()
    assert old in s, f'mutation anchor missing: {old[:50]}'
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, count))


def hp_count(path, s):
    return open(path, encoding='utf-8').read().count(s)


def _plan_edit(d, fn):
    p = os.path.join(d, 'book.json')
    j = json.load(open(p, encoding='utf-8'))
    fn(j)
    json.dump(j, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _approve(base):
    import datetime
    p = os.path.join(base, 'book.json')
    j = json.load(open(p, encoding='utf-8'))
    gaps = round_gaps(j)
    if gaps:
        rs = j.setdefault('rounds', [])
        if not rs or not isinstance(rs[0], dict):
            rs.insert(0, {'n': 1, 'directives': []})
        rs[0].setdefault('directives', []).extend({'topic': t, 'text': f'{t}: per band'} for t in gaps)
    json.dump(j, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    j['gates'] = dict(j.get('gates') or {}, skeleton={'approved_by': 'self', 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'plan_hash': plan_hash(Plan(p))})
    json.dump(j, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _lang_case(base, hp, plant, P, cu, code, m):
    def ed(j):
        j['book']['lang'] = code
        j['concepts'][0].update(m.get('concept', {}))
        j['book'].setdefault('strings', {}).update(m.get('strings', {}))
    _plan_edit(base, ed)
    if 'plant' in m:
        plant(m['plant'].replace('{term}', P.d['concepts'][0]['term']).replace('{cu}', cu))
    if 'option' in m:
        _sub(hp, 'Because 8 is a power of two<p', m['option'] + '<p')


def mutate(d=None):
    """Build the book (default: the sample), require 0 errors, then plant one defect per case; a missing anchor fails."""
    base = tempfile.mkdtemp()
    src = d or TEMPLATES
    for x in ('book.json', 'units.html', 'facts.json', 'book.js'):
        if os.path.exists(os.path.join(src, x)):
            shutil.copy(os.path.join(src, x), base)
    for x in ('units', 'figs'):
        if os.path.isdir(os.path.join(src, x)):
            shutil.copytree(os.path.join(src, x), os.path.join(base, x))
    build(base)
    _approve(base)  # the copy stands in for an approved skeleton so B5 tests detect, not the sample's state
    clean = lint(base)
    errs = [f for f in clean if f['level'] == 'error']
    print(f"clean build: {len(errs)} errors, {sum(1 for f in clean if f['level'] == 'warn')} warns")
    if errs:
        report(errs)
        return 1
    P = Plan(os.path.join(base, 'book.json'))
    hp = os.path.join(base, 'book.html')
    cu = next(u['id'] for u in P.live if u['role'] == 'core')
    cui = [u['id'] for u in P.d['units']].index(cu)
    later = next((c for c in P.C.values() if P.idx.get(c['unit'], 0) > P.idx[cu]), None)
    sec = re.search(r'<section id="u-' + re.escape(cu) + r'".*?</section>', open(hp, encoding='utf-8').read(), re.S).group(0)
    nsent = len(sentences(parse(sec).text(NO_MATH)))
    anchor = '<div data-c="step"><p class="blab">' + P.st('lab_step') + '</p><p>'
    plant = lambda txt: _sub(hp, anchor, anchor + txt)
    cases = [
        ('G1', lambda: _sub(hp, '<h2>', '<h2>X')),
        ('G2', lambda: _sub(hp, 'data-ref="', 'data-ref="nowhere-')),
        ('G2', lambda: plant('TODO ')),
        ('U1', lambda: _sub(hp, '<div data-c="gist">', '<div data-c="gistx">')),
        ('G1', lambda: _sub(hp, '<b class="qn">1.</b>', '<b class="qn">9.</b>')),
        ('U2', lambda: _sub(hp, '<div data-c="step">', '<div data-c="probe" data-move="predict" data-level="understand" data-diff="1"><p data-p="q">Which?</p><ol data-p="opts"><li data-ok>a<p data-p="why">w</p></li><li>b<p data-p="why">w</p></li><li>c<p data-p="why">w</p></li></ol></div><div data-c="step">')),
        ('U3', lambda: _sub(hp, 'data-c="defn" data-concept="', 'data-c="defn" data-concept="nope-')),
        ('U3', lambda: _sub(hp, '<p data-c="key">', '<p>')),
        ('U4', lambda: _sub(hp, '<li data-ok>', '<li>')),
        ('U4', lambda: plant('<span title="hover only">x</span> ')),
        ('F1', lambda: _sub(hp, '<svg viewBox', '<svg fill="#ff0000" viewBox')),
        ('F5', lambda: _sub(hp, '<div data-c="warn"><p class="blab">' + P.st('lab_warn') + '</p><p>', '<div data-c="warn"><figure data-c="fig" data-tactic="geom" data-kind="conceptual"><svg viewBox="0 0 10 10"></svg></figure><p>')),
        ('F2', lambda: _sub(hp, 'data-tactic="', 'data-tactic="x')),
        ('F4', lambda: _sub(hp, '</svg>', '<g data-node="n1"><circle cx="1" cy="1" r="1"/></g></svg>')),
        ('S1', lambda: (_plan_edit(base, lambda j: j['forbid'].append({'id': 'probe', 're': 'Zqxw', 'in': 'prose', 'level': 'error', 'fix': 'probe', 'example': 'Zqxw'})), plant('Zqxw '))),
        ('S2', lambda: plant('This chapter does not cover history. ')),
        ('K1', lambda: _sub(hp, 'The worse answer keeps the larger group<p', 'The worse answer keeps the larger group, and that branch decides the count every time<p')),
        ('K3', lambda: _sub(hp, 'Wording limits what', 'Wording always limits what')),
        ('K4', lambda: _sub(hp, 'Because 8 is a power of two<p', 'None of the above<p')),
        ('K5', lambda: _sub(hp, 'The worse answer keeps the larger group<p', 'An answer has two values, so it splits the candidates<p')),
        ('K6', lambda: _sub(hp, 'data-move="explain"', 'data-move="guess"')),
        ('K7', lambda: _sub(hp, 'Why can no single yes or no question remove', 'Which is not why a single yes or no question cannot remove')),
        ('K8', lambda: _sub(hp, 'data-level="understand"', 'data-level="x"')),
        ('V1', lambda: plant('K is a key press, P is pointing and H is homing. ')),
        ('G2', lambda: plant('[VERIFIED by expert] ')),
        ('L4', lambda: [_sub(hp, '<p data-p="why">', '<p data-p="why">Same closing formula here. ', n) for n in [hp_count(hp, '<p data-p="why">')]][0]),
        ('K9', lambda: _sub(hp, 'This chapter finds the smallest number', 'Three questions always suffice. This chapter finds the smallest number')),
        ('K10', lambda: _sub(hp, 'Wording limits what one question can ask<p', 'Wording can somehow ask anything at all<p')),
        ('K11', lambda: _sub(hp, 'The limit holds for any number of candidates', 'True, but the limit holds for any number of candidates')),
        ('O2', lambda: plant('<b data-c="badge" data-b="example">example</b> The bot keeps going. ')),
        ('L4', lambda: _sub(hp, anchor, '<p>Notice that one.</p><p>Notice that two.</p><p>Notice that three.</p><p>Notice that four.</p>' + anchor)),
        ('F6', lambda: plant('As frame 3 shows, the bar halves. ')),
        ('F7', lambda: _sub(hp, '<div data-c="close">', '<h3>Path</h3><p>The browser asks DNS for shop.example.com, IIS runs checkout.asp, which calls check.asp and reserve.asp, then SQL Server.</p><div data-c="close">')),
        ('O3', lambda: _plan_edit(base, lambda j: j.__setitem__('sources', [{'id': 'x', 'name': 'X', 'forms': ['.'], 'unit': cu}]))),
        ('S4', lambda: (_plan_edit(base, lambda j: j['concepts'][0].__setitem__('avoid', ['zqbit'])), plant('A zqbit is here. '))),
        ('S4', lambda: (_plan_edit(base, lambda j: j['concepts'][0].__setitem__('avoid', ['zqbit'])), _sub(hp, '</svg>', '<text x="1" y="9">zqbit</text></svg>'))),
        ('C1', lambda: (_plan_edit(base, lambda j: j.__setitem__('canon', {'kinds': {'ip': r'\b\d{1,3}(?:\.\d{1,3}){3}\b'}, 'values': {'db': '10.0.2.20'}})), plant('The server 10.0.3.20 answers. '))),
        ('L5', lambda: plant('Halving halving works here. ')),
        ('B4', lambda: _plan_edit(base, lambda j: j['book'].pop('emphasis', None))),
        ('B4', lambda: _plan_edit(base, lambda j: j['book'].__setitem__('register', 'zz'))),
        ('G2', lambda: _sub(hp, 'data-variant-of="ask-bits-1"', 'data-variant-of="nowhere"')),
        ('K9', lambda: (_sub(hp, '>Half of them<', '>Because 8 is a power of two<'), _sub(hp, '>All but one<', '>Wording limits what one question can ask<'))),
        ('U4', lambda: _sub(hp, 'id="task-bits-order" data-kind="order"', 'id="task-bits-order" data-kind="compose"')),
        ('H1', lambda: _sub(hp, anchor, '<h3>Why does halving work?</h3>' + anchor)),
        ('T2', lambda: open(os.path.join(base, 'facts.json'), 'w', encoding='utf-8').write(json.dumps({'q_avg': {'value': 1.75, 'text': 'The bot asks fewer questions.'}}))),
        ('B1', lambda: _plan_edit(base, lambda j: j['concepts'].append({'id': 'c-orphan', 'term': 'orphan', 'unit': cu, 'needs': []}))),
        ('B2', lambda: _plan_edit(base, lambda j: j['units'][cui].__setitem__('takes', ['never_made']))),
        ('B3', lambda: _plan_edit(base, lambda j: j['lexicon'].append(dict(j['lexicon'][0], id='dup')))),
        ('B4', lambda: _plan_edit(base, lambda j: j['units'][cui].__setitem__('title', 'Why: this'))),
        ('L3', lambda: _sub(hp, anchor, anchor + 'The same long sentence is planted twice to test repetition across units. ', 2)),
        ('O1', lambda: plant('Unlike ' + later['term'] + ', this is simple. ')),
        ('M1', lambda: _plan_edit(base, lambda j: j['symbols'][0].__setitem__('scope', ['nowhere']))),
        ('M2', lambda: (_plan_edit(base, lambda j: j['symbols'].append({'tex': 'Dz', 'meaning': 'probe', 'asym': True})), plant('<span data-m>Dz(p\\|q) = Dz(q\\|p)</span> '))),
        ('F3', lambda: _plan_edit(base, lambda j: j['book'].__setitem__('bands', {'core': {'figs': [20, 30]}}))),
        ('L1', lambda: _plan_edit(base, lambda j: j['book'].__setitem__('bands', {'core': {'chars': [90000, 99000]}}))),
        ('L2', lambda: _sub(hp, anchor, '<p>' + 'Short one. ' * (2 * nsent + 10) + '</p>' + anchor)),
        ('B5', lambda: _plan_edit(base, lambda j: j['gates'].pop('skeleton'))),
        ('B5', lambda: _plan_edit(base, lambda j: j['concepts'][0].__setitem__('term', j['concepts'][0]['term'] + ' x'))),
        ('B5', lambda: _plan_edit(base, lambda j: j['rounds'][0].__setitem__('directives', [x for x in j['rounds'][0]['directives'] if not (isinstance(x, dict) and x.get('topic') in ('terms', 'terms-box'))]))),
        ('B5', lambda: _plan_edit(base, lambda j: j['gates']['skeleton'].__setitem__('approved_by', 'agent'))),
    ]
    # --- rules (B2): figure alt, lexicon ramps, evidence, card fairness, case consistency
    close = '<div data-c="close">'
    before_close = lambda txt: _sub(hp, close, txt + close)
    lex = lambda *es: _plan_edit(base, lambda j: j['lexicon'].extend(es))
    cases += [
        ('F8', lambda: _sub(hp, 'aria-label="One tally row: dish B, 40 of 80 orders"', 'aria-label="f-tally"')),
        ('B3', lambda: lex({'id': 'hot', 'meaning': 'zq hot', 'mark': 'fill', 'kind': 'semantic', 'light': 'oklch(0.55 0.15 25)'}, {'id': 'ok', 'meaning': 'zq ok', 'mark': 'fill', 'kind': 'semantic', 'light': 'oklch(0.55 0.15 145)'})),
        ('B3', lambda: lex(*({'id': f'r{i}', 'meaning': f'zq level {i}', 'mark': 'dot', 'kind': 'sequential', 'ramp': 'lvl', 'light': f'oklch({L} 0.1 250)'} for i, L in enumerate((0.4, 0.75, 0.55))))),
        ('O4', lambda: _sub(hp, 'Why can no single yes or no question remove', 'In sentence 3, why can no single yes or no question remove')),
        ('K10', lambda: _sub(hp, 'The worse answer keeps the larger group<p', 'The worse answer keeps the larger group, as Shannon showed in 1948 for 8 dishes<p')),
        ('K12', lambda: _sub(hp, 'A is first on the menu, but it holds only', 'A is first on the menu, as Knuth found, but it holds only')),
        ('K13', lambda: _sub(hp, '<li>Dish A<p', '<li>Dish A, the cautious answer<p')),
        ('C2', lambda: (plant('The menu serves 120 users. '), _sub(hp, anchor + 'The bot asks about the popular', anchor + 'The menu serves 150 users. The bot asks about the popular'))),
        ('C3', lambda: (plant('The menu serves 1200 users. '), _sub(hp, anchor + 'The bot asks about the popular', anchor + 'The menu serves 1,200 users. The bot asks about the popular'))),
        ('U6', lambda: before_close('<h3>Studies</h3>' + ''.join(f'<details data-c="note" data-grade="weak"><summary>Study {i}</summary><p>Finding {i}.</p></details>' for i in range(3)))),
        ('F9', lambda: before_close('<h3>Kit</h3><p>The kit holds a bowl, a whisk, a scale, a timer and a tray.</p>')),
        ('V2', lambda: before_close('<h3>Rate</h3><div data-c="eqp"><p><span data-m>r = n / t</span></p></div><div data-c="terms"><p data-p="t">Rate</p><dl><dt>r</dt><dd>orders per hour</dd></dl></div>')),
        ('V2', lambda: plant('<span data-m>r</span> denotes the order rate. ')),
        ('E1', lambda: before_close('<p>Readers were 40% faster with a short menu.</p>')),
        ('E2', lambda: before_close('<details data-c="note" id="n-zq" data-grade="weak"><summary>Menu study</summary><p>Twelve diners.</p></details><p>This <a data-cite="n-zq">proves</a> that short menus help.</p>')),
        ('E3', lambda: before_close('<details data-c="note" data-grade="strong"><summary>Menu study</summary><p data-p="design">A lab study of menus.</p><p data-p="source">Smith, Menus</p></details>')),
    ]
    # --- end rules (B2)
    for p in P.d['forbid']:
        cases.append(('S1', lambda p=p: plant(p['example'] + ' ')))
    for code in sorted(f[:-5] for f in os.listdir(LANG_DIR) if f.endswith('.json')):  # each pack plants the defects only its rules see
        for m in pack(code).get('mutate', []):
            cases.append((m['rule'], lambda code=code, m=m: _lang_case(base, hp, plant, P, cu, code, m)))
    fail = 0
    pristine = {f: open(os.path.join(base, f), encoding='utf-8').read() for f in ('book.json', 'book.html')}
    for rule, fn in cases:
        for f, s in pristine.items():
            open(os.path.join(base, f), 'w', encoding='utf-8').write(s)
        try:
            fn()
            hit = any(f['rule'] == rule and f['level'] in ('error', 'warn') for f in lint(base))
            print(f"{rule:3} {'caught' if hit else 'MISSED'}")
        except (AssertionError, PlanError, AttributeError, TypeError, IndexError, StopIteration) as e:
            hit = False
            print(f'{rule:3} FAILED to plant ({e.__class__.__name__}: {e})')
        fail += not hit
    for f, s in pristine.items():
        open(os.path.join(base, f), 'w', encoding='utf-8').write(s)
    if os.path.exists(os.path.join(src, 'facts.json')):  # the T2 case rewrote facts.json
        shutil.copy(os.path.join(src, 'facts.json'), base)
    elif os.path.exists(os.path.join(base, 'facts.json')):
        os.remove(os.path.join(base, 'facts.json'))
    from . import agents, publish  # the publish gate: a record of the current build passes; a build changed after the record is refused
    publish.record(base, 'file', os.path.join(base, 'out.html'))
    _jr = json.load(open(os.path.join(base, 'book.json'), encoding='utf-8'))  # publish also needs the review gate at this plan hash
    _jr.setdefault('gates', {})['review'] = {'approved_by': 'self', 'at': '2026-01-01T00:00:00+00:00', 'plan_hash': plan_hash(Plan(os.path.join(base, 'book.json')))}
    json.dump(_jr, open(os.path.join(base, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for name, change, want in (('record matches the build', lambda: None, False), ('build changed after the record', lambda: _sub(hp, '<h2>', '<h2>X'), True)):
        change()
        try:
            agents.approve(base, 'publish', 'self')
            refused = False
        except agents.AgentsError:
            refused = True
        print(f"PUB {('caught' if want else 'clean') if refused == want else 'MISSED'} ({name})")
        fail += refused != want
    cases = cases + [('PUB', None)] * 2
    for f, s in pristine.items():
        open(os.path.join(base, f), 'w', encoding='utf-8').write(s)
    # --- reader page (B1): targets, reading state, deep links, reduced motion, all frames, search, glossary, fisheye
    rp_fail, rp_n = reader_cases(base, cu)
    fail += rp_fail
    cases = cases + [('RP', None)] * rp_n
    # --- end reader page (B1)
    # --- catalog (C1): element checks x their breaks, slots validation, gates, forbid migration, G3, L4 note fields
    c_fail, c_n = catalog_cases(base, hp, pristine, before_close)
    fail += c_fail
    cases = cases + [('CAT', None)] * c_n
    # --- end catalog (C1)
    # --- fix stage: E findings -> one sources task (haiku), other unit findings -> one fixer task (sonnet), G1 -> the lead
    f_fail, f_n = fix_cases(base, hp, pristine, before_close)
    fail += f_fail
    cases = cases + [('FIX', None)] * f_n
    # --- end fix stage
    # --- fix round (F2): markup balance, duplicate ids, one-word alts, note fields, edit refusals
    f2_fail, f2_n = f2_cases(base, hp, pristine, before_close)
    fail += f2_fail
    cases = cases + [('F2', None)] * f2_n
    # --- end fix round (F2)
    # --- fix round (F3): no.tsv and render findings, scout task, coherence per part, publish gate, CLI order
    f3_fail, f3_n = f3_cases(base, hp, pristine, before_close)
    fail += f3_fail
    cases = cases + [('F3', None)] * f3_n
    # --- end fix round (F3)
    # --- fix round (F4): zero new patterns needs the user's word, infer labels exist, figure pattern labels count, promote shape and checks, host calls
    f4_fail, f4_n = f4_cases(base, hp, pristine, before_close)
    fail += f4_fail
    cases = cases + [('F4', None)] * f4_n
    # --- end fix round (F4)
    # --- fix round (F1): shots deep in a tall page, failed and empty shots exit non-zero, --out FILE.png
    f1_fail, f1_n = f1_cases(base, cu)
    fail += f1_fail
    cases = cases + [('F1', None)] * f1_n
    # --- end fix round (F1)
    # skill coverage: every criteria row reachable by a brief, every seed a row; then planted gaps
    rows, seeds, unr = coverage(base)
    gaps = cov_gaps(rows, seeds, unr)
    print('COV ' + ('clean' if not gaps else 'GAPS: ' + '; '.join(gaps[:8])))
    fail += bool(gaps)
    for name, args in (('unreachable row', (rows, seeds, unr + [rows[0]])), ('seed without row', (rows, seeds + ['zz-no-such-row'], unr)), ('duplicate row', (rows + [rows[0]], seeds, unr))):
        hit = len(cov_gaps(*args)) > len(gaps)
        print(f"COV {'caught' if hit else 'MISSED'} ({name})")
        fail += not hit
    # planted doc defects: a write.md row outside the sections the writer brief names, a review.md row outside every lens
    ref = os.path.join(base, 'ref')
    for name, f, add in (('write.md row in an unnamed section', 'write.md', '\n## extra\n| id | criterion |\n|---|---|\n| zz-extra-row | x |\n'),
                         ('review.md row outside a lens', 'review.md', '\n## notes\n| id | yes when |\n|---|---|\n| zz-hidden-row | x |\n')):
        shutil.copytree(REFERENCES, ref, dirs_exist_ok=True)
        src_ = open(os.path.join(ref, f), encoding='utf-8').read()
        src_ += add
        open(os.path.join(ref, f), 'w', encoding='utf-8').write(src_)
        hit = any(r.startswith('zz-') for r in agents.coverage(base, ref))
        print(f"COV {'caught' if hit else 'MISSED'} ({name})")
        fail += not hit
    cmds = agents.commands(base)  # every command a brief or task list prints parses as printed
    bad = cmd_gaps(cmds)
    print(f'CMD {len(cmds)} brief commands: ' + ('all parse' if not bad else 'BAD: ' + '; '.join(bad[:4])))
    fail += bool(bad)
    hit = len(cmd_gaps(cmds + [shlex.quote(sys.executable) + ' ' + shlex.quote(MAKE_BOOK) + ' outline --nosuch'])) > len(bad)
    print(f"CMD {'caught' if hit else 'MISSED'} (a command that does not parse)")
    fail += not hit
    cases = cases + [('COV', None)] * 7
    shutil.rmtree(base, ignore_errors=True)
    print(f'-- {len(cases) - fail}/{len(cases)} caught')
    return 1 if fail else 0

# --- fix stage
def fix_cases(base, hp, pristine, before_close):
    """An E3 and a K10 finding give one sources task (haiku) and one fixer task (sonnet) beside the lead line the sample's G1 warn makes; briefs parse and fit."""
    from . import agents
    for f, t in pristine.items():
        open(os.path.join(base, f), 'w', encoding='utf-8').write(t)
    kinds = lambda: collections.Counter((t.split('\t')[1], t.split('\t')[2]) for t in agents.tasks(base, 'fix'))
    clean = kinds()
    _sub(hp, 'The worse answer keeps the larger group<p', 'The worse answer keeps the larger group, as Shannon showed in 1948 for 8 dishes<p')
    before_close('<details data-c="note" data-grade="strong"><summary>Menu study</summary><p data-p="design">A lab study of menus.</p><p data-p="source">Smith, Menus</p></details>')
    new = kinds() - clean
    want = {('sources', 'haiku'): 1, ('fixer', 'sonnet'): 1}
    ts = [t.split('\t') for t in agents.tasks(base, 'fix')]
    cmds = [t[4] for t in ts if t[1] != 'main']
    bad = cmd_gaps(cmds) + [c for c in cmds if 'brief --fix' not in c]
    briefs = []
    for t in ts:
        if t[1] in ('sources', 'fixer'):
            w = shlex.split(t[4])
            briefs.append(agents.fix_brief(base, w[w.index('--fix') + 1].split(','), w[w.index('--units') + 1].split(','), t[0]))
    big = [len(b) for b in briefs if len(b) > agents.WRITER_MAX]
    ok = new == collections.Counter(want) and clean[('main', 'main')] == 1 and not bad and not big and all('40 tool calls' in b for b in briefs)
    print(f"FIX {'caught' if ok else 'MISSED'} (E3+K10 give " + ', '.join(f'{k[0]}:{k[1]}' for k in sorted(new)) + ')')
    for f, t in pristine.items():
        open(os.path.join(base, f), 'w', encoding='utf-8').write(t)
    return (not ok), 1
# --- end fix stage


# --- reader page (B1)
RP_CASES = (  # (name, template text in book.html, replacement, words the failure must contain)
    ('targets', '.bar button{min-height:44px;min-width:44px;padding:0 10px}', '.bar button{min-height:0;min-width:0;height:20px;padding:0}', 'targets<24px'),
    ('solved cards after reload', 'try{localStorage.setItem(KEY', 'try{0&&localStorage.setItem(KEY', 'not kept after reload'),
    ('deep link into gated content', 'jump(location.hash,true)', '0', 'deep link'),
    ('URL follows the current unit', "history.replaceState(history.state,'',", '(function(){})(', 'URL hash'),
    ('reduced motion CSS', '@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}', '@media (prefers-reduced-motion:no-such){html{scroll-behavior:auto}', 'reduced motion'),
    ('frames autoplay under reduced motion', "if(!still&&!f.classList.contains('all'))play()", "if(!f.classList.contains('all'))play()", 'autoplay'),
    ('all-frames toggle', "f.classList.toggle('play',!a);", '', 'all-frames'),
    ('search by alias', '.concat(t.a||[],t.v||[])', '', 'search misses'),
    ('glossary see entry', '<dt>zqalias</dt>', '<dt>zqalia</dt>', 'see entry'),
    ('fisheye contents', 'li.cur>.sub{display:block}', 'li.cur>.sub{display:none}', 'sections'),
)


def reader_cases(base, cu):
    """Reader-page defects planted in a built copy (one alias and two sections added, since the sample has none); each must fail reader_check."""
    try:
        from .qa import reader_check
        import playwright.sync_api  # noqa: F401
    except ImportError:
        print('RP  skipped (playwright not installed)')
        return 0, 0
    rp = os.path.join(base, 'rp')
    os.makedirs(rp)
    for x in ('book.json', 'units.html', 'facts.json', 'book.js', 'units', 'figs'):
        src = os.path.join(base, x)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(rp, x))
        elif os.path.exists(src):
            shutil.copy(src, rp)
    _plan_edit(rp, lambda j: j['concepts'][0].__setitem__('aliases', list(j['concepts'][0].get('aliases', [])) + ['zqalias']))
    up = os.path.join(rp, 'units.html')
    if os.path.exists(up):
        u = open(up, encoding='utf-8').read()
        i = u.index(f'<section data-u="{cu}">') + len(f'<section data-u="{cu}">')
        j = u.index('<div data-c="close">', i)
        u = u[:i] + '<h3>Zq first part</h3>' + u[i:j] + '<h3>Zq second part</h3>' + u[j:]
        open(up, 'w', encoding='utf-8').write(u)
    hp = build(rp)
    clean = open(hp, encoding='utf-8').read()
    base_fails = reader_check(rp)
    print('RP  clean reader page' if not base_fails else 'RP  reader page not clean: ' + '; '.join(f'{f[2]} {f[3]}' for f in base_fails[:4]))
    fail = bool(base_fails)
    for name, old, new, want in RP_CASES:
        open(hp, 'w', encoding='utf-8').write(clean)
        try:
            _sub(hp, old, new)
            hit = any(want in f'{f[2]} {f[3]}' for f in reader_check(rp))
            print(f"RP  {'caught' if hit else 'MISSED'} ({name})")
        except AssertionError as e:
            hit = False
            print(f'RP  FAILED to plant ({name}: {e})')
        fail += not hit
    open(hp, 'w', encoding='utf-8').write(clean)
    return fail, len(RP_CASES) + 1
# --- end reader page (B1)


# --- fix round (F1)
def f1_cases(base, cu):
    """shot: an element 20000px down a page still shoots (full-page clips never finish there) to the named --out file;
    a selector matching nothing and a failed step both exit non-zero with their line."""
    try:
        from .qa import shot
        import playwright.sync_api  # noqa: F401
    except ImportError:
        print('F1  skipped (playwright not installed)')
        return 0, 0
    import contextlib
    import io
    sp = os.path.join(base, 'f1')
    os.makedirs(sp)
    for x in ('book.json', 'units.html', 'facts.json', 'book.js', 'units', 'figs'):
        src = os.path.join(base, x)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(sp, x))
        elif os.path.exists(src):
            shutil.copy(src, sp)
    up = os.path.join(sp, 'units.html')
    if not os.path.exists(up):
        print('F1  skipped (sample has no units.html)')
        return 0, 0
    tag = f'<section data-u="{cu}">'
    _sub(up, tag, tag + '<div style="height:20000px"></div><p id="zqdeep">deep</p>')
    build(sp)
    png, steps = os.path.join(sp, 'deep.png'), os.path.join(sp, 'steps.json')
    json.dump([{'op': 'tap', 'sel': '#zq-no-such-button'}], open(steps, 'w'))
    fail = 0
    for name, kw, ok in (('element 20000px down, --out FILE.png', dict(sel='#zqdeep', out=png), lambda rc, o: rc == 0 and os.path.isfile(png)),
                         ('selector matched nothing', dict(sel='#zq-nothing'), lambda rc, o: rc != 0 and 'selector matched nothing' in o),
                         ('failed step counts as failed', dict(sel='#zqdeep', steps=steps), lambda rc, o: rc != 0 and 'failed (' in o)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                rc = shot(sp, cu, widths=(390,), schemes=('light',), **kw)
            except Exception as e:
                rc = f'raised {e}'
        hit = ok(rc, buf.getvalue())
        print(f"F1  {'caught' if hit else 'MISSED'} ({name})" + ('' if hit else f': rc={rc} {buf.getvalue().strip().splitlines()[-1:]}'))
        fail += not hit
    return fail, 3
# --- end fix round (F1)


# ---------------------------------------------------------------- skill coverage: criteria rows, briefs, seeds


ROW_ID = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$')


def table_ids(path):
    """First-cell ids of `| id | ... |` table rows (lowercase kebab) and kebab headings, in order."""
    if not os.path.exists(path):
        return None
    ids = []
    for ln in open(path, encoding='utf-8'):
        m = re.match(r'^\s*\|\s*`?([^|`]+?)`?\s*\|', ln) or re.match(r'^#{2,4}\s+`?([^`\s]+)`?\s*$', ln)
        if m and ROW_ID.match(m.group(1).strip()):
            ids.append(m.group(1).strip())
    return ids


def coverage(base):
    """(criteria row ids of write.md and review.md, seed ids, rows no generated brief reaches)."""
    from . import agents
    ref = REFERENCES
    rows = (table_ids(os.path.join(ref, 'write.md')) or []) + (table_ids(os.path.join(ref, 'review.md')) or [])
    return rows, table_ids(os.path.join(ASSETS, 'seeds.md')) or [], list(agents.coverage(base) or [])


def cmd_gaps(cmds):
    """Printed `python3 .../book.py ...` lines that would not run: a missing script or arguments the parser rejects."""
    import contextlib, io, shlex
    from .cli import parser, resolve_dir
    out = []
    for c in cmds:
        w = shlex.split(c)
        if len(w) < 2 or not os.path.exists(w[1]):
            out.append(f'no script: {c[:80]}')
            continue
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                resolve_dir(parser().parse_args(w[2:]))
        except (SystemExit, PlanError):
            out.append(f'does not parse: {" ".join(w[2:])[:80]}')
    return out


def cov_gaps(rows, seeds, unreachable):
    out = [f'row {x} appears in no generated brief' for x in unreachable]
    out += [f'seed {x} is not a row of write.md or review.md' for x in seeds if x not in rows]
    return out + [f'row id {x} is not unique' for x in sorted({x for x in rows if rows.count(x) > 1})]



# --- catalog (C1)
def catalog_cases(base, hp, pristine, before_close):
    """Each element's example is clean and each check catches its breaks; P1 refuses malformed slots; gates refuse new_patterns gaps; forbid migrates; G3; L4 skips note fields."""
    from . import agents
    from . import catalog
    fail = n = 0

    def say(tag, ok, name):
        nonlocal fail, n
        n += 1
        fail += not ok
        print(f"{tag} {'caught' if ok else 'MISSED'} ({name})")
    E = catalog.elements()
    for eid, chk, msg, ok in catalog.element_cases(E, pack('en')):
        say('EL ', ok, f'{eid} {chk}' + ('' if ok else f': {msg}'))
    restore = lambda: [open(os.path.join(base, f), 'w', encoding='utf-8').write(s) for f, s in pristine.items()]
    up = os.path.join(base, 'units.html')
    src = open(up, encoding='utf-8').read()
    uid = re.search(r'<section data-u="([^"]+)"', src.split('</section>', 2)[1]).group(1)  # the first core unit after the map
    good = json.loads(json.dumps(E["rival"]["example"]))

    def slots(entries, ph):
        open(up, 'w', encoding='utf-8').write(src.replace('<div data-c="close">', ph + '<div data-c="close">', 1) if ph else src)
        os.makedirs(os.path.join(base, 'slots'), exist_ok=True)
        json.dump(entries, open(os.path.join(base, 'slots', uid + '.json'), 'w', encoding='utf-8'))
    slots({'ask-zq': good}, '<!--card ask-zq-->')
    try:
        build(base)
        F = lint(base)
        ok = not any(f['rule'] in ('P1', 'P2') and f['level'] == 'error' for f in F) and 'id="ask-zq"' in open(hp, encoding='utf-8').read()
    except PlanError as e:
        ok = False
        print(f'P1  slots entry did not build: {e}')
    say('P1 ', ok, 'a valid entry builds and lints clean')
    for name, entries, ph in (
            ('placeholder with no entry', {}, '<!--card ask-zq-->'),
            ('entry placed nowhere', {'ask-zq': good}, ''),
            ('TODO slot', {'ask-zq': dict(good, elements=[dict(good['elements'][0], text='TODO')] + good['elements'][1:])}, '<!--card ask-zq-->'),
            ('wrong slot type', {'ask-zq': dict(good, elements=good['elements'][:3] + [dict(good['elements'][3], ruled_out_by='fact 1')] + good['elements'][4:])}, '<!--card ask-zq-->'),
            ('kind cannot hold the element', {'ask-zq': dict(good, elements=good['elements'] + [{'el': 'items', 'list': []}])}, '<!--card ask-zq-->')):
        slots(entries, ph)
        try:
            build(base)
            hit = False
        except PlanError as e:
            hit = 'P1' in str(e)
        say('P1 ', hit and any(f['rule'] == 'P1' for f in lint(base)), name)
    slots({'ask-zq': dict(good, elements=good['elements'][:3] + [dict(good['elements'][3], ruled_out_by=[9])] + good['elements'][4:])}, '<!--card ask-zq-->')
    build(base)
    say('P2 ', any(f['rule'] == 'P2' and 'rival-real' in f['msg'] for f in lint(base)), 'element check in lint')
    open(up, 'w', encoding='utf-8').write(src)
    shutil.rmtree(os.path.join(base, 'slots'), ignore_errors=True)
    build(base)
    for f, s in pristine.items():
        if f != 'book.html':
            open(os.path.join(base, f), 'w', encoding='utf-8').write(s)
    pristine['book.html'] = open(hp, encoding='utf-8').read()
    j0 = json.loads(pristine['book.json'])
    j0.pop('gates', None)

    def approve(j):
        open(os.path.join(base, 'book.json'), 'w', encoding='utf-8').write(json.dumps(j))
        try:
            agents.approve(base, 'skeleton', 'self')
            return True
        except agents.AgentsError:
            return False
    say('B5 ', not approve(dict(j0, new_patterns=[])), 'skeleton refused without new patterns')
    np_ = [{'id': 'zq-trace', 'family': 'problem', 'why': 'w', 'elements': ['stem', 'exhibit', 'answer', 'rival'], 'nearest': 'read-exhibit', 'differs': 'the reader replays the steps', 'units': [uid]},
           {'id': 'zq-ladder', 'family': 'visual', 'why': 'w', 'elements': ['steps', 'alt'], 'nearest': 'frames', 'differs': 'each rung keeps the last', 'units': [uid]}]
    say('B5 ', approve(dict(j0, new_patterns=np_)), 'skeleton accepts two well-formed new patterns (clean)')
    say('B5 ', not approve(dict(j0, new_patterns=[dict(np_[0], nearest='')] + np_[1:])), 'new pattern without nearest')
    j2 = json.loads(json.dumps(j0))
    j2['book'].setdefault('policies', {})['new_patterns'] = 0
    j2['decisions'] = list(j2.get('decisions') or []) + [{'node': 'policies.new_patterns', 'chosen': 0, 'how': 'user'}]
    say('B5 ', approve(dict(j2, new_patterns=[])), 'policies.new_patterns 0 with the user decision accepts none (clean)')
    restore()
    j1 = json.loads(pristine['book.json'])
    j1['patterns'] = j1.pop('forbid', [])
    open(os.path.join(base, 'book.json'), 'w', encoding='utf-8').write(json.dumps(j1))
    P1 = Plan(os.path.join(base, 'book.json'))
    say('MIG', 'forbid' in P1.d and 'patterns' not in json.load(open(os.path.join(base, 'book.json'), encoding='utf-8')), 'book.json patterns migrates to forbid')
    restore()
    say('G3 ', not any(f['rule'] == 'G3' for f in lint(base)), 'sample concepts all have aliases (clean)')
    _plan_edit(base, lambda j: j['concepts'][0].pop('aliases', None))
    say('G3 ', any(f['rule'] == 'G3' for f in lint(base)), 'a concept without aliases')
    restore()
    before_close(''.join(f'<details data-c="note" data-grade="weak"><summary>Study {i}</summary><p data-p="design"><b class="np">Design</b> A lab study of {i} menus with 20 diners.</p></details>' for i in range(4)))
    say('L4 ', not any(f['rule'] == 'L4' for f in lint(base)), 'note fields opening on their labels are not openers (clean)')
    restore()
    return fail, n
# --- end catalog (C1)


# --- fix round (F2)
def f2_cases(base, hp, pristine, before_close):
    """Planted markup defects name their rule and element; edit --patch refuses unbalanced results and bad patch files."""
    import contextlib, io
    from .cli import main as cli_main
    fail = n = 0

    def restore():
        for f, t in pristine.items():
            open(os.path.join(base, f), 'w', encoding='utf-8').write(t)

    def say(name, ok, what):
        nonlocal fail, n
        n += 1
        fail += not ok
        print(f"{name:3} {'caught' if ok else 'MISSED'} ({what})")
    msgs = lambda rule: ' | '.join(f['msg'] for f in lint(base) if f['rule'] == rule and f['level'] in ('error', 'warn'))
    for rule, what, plant, word in (
            ('G4', 'an unclosed div', lambda: before_close('<div data-c="aside" id="zq-open"><p>Open.</p>'), 'zq-open'),
            ('G4', 'a duplicate id', lambda: (before_close('<p id="zq-dup">One.</p><p id="zq-dup">Two.</p>')), 'zq-dup'),
            ('F8', 'a one-word alt', lambda: _sub(hp, 'aria-label="One tally row: dish B, 40 of 80 orders"', 'aria-label="Tally"'), 'one word'),
            ('E3', 'a note with no limits part', lambda: before_close('<details data-c="note" data-grade="strong"><summary>Menu study</summary><p data-p="design">A lab study of 40 diners.</p><p data-p="source"><a href="https://doi.org/10.1/x">Smith 2020</a></p></details>'), 'limits')):
        restore()
        try:
            plant()
            say(rule, word in msgs(rule), what)
        except (AssertionError, PlanError) as e:
            say(rule, False, f'FAILED to plant {e}')
    restore()
    P = Plan(os.path.join(base, 'book.json'))
    uid = next((u['id'] for u in P.live if 'The worse answer keeps the larger group<p' in (lambda r: r[1][r[2][0]:r[2][1]])(unit_src(base, u['id']))), None)
    tmp = os.path.join(base, '.work')
    os.makedirs(tmp, exist_ok=True)
    pj = os.path.join(tmp, 'f2.json')

    def run(args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli_main(args)
        return code, out.getvalue()
    for name, body, word in (('unbalanced sub', json.dumps([{'op': 'sub', 'old': 'The worse answer keeps the larger group<p', 'new': 'The worse answer keeps the larger group<div><p'}]), 'tag balance'),
                             ('unbalanced replace', json.dumps([{'op': 'replace', 'sel': 'close', 'html': '<div data-c="close"><p>x</p>'}]), 'tag balance'),
                             ('invalid JSON', '{bad', 'not valid JSON')):
        restore()
        open(pj, 'w', encoding='utf-8').write(body)
        code, out = run(['edit', base, uid, '--patch', pj])
        say('EDT', code == 1 and word in out and len(out.strip().splitlines()) == 1, name)
    code, out = run(['edit', base, uid, '--patch', os.path.join(tmp, 'none.json')])
    say('EDT', code == 1 and 'not found' in out, 'missing patch file')
    restore()
    return fail, n
# --- end fix round (F2)


# --- fix round (F4)
def f4_cases(base, hp, pristine, before_close):
    from . import agents, publish
    from . import catalog, pcheck
    fail = n = 0

    def say(name, ok, what):
        nonlocal fail, n
        n += 1
        fail += not ok
        print(f"{name} {'caught' if ok else 'MISSED'} ({what})")
    restore = lambda: [open(os.path.join(base, f), 'w', encoding='utf-8').write(t) for f, t in pristine.items()]

    def approve(j):
        open(os.path.join(base, 'book.json'), 'w', encoding='utf-8').write(json.dumps(j))
        try:
            agents.approve(base, 'skeleton', 'self')
            return True
        except agents.AgentsError:
            return False
    j0 = json.loads(pristine['book.json'])
    j0.pop('gates', None)
    j2 = json.loads(json.dumps(j0))
    j2['book'].setdefault('policies', {})['new_patterns'] = 0
    j2['new_patterns'] = []
    say('B5 ', not approve(j2), 'policies.new_patterns 0 with no user decision')
    j3 = json.loads(json.dumps(j2))
    j3['decisions'] = list(j3.get('decisions') or []) + [{'node': 'policies.new_patterns', 'chosen': 0, 'how': 'user'}]
    say('B5 ', approve(j3), 'policies.new_patterns 0 with the user decision (clean)')
    j4 = json.loads(json.dumps(j3))
    j4['decisions'][-1]['how'] = 'self'
    say('B5 ', not approve(j4), 'policies.new_patterns 0 decided by the agent')
    restore()
    ids = set(catalog.patterns())
    labs = {catalog.infer(parse(f'<div data-c="ask" data-move="{m}">{x}</div>').first(lambda q: q.get('data-c') == 'ask')) for m in ('predict', 'intervene', 'decide', 'diagnose', 'explain', 'compute', 'zz') for x in ('', '<div data-c="frames"></div>')}
    say('PAT', labs - {'hand'} <= ids, 'infer maps only to patterns the catalog has')
    say('PAT', catalog.infer(parse('<div data-c="ask" data-move="predict"><div data-c="frames"></div></div>').first(lambda q: q.get('data-c') == 'ask')) == 'intervene', 'a predict card with frames is labelled by structure')
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, 'units'))
    os.makedirs(os.path.join(tmp, 'figs'))
    open(os.path.join(tmp, 'figs', 'f-zq.svg'), 'w', encoding='utf-8').write('<svg data-pattern="zq-ladder" viewBox="0 0 10 10" role="img" aria-label="a b c d"></svg>')
    open(os.path.join(tmp, 'units', 'u.html'), 'w', encoding='utf-8').write('<section data-u="u-zq"><figure data-pattern="zq-ladder"><svg viewBox="0 0 1 1"></svg></figure><figure><!--svg f-zq--></figure><figure><svg viewBox="0 0 1 1"></svg></figure></section>')
    say('VIS', catalog.uses(tmp)['zq-ladder'] == 2, 'figure data-pattern (on the figure, or in a figure file) counts as a use')
    say('VIS', catalog.uses(tmp)['zq-ladder'] != 3, 'an unlabelled figure does not count')
    os.makedirs(os.path.join(tmp, 'catalog', 'elements'))
    bad = lambda e: json.dump(e, open(os.path.join(tmp, 'catalog', 'elements', 'zq.json'), 'w'))
    bad(['not', 'an', 'object'])
    try:
        catalog.elements(tmp)
        hit = False
    except PlanError as e:
        hit = 'JSON object' in str(e)
    say('PRM', hit, 'element JSON that is no object')
    say('PRM', any('slots must be an object' in m for m in catalog.element_shape('zq', {'id': 'zq', 'family': 'problem', 'why': 'w', 'zone': 'body', 'kinds': ['ask'], 'slots': [], 'render': 'x', 'checks': [], 'example': {'elements': []}})), 'element slots of the wrong type')
    say('PRM', any('family' in m for m in catalog.element_shape('zq', {'id': 'zq', 'family': 3})), 'element family of the wrong type')
    ok_el = json.loads(json.dumps(catalog.elements()['rival']))
    say('PRM', catalog.element_shape('rival', ok_el) == [], 'a skill element passes the shape check (clean)')
    ok_el['checks'] = [{'id': 'zq-check', 'breaks': [{'set': 'elements.0.text', 'to': 'x'}]}]
    gap = catalog.book_check_gaps(tmp, 'rival', ok_el)
    say('PRM', any('catalog/checks/zq-check.py' in m for m in gap), 'a new check with no code in the book')
    os.makedirs(os.path.join(tmp, 'catalog', 'checks'))
    cp = os.path.join(tmp, 'catalog', 'checks', 'zq-check.py')
    open(cp, 'w').write('def check(spec, i, ctx):\n    return [("error", "zq")]\n')
    say('PRM', catalog.book_check_gaps(tmp, 'rival', ok_el) == [], 'a new check with code in the book (clean)')
    open(cp, 'w').write('def txt(h):\n    return h\n\ndef check(spec, i, ctx):\n    return []\n')
    say('PRM', any('already has' in m for m in catalog.book_check_gaps(tmp, 'rival', ok_el)), 'book check code that shadows a pcheck name')
    open(cp, 'w').write('def check(spec, i, ctx):\n    return [("error", "zq")]\n')
    os.remove(os.path.join(tmp, 'catalog', 'elements', 'zq.json'))
    catalog.elements(tmp)
    say('PRM', 'zq-check' in pcheck.CHECKS and 'zq-check' in pcheck.BOOK_CHECKS, 'the book check loads into pcheck at run time')
    pcheck.CHECKS.pop('zq-check', None)
    pcheck.BOOK_CHECKS.discard('zq-check')
    open(os.path.join(tmp, 'book.js'), 'w').write('window.claude.use("sample");')
    say('PUB', 'sample' in publish.host_warning(tmp), 'book js that calls a host capability warns on file/static')
    open(os.path.join(tmp, 'book.js'), 'w').write('var x = 1;')
    say('PUB', publish.host_warning(tmp) == '', 'book js without host calls (clean)')
    restore()
    return fail, n
# --- end fix round (F4)


# --- fix round (F3)
def f3_cases(base, hp, pristine, before_close):
    """agents: reviewers' no rows and render findings reach fixer tasks, the scout task, coherence once per part, the publish gate, DIR/STAGE order."""
    import contextlib, io
    from . import agents
    fail = n = 0

    def restore():
        for f, t in pristine.items():
            open(os.path.join(base, f), 'w', encoding='utf-8').write(t)
        shutil.rmtree(os.path.join(base, '.work'), ignore_errors=True)

    def say(name, ok, what):
        nonlocal fail, n
        n += 1
        fail += not ok
        print(f"{name:3} {'caught' if ok else 'MISSED'} ({what})")
    restore()
    P = Plan(os.path.join(base, 'book.json'))
    uid = next(u['id'] for u in P.live if u['role'] == 'core')
    fx = lambda *a, **k: [t.split('\t') for t in agents.tasks(base, 'fix', *a, **k)]
    base_n = len(fx())
    os.makedirs(os.path.join(base, '.work', 'r-zq-1'))
    open(os.path.join(base, '.work', 'r-zq-1', 'no.tsv'), 'w', encoding='utf-8').write(f'{uid}\tc1\tev-claim\tname the source\nnowhere\t-\tev-claim\tx\n')
    ts = fx()
    ok = any('no:ev-claim' in t[4] and t[1] == 'fixer' for t in ts) and any(t[1] == 'main' and 'no:ev-claim' in t[0] for t in ts)
    br = agents.fix_brief(base, ['no:ev-claim'], [uid], 'fx-zq')
    say('F3a', ok and f'no:ev-claim {uid} #c1 name the source' in br and not cmd_gaps([t[4] for t in ts if t[1] != 'main']), 'a no.tsv row reaches a fixer task and its brief; an unknown unit goes to the lead')
    restore()
    rp = os.path.join(base, 'rend.txt')
    open(rp, 'w', encoding='utf-8').write(f'fail 390px light {uid} c2 overflow-x: wide\nfail 1200px dark {uid} c2 overflow-x: wide\nfail 390px light - - page-error: boom\n')
    ts = fx(None, None, rp)
    br = agents.fix_brief(base, ['render:overflow-x'], [uid], 'fx-zq', render=rp)
    say('F3b', any('render:overflow-x' in t[4] and '--render' in t[4] for t in ts) and br.count('- render:overflow-x ') == 1 and any(t[1] == 'main' and 'render:page-error' in t[0] for t in ts)
        and not cmd_gaps([t[4] for t in ts if t[1] != 'main']), 'render findings route to a fixer (deduplicated across widths); a page-level failure goes to the lead')
    restore()
    say('F3c', all('40 tool calls' in agents.lens_brief(base, n_, [uid], P=P) for n_ in agents.lenses()) and '40 tool calls' in agents.role_brief(base, 'test', 'x', P=P, uid=uid), 'the tool-call budget is in every brief')
    j = json.load(open(os.path.join(base, 'book.json'), encoding='utf-8'))
    j['book'].setdefault('policies', {})['new_patterns'] = 1
    json.dump(j, open(os.path.join(base, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sc = [t for t in agents.tasks(base, 'plan') if t.startswith('b-pattern-scout')]
    sb = agents.role_brief(base, 'research', sc[0].split('\t')[4].split('--research ')[1].split(' --as')[0].strip("'") if sc else 'Pattern scout', 'b-pattern-scout', True)
    say('F3d', len(sc) == 1 and '\thaiku\t' in sc[0] and 'pattern list' in sb and not cmd_gaps([sc[0].split('\t')[4]]), 'the plan stage emits one haiku pattern-scout task')
    j['book']['policies']['new_patterns'] = 0
    json.dump(j, open(os.path.join(base, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    say('F3d', not any(t.startswith('b-pattern-scout') for t in agents.tasks(base, 'plan')), 'no scout task when new_patterns is 0')
    restore()
    x = agents.lenses()
    co = next(v for v in x.values() if v['role'] == 'review-coherence')
    pool = [u['id'] for u in P.live]
    sizes = agents._sizes(base, P, pool, {None})
    parts = {P.U[u].get('part') for u in pool}
    gs = agents.review_groups(base, P, dict(co, inputs=['text --unit U']), pool, {None: sizes[None]} if False else sizes)
    say('F3e', len(gs) == len(parts) and all(':' not in t for g in gs for t in g), 'coherence: one task per part, whole units')
    big = [('a', [(0, 24000)]), ('b', [(0, 24000)]), ('c', [(0, 2000)])]
    g2 = agents._pack(big)
    say('F3f', len(g2) == 2 and 'c' in g2[-1], 'a small leftover slice joins the previous batch')
    def run(argv):
        e = io.StringIO()
        with contextlib.redirect_stdout(e), contextlib.redirect_stderr(io.StringIO()):
            try:
                from .cli import main as cli_main
                r = cli_main(argv)
            except SystemExit as ex:
                r = ex.code
        return r, e.getvalue()
    a1, a2, a3 = run(['agents', base, 'fix']), run(['agents', 'fix', base]), run(['agents', 'fix', '--dir', base])
    r4 = run(['agents', 'fix', base, '--symptom', 'x'])
    say('F3g', a1 == a2 == a3 and a1[0] == 0 and r4[0] not in (0, None), 'agents takes DIR before or after STAGE; --symptom outside debug is an error')
    ok = True
    j = json.load(open(os.path.join(base, 'book.json'), encoding='utf-8'))
    j.pop('gates', None)
    json.dump(j, open(os.path.join(base, 'book.json'), 'w'), ensure_ascii=False, indent=1)
    try:
        agents.approve(base, 'publish', 'self')
        ok = False
    except agents.AgentsError as e:
        ok = 'review gate' in str(e)
    say('F3h', ok, 'publish approval refused without an approved review gate at this plan hash')
    restore()
    return fail, n
# --- end fix round (F3)
