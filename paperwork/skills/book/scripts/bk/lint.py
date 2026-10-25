import html, os, re
from html.parser import HTMLParser
from .build import CARDS, MARKERS, before_text, g_glossary, g_head, g_hero, g_nav, g_pn, g_tokens, ol_has_order, opt_len, opt_shape, ref_target
from .lang import final_sound, native, pack, stems_of, words_of
from .const import INLINE_STRINGS, LEVELS, MOVES, REF_OF, TACTICS, TASK_KINDS, TIERS
from .dom import NO_MATH, Node, TEXTISH, canon, is_c, opts, parse, prose_blocks, sentences, tex_of, unit_blocks, vis
from .plan import Plan, PlanError, check_plan, fact_text, settle

def lint(d, unit=None, quick=False):
    P = Plan(os.path.join(d, 'book.json'))
    LP = P.pack
    F = check_plan(P)
    path = os.path.join(d, 'book.html')
    if not os.path.exists(path):
        raise PlanError('book.html not found; run `book.py build` first')
    if unit and unit not in P.U:
        raise PlanError(f'--unit {unit} is not in book.json')
    book_src = open(path, encoding='utf-8').read()
    root = parse(book_src)
    secs = {s.get('data-u'): s for s in root.find(lambda n: n.tag == 'section' and n.get('data-u'))}
    asks = {n.get('id'): n for n in root.find(lambda n: is_c(n, 'ask', 'task') and n.get('id') and not n.get('data-src'))}
    ask_unit = {k: v.up(lambda p: p.get('data-u') is not None).get('data-u') for k, v in asks.items()}
    pol, b, s_ = P.pol, P.bands, P.s

    def cmp(name, node, expect, uid):
        if node is None:
            if expect:
                F.add('G1', 'error', uid, f'chrome {name} missing')
        elif not expect:
            F.add('G1', 'error', uid, f'chrome {name} present but not expected')
        elif canon(node) != canon(expect):
            F.add('G1', 'error', uid, f'chrome {name} differs from book.json; rebuild', node.text()[:80])
    first = lambda s, k: s.first(lambda n: n.get('data-d') == k)
    if pol['scale'] != 'page':
        cmp('hero', first(root, 'hero'), g_hero(P), '-')
        cmp('nav', first(root, 'nav'), g_nav(P), '-')
    tok = first(root, 'tokens')
    if tok is None or re.sub(r'\s', '', tok.text()) != re.sub(r'\s', '', g_tokens(P)):
        F.add('G1', 'error', '-', 'lexicon tokens differ from book.json; rebuild')
    seen_id = {}
    for n in root.walk():
        if isinstance(n, Node) and n.get('id'):
            seen_id.setdefault(n.get('id'), []).append((n.up(lambda p: p.get('data-u') is not None) or n).get('data-u') or '-')
    for k, us in sorted(seen_id.items()):
        if len(us) > 1 and (not unit or unit in us):
            F.add('G4', 'error', us[0], f'id "{k}" is used {len(us)} times (units {", ".join(dict.fromkeys(us))}); ids must be unique', k)
    for extra in sorted(set(secs) - {u['id'] for u in P.live}):
        F.add('G1', 'error', extra, 'unit in book.html is not a live unit of book.json')
    for u in P.live:
        s = secs.get(u['id'])
        if s is None:
            F.add('G1', 'error', u['id'], 'unit missing from book.html; write it or mark it "status": "planned"')
            continue
        cmp('head', first(s, 'head'), g_head(P, u), u['id'])
        cmp('pn', first(s, 'pn'), g_pn(P, u), u['id'])
        for k in ('legend', 'notation'):
            if first(s, k) is not None:
                cmp(k, first(s, k), MARKERS[k](P), u['id'])
    if pol['scale'] == 'book' and P.C:
        cmp('glossary', first(root, 'glossary'), g_glossary(P), '-')
    if pol['scale'] == 'book' and P.L and first(root, 'legend') is None:
        F.add('G1', 'warn', '-', 'no legend; put <!--@legend--> in the appendix unit')
    for sec_ in secs.values():  # build-time dressing is current: numbers and option order
        for i, c in enumerate(sec_.find(lambda x: is_c(x, *CARDS)), 1):
            qn = c.first(lambda x: x.get('class') == 'qn')
            if qn is None or qn.text().strip() != f'{i}.':
                F.add('G1', 'error', sec_.get('data-u'), 'card numbers stale; rebuild', c.get('id') or c.get('data-c'))
                break
        for ol in sec_.find(lambda x: x.get('data-p') == 'opts' and not x.has('data-order')):
            ls = [opt_len(k) for k in ol.kids if isinstance(k, Node) and k.tag == 'li']
            if ls != sorted(ls):
                F.add('G1', 'error', sec_.get('data-u'), 'options not in ascending length; rebuild (or mark data-order for a logical order)')

    def where(n):
        sec = n.up(lambda p: p.get('data-u') is not None)
        return sec.get('data-u') if sec else '-'
    # O3 sources: a card reads a record only after the block that shows where and how to open it
    order = {id(n): i for i, n in enumerate(root.walk())}
    for src in P.d.get('sources', []):
        teach = root.first(lambda n: n.get('data-see') == src.get('id'))
        if teach is None:
            F.add('O3', 'warn', src.get('unit', '-'), f'source {src.get("id")} has no block marked data-see="{src.get("id")}"; show where and how the reader opens {src.get("name")} before the first card that reads it')
        rxs = []
        for fx in src.get('forms', []):
            try:
                rxs.append(re.compile(fx))
            except re.error:
                pass
        for c in root.find(lambda n: is_c(n, 'ask', 'task')):
            if (teach is None or order[id(c)] < order[id(teach)]) and any(r.search(c.text(lambda x: NO_MATH(x) or x.get('data-p') == 'why')) for r in rxs):
                F.add('O3', 'warn', where(c), f'card reads {src.get("name")} before the block that shows where and how to open it', c.text(NO_MATH)[:70])
    # G2 references, facts, ids, leaks
    for a in root.find(lambda n: n.tag == 'a' and n.get('data-ref')):
        uid, txt, gloss = ref_target(P, a.get('data-ref'))
        if uid is None:
            F.add('G2', 'error', where(a), 'data-ref target unknown', a.get('data-ref'))
        elif a.text().strip() != txt or a.get('data-gloss') != gloss:
            F.add('G2', 'error', where(a), 'reference text or gloss stale; rebuild', a.text())
        elif P.U[uid].get('status') == 'planned':
            F.add('G2', 'warn', where(a), 'reference to a unit that is only planned', a.get('data-ref'))
    for v in root.find(lambda n: n.tag == 'span' and n.get('data-v') is not None):
        ft = fact_text(P, v.get('data-v'))
        if ft is None:
            F.add('G2', 'error', where(v), 'data-v fact missing from facts.json', v.get('data-v'))
        elif v.text().strip() != ft:
            F.add('G2', 'error', where(v), 'fact value stale; rebuild', v.get('data-v'))
    for n in root.find(lambda n: n.tag == '#comment' and re.match(r'\s*(@|svg )', n.get('text', ''))):
        F.add('G2', 'error', where(n), 'unfilled build marker', n.get('text'))
    titles = sorted((re.escape(u['title']) for u in P.units if u['title']), key=len, reverse=True)
    ref_re = None
    if '{n}' in s_['ref'] and titles:
        pre, post = s_['ref'].split('{title}')[0].split('{n}')[:2]
        ref_re = re.compile(re.escape(pre) + r'\d+' + re.escape(post) + r'\s*' + ('(?:' + LP['genitive'] + r'\s*)?' if LP.get('genitive') else '') + r'(?:' + '|'.join(titles) + ')')
    for uid, s in secs.items():
        for blk in prose_blocks(s):
            t = blk.text(lambda n: NO_MATH(n) or n.get('data-ref') is not None)
            if re.search(r'\{\{\w+\}\}|TODO|#ex[ -]\w|\[(VERIFIED|UNVERIFIED|CORRECTED|CHECK|FIXME|from memory)[^\]]*\]', t, re.I):
                F.add('G2', 'error', uid, 'leaked token', t[:80])
            if ref_re and ref_re.search(t):
                F.add('G2', 'warn', uid, 'unit number typed by hand; use data-ref', ref_re.search(t).group(0))
    for c in root.find(lambda n: n.get('data-variant-of')):
        src = asks.get(c.get('data-variant-of'))
        if src is None:
            F.add('G2', 'error', where(c), 'data-variant-of names no card', c.get('data-variant-of'))
        elif P.idx.get(where(src), 10 ** 6) >= P.idx.get(where(c), -1):
            F.add('G2', 'error', where(c), 'a review variant must vary a card of an earlier unit', c.get('data-variant-of'))
        else:
            q1, q2 = (vis(x.first(lambda n: n.get('data-p') == 'q') or x) for x in (src, c))
            w1, w2 = words_of(q1, LP), words_of(q2, LP)
            if w1 and w2 and len(w1 & w2) / min(len(w1), len(w2)) >= 0.7:
                F.add('K9', 'warn', where(c), f'review of {c.get("data-variant-of")} repeats its stem; ask the same idea on a new case')
            r1 = words_of(' '.join(vis(li) for li in opts(src) if not li.has('data-ok')), LP)
            r2 = words_of(' '.join(vis(li) for li in opts(c) if not li.has('data-ok')), LP)
            if r1 and r2 and len(r1 & r2) / min(len(r1), len(r2)) >= 0.5:
                F.add('K9', 'warn', where(c), f'review of {c.get("data-variant-of")} reuses its rivals; give the variant new rival beliefs')
    # homes (F2) across the book
    homes_seen = {}
    for f in root.find(lambda n: n.tag == 'figure' and n.get('data-home')):
        homes_seen.setdefault(f.get('data-home'), []).append(f)
    map_id = next((u['id'] for u in P.live if u['role'] == 'map'), None)
    for h, figs_ in homes_seen.items():
        if h not in P.H:
            F.add('F2', 'error', where(figs_[0]), 'data-home names no home figure', h)
            continue
        for f in figs_:
            if map_id and where(f) == map_id:
                F.add('F2', 'error', map_id, f'home {h} drawn in the map; draw it first where the book first needs it')
        for f in figs_[1:]:
            if f.get('data-focus') not in P.H[h]['regions']:
                F.add('F2', 'error', where(f), f'home instance needs data-focus from {P.H[h]["regions"]}', f.get('data-focus'))
    for h in P.H:
        n_ = len(homes_seen.get(h, []))
        if n_ == 0:
            F.add('F2', 'warn', '-', f'home {h} is never drawn')
        elif n_ == 1 and len(P.live) > 2:
            F.add('F2', 'warn', '-', f'home {h} is drawn once; a home recurs')
    # unit rules
    q_on = pol['interaction'] != 'none'
    stem_reg = '(' + '|'.join(x for g in LP.get('stem_registers', []) for x in g) + r')\??\.?$' if LP.get('stem_registers') else None
    kstat = dict(moves=[], levels=[], diffs=[], tasks=[], nopts=[], pos=[], stem_ends=[])
    fs, fq = LP['fact_sent'], LP.get('fact_question')
    for f in set(P.facts_decl) | set(P.facts):
        t = fact_text(P, f)
        if t and (re.search(fs, t.strip().strip('"\'”’')) or re.search(r'[:→()\[\]]', t) or len(t) > P.common['fact_max'] or fq and re.search(fq, t) and not re.match(r'^[\'"‘“]', t)):
            F.add('T2', 'error', '-', f'fact {f} must be a short noun phrase (<= {P.common["fact_max"]} chars, no colon, arrow or brackets); put details in a table or the prose', t[:60])
    spl = {}
    for uid_, sec_ in secs.items():
        for v in sec_.find(lambda n: n.get('data-v') is not None):
            spl.setdefault(v.get('data-v'), set()).add(uid_)
    for f, us in spl.items():
        if len(us) >= 3 and isinstance(P.facts.get(f), dict) and len(fact_text(P, f) or '') > 15:
            F.add('T2', 'warn', '-', f'fact {f} is spliced into {len(us)} units; recall it in fresh words after its first use', ', '.join(sorted(us)))
    for u in P.live:
        uid, role = u['id'], u['role']
        s = secs.get(uid)
        if s is None or (unit and uid != unit):
            continue
        blocks = unit_blocks(s)
        names = [x.get('data-c') for x in blocks]
        # U1 shape
        if role in ('core', 'capstone', 'catalog', 'map'):
            if not names or names[0] != 'gist':
                F.add('U1', 'error', uid, 'gist must be the first component')
            g = next((x for x in blocks if is_c(x, 'gist')), None)
            if g is not None and not P.common['gist'][0] <= len(sentences(vis(g))) <= P.common['gist'][1]:
                F.add('U1', 'warn', uid, f'gist has {len(sentences(vis(g)))} sentences ({P.common["gist"][0]}-{P.common["gist"][1]})')
        if role == 'core':
            for nm in ['defn'] + (['probe', 'close'] if q_on else []):
                if nm not in names:
                    F.add('U1', 'error', uid, f'core unit lacks {nm}')
            if q_on and 'probe' in names and names.index('probe') != 1:
                F.add('U1', 'error', uid, 'the probe must follow the gist')
            if 'close' in names and names[-1] != 'close':
                F.add('U1', 'warn', uid, 'close is not the last component')
            if pol['structure'] == 'project' and u.get('makes') and 'step' not in names:
                F.add('U1', 'error', uid, 'unit makes a project fact but has no step')
        # U5 placements
        for n in s.find(lambda n: is_c(n, 'note') and n.tag != 'details'):
            F.add('U5', 'error', uid, 'note must be details[data-c=note] with a summary so it stays folded')
        for n in s.find(lambda n: is_c(n, 'aside', 'note') and n.tag == 'details' and not n.first(lambda x: x.tag == 'summary')):
            F.add('U5', 'error', uid, 'folded block without a summary')
        for k in ('legend', 'notation'):
            if s.first(lambda n, k=k: n.get('data-d') == k) and role != 'ref':
                F.add('U5', 'error', uid, f'{k} belongs in the appendix (a ref unit), not in {role}')
        # U2 probe
        if names.count('probe') > 1:
            F.add('U2', 'error', uid, 'one probe per unit')
        for cd in s.find(lambda n: is_c(n, 'cond')):
            blk = cd.up(lambda p: p.tag in ('p', 'li', 'div'))
            if blk is not None and not blk.find(lambda n: n.get('data-ref')):
                F.add('U2', 'warn', uid, 'insight sentence without a data-ref to the concept it links')
        pb = next((x for x in blocks if is_c(x, 'probe')), None)
        if pb is not None:
            pt = vis(pb)
            for c in (c for c in P.C.values() if P.idx.get(c['unit'], -1) >= P.idx[uid]):
                f = next((f for f, _ in P.forms(c) if len(f) >= 2 and re.search(r'(?<!\w)' + re.escape(f) + r'(?![A-Za-z])', pt)), None)
                if f:
                    F.add('U2', 'warn', uid, f'probe uses "{f}", defined only in {c["unit"]}; ask in words a newcomer has')
                    break
        # U3 definitions and the key-then-rich shape
        defs = s.find(lambda n: is_c(n, 'defn'))
        got = [x.get('data-concept') for x in defs]
        for cid in got:
            if cid not in P.C:
                F.add('U3', 'error', uid, 'definition of an unknown concept', cid)
            elif P.C[cid]['unit'] != uid:
                F.add('U3', 'error', uid, f'{cid} is defined outside its home {P.C[cid]["unit"]}')
        for cid in {x for x in got if got.count(x) > 1}:
            F.add('U3', 'error', uid, 'concept defined twice', cid)
        for c in P.defines[uid]:
            if c['id'] not in got:
                F.add('U3', 'error', uid, 'home concept has no definition', c['id'])
        for fm in s.find(lambda n: is_c(n, 'formal')):
            if not fm.up(lambda p: is_c(p, 'defn')):
                F.add('U3', 'warn', uid, 'formal toggle outside a defn')
        if role == 'core':
            for dn in defs:
                k = dn.first(lambda n: is_c(n, 'key'))
                if k is None:
                    F.add('U3', 'error', uid, 'defn without its one-sentence key (p[data-c=key])', dn.get('data-concept'))
                    continue
                if len(sentences(vis(k))) > 1 or len(vis(k)) > P.common['key_max']:
                    F.add('U3', 'warn', uid, f'key is longer than one plain sentence ({len(vis(k))} chars)', vis(k)[:60])
                cid = dn.get('data-concept')
                if not s.find(lambda n, cid=cid: is_c(n, 'frames') and cid in (n.get('data-concept') or '').split()):
                    F.add('U3', 'warn', uid, f'{cid}: no frames figure (data-concept) builds this concept step by step')
            ks = [n for n in s.walk() if is_c(n, 'key')]
            flat = [n for n in s.walk() if n.tag in ('p', 'li', 'figcaption') and not n.up(lambda p: is_c(p, *CARDS, 'close') or p.tag == 'svg')]
            for k in ks:
                i = flat.index(k) if k in flat else -1
                tail = []
                for n in flat[i + 1:]:
                    if is_c(n, 'key'):
                        break
                    tail.append(vis(n))
                if i >= 0 and len(' '.join(tail)) < P.common['elab_min']:
                    F.add('U3', 'warn', uid, f'key followed by only {len(" ".join(tail))} chars of elaboration; state briefly, then explain richly', vis(k)[:50])
        # U4 cards: every card is a gate the reader opens by answering it
        cue = LP.get('cue_words')
        otext = lambda li: re.sub(r'\s+', ' ', li.text(lambda n: n.get('data-p') == 'why' or n.tag == 'svg' or n.has('data-m'))).strip()
        outside = ' '.join(vis(x) for x in prose_blocks(s) if not x.up(lambda p: is_c(p, *CARDS, 'close')))

        def runs(t):
            return {t[i:i + 20] for i in range(len(t) - 19)} if LP['ngram'] == 'chars' else {' '.join(w[i:i + 8]) for w in [t.split()] for i in range(len(w) - 7)}
        own = [c for c in s.find(lambda n: is_c(n, *CARDS)) if not c.get('data-src') and not c.up(lambda p: p.get('data-src'))]
        for c in own:
            what = f'{c.get("data-c")} {c.get("id") or ""}'.strip()
            q = c.first(lambda n: n.get('data-p') == 'q')
            if q is None:
                F.add('U4', 'error', uid, f'{what} has no stem p[data-p=q]')
                continue
            stem = vis(q)
            m_ = stem_reg and re.search(stem_reg, stem.strip())
            kstat['stem_ends'].append(m_.group(1) if m_ else None)
            if not re.search(LP['stem_end'], stem.strip()):
                F.add('K7', 'warn', uid, f'{what}: the stem must end as a question or an instruction', stem[-40:])
            neg = LP.get('neg_stem')
            if neg and re.search(neg, stem) and not q.first(lambda n: n.tag in ('u', 'b', 'strong') and re.search(neg, n.text())):
                F.add('K7', 'warn', uid, f'{what}: negative stem without the negation underlined (<u>)', stem[:60])
            mv, lv, df = c.get('data-move'), c.get('data-level'), c.get('data-diff')
            if mv not in MOVES:
                F.add('K6', 'error', uid, f'{what}: data-move must be one of {MOVES}', mv)
            if lv not in LEVELS:
                F.add('K8', 'error', uid, f'{what}: data-level must be one of {LEVELS}', lv)
            if df not in ('1', '2', '3'):
                F.add('K8', 'error', uid, f'{what}: data-diff must be 1, 2 or 3', df)
            kstat['moves'].append(mv)
            kstat['levels'].append(lv)
            kstat['diffs'].append(df)
            if is_c(c, 'task'):
                kind = c.get('data-kind')
                kstat['tasks'].append(kind)
                items = [k for x in c.find(lambda n: n.get('data-p') == 'items') for k in x.kids if isinstance(k, Node) and k.tag == 'li']
                if kind not in TASK_KINDS:
                    F.add('U4', 'error', uid, f'{what}: data-kind must be one of {TASK_KINDS}' + ('; free text cannot be checked, so the reader could never pass it: ask the same idea as a choice, order, sort or estimate' if kind == 'compose' else ''), kind)
                elif kind == 'order' and (len(items) < 3 or not c.first(lambda n: n.tag == 'ol' and n.get('data-p') == 'items')):
                    F.add('U4', 'error', uid, f'{what}: order needs ol[data-p=items] with 3+ items in the right order')
                elif kind == 'select' and (len(items) < 3 or not any(x.has('data-ok') for x in items) or all(x.has('data-ok') for x in items)):
                    F.add('U4', 'error', uid, f'{what}: select needs 3+ items, some data-ok and some not')
                elif kind == 'estimate':
                    box = c.first(lambda n: n.get('data-p') == 'input')
                    try:
                        float((box.get('data-ans') if box else None) or 'x')
                    except ValueError:
                        F.add('U4', 'error', uid, f'{what}: estimate needs div[data-p=input][data-ans]')
                    try:
                        av, tv = float(box.get('data-ans')), float(box.get('data-tol') or 0.2)
                        if av == int(av) and not box.has('data-int') and abs(av) * tv >= 1:
                            F.add('U4', 'warn', uid, f'{what}: integer answer {av:g} accepts neighbouring integers at tolerance {tv:g}; add data-int for an exact count')
                    except (TypeError, ValueError):
                        pass
                    for h in ('lo', 'hi', 'why'):
                        if not c.first(lambda n, h=h: n.get('data-p') == h):
                            F.add('U4', 'error', uid, f'{what}: estimate needs p[data-p={h}]')
                elif kind == 'sort' and (len(items) < 3 or any(not x.get('data-cat') for x in items) or not c.first(lambda n: n.get('data-cats'))):
                    F.add('U4', 'error', uid, f'{what}: sort needs ul[data-p=items][data-cats="A,B"] with 3+ items, each with data-cat')
                elif kind == 'custom' and (not c.get('data-widget') or c.get('data-widget') not in P.bookjs):
                    F.add('U4', 'error', uid, f'{what}: custom task needs data-widget naming a widget that book.js wires (bookSolve and __solve)', c.get('data-widget'))
                if kind in ('order', 'select') and sum(1 for x in items if not x.get('data-why')) > (0 if kind == 'select' else 1):
                    F.add('U4', 'warn', uid, f'{what}: give each item a data-why shown when it is misplaced or wrongly picked')
                continue
            os_ = opts(c)
            in_ex = c.up(lambda p: is_c(p, 'ex')) is not None
            if sum(1 for li in os_ if li.has('data-ok')) != 1:
                F.add('U4', 'error', uid, f'{what} needs exactly one data-ok option')
            if any(not li.first(lambda x: x.get('data-p') == 'why') for li in os_):
                F.add('U4', 'error', uid, f'{what}: every option needs a why (wrong: why it fails; right: why it holds)')
            if len(os_) < 3:
                F.add('K7', 'warn', uid, f'{what}: {len(os_)} options; every choice card, example steps included, offers 3 or more real moves')
            if not in_ex:
                kstat['nopts'].append(len(os_))
            for li in os_:
                y = li.first(lambda x: x.get('data-p') == 'why')
                if y is not None and not li.has('data-ok'):
                    for sent in sentences(stem):
                        sw = words_of(sent, LP)
                        if len(sw) >= 3 and len(sw & words_of(vis(y), LP)) / len(sw) >= 0.7:
                            F.add('K11', 'warn', uid, f'{what}: a wrong option is refuted by the stem itself; the reader can eliminate it without the idea', sent[:60])
                            break
                if y is not None and not li.has('data-ok') and re.search(LP['concede'], vis(y)):
                    F.add('K11', 'warn', uid, f'{what}: a wrong option\'s why concedes it ({vis(y)[:30]}); a conceded option is a second answer', vis(y)[:60])
            if len(os_) < 2 or sum(1 for li in os_ if li.has('data-ok')) != 1:
                continue
            T = [(li.has('data-ok'), otext(li)) for li in os_]
            okt = next(t for k, t in T if k)
            wr = [t for k, t in T if not k]
            L, W = len(okt), [len(t) for t in wr]
            words = lambda t: words_of(t, LP)
            before = before_text(s, c, P.common['novelty_window'])
            kw = words(okt)
            if c.get('data-level') in LEVELS[2:] and len(kw) >= 3 and len(kw & words(before)) / len(kw) >= P.common['novelty']:
                F.add('K9', 'warn', uid, f'{what}: {len(kw & words(before))}/{len(kw)} of the answer\'s words appear just above it; an apply card needs a new case, and the answer must not restate the prose', okt[:60])
            if is_c(c, 'probe'):
                g = next((x for x in blocks if is_c(x, 'gist')), None)
                if g is not None and kw and len(kw & words(vis(g))) / len(kw) >= P.common['novelty']:
                    F.add('K9', 'error', uid, 'the gist gives away the probe\'s answer', okt[:60])
            hedge = LP.get('hedge')
            if hedge and any(re.search(hedge, t) for t in wr) and not re.search(hedge, okt):
                F.add('K10', 'warn', uid, f'{what}: vague or extreme words only in wrong options; make every rival a move a competent person would make', next(t for t in wr if re.search(hedge, t))[:60])
            if re.search(r'\d', okt) and not any(re.search(r'\d', t) for t in wr) and not ol_has_order(c):
                F.add('K10', 'warn', uid, f'{what}: only the answer is concrete (has a number); give every option the same concreteness', okt[:60])
            if len(os_) == 2 and c.get('data-level') in LEVELS[2:]:
                F.add('K8', 'warn', uid, f'{what}: a two-option card cannot test application; add real rivals or relabel')
            ol = c.first(lambda n: n.get('data-p') == 'opts')
            if not ol.has('data-order'):
                pos = sorted(range(len(os_)), key=lambda i: opt_len(os_[i])).index(next(i for i, li in enumerate(os_) if li.has('data-ok')))
                kstat['pos'].append((pos, len(os_)))
            if L > max(W) * P.common['len_ratio'] or L * P.common['len_ratio'] < min(W):
                F.add('K1', 'warn', uid, f'{what}: answer {L} chars vs wrong {min(W)}-{max(W)}; make lengths alike', okt[:60])
            if cue and not is_c(c, 'probe') and any(re.search(cue, t) for t in wr) and not re.search(cue, okt):
                F.add('K3', 'warn', uid, f'{what}: absolutes only in wrong options', next(t for t in wr if re.search(cue, t))[:60])
            for t in [okt] + wr:
                if LP['catch_all_re'].match(t):
                    F.add('K4', 'error', uid, f'{what}: catch-all option', t)
            if any(r in outside for r in runs(okt)) and not any(r in outside for t in wr for r in runs(t)):
                F.add('K5', 'warn', uid, f'{what}: answer copies the prose; paraphrase it', okt[:60])
            ends = {opt_shape(t, LP) for t in [okt] + wr}
            if len(ends) > 1:
                F.add('K7', 'warn', uid, f'{what}: options mix sentence and phrase endings; give them one grammatical shape', ' / '.join(t[-12:] for t in [okt] + wr))
            low = [re.sub(r'\W', '', t) for t in [okt] + wr]
            if any(a and a != b and a in b for a in low for b in low):
                F.add('K7', 'warn', uid, f'{what}: one option contains another; make options exclusive')
            stem_w, ok_w = stems_of(stem, LP), stems_of(okt, LP)
            if stem_w and len(ok_w & stem_w) >= 2 and all(len(stems_of(t, LP) & stem_w) + 2 <= len(ok_w & stem_w) for t in wr):
                F.add('K5', 'warn', uid, f'{what}: answer repeats stem words the others do not (clang)', ' '.join(sorted(ok_w & stem_w))[:60])
        kinds_here = {c.get('data-kind') for c in own if is_c(c, 'task')}
        if role == 'core' and q_on and not kinds_here & {'order', 'estimate', 'custom'}:
            F.add('K8', 'warn', uid, 'no production task (order, estimate or custom); the reader must make or operate something with the idea')
        keys_ = [(c, words_of(next((otext(li) for li in opts(c) if li.has('data-ok')), ''), LP)) for c in own if opts(c)]
        for i_, (c1, k1) in enumerate(keys_):
            for c2, k2 in keys_[i_ + 1:]:
                if k1 and k2 and len(k1 & k2) / min(len(k1), len(k2)) >= 0.7:
                    F.add('K9', 'warn', uid, f'{c1.get("id") or c1.get("data-c")} and {c2.get("id") or c2.get("data-c")} test the same claim with near-identical answers')
        if role == 'core' and q_on and own and not {c.get('data-move') for c in own} & {'predict', 'intervene', 'decide', 'diagnose'}:
            F.add('K6', 'warn', uid, 'no predict, intervene, decide or diagnose card; cards only recall or compute')
        if role == 'core' and q_on:
            lo_, hi_ = b.get('core', {}).get('qs', (0, 99))
            if not lo_ <= len(own) <= hi_:
                F.add('L1', 'warn', uid, f'{len(own)} cards; band {lo_}-{hi_}')
        for cl in s.find(lambda n: is_c(n, 'close') and not n.get('data-src')):
            if not cl.first(lambda n: n.tag == 'p' and not n.up(lambda p: is_c(p, *CARDS))):
                F.add('U4', 'error', uid, 'close needs its summary paragraph')
            if pol['interaction'] == 'full' and role == 'core' and any(P.idx.get(x, 10 ** 6) < P.idx[uid] and P.U.get(x, {}).get('role') == 'core' for x in ask_unit.values()):
                if not cl.find(lambda n: n.get('data-variant-of')):
                    F.add('U4', 'warn', uid, 'close has no review variant (a card with data-variant-of an earlier unit\'s card)')
        for ex in s.find(lambda n: is_c(n, 'ex')):
            if ex.get('data-tier') not in TIERS:
                F.add('U4', 'warn', uid, f'example tier must be one of {TIERS}', ex.get('data-tier'))
            if not ex.first(lambda n: is_c(n, 'worked')):
                F.add('U4', 'error', uid, 'example needs a modelled step first (p[data-c=worked]: the step done and explained) before the reader takes over')
            if len(ex.find(lambda n: is_c(n, *CARDS))) < 2:
                F.add('U4', 'error', uid, 'example needs 2+ steps the reader takes (asks or a final task)')
        for n in s.find(lambda n: (is_c(n, 'note') and n.get('data-grade') is not None) or is_c(n, 'badge')):
            vocab, val = (s_['grades'], n.get('data-grade')) if is_c(n, 'note') else (s_['badges'], n.get('data-b'))
            if vocab and val not in vocab:
                F.add('U4', 'warn', uid, f'value {val} not in {vocab}')
        for n in s.find(lambda n: (n.has('title') and n.tag != 'svg' and not n.up(lambda p: p.tag == 'svg')) or any(k in n.attrs for k in ('onmouseover', 'onmouseenter'))):
            F.add('U4', 'warn' if n.has('title') else 'error', uid, 'hover-only information; make it visible or tap-to-open', n.tag)
        # H1 headings
        hs = LP['head_sent']
        for h in s.find(lambda n: n.tag in ('h3', 'h4') and not n.up(lambda p: p.tag == 'svg')):
            if re.search(hs, h.text().strip()):
                F.add('H1', 'warn', uid, 'heading is a question or a sentence; use a noun phrase', h.text().strip()[:60])
        # F figures
        figs = s.find(lambda n: n.tag == 'figure' and is_c(n, 'fig', 'frames'))
        for f in figs:
            if f.up(lambda p: is_c(p, 'warn', 'gist', 'key', *CARDS)):
                F.add('F5', 'error', uid, 'figure inside a warn, gist or card; a figure stands in the body where the prose before it asks what it answers')
        tactics = set()
        for f in figs:
            enc = (f.get('data-enc') or '').split()
            for e in enc:
                if e not in P.L:
                    F.add('F1', 'error', uid, 'figure data-enc names an unknown lexicon entry', e)
            for el in f.walk():
                for at in ('fill', 'stroke', 'color', 'stop-color'):
                    v = (el.get(at) or '').strip().lower()
                    if v and v not in ('none', 'currentcolor', 'transparent', 'inherit') and not v.startswith(('url(', 'var(')):
                        F.add('F1', 'error', uid, f'literal color {at}="{v}"; use lexicon classes')
                for decl in (el.get('style') or '').split(';'):
                    k, _, v = decl.partition(':')
                    v = v.strip().lower()
                    if k.strip().lower() in ('fill', 'stroke', 'color', 'stop-color', 'background') and v and v not in ('none', 'currentcolor', 'transparent', 'inherit') and not v.startswith('var('):
                        F.add('F1', 'error', uid, 'literal color in style; use lexicon classes', decl.strip())
                if el.tag == 'style':
                    F.add('F1', 'error', uid, 'style element inside a figure; use lexicon classes')
                for cl in (el.get('class') or '').split():
                    if cl.startswith('lx-'):
                        if cl[3:] not in P.L:
                            F.add('F1', 'error', uid, 'class names an unknown lexicon entry', cl)
                        elif cl[3:] not in enc:
                            F.add('F1', 'warn', uid, f'{cl} used but not declared in data-enc')
            t = f.get('data-tactic')
            if t not in TACTICS:
                F.add('F2', 'error', uid, f'figure tactic {t} not in {TACTICS}')
            tactics.add(t)
            if f.get('data-kind') not in ('computed', 'conceptual'):
                F.add('F2', 'warn', uid, 'figure data-kind must be computed or conceptual')
            if role == 'core' and not f.first(lambda n: n.tag == 'figcaption'):
                F.add('F2', 'warn', uid, 'core figure without a caption')
            nodes = [g.get('data-node') for g in f.find(lambda n: n.get('data-node') is not None)]
            for g in f.find(lambda n: n.get('data-node') is not None):
                if not (g.get('data-note') or '').strip():
                    F.add('F4', 'error', uid, 'selectable node without a data-note', g.get('data-node'))
            for k in {x for x in nodes if nodes.count(x) > 1}:
                F.add('F4', 'error', uid, 'node id repeated in one figure', k)
            for e in f.find(lambda n: n.get('data-edge') is not None):
                ends = (e.get('data-edge') or '').split()
                if len(ends) != 2 or any(x not in nodes for x in ends):
                    F.add('F4', 'error', uid, 'data-edge must name two nodes of the figure', e.get('data-edge'))
            if is_c(f, 'frames'):
                if len(f.find(lambda n: n.tag == 'li')) < 3:
                    F.add('F2', 'warn', uid, 'frames need 3 or more frames')
                if not f.first(lambda n: is_c(n, 'read')):
                    F.add('F2', 'warn', uid, 'frames without a read line')
            svg_seen = False
            for el in f.walk():
                svg_seen = svg_seen or el.tag == 'svg'
                if el.tag in ('input', 'button', 'select') and not svg_seen:
                    F.add('F2', 'warn', uid, 'controls above the figure; put them below')
                    break
        # F7 a path or structure narrated in prose with no figure in its section
        if role not in ('map', 'ref'):
            sec_i, has_fig, paras = 0, set(), []
            for n in s.walk():
                if n.tag in ('h2', 'h3'):
                    sec_i += 1
                elif is_c(n, 'fig', 'frames'):
                    has_fig.add(sec_i)
                elif n.tag == 'p' and n.get('data-p') is None and not n.up(lambda p: is_c(p, *CARDS, 'note') or p.tag in ('details', 'figure', 'svg')):
                    toks = {m.group(0).rstrip('.,:') for m in re.finditer(r'(?<![A-Za-z0-9_/.:-])[A-Za-z0-9_./:*\\-]*[A-Za-z][A-Za-z0-9_./:*\\-]*', n.text(lambda x: NO_MATH(x) or x.get('data-ref') is not None))}
                    toks -= set(re.findall(r'[A-Za-z]+', s_['ref']))
                    if len(toks) >= P.common['path_names']:
                        paras.append((sec_i, n, toks))
            for i, n, toks in paras:
                if i not in has_fig:
                    F.add('F7', 'warn', uid, f'{len(toks)} system names in one paragraph and no figure in its section; draw the path or structure', ', '.join(sorted(toks))[:90])
        lo, hi = b.get(role, {}).get('figs', (0, 99))
        if not lo <= len(figs) <= hi:
            F.add('F3', 'warn', uid, f'{len(figs)} figures; band {lo}-{hi}')
        if role == 'core' and len(tactics - {None}) < b.get('core', {}).get('tactics', 0):
            F.add('F3', 'warn', uid, f'{len(tactics - {None})} distinct tactics; want {b["core"]["tactics"]}')
        # L1 band
        band = b.get(role, {})
        counts = dict(chars=len(vis(s)), ex=len(s.find(lambda n: is_c(n, 'ex'))), defs=len(defs))
        for k, v in counts.items():
            if k in band and not band[k][0] <= v <= band[k][1]:
                F.add('L1', 'warn', uid, f'{v} {k}; band {band[k][0]}-{band[k][1]}')
        # S1, T1, O1, M
        blocks_txt = [(blk, blk.text(NO_MATH)) for blk in prose_blocks(s)]
        labels = [t.text() for t in s.find(lambda n: n.tag == 'text' and n.up(lambda p: p.tag == 'svg'))]
        texs = tex_of(s)
        pools = {'prose': [t for _, t in blocks_txt], 'tex': texs, 'label': labels}
        for p in P.d['forbid']:
            try:
                r, un = re.compile(p['re']), (re.compile(p['unless']) if p.get('unless') else None)
            except re.error:
                continue
            sc = p.get('in', 'prose')
            for t in (pools['prose'] + texs + labels if sc == 'all' else pools.get(sc, [])):
                for m in r.finditer(t):
                    ctx = t[max(0, m.start() - 12):m.end() + 12]
                    if not (un and un.search(ctx)):
                        F.add('S1', p.get('level', 'error'), uid, f'{p["id"]}: {p.get("fix", "")}', ctx)
        for rx in LP.get('fourth_wall', []):
            for t in pools['prose']:
                for m in re.finditer(rx, t, re.I):
                    F.add('S2', 'error', uid, 'fourth-wall narration; state the subject, not how the book was made or scoped', t[max(0, m.start() - 12):m.end() + 12])
        # prose craft: badges, register, openers, positional references, avoided synonyms
        for blk in prose_blocks(s):
            for bd in blk.find(lambda n: is_c(n, 'badge')):
                after = blk.html().split(bd.html(), 1)[-1]
                if re.search(r'[^\W\d_]{2,}', re.sub(r'<[^>]+>', '', after)):
                    F.add('O2', 'warn', uid, 'badge in mid-paragraph reads into the next words; put it at the end of the paragraph or caption', vis(blk)[:50])
        rg = LP.get('register') or {}
        reg = (rg.get('forms') or {}).get(P.book.get('register') or rg.get('default'))
        if reg:
            for c in own:
                for n in c.find(lambda n: n.tag == 'li' or n.get('data-p') in ('why', 'lo', 'hi')):
                    t = re.sub(r'\s+', ' ', n.text(lambda x: x.get('data-p') == 'why' and x is not n)).strip()
                    if t and re.search(reg, t) and not n.up(lambda p: p.get('data-quote') is not None):
                        F.add('R1', 'warn', uid, rg['fix'], t[-30:])
                        break
        oe = reg and rg.get('option_end')
        if oe:
            for c in own:
                for li in opts(c):
                    t = re.sub(r'\s+', ' ', li.text(lambda x: x.get('data-p') == 'why')).strip().rstrip('.')
                    if re.search(oe['bad'], t) and not re.search(oe['ok'], t):
                        F.add('R1', 'warn', uid, oe['fix'], t[-20:])
                        break
        pt = LP.get('particles')
        for blk, t in blocks_txt if pt else []:
            for m in re.finditer(r'([' + native(LP) + r'])(' + pt['after_consonant'] + r')(?=[\s.,?!)」’”]|$)', t):
                if final_sound(m.group(1), LP) in ('c', 'l'):
                    F.add('T1', 'error', uid, f'particle {m.group(2)} after a syllable with a final consonant', t[max(0, m.start() - 10):m.end() + 4])
        ops = {}
        for c in own:
            for y in c.find(lambda n: n.get('data-p') == 'why'):
                ops.setdefault(vis(y)[:6], []).append(vis(y))
        for blk in prose_blocks(s):
            if blk.tag == 'p' and not blk.up(lambda p: is_c(p, *CARDS)) and not (blk.get('data-p') and blk.up(lambda p: is_c(p, 'note'))):  # note fields open on their pack labels
                ops.setdefault(vis(blk)[:6], []).append(vis(blk))
        ends = {}
        for c in own:
            for y in c.find(lambda n: n.get('data-p') == 'why'):
                for k_ in {re.sub(r'[.\s]+$', '', x)[-5:] for x in sentences(vis(y))}:
                    ends.setdefault(k_, []).append(1)
        nwhy = sum(1 for c in own for y in c.find(lambda n: n.get('data-p') == 'why'))
        for k, v in ends.items():
            if len(k) >= 4 and nwhy >= 8 and len(v) / nwhy > 0.25:
                F.add('L4', 'warn', uid, f'{len(v)} of {nwhy} feedback lines use the same sentence ending; open on the fact that breaks the belief instead of a formula', k)
        for k, v in ops.items():
            if len(k) >= 4 and len(v) > P.common['opener_max'] + 1:
                F.add('L4', 'warn', uid, f'{len(v)} paragraphs or feedback lines open the same way; vary the openings', k)
        pr = LP.get('pos_ref')
        for _, t in blocks_txt:
            if pr and re.search(pr, t):
                F.add('F6', 'warn', uid, 'prose points at a frame by position; frames play on their own, so name what the frame shows', re.search(pr, t).group(0))
        for c in (list(P.C.values()) + [dict(term=t_['use'], avoid=t_.get('avoid', [])) for t_ in P.d.get('terms', [])]) if role != 'ref' else []:
            for bad in c.get('avoid', []):
                for t in [x for _, x in blocks_txt] + labels:
                    t = re.sub(re.escape(c['term']) + r'\([^)]*\)', c['term'], t)
                    if re.search(r'(?<!\w)' + re.escape(bad), t):
                        F.add('S4', 'warn', uid, f'"{bad}" is an avoided form of {c["term"]}', t[max(0, t.find(bad) - 12):t.find(bad) + 20])
                        break
        for _, t in blocks_txt:
            w = t.split()
            for i in range(len(w)):
                for n in (1, 2, 3):
                    wa, wb = w[i:i + n], w[i + n:i + 2 * n]
                    if len(wb) == n and not wa[-1].endswith((',', '.')) and [x.strip('.,').lower() for x in wa] == [x.strip('.,').lower() for x in wb] and all(re.fullmatch(r'[^\W\d_]{2,}', x.strip('.,')) for x in wa):
                        F.add('L5', 'warn', uid, 'a word or phrase repeats; check a literal word beside a ref that fills in the same word', ' '.join(w[max(0, i - 2):i + 2 * n + 1]))
        cn = P.d.get('canon') or {}
        kinds, vals = cn.get('kinds') or {}, [str(v) for v in (cn.get('values') or {}).values()]
        if kinds:
            code = [x.text() for x in s.find(lambda n: n.tag == 'pre')]
            seen = set()
            for t in [x for _, x in blocks_txt] + labels + code:
                for k, rx in kinds.items():
                    try:
                        ms = list(re.finditer(rx, t))
                    except re.error:
                        continue
                    for m in ms:
                        v = m.group(0)
                        if v not in seen and not any(v == x or v in x for x in vals):
                            seen.add(v)
                            F.add('C1', 'warn', uid, f'{k} {v} is not a canon value; declare it in canon.values or use the declared one', t[max(0, m.start() - 16):m.end() + 16])
        sets_ = [c for c in own if len(opts(c)) >= 3 and not ol_has_order(c)]
        if len(sets_) >= 4:
            last = sum(1 for c in sets_ if any(li.has('data-ok') and opt_len(li) >= max(map(opt_len, opts(c))) for li in opts(c)))
            first = sum(1 for c in sets_ if any(li.has('data-ok') and opt_len(li) <= min(map(opt_len, opts(c))) for li in opts(c)))
            for n_, name in ((last, 'longest (last)'), (first, 'shortest (first)')):
                if n_ / len(sets_) > 0.5:
                    F.add('K1', 'warn', uid, f'the answer is the {name} option in {n_}/{len(sets_)} sets of this unit; a reader can answer by position')
        for c in own:
            for li in c.find(lambda n: n.tag == 'li' and n.get('data-cat')):
                if li.get('data-cat') in vis(li):
                    F.add('K10', 'warn', uid, f'a sort item names its own category ({li.get("data-cat")})', vis(li)[:40])
        vrx = LP.get('inline_def')
        if vrx:
            for blk, t in blocks_txt:
                if blk.up(lambda q: is_c(q, 'terms', 'exhibit')):
                    continue
                names = {m.group(1) for m in re.finditer(vrx, t)}
                if len(names) >= 3:
                    F.add('V1', 'warn', uid, 'named parts defined inline (' + ', '.join(sorted(names)) + '); give each an exact definition in a terms box', t[:60])
        for rx, fix in LP.get('translationese', []):
            for t in pools['prose']:
                for m in re.finditer(rx, t):
                    F.add('S3', 'warn', uid, f'translationese: {fix}', t[max(0, m.start() - 14):m.end() + 10])
        if pt:
            bad, nl = pt['wrong'], native(LP)
            for c in P.C.values():
                for form, fin in P.forms(c):
                    if fin not in bad:
                        continue
                    r = re.compile(re.escape(form) + r'(' + bad[fin] + r')(?![' + nl + '])')
                    for _, t in blocks_txt:
                        for m in r.finditer(t):
                            F.add('T1', 'error', uid, f'particle {m.group(1)} after {form} (final {fin})', t[max(0, m.start() - 10):m.end() + 6])
            raw = s.html()
            for m in re.finditer(r'<(a|span)\b([^>]*\bdata-(?:ref|v)="[^"]*"[^>]*)>([^<]*)</\1>(' + pt['all'] + r')(?![' + nl + '])', raw):
                fin = final_sound(html.unescape(m.group(3)).strip(), LP)
                if fin and re.fullmatch(bad[fin], m.group(4)):
                    F.add('T1', 'error', uid, f'particle {m.group(4)} after «{html.unescape(m.group(3)).strip()}» (final {fin})', html.unescape(m.group(3))[-20:] + m.group(4))
        if role not in ('map', 'ref'):
            for c in P.C.values():
                if P.idx.get(c['unit'], -1) <= P.idx[uid]:
                    continue
                forms = [f for f, _ in P.forms(c) if len(f) >= 2]
                for blk, t in blocks_txt:
                    if blk.up(lambda p: is_c(p, 'probe')):
                        continue
                    hit = next((f for f in forms if re.search(r'(?<!\w)' + re.escape(f) + r'(?![A-Za-z])', t)), None)
                    if hit and not blk.find(lambda n: n.get('data-ref') in (c['id'], c['unit'])):
                        F.add('O1', 'warn', uid, f'{hit} used before its home {c["unit"]} without a link', t[:80])
                        break
        for sym in P.d['symbols']:
            sc = sym.get('scope')
            pats = [sym['tex']] + list(sym.get('forms', []))
            if sc and uid not in sc and not any(x['tex'] == sym['tex'] and (not x.get('scope') or uid in x['scope']) for x in P.d['symbols'] if x is not sym):
                if any(re.search(r'(?<![A-Za-z\\_^])(?<!_\{)(?<!\^\{)' + re.escape(f) + r'(?![A-Za-z])', TEXTISH.sub('', t)) for f in pats for t in texs):
                    F.add('M1', 'warn', uid, f'{sym["tex"]} used outside its scope')
            if sym.get('asym'):
                sep = r'(?:\\\||\\parallel|\|\||∥|\\mid|,)'
                for f in pats:
                    tx = re.escape(f)
                    arg = r'\s*(?:\\left)?\(([^()]*?)' + sep + r'([^()]*?)(?:\\right)?\)'
                    rx = re.compile(tx + arg + r'\s*=\s*' + tx + arg)
                    for t in texs:
                        for m in rx.finditer(t):
                            a1, b1, a2, b2 = (m.group(i).strip() for i in range(1, 5))
                            if a1 == b2 and b1 == a2 and a1 != b1:
                                F.add('M2', 'error', uid, f'asymmetric {f} written as a symmetric equality', m.group(0))
        for t in texs if native(LP) else []:
            for m in re.finditer(r'\\text\{([^}]*)\}', t):
                if len(re.findall('[' + native(LP) + ']', m.group(1))) > P.common['max_text_native']:
                    F.add('M3', 'warn', uid, 'long native-script text inside \\text{}; move it to prose', m.group(1)[:40])
        if not quick and role not in ('ref', 'catalog'):
            ss = [x for blk, t in blocks_txt if not blk.up(lambda p: is_c(p, 'gist', 'close', *CARDS)) for x in sentences(t)]
            if len(ss) >= 8:
                mean = sum(map(len, ss)) / len(ss)
                short = sum(1 for x in ss if len(x) < P.common['short_sentence']) / len(ss)
                if mean < P.common['mean_sentence'] or short > P.common['max_short_share']:
                    F.add('L2', 'warn', uid, f'choppy rhythm: mean {mean:.0f} chars, short share {short:.0%}')
            cl = next((x for x in blocks if is_c(x, 'close')), None)
            if cl is not None:
                tri = lambda t: {tuple(w[i:i + 3]) for w in [re.findall(r'\w+', t.lower())] for i in range(max(0, len(w) - 2))}
                a = tri(' '.join(x.text() for x in cl.kids if isinstance(x, Node) and x.tag == 'p'))
                for w in (x for x in blocks if is_c(x, 'warn')):
                    bb = tri(vis(w))
                    if a and bb and len(a & bb) / min(len(a), len(bb)) > P.common['overlap']:
                        F.add('L3', 'warn', uid, 'summary repeats a warn box')
    if not unit:
        pos = [(p_, n_) for p_, n_ in kstat['pos'] if n_ >= 3]
        if len(pos) >= 8:
            for name, sel in (('last (longest)', lambda p_, n_: p_ == n_ - 1), ('first (shortest)', lambda p_, n_: p_ == 0)):
                hit = sum(1 for p_, n_ in pos if sel(p_, n_))
                exp = sum(1 / n_ for _, n_ in pos)
                if hit > 1.5 * exp + 1:
                    F.add('K1', 'error', '-', f'answer sits {name} in {hit}/{len(pos)} sets (expected about {exp:.0f}); a reader can answer by position')
        two = [p_ for p_, n_ in kstat['pos'] if n_ == 2]
        if len(two) >= 8 and not 0.3 <= sum(two) / len(two) <= 0.7:
            F.add('K1', 'error', '-', f'in two-way steps the answer is the longer one in {sum(two)}/{len(two)}; balance them')
        if len(set(kstat['nopts'])) > 1:
            F.add('K7', 'warn', '-', f'option counts vary across cards ({sorted(set(kstat["nopts"]))}); keep one count in a book')
        if LP['code'] != 'en':
            for k in INLINE_STRINGS:
                if re.search(r'[A-Za-z]{2,}', re.sub(r'\{\w+\}', '', str(P.s.get(k, '')))):
                    F.add('S5', 'warn', '-', f'string {k} lands inside {P.book["lang"]} prose but is English; set it in lang/<code>.json or book.strings', P.s.get(k))
            en_s = pack('en')['strings']
            eng = sorted(k for k, v in en_s.items() if isinstance(v, str) and re.search(r'[A-Za-z]{2,}', v) and P.s.get(k) == v)
            if eng:
                F.add('S5', 'warn', '-', f'{len(eng)} reader strings fall back to English; add them to lang/{LP["code"]}.json or book.strings', ', '.join(eng[:8]))
            for k in ('grades', 'badges'):
                if any(re.search(r'[A-Za-z]{3,}', str(x)) for x in P.s.get(k, [])):
                    F.add('S5', 'warn', '-', f'{k} print inside the prose but are English', ', '.join(map(str, P.s.get(k))))
        for grp in LP.get('stem_registers', []):
            ends = {m for m in kstat['stem_ends'] if m in grp}
            if len(ends) > 1:
                F.add('R1', 'warn', '-', f'stems end in several registers ({", ".join(sorted(ends))}); pick one', '')
        lv = [x for x in kstat['levels'] if x]
        if len(lv) >= 8 and sum(1 for x in lv if x in LEVELS[2:]) / len(lv) < P.common['apply_share']:
            F.add('K8', 'warn', '-', f'apply-or-higher cards are {sum(1 for x in lv if x in LEVELS[2:])}/{len(lv)}; want {P.common["apply_share"]:.0%}')
        if len(lv) >= 8 and len(set(kstat['diffs']) & {'1', '2', '3'}) < 3:
            F.add('K8', 'warn', '-', 'difficulties 1, 2 and 3 should all appear')
        if pol['interaction'] == 'full' and pol['scale'] != 'page':
            for k in ('order', 'estimate', 'custom'):
                if k not in kstat['tasks']:
                    F.add('K8', 'warn', '-', f'no {k} task in the book; arrangement, approximation and a domain-specific manipulation each appear at least once')
        mv = kstat['moves']
        if len(mv) >= 8 and mv.count('compute') / len(mv) > 0.4:
            F.add('K6', 'warn', '-', f'compute is {mv.count("compute")}/{len(mv)} of card moves; test the idea, not the arithmetic')
    if not unit:
        cite = {}
        for uid_, sec_ in secs.items():
            for nt in sec_.find(lambda n: is_c(n, 'note')):
                for m in re.finditer(r'([A-Z][A-Za-z\-]+)(?:[^()]{0,40}?)[,(]\s*((?:19|20)\d\d)', vis(nt)):
                    cite.setdefault(m.group(1) + ' ' + m.group(2), set()).add(uid_)
        for k, us in cite.items():
            if len(us) > 1 and P.U.get(sorted(us)[0], {}).get('role') != 'ref':
                F.add('L3', 'warn', '-', f'study {k} has notes in {len(us)} units; give it one home and refer to it elsewhere in a clause', ', '.join(sorted(us)))
    if not quick and not unit:
        seen = {}
        for uid, s in secs.items():
            if P.U.get(uid, {}).get('role') == 'ref':
                continue
            for blk in prose_blocks(s):
                if blk.up(lambda p: p.get('data-src')):
                    continue
                for x in sentences(blk.text(lambda n: NO_MATH(n) or n.has('data-v'))):
                    k = re.sub(r'\W', '', x)
                    if len(k) >= P.common['repeat_min']:
                        if k in seen and seen[k] != uid:
                            F.add('L3', 'warn', uid, f'sentence repeated from {seen[k]}', x[:80])
                        seen.setdefault(k, uid)
    notes = {n.get('id'): n for n in root.find(lambda n: is_c(n, 'note') and n.get('id'))}
    for u in P.live:
        s = secs.get(u['id'])
        if s is None or (unit and u['id'] != unit):
            continue
        check_alt(F, u['id'], s, LP.get('alt_words') or P.common['alt_words'])
        check_markup(F, u['id'], book_src)
        check_bare_alts(F, u['id'], s)
        if u['role'] == 'ref':
            continue
        own = [c for c in s.find(lambda n: is_c(n, *CARDS)) if not c.get('data-src') and not c.up(lambda p: p.get('data-src'))]
        check_cards(F, u['id'], s, own, LP, P)
        check_sections(F, u['id'], s, LP, P)
        check_evidence(F, u['id'], s, LP, P, notes)
    if not unit:
        check_book(F, P, secs, LP)
        bare = {}
        for c in P.C.values():
            if not c.get('aliases') and P.U.get(c['unit'], {}).get('status') != 'planned':
                bare.setdefault(c['unit'], []).append(c['term'])
        for uid, ts in bare.items():
            F.add('G3', 'warn', uid, f'{len(ts)} concepts have no aliases; add the forms readers search for (abbreviations, the source-language term, common synonyms)', ', '.join(ts))
    from .catalog import lint_findings
    lint_findings(d, P, F, unit)
    return settle(P, F, unit)

