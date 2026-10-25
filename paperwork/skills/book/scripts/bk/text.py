import collections, json, os, random, re
from .dom import BLOCKS, is_c, opts, parse, sentences, vis
from .build import CARDS
from .plan import Plan, PlanError
from .lang import pack

# ---------------------------------------------------------------- stats


def _choice_sets(d, units=None):
    """Every choice set in the built book, review clones excluded: (id, unit, kind, move, stem, [(ok, text)])."""
    root = parse(open(os.path.join(d, 'book.html'), encoding='utf-8').read())
    out = []
    clean = lambda n: re.sub(r'\s+', ' ', n.text(lambda x: x.get('data-p') in ('why', 'fix') or x.tag == 'svg')).strip()
    for sec in root.find(lambda n: n.tag == 'section' and n.get('data-u')):
        uid = sec.get('data-u')
        if units and uid not in units:
            continue
        for c in sec.find(lambda n: is_c(n, 'ask', 'probe') and not n.get('data-src') and not n.up(lambda p: p.get('data-src'))):
            kind, cid, mv = c.get('data-c'), c.get('id') or f'{c.get("data-c")}-{uid}', c.get('data-move')
            q = c.first(lambda n: n.get('data-p') == 'q')
            os_ = opts(c)
            if os_:
                out.append((cid, uid, kind, mv, re.sub(r'^\d+\.\s*', '', clean(q)) if q else '', [(li.has('data-ok'), clean(li)) for li in os_]))
    return out