# ---------------------------------------------------------------- figure alt, evidence, card fairness, case consistency

NUM = re.compile(r'(?<![A-Za-z0-9_.,-])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![A-Za-z0-9_,])|(?<![A-Za-z0-9_.,-])\d+(?:\.\d+)?(?![A-Za-z0-9_,]\d)')
PROPER = re.compile(r'(?:(?<=[^\s.!?:]\s)|(?<=[(\[“"‘\'/]))[A-Z][A-Za-z]+(?:[- ][A-Z][A-Za-z]+)*')  # a capitalised word not opening a sentence
EXHIBIT = lambda n: is_c(n, 'exhibit') or n.tag in ('figure', 'svg', 'img', 'pre', 'table', 'blockquote') or n.has('data-quote')


def norm_num(v):
    v = v.replace(',', '')
    return v.rstrip('0').rstrip('.') if '.' in v else v


def concrete(t):
    """Numbers and Latin proper nouns in a text: how concrete an option is."""
    return len(NUM.findall(t)) + len(PROPER.findall(t))


def facts_of(t):
    """Checkable tokens of a text: numbers (normalised) and Latin names (capitalised words with lowercase letters)."""
    return {norm_num(m.group(0)) for m in NUM.finditer(t)} | {m.group(0).lower() for m in PROPER.finditer(t) if len(m.group(0)) >= 3 and not m.group(0).isupper()}


def derived(x, given):
    """Whether number x follows from the given numbers by one step (sum, difference, product, ratio, percent, halving)."""
    try:
        v, g = float(x), [float(a) for a in given if re.fullmatch(r'\d+(?:\.\d+)?', a)][:60]
    except ValueError:
        return True
    near = lambda a: abs(a - v) <= max(0.02 * abs(v), 0.011)
    for a in g:
        if any(near(y) for y in (a, a * 100, a / 100, a / 2, a * 2, a - 1, a + 1, 100 - a, 1 - a)):
            return True
        for b in g:
            if any(near(y) for y in (a + b, a - b, a * b) + ((a / b,) if b else ())):
                return True
    return False


def math_text(n):
    """Visible text of a node with TeX kept as $...$."""
    out = []
    for k in n.kids:
        if isinstance(k, str):
            out.append(k)
        elif k.has('data-m'):
            out.append('$' + (k.get('data-tex') or k.text()) + '$')
        elif not NO_MATH(k):
            out.append(math_text(k))
    return ''.join(out)


def section_of(s):
    """{id(node): n}: the section (h3 to h3, 0 before the first) of every node of a unit."""
    out, k = {}, 0
    for n in s.walk():
        if n.tag == 'h3' and not n.up(lambda p: p is not s and p.get('data-c') is not None):
            k += 1
        out[id(n)] = k
    return out