def cards(d, units=None, out='cards.json', score=None):
    """Blind-solving bundle: options shuffled, keys apart; with --score, grade a solver's picks against the key."""
    sets = _choice_sets(d, units)
    keyp = os.path.join(d, os.path.splitext(out)[0] + '.key.json')
    if score:
        key = json.load(open(keyp, encoding='utf-8'))
        ans = json.load(open(score, encoding='utf-8'))
        if isinstance(ans, list):  # [{"id": ..., "pick": ..., "cue": ...}]
            ans = {a.get('id'): a for a in ans if isinstance(a, dict)}
        n = hit = 0
        chance = 0.0
        cue, per = 0, {}
        for cid, k in key.items():
            if cid not in ans:
                continue
            a = ans[cid] if isinstance(ans[cid], dict) else {'pick': ans[cid]}
            n += 1
            chance += 1 / k['n']
            u = per.setdefault(k.get('unit', '-'), [0, 0])
            u[1] += 1
            if a.get('pick') == k['key']:
                hit += 1
                tag = a.get('cue', '?')
                cue += tag == '?'
                u[0] += tag in ('cue', 'guess')
                print(f'solved {cid}: {tag}')
        print(f'-- {hit}/{n} of {len(key)} sets solved without the text; chance {chance:.1f}; excess {hit - chance:+.1f}')
        if n < len(key):
            print(f'error: {len(key) - n} sets have no answer; answer every set')
            return 1
        if cue:
            print('error: tag every solved pick as {"pick": ..., "cue": "knowledge|cue|guess"}')
            return 1
        bad = {u: f'{c}/{t}' for u, (c, t) in per.items() if c > 0.2 * t}
        for u, (c, t) in per.items():
            print(f'{u}: {c}/{t} solved by cue or guess' + ('  FAIL over 20%' if u in bad else ''))
        return 1 if bad else 0
    ids = [x[0] for x in sets]
    if len(ids) != len(set(ids)):
        raise PlanError(f'duplicate card ids: {sorted({i for i in ids if ids.count(i) > 1})}; rebuild')
    rnd = random.Random(7)
    pub, key = [], {}
    for cid, uid, kind, mv, stem, os_ in sets:
        idx = list(range(len(os_)))
        rnd.shuffle(idx)
        letters = 'abcdefgh'
        pub.append({'id': cid, 'unit': uid, 'kind': kind, 'move': mv, 'stem': stem, 'options': {letters[j]: os_[i][1] for j, i in enumerate(idx)}})
        key[cid] = {'key': letters[next(j for j, i in enumerate(idx) if os_[i][0])], 'n': len(os_), 'unit': uid}
    os.makedirs(os.path.dirname(os.path.join(d, out)) or '.', exist_ok=True)
    json.dump(pub, open(os.path.join(d, out), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(key, open(keyp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(pub)} choice sets -> {out}; key -> {os.path.basename(keyp)} (do not give it to the solver; score with the same --out); answers as {{id: {{"pick": letter, "cue": "knowledge|cue|guess"}}}}')
    return 0


FIG_KINDS = ('fig', 'frames', 'exhibit', 'terms')
ONLY = ('prose', 'stems', 'cards', 'claims', 'figs')  # stems: prose whole, cards by stem, figures by caption


def _flat(n, skip=lambda x: False):
    out = []
    for k in n.kids:
        if isinstance(k, str):
            out.append(k)
        elif k.tag == '#comment' or k.tag in ('svg', 'script', 'style') or skip(k):
            continue
        elif k.has('data-m'):
            out.append('$' + (k.get('data-tex') or k.text()) + '$')
        else:
            out.append(_flat(k, skip))
            if k.tag in BLOCKS:
                out.append(' ')
    return re.sub(r'\s+', ' ', ''.join(out)).strip()


def _ctx(b):
    """'card', 'fig' or 'prose': the region a node sits in (a figure inside a card counts as both; card wins for --only cards)."""
    me = lambda n: is_c(n, *CARDS)
    fg = lambda n: n.tag == 'figure' or is_c(n, *FIG_KINDS)
    return {'card': me(b) or b.up(me) is not None, 'fig': fg(b) or b.up(fg) is not None}


def _keep(b, only):
    if not only or only in ('claims', 'stems'):
        return True
    c = _ctx(b)
    return {'prose': not c['card'] and not c['fig'], 'cards': c['card'], 'figs': c['fig']}[only]


CLAIM_NUM = re.compile(r'(?<![\w.-])\d[\d,.]*(?:e-?\d+)?')  # a number not inside an identifier such as run-0425


def is_head(b, sec):
    """A section heading of a unit: an h3 outside every component."""
    return b.tag == 'h3' and b.up(lambda p: p is not sec and p.get('data-c') is not None) is None


def claim_sents(t, b, lang):
    """Sentences of a leaf that state checkable things: a number, a citation, a linked source, a fact value, a badge or an absolute; questions are skipped."""
    facts = [vis(v) for v in b.find(lambda x: x.has('data-v'))]
    src = bool(b.find(lambda x: x.tag == 'a' and (x.get('href') or '').startswith('http'))) or bool(b.find(lambda x: x.get('data-c') == 'badge'))
    L = pack(lang)
    cue = re.compile(L['claim_cue'])
    cite = re.compile(r'\([^()]*\b(1[5-9]|20)\d\d[a-z]?\)|\b(' + '|'.join({L['cite'], 'et al'}) + r')\b')
    badges = {vis(x).strip() for x in b.find(lambda x: x.get('data-c') == 'badge')}
    for s_ in sentences(t) or ([t] if t else []):
        if s_.rstrip().endswith('?') or s_.strip() in badges:
            continue
        bare = re.sub(r'\s\d{1,2}\.$', '', re.sub(r'\$[^$]*\$', '', s_))  # a list number is not a claim
        if src or CLAIM_NUM.search(bare) or cite.search(s_) or cue.search(s_) or any(f and f in s_ for f in facts):
            yield s_


WRITER_META = {}


def emit_text(sec, only=None, lang='en', out=print, section=None):
    """Flat reviewer text of a node: blocks in order, components marked, math as $TeX$, right options starred, wrong options' why indented.
    section=N keeps the Nth section only (0 = before the first section heading); out may take (line, n) when it has two parameters."""
    leaf = lambda b: b.tag in ('p', 'li', 'figcaption', 'summary', 'td', 'dt', 'dd', 'h2', 'h3', 'h4') and not b.up(lambda p: p.tag in ('svg', 'summary'))
    k = [0]
    two = getattr(out, '__code__', None) is not None and out.__code__.co_argcount == 2
    put = out
    keep = (lambda n: True) if section is None else (lambda n: n in section) if isinstance(section, (set, list, tuple, range)) else (lambda n: n == section)
    out = lambda line: (put(line, k[0]) if two else put(line)) if keep(k[0]) else None
    for b in sec.walk():
        if b is not sec and is_head(b, sec):
            k[0] += 1
        if not _keep(b, only):
            continue
        c = b.get('data-c')
        if only != 'claims' and c in CARDS + ('defn', 'warn', 'note', 'aside', 'step', 'ex', 'frames', 'fig', 'close', 'gist', 'drv', 'exhibit', 'terms') and not b.get('data-src'):
            meta = ' '.join(x for x in (b.get('id'), b.get('data-kind'), b.get('data-move'), b.get('data-level'), b.get('data-diff') and 'diff ' + b.get('data-diff'), b.get('data-grade'), b.get('data-variant-of') and 'variant of ' + b.get('data-variant-of'), b.get('data-demo') and 'demo ' + b.get('data-demo')) if x)
            out(f'[{c}{" " + meta if meta else ""}]')
            for line in WRITER_META.get(b.get('id'), []) if c in CARDS and only in (None, 'cards') else []:  # slots entries: label and rival metadata for reviewers
                out(line)
        if b.tag == 'pre' and not b.up(lambda p: p.tag == 'svg'):
            if only != 'claims':
                out('[code]\n' + b.text().rstrip() + '\n[/code]')
            continue
        if b.tag == 'svg':
            labels = [re.sub(r'\s+', ' ', t.text()).strip() for t in b.find(lambda x: x.tag == 'text')]
            if only == 'claims':
                labels = [x for x in labels if CLAIM_NUM.search(x)]
                blk = b.up(lambda p: p.get('id') or p.get('data-c'))
                if labels:
                    out(f'[{(blk.get("id") or blk.get("data-c")) if blk else "svg"} labels] ' + ' | '.join(labels))
            elif labels and only != 'stems':
                out('    [svg labels] ' + ' | '.join(x for x in labels if x))
            continue
        if not (leaf(b) or b.get('data-p') == 'why') or b.up(lambda p: p.get('data-p') == 'why'):
            continue
        if only == 'stems' and b.tag != 'svg':  # prose whole; cards by stem; figures by caption
            cx = _ctx(b)
            in_terms = b.tag in ('dt', 'dd') and b.up(lambda p: is_c(p, 'terms')) is not None  # terms entries print so a reviewer can judge definition, unit and value
            if (cx['card'] and leaf(b) and not (b.get('data-p') == 'q' or b.up(lambda p: p.get('data-p') == 'q'))) or (cx['fig'] and not cx['card'] and leaf(b) and b.tag != 'figcaption' and not in_terms) or b.get('data-p') == 'why':
                continue
        if b.get('data-p') == 'why' and only not in ('claims', 'stems'):
            out('    why: ' + _flat(b))
            continue
        if b.tag == 'li' and b.find(lambda x: x.tag in ('p', 'li') and not x.get('data-p') == 'why'):
            continue
        t = _flat(b, lambda x: x.get('data-p') == 'why') if b.get('data-p') != 'why' else _flat(b)
        if only == 'claims' and b.up(lambda p: p.get('data-d') is not None):
            continue
        if only == 'claims':  # checkable statements in prose, cards (stems, options, whys) and captions
            blk = b.up(lambda p: p.get('id') or p.get('data-c'))
            where = (blk.get('id') or blk.get('data-c')) if blk else b.tag
            where += ' why' if b.get('data-p') == 'why' else ' answer' if b.has('data-ok') else ''
            ab = pack(lang).get('absolute')
            for s_ in claim_sents(t, b, lang):
                m_ = ab and re.search(ab, s_)
                out(f'[{where}{" absolute: " + m_.group(0) + "; search for a counterexample" if m_ else ""}] {s_}')
            continue
        if b.get('data-p') == 'why':
            continue
        if b.get('data-why'):
            t += '  (why if misplaced: ' + b.get('data-why') + ')'
        if not t:
            continue
        tag = '# ' if b.tag == 'h2' else '## ' if b.tag in ('h3', 'h4') else '* ' if b.has('data-ok') else '- ' if b.tag in ('li', 'dt') else '    ' if b.tag == 'dd' else '> ' if c == 'key' else ''
        out(tag + t)


def unit_sections(sec):
    """[(n, heading, concepts)] of a unit's sections; section 0 runs from the unit start to the first section heading."""
    out, k = [[0, '', []]], 0
    for b in sec.walk():
        if b is not sec and is_head(b, sec):
            k += 1
            out.append([k, _flat(b), []])
        elif b.get('data-c') == 'defn' and b.get('data-concept'):
            out[k][2].append(b.get('data-concept'))
    return [tuple(x) for x in out]


def text_slices(d, only=None, units=None, root=None):
    """{unit: [(n, heading, concepts, chars)]}: the size of each section's `text --only` view, for sizing review batches."""
    root = root or parse(open(os.path.join(d, 'book.html'), encoding='utf-8').read())
    lang = str(Plan(os.path.join(d, 'book.json')).book.get('lang', 'en'))
    res = {}
    for sec in root.find(lambda n: n.tag == 'section' and n.get('data-u')):
        uid = sec.get('data-u')
        if units and uid not in units:
            continue
        size = collections.Counter()
        emit_text(sec, only, lang, lambda line, n: size.update({n: len(line) + 1}))
        res[uid] = [(n, h, cs, size[n]) for n, h, cs in unit_sections(sec)]
    return res


def sections(spec):
    """'2', '2-6' or '2,4' -> {2, ...}; None stays None."""
    if spec is None:
        return None
    want = set()
    for x in str(spec).split(','):
        a, _, z = x.partition('-')
        want.update(range(int(a), int(z or a) + 1))
    return want


def text(d, unit=None, only=None, section=None, concept=None):
    """Plain text of the built units for reviewers; --only narrows to prose, cards, claims or figures; --section or --concept to one section of --unit."""
    if (section is not None or concept) and not unit:
        raise PlanError('--section and --concept need --unit')
    root = parse(open(os.path.join(d, 'book.html'), encoding='utf-8').read())
    lang = str(Plan(os.path.join(d, 'book.json')).book.get('lang', 'en'))
    from .catalog import writer_meta
    WRITER_META.clear()
    WRITER_META.update(writer_meta(d))
    n = 0
    for sec in root.find(lambda n: n.tag == 'section' and n.get('data-u')):
        uid = sec.get('data-u')
        if unit and uid != unit:
            continue
        n += 1
        parts = unit_sections(sec)
        want = None
        if concept:
            hit = [k for k, _, cs in parts if concept in cs]
            if not hit:
                raise PlanError(f'no defn of {concept} in {uid}; sections: ' + '; '.join(f'{k} {h[:30]}' for k, h, _ in parts))
            want = {hit[0]}
        elif section is not None:
            want = sections(section)
            if not want <= set(range(len(parts))):
                raise PlanError(f'{uid} has sections 0-{len(parts) - 1}')
        head = (' sections ' + ', '.join(f'{k} {parts[k][1]}'.strip() for k in sorted(want))) if want else ''
        print(f'\n===== {uid}{head}' + (f' --only {only}' if only else ''))
        emit_text(sec, only, lang, section=want)
    if unit and not n:
        raise PlanError(f'unit {unit} not in book.html; build first')
    return 0


def stats(path, sel=None):
    root = parse(open(path, encoding='utf-8').read())
    if sel and sel.startswith('.'):
        pick = lambda n: sel[1:] in (n.get('class') or '').split()
    elif sel:
        pick = lambda n: n.tag == sel
    else:
        pick = lambda n: n.tag == 'section' and bool(n.get('data-u') or n.get('id'))
    secs = [n for n in root.find(pick) if not n.up(pick)]
    skip = lambda n: n.tag in ('svg', 'script', 'style', 'annotation') or n.has('data-m') or bool({'katex', 'katex-display'} & set((n.get('class') or '').split()))
    rows = []
    for s in secs:
        t = re.sub(r'\s+', ' ', s.text(skip)).strip()
        ss = sentences(t)
        rows.append(dict(unit=s.get('data-u') or s.get('id') or '?', chars=len(t), figs=len(s.find(lambda n: n.tag == 'figure')), svgs=len(s.find(lambda n: n.tag == 'svg')),
                         sent=len(ss), mean=round(sum(map(len, ss)) / len(ss)) if ss else 0))
    for r in rows:
        print(f"{r['unit']:20} chars {r['chars']:6}  figures {r['figs']:3}  svg {r['svgs']:3}  sentences {r['sent']:4}  mean {r['mean']:4}")
    if not rows:
        print('no units matched; pass --sel .CLASS or --sel TAG')
        return 1
    cs = sorted(r['chars'] for r in rows)
    q = lambda p: cs[min(len(cs) - 1, int(p * len(cs)))]
    print(f"-- {len(rows)} units; chars p10 {q(.1)} median {q(.5)} p90 {q(.9)}")
    return 0