OPT_END = {'p', 'li', 'dt', 'dd', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot', 'option', 'colgroup', 'caption'}


class _Bal(HTMLParser):
    """Counts start and end tags; an element left open at the end, or an end tag with no start, is a problem."""
    def __init__(self, line0=1):
        super().__init__(convert_charrefs=False)
        self.net, self.stack, self.bad, self.line0 = {}, [], [], line0

    def _bid(self):
        for t, a, _ in reversed(self.stack):
            if a.get('id') or a.get('data-c'):
                return a.get('id') or a.get('data-c')
        return None

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        self.stack.append((tag, dict(attrs), self.getpos()[0] + self.line0 - 1))
        if tag not in OPT_END:
            self.net[tag] = self.net.get(tag, 0) + 1

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag not in OPT_END:
            self.net[tag] = self.net.get(tag, 0) - 1
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                for t, a, ln in self.stack[k + 1:]:
                    if t not in OPT_END:
                        self.bad.append(('unclosed', t, ln, a.get('id') or a.get('data-c') or self._bid()))
                del self.stack[k:]
                return
        self.bad.append(('stray', tag, self.getpos()[0] + self.line0 - 1, self._bid()))


VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


def tag_balance(frag, line0=1):
    """(net start-minus-end count per tag, problems [(kind, tag, line, block id)]) of one HTML fragment."""
    b = _Bal(line0)
    b.feed(frag)
    b.close()
    for t, a, ln in b.stack:
        if t not in OPT_END:
            b.bad.append(('unclosed', t, ln, a.get('id') or a.get('data-c')))
    return {k: v for k, v in b.net.items() if v}, sorted(b.bad, key=lambda x: x[2])


def check_markup(F, uid, raw):
    """G4: tags balance inside the unit's section; names the first unclosed (or stray) element and its block."""
    m = re.search(r'<section\b[^>]*\bdata-u="' + re.escape(uid) + r'"[^>]*>(.*?)</section>', raw, re.S)
    if not m:
        return
    net, bad = tag_balance(m.group(1), raw.count('\n', 0, m.start(1)) + 1)
    if bad:
        kind, tag, ln, bid = bad[0]
        what = f'<{tag}> opened at line {ln} is never closed' if kind == 'unclosed' else f'</{tag}> at line {ln} closes nothing'
        F.add('G4', 'error', uid, f'unbalanced tags: {what}' + (f' (block #{bid})' if bid else '') + (f'; {len(bad)} problems in all' if len(bad) > 1 else ''), f'<{tag}>')


def check_alt(F, uid, s, mn):
    """F8: every figure and image exhibit has an accessible name of mn+ words that is not an id; a frame counts its own caption."""
    nw = lambda t: len((t or '').split())
    for blk in s.find(lambda n: (n.tag == 'figure' and is_c(n, 'fig', 'frames')) or is_c(n, 'exhibit')):
        if blk.get('role') == 'img':
            alts = [(blk.get('aria-label') or '', '')]
        elif is_c(blk, 'frames'):
            alts = [((sv.get('aria-label') or ''), ' '.join(vis(p) for p in li.kids if isinstance(p, Node) and p.tag == 'p'))
                    for li in blk.find(lambda n: n.tag == 'li') for sv in [li.first(lambda n: n.tag == 'svg')] if sv is not None]
        else:
            alts = [(sv.get('aria-label') or '', '') for sv in blk.find(lambda n: n.tag == 'svg' and n.get('aria-hidden') != 'true' and not n.up(lambda p: p.tag == 'svg'))]
        for a, extra in alts:
            a = a.strip()
            if a and nw(a) < 2 and not (re.fullmatch(r'[\w.-]+', a) and re.search(r'[-_\d]', a)):  # a one-word label never names kind, encoding and point, whatever the caption adds
                F.add('F8', 'error', uid, f'alt "{a}" is one word; an alt names the kind, what it encodes and the point ({mn}+ words)', a)
                break
            bad = 'no alt' if not a else 'alt is an id' if re.fullmatch(r'[\w.-]+', a) and re.search(r'[-_\d]', a) else f'alt has {nw(a) + nw(extra)} words' if nw(a) + nw(extra) < mn else None
            if bad:
                F.add('F8', 'error', uid, f'{bad}; an alt names the kind, what it encodes and the point ({mn}+ words)', a or blk.get('data-c'))
                break


def check_bare_alts(F, uid, s):
    """F8: any role=img svg or img outside the exhibits needs a label of 2+ words."""
    for n in s.find(lambda n: (n.tag == 'svg' and n.get('role') == 'img') or n.tag == 'img'):
        a = (n.get('aria-label') if n.tag == 'svg' else n.get('alt')) or ''
        if len(a.split()) < 2 and not n.up(lambda p: (p.tag == 'figure' and is_c(p, 'fig', 'frames')) or is_c(p, 'exhibit', 'frames')):
            F.add('F8', 'error', uid, f'{n.tag} {"has no label" if not a.strip() else "label is one word"}; name the kind, what it encodes and the point', a or n.tag)
            break


def check_cards(F, uid, s, own, LP, P):
    """O4 unseen material, K10 concreteness parity, K12 whys bringing new facts, K13 options ending in a type label."""
    unseen, label = LP.get('unseen_ref'), LP.get('label_end')
    otext = lambda li: re.sub(r'\s+', ' ', li.text(lambda n: n.get('data-p') == 'why' or n.tag == 'svg' or n.has('data-m'))).strip()
    order = {id(x): i for i, x in enumerate(s.walk())}
    prose = [(order[id(b)], vis(b)) for b in prose_blocks(s) if not b.up(lambda p: is_c(p, *CARDS))]
    prose += [(order[id(t)], t.text()) for t in s.find(lambda n: n.tag == 'text') if not t.up(lambda p: is_c(p, *CARDS))]
    for c in own:
        what = f'{c.get("data-c")} {c.get("id") or ""}'.strip()
        q = c.first(lambda n: n.get('data-p') == 'q')
        stem = vis(q) if q is not None else ''
        shown = c.find(EXHIBIT)
        if unseen and q is not None and not shown and re.search(unseen, stem):
            F.add('O4', 'warn', uid, f'{what}: the stem points at material the card does not show; put it in an exhibit', re.search(unseen, stem).group(0))
        os_ = opts(c)
        if len(os_) < 3 or sum(1 for li in os_ if li.has('data-ok')) != 1:
            continue
        ok = next(li for li in os_ if li.has('data-ok'))
        okt, wr = otext(ok), [li for li in os_ if li is not ok]
        oc, wc = concrete(okt), [concrete(otext(li)) for li in wr]
        if oc >= 2 and not any(li.find(EXHIBIT) for li in os_) and max(wc) <= oc - 2:
            F.add('K10', 'warn', uid, f'{what}: the answer carries {oc} numbers or names, the wrong options at most {max(wc)}; make rivals as concrete', okt[:60])
        if label and any(re.search(label, t) for t in [okt] + [otext(li) for li in wr]):
            F.add('K13', 'warn', uid, f'{what}: an option ends in a label for its type of answer; state the move itself', next(t for t in [okt] + [otext(li) for li in wr] if re.search(label, t))[-30:])
        seen = facts_of(' '.join([stem, okt, vis(ok)] + [otext(li) for li in wr] + [x.text() + ' ' + (x.get('aria-label') or '') for x in shown] + [t for i, t in prose if i < order[id(c)]]))
        for li in wr:
            y = li.first(lambda x: x.get('data-p') == 'why')
            yt = vis(y) if y is not None else ''
            calc = {norm_num(m) for m in re.findall(r'\d[\d,.]*(?=\s*[×x*/÷+=−-]\s*\d)|(?<=[×x*/÷+=−-])\s*\d[\d,.]*', yt)}
            new = sorted(f for f in facts_of(yt) - seen - calc if not (re.fullmatch(r'[\d.]+', f) and derived(f, (seen | calc | facts_of(yt)) - {f})))
            if new:
                F.add('K12', 'warn', uid, f'{what}: a wrong option\'s why rests on {", ".join(new[:3])}, which the stem, exhibit and prose before it never gave', yt[:60])
                break
    for ex in s.find(lambda n: is_c(n, 'ex')):
        t = ' '.join(vis(w) for w in ex.find(lambda n: is_c(n, 'worked')))
        if unseen and t and not ex.find(EXHIBIT) and re.search(unseen, t):
            F.add('O4', 'warn', uid, 'a worked step narrates material the reader cannot see; show it in an exhibit', re.search(unseen, t).group(0))


def check_sections(F, uid, s, LP, P):
    """U6 studies merged without case or frames; F9 a structure listed in one sentence with no figure; V2 formula before the terms box, symbols defined inline."""
    sec = section_of(s)
    by = {}
    for n in s.walk():
        by.setdefault(sec[id(n)], []).append(n)
    sep, item_max = LP.get('list_sep', r',\s+'), LP.get('list_item', 4)  # list_item: words per listed part
    for k, ns in by.items():
        figs = [n for n in ns if (n.tag == 'figure' and is_c(n, 'fig', 'frames')) or is_c(n, 'exhibit') or n.tag == 'table']
        first_card = next((i for i, n in enumerate(ns) if is_c(n, *CARDS)), len(ns))
        notes = [n for n in ns[:first_card] if is_c(n, 'note')]
        if len(notes) >= 3 and not any(is_c(n, 'frames', 'ex', 'step') for n in ns):
            F.add('U6', 'warn', uid, f'{len(notes)} studies before the section\'s first card and no frames or case; build the idea on a case before merging studies', vis(notes[0].first(lambda x: x.tag == 'summary') or notes[0])[:50])
        if not figs:
            for n in ns:
                if n.tag != 'p' or n.get('data-p') or n.up(lambda p: is_c(p, *CARDS, 'note', 'terms', 'exhibit') or p.tag in ('details', 'figure', 'svg')):
                    continue
                for st in sentences(vis(n)):
                    parts = re.split(sep, st)
                    if len(parts) >= 4 and all(0 < len(x.split()) <= item_max and not (LP.get('list_clause') and re.search(LP['list_clause'], x)) for x in parts[1:-1]):
                        F.add('F9', 'warn', uid, f'{len(parts)} parts listed in one sentence and no figure in its section; draw the structure', st[:70])
                        break
        terms = next((i for i, n in enumerate(ns) if is_c(n, 'terms')), None)
        if terms is not None:
            fm = next((n for n in ns[:terms] if is_c(n, 'eqp', 'drv', 'formal') and not n.up(lambda p: is_c(p, *CARDS))), None)
            if fm is not None:
                F.add('V2', 'warn', uid, 'a formula comes before the section\'s terms box; put the terms box first so every symbol is defined before use', vis(fm)[:60])
    rx = LP.get('symbol_def')
    if rx:
        for blk in prose_blocks(s):
            if blk.up(lambda p: is_c(p, 'terms', 'exhibit', *CARDS) or p.get('data-d') is not None):
                continue
            m = re.search(rx, math_text(blk))
            if m:
                F.add('V2', 'warn', uid, 'a symbol is defined in running prose; define it in a terms box before its first use', m.group(0)[:60])


def check_evidence(F, uid, s, LP, P, notes):
    """E1 uncited quantitative or causal sentences, E2 hedge stronger than the cited grade, E3 note fields."""
    grades = list(P.s.get('grades') or [])
    hedges = P.s.get('hedges') or {}
    if not hedges and LP.get('hedges') and grades:
        hedges = {g: LP['hedges'][min(i, len(LP['hedges']) - 1)] for i, g in enumerate(grades)}
    quant, causal = LP.get('quant'), LP.get('causal')
    cite = re.compile(r'\([^()]*\b(1[5-9]|20)\d\d[a-z]?\)|\b(' + '|'.join({LP['cite'], 'et al'}) + r')\b')
    for blk in prose_blocks(s):
        if blk.up(lambda p: is_c(p, *CARDS, 'note', 'aside', 'ex', 'step', 'terms', 'exhibit', 'fig', 'frames', 'gist', 'close') or p.tag in ('figure', 'details', 'svg') or p.get('data-d') is not None):
            continue
        cited = blk.find(lambda n: n.get('data-cite') is not None)
        badged = blk.find(lambda n: is_c(n, 'badge'))
        for st in sentences(vis(blk)):
            if not (cited or badged or cite.search(st) or re.search(r'(?<!\d)(?:1[5-9]|20)\d\d(?!\d)', st)) and ((quant and re.search(quant, st) and not (LP.get('quant_skip') and re.search(LP['quant_skip'], st))) or (causal and re.search(causal, st))):
                F.add('E1', 'warn', uid, 'a quantitative or causal claim with no data-cite or badge', st[:70])
        for a in cited:
            nt = notes.get(a.get('data-cite'))
            g = nt.get('data-grade') if nt is not None else None
            if nt is None:
                F.add('E2', 'warn', uid, 'data-cite names no note', a.get('data-cite'))
            elif g in grades:
                t = vis(blk)
                strong = [f for gg in grades[:grades.index(g)] for f in hedges.get(gg, [])]
                hit = next((f for f in strong if re.search(f, t)), None)
                if hit:
                    F.add('E2', 'warn', uid, f'"{hit}" claims more than a {g} note supports; use that grade\'s forms ({", ".join(hedges.get(g, [])[:3])})', t[:60])
    labels = P.s.get('note_parts') or {}
    loose = 0
    for nt in s.find(lambda n: is_c(n, 'note')):
        parts = {p.get('data-p'): p for p in nt.find(lambda n: n.get('data-p') in NOTE_PARTS)}
        if not parts:
            loose += 1
            for p in nt.find(lambda n: n.tag == 'p'):
                for k, lab in labels.items():
                    if vis(p).startswith(lab):
                        parts.setdefault(k, p)
        d = parts.get('design')
        dt = vis(d) if d is not None else ''
        if d is not None and d.get('data-p') != 'design' and LP.get('note_label'):  # a free-text note: the design runs to the next label
            dt = re.split(LP['note_label'], dt[len(labels['design']) + 1:])[0]
        if dt and LP.get('sample') and not re.search(LP['sample'], dt) and not (LP.get('no_sample') and re.search(LP['no_sample'], dt)):
            F.add('E3', 'warn', uid, 'a study note\'s design names no sample size', dt[:60])
        miss = [k for k in ('source', 'limits') if k not in parts]
        if miss and parts:
            F.add('E3', 'warn', uid, f'a study note has no {" or ".join(miss)} part; keep every field (p[data-p=source|limits])', vis(nt)[:50])
        src = parts.get('source')
        if src is not None and not src.find(lambda n: n.tag == 'a' and n.get('href')):
            F.add('E3', 'warn', uid, 'a study note\'s source has no link (URL or DOI)', vis(src)[:60])
    if loose:
        F.add('E3', 'warn', uid, f'{loose} notes keep design, finding, limits and source as free text; mark them p[data-p=design|found|limits|source] with a linked source and locator')


NOTE_PARTS = ('design', 'found', 'limits', 'source')


def check_book(F, P, secs, LP):
    """Across units: S6 one foreign name spelled two ways, C2 a case quantity with two values, C3 one case number written two ways, T3 list facts spliced before a particle."""
    nl = native(LP)
    if nl:
        pairs = {}
        for uid, s in secs.items():
            for blk in prose_blocks(s):
                for m in re.finditer(r'(?<![' + nl + r'])([' + nl + r']{2,})\(([A-Z][A-Za-z.\'’-]+(?: [A-Z][A-Za-z.\'’-]+)*)(?:,\s*(?:1[5-9]|20)\d\d[a-z]?)?\)', vis(blk)):
                    if not (LP.get('sentence_end') and re.search(LP['sentence_end'], m.group(1))):
                        pairs.setdefault(m.group(2).lower(), {}).setdefault(m.group(1), set()).add(uid)
        for latin, natives in pairs.items():
            if len(natives) > 1:
                F.add('S6', 'warn', sorted(set().union(*natives.values()))[0], f'{latin} is spelled {" / ".join(sorted(natives))}; keep one spelling', '; '.join(f'{k}: {", ".join(sorted(v))}' for k, v in sorted(natives.items())))
    cn = P.d.get('canon') or {}
    anchors = [str(v) for v in (cn.get('values') or {}).values()] + list(cn.get('names') or [])
    anchors += [w for w in re.findall(r'[A-Za-z][A-Za-z0-9]{2,}', str((P.d.get('project') or {}).get('name', ''))) if not w.isupper()]
    counters, hypo = LP.get('counters'), LP.get('hypothetical')
    if counters:
        lt = (nl or '') + 'A-Za-z'
        trip = re.compile(r'([' + lt + r']{2,})\s((?:' + NUM.pattern + r'))\s?(' + counters + r')(?![' + lt + r'])')
        vals, raws = {}, {}
        for uid, s in secs.items():
            if P.U.get(uid, {}).get('role') == 'ref':
                continue
            for blk in prose_blocks(s):
                case = blk.up(lambda p: is_c(p, 'step')) is not None
                for st in sentences(vis(blk)):
                    if not (case or any(a in st for a in anchors)) or (hypo and re.search(hypo, st)):
                        continue
                    for m in trip.finditer(st):
                        noun, raw, ctr = m.group(1), m.group(2), m.group(3)
                        vals.setdefault((noun, ctr), {}).setdefault(norm_num(raw), set()).add(uid)
                        raws.setdefault(norm_num(raw) + ctr, {}).setdefault(raw, set()).add(uid)
        for (noun, ctr), vs in vals.items():
            us = set().union(*vs.values())
            if len(vs) > 1 and len(us) > 1:
                F.add('C2', 'warn', sorted(us)[0], f'the case\'s {noun} … {ctr} has {len(vs)} values across units; keep one or say what changed', '; '.join(f'{v}: {", ".join(sorted(u))}' for v, u in sorted(vs.items())))
        fmt = (cn.get('format') or {}).get('thousands')
        for k, rs in raws.items():
            if len(rs) > 1:
                F.add('C3', 'warn', sorted(set().union(*rs.values()))[0], f'one case number written {len(rs)} ways ({" / ".join(sorted(rs))}); write it one way', k)
            for r in rs if fmt is not None else ():
                if len(norm_num(r).split('.')[0]) >= 4 and ((',' in r) != (fmt == ',')):
                    F.add('C3', 'warn', sorted(rs[r])[0], f'{r} breaks canon.format.thousands "{fmt}"', k)
    after = LP.get('list_splice')
    if after:
        for uid, s in secs.items():
            for m in re.finditer(r'<span\b[^>]*\bdata-v="([^"]*)"[^>]*>([^<]*)</span>(' + after + ')', s.html()):
                if re.search(r'[,、]', html.unescape(m.group(2))):
                    F.add('T3', 'warn', uid, f'fact {m.group(1)} is a list spliced before a particle; name the group in the sentence and list the items after it', html.unescape(m.group(2))[-30:] + m.group(3))


def report(F):
    for f in sorted(F, key=lambda f: ({'error': 0, 'warn': 1, 'info': 2}[f['level']], f['rule'], f['unit'])):
        print(f"{f['level']:5} {f['rule']:3} {f['unit']:14} {f['msg']}" + (f"  [{f['ev']}]" if f['ev'] else ''))
    c = {k: sum(1 for f in F if f['level'] == k) for k in ('error', 'warn', 'info')}
    refs = {}
    for f in F:
        ref = REF_OF.get(f['rule']) or REF_OF.get(f['rule'][0])
        if f['level'] != 'info' and ref:
            refs.setdefault(ref, set()).add(f['rule'])
    tail = '; '.join(f"{', '.join(sorted(r))} -> {p}" for p, r in sorted(refs.items()))
    print(f"-- {c['error']} errors, {c['warn']} warns, {c['info']} info" + (f"; read {tail}" if tail else ''))
    return 1 if c['error'] else 0
