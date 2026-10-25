import html, json, os, re, subprocess, sys
from .const import LABELED, TEMPLATES, UI_KEYS
from .dom import Node, esc, is_c, parse, prose_blocks, read_js, vis
from .plan import Plan, PlanError, fact_text

# ---------------------------------------------------------------- chrome generators (pure functions of the plan)


def g_head(plan, u):
    n = plan.num[u['id']]
    k = '' if n is None else f'<p class="kicker">{esc(plan.st("kicker", n=n))}</p>'
    return f'<header data-d="head">{k}<h2>{esc(u["title"])}</h2></header>'


def g_pn(plan, u):
    seq = plan.live
    i = seq.index(u)
    a = f'<a href="#u-{seq[i - 1]["id"]}">{esc(plan.st("prev_unit"))} {esc(plan.label(seq[i - 1]["id"]))}</a>' if i > 0 else '<span></span>'
    b = f'<a href="#u-{seq[i + 1]["id"]}">{esc(plan.label(seq[i + 1]["id"]))} {esc(plan.st("next_unit"))}</a>' if i + 1 < len(seq) else '<span></span>'
    return f'<nav data-d="pn">{a}{b}</nav>'


def g_nav(plan):
    if plan.pol['scale'] == 'page':
        return ''
    out, cur, ref_started = [f'<nav data-d="nav" aria-label="{esc(plan.st("toc"))}"><ol>'], None, False
    for u in plan.units:
        if u['role'] == 'ref' and not ref_started:
            out.append('<li><hr></li>')
            ref_started = True
        if len(plan.parts) > 1 and u.get('part') in plan.part_by_id and u.get('part') != cur and u['role'] != 'ref':
            cur = u['part']
            no = next(i + 1 for i, p in enumerate(plan.parts) if p['id'] == cur)
            out.append(f'<li class="tp" style="color:var(--loc-{esc(cur)})">{esc(plan.st("part", n=no, name=plan.part_by_id[cur]["name"]))}</li>')
        n = plan.num[u['id']]
        inner = f'<span class="n">{"" if n is None else n}</span><span>{esc(u["title"])}</span>'
        out.append(f'<li><span>{inner}</span></li>' if u.get('status') == 'planned' else f'<li><a href="#u-{esc(u["id"])}">{inner}</a></li>')
    out.append('</ol></nav>')
    return ''.join(out)


def g_hero(plan):
    if plan.pol['scale'] == 'page':
        return ''
    b, chips = plan.book, ''
    if len(plan.parts) > 1:
        first = {}
        for u in plan.live:
            if u.get('part') and u['part'] not in first:
                first[u['part']] = u['id']
        chips = '<p class="chips">' + ''.join(f'<a href="#u-{first[p["id"]]}">{esc(p["name"])}</a>' for p in plan.parts if p['id'] in first) + '</p>'
    return f'<header data-d="hero"><p class="kicker">{esc(b.get("kicker", ""))}</p><h1>{esc(b.get("title", ""))}</h1><p class="lead">{esc(b.get("lead", ""))}</p>{chips}</header>'


MARK_SVG = {'fill': '<rect class="fill" x="2" y="3" width="30" height="12" rx="2"/>', 'line': '<line class="line" x1="2" y1="9" x2="32" y2="9"/>',
            'dash': '<rect class="line dash" x="2" y="3" width="30" height="12"/>', 'dot': '<circle class="fill" cx="17" cy="9" r="6"/>'}


def g_legend(plan):
    rows = ''.join(f'<li><svg viewBox="0 0 34 18" aria-hidden="true"><g class="lx-{esc(e["id"])}">{MARK_SVG.get(e["mark"], MARK_SVG["fill"])}</g></svg><span>{esc(e["meaning"])}</span></li>' for e in plan.lexicon_by_id.values())
    return f'<div data-d="legend"><h3>{esc(plan.st("legend"))}</h3><ul>{rows}</ul></div>'


def g_notation(plan):
    rows = ''.join(f'<tr><td><span data-m>{esc(s["tex"])}</span></td><td>{esc(s["meaning"])}</td></tr>' for s in plan.d['symbols'])
    return f'<div data-d="notation"><h3>{esc(plan.st("notation"))}</h3><div class="tw"><table><tbody>{rows}</tbody></table></div></div>'


# reader-page strings a language pack may lack; the pack (or book.strings) overrides each
READER_UI = {'search': 'Search terms and headings', 'nohit': 'No match', 'all': 'All frames', 'later': 'Behind a question above; answer it to open',
             'see': 'see', 'used_in': 'Used in'}


def rs(plan, k):
    return plan.s.get(k) or READER_UI[k]


def forms(c, key):
    """Plain strings of a concept's aliases or avoided forms (an alias may be {form, final})."""
    return [a.get('form') if isinstance(a, dict) else a for a in c.get(key, []) if (a.get('form') if isinstance(a, dict) else a)]


def concept_uses(plan):
    """concept id -> live unit ids whose prose cites it with data-ref, in reading order."""
    parts, out = read_units(plan.dir), {}
    for u in plan.live:
        for rid in re.findall(r'data-ref="([^"#]+)', parts.get(u['id'], '')):
            if rid in plan.concept_by_id and u['id'] not in out.setdefault(rid, []):
                out[rid].append(u['id'])
    return out


def g_glossary(plan):
    """Terms with gloss, home unit and the units that use them; aliases and avoided forms as see entries."""
    uses, items = concept_uses(plan), []
    live = lambda uid: uid in plan.unit_by_id and plan.unit_by_id[uid].get('status') != 'planned'
    for c in plan.concept_by_id.values():
        en = f' ({esc(c["en"])})' if c.get('en') and c['en'] != c['term'] else ''
        link = f' <a href="#u-{esc(c["unit"])}">{esc(plan.label(c["unit"]))}</a>' if live(c['unit']) else ''
        used = [u for u in uses.get(c['id'], []) if u != c['unit']]
        gu = f'<span class="gu">{esc(rs(plan, "used_in"))}: ' + ' · '.join(f'<a href="#u-{esc(u)}">{esc(plan.label(u))}</a>' for u in used) + '</span>' if used else ''
        items.append((c['term'].lower(), f'<dt id="g-{esc(c["id"])}">{esc(c["term"])}{en}</dt><dd>{esc(c.get("gloss", ""))}{link}{gu}</dd>'))
        for f in dict.fromkeys(forms(c, 'aliases') + forms(c, 'avoid')):
            if f != c['term'] and f != c.get('en'):
                items.append((f.lower(), f'<dt>{esc(f)}</dt><dd class="see">{esc(rs(plan, "see"))} <a href="#g-{esc(c["id"])}">{esc(c["term"])}</a></dd>'))
    return f'<div data-d="glossary"><h3>{esc(plan.st("glossary"))}</h3><dl>{"".join(h for _, h in sorted(items, key=lambda x: x[0]))}</dl></div>'


def g_terms(plan):
    """Search index of concepts for the reader page: term, english, aliases, avoided forms, home unit."""
    rows = [dict(id=c['id'], t=c['term'], en=c.get('en') or '', a=forms(c, 'aliases'), v=forms(c, 'avoid'), u='#u-' + c['unit']) for c in plan.concept_by_id.values() if c['unit'] in plan.unit_by_id and plan.unit_by_id[c['unit']].get('status') != 'planned']
    return json.dumps(rows, ensure_ascii=False).replace('</', '<\\/')


def g_tokens(plan):
    light, dark = [], []
    for e in plan.lexicon_by_id.values():
        light.append(f'--enc-{e["id"]}:{e["light"]}')
        dark.append(f'--enc-{e["id"]}:{e.get("dark", e["light"])}')
    for i, p in enumerate(plan.parts):
        h = p.get('hue', round(30 + 300 * i / max(1, len(plan.parts))))
        light.append(f'--loc-{p["id"]}:oklch(0.52 0.12 {h})')
        dark.append(f'--loc-{p["id"]}:oklch(0.76 0.10 {h})')
    cls = ''.join(f'.lx-{e["id"]}{{--c:var(--enc-{e["id"]})}}' for e in plan.lexicon_by_id.values())
    return (f':root{{{";".join(light)}}}@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{";".join(dark)}}}}}'
            f':root[data-theme="dark"]{{{";".join(dark)}}}{cls}')


MARKERS = {'legend': g_legend, 'notation': g_notation, 'glossary': g_glossary}
CARDS = ('probe', 'ask', 'task')


def before_text(sec, card, n):
    """The last n visible characters of prose before a card in its unit, other cards excluded."""
    order = {id(x): i for i, x in enumerate(sec.walk())}
    pos = order[id(card)]
    return ' '.join(vis(b) for b in prose_blocks(sec) if order[id(b)] < pos and not b.up(lambda p: is_c(p, *CARDS)))[-n:]






def ol_has_order(c):
    ol = c.first(lambda n: n.get('data-p') == 'opts')
    return ol is not None and ol.has('data-order')


def opt_shape(t, lang_pack):
    """'s' for a sentence ending, 'p' for a phrase; options of one card share one shape (packs with `sentence_end`)."""
    t = t.strip().rstrip('.')
    return 's' if lang_pack.get('sentence_end') and re.search(lang_pack['sentence_end'], t) else 'p'


def opt_len(li):
    """Visible length of an option without its why; inline math counts as 3."""
    return len(re.sub(r'\s+', ' ', li.text(lambda n: n.get('data-p') == 'why' or n.has('data-m'))).strip()) + 3 * len(li.find(lambda n: n.has('data-m') and not n.up(lambda p: p.get('data-p') == 'why')))


def dress(inner, plan, uid=''):
    """Build-time card dressing: options in ascending length unless data-order, card numbers per unit, aside and note tags."""
    root = parse(inner)
    for ol in root.find(lambda n: n.get('data-p') == 'opts' and not n.has('data-order')):
        lis = [k for k in ol.kids if isinstance(k, Node) and k.tag == 'li']
        ol.kids = sorted(lis, key=lambda li: (opt_len(li), sum(map(ord, li.text())) % 7))
    for i, c in enumerate(root.find(lambda x: is_c(x, *CARDS)), 1):
        c.attrs.setdefault('id', f'c-{uid}-{i}')
        q = c.first(lambda x: x.get('data-p') == 'q')
        if q is not None:
            q.kids = [k for k in q.kids if not (isinstance(k, Node) and k.get('class') == 'qn')]
            b = Node('b', {'class': 'qn'}, q)
            b.kids = [f'{i}.']
            q.kids = [b, ' '] + q.kids
    for i, h in enumerate(root.find(lambda x: x.tag == 'h3' and not x.up(lambda p: p.has('data-d') or p.has('data-c'))), 1):  # sections are linkable: search, fisheye contents, deep links
        h.attrs.setdefault('id', f's-{uid}-{i}')
    for sv in root.find(lambda x: x.tag == 'svg' and x.get('viewbox') and x.up(lambda p: p.tag == 'figure')):
        try:
            sv.attrs['style'] = f'--fw:{float(sv.get("viewbox").split()[2]) * 1.35:.0f}px'
        except (ValueError, IndexError):
            pass
    for blk in root.find(lambda x: is_c(x, *LABELED) and not x.first(lambda y: y.get('class') == 'blab')):
        lab = Node('p', {'class': 'blab'}, blk)
        lab.kids = [plan.st('lab_' + blk.get('data-c'))]
        blk.kids = [lab] + blk.kids
    np = plan.s.get('note_parts') or {}
    for part in root.find(lambda x: x.get('data-p') in np and x.up(lambda y: is_c(y, 'note'))):  # a study note's fields carry their pack labels
        if not (part.kids and isinstance(part.kids[0], Node) and part.kids[0].get('class') == 'np'):
            lab = Node('b', {'class': 'np'}, part)
            lab.kids = [np[part.get('data-p')]]
            part.kids = [lab, ' '] + part.kids
    for dt in root.find(lambda x: x.tag == 'details' and is_c(x, 'aside', 'note')):
        sm = dt.first(lambda x: x.tag == 'summary')
        if sm is None:
            continue
        sm.kids = [k for k in sm.kids if not (isinstance(k, Node) and k.get('class') == 'tag')]
        t = Node('span', {'class': 'tag'}, sm)
        t.kids = [plan.st('aside') if is_c(dt, 'aside') else (dt.get('data-grade') or plan.st('aside'))]
        sm.kids = [t] + sm.kids
    return root.html()


def ref_target(plan, rid):
    """(unit id, text, gloss) of a data-ref value: a unit id or a concept id, optionally #anchor."""
    rid = rid.split('#')[0]
    if rid in plan.unit_by_id:
        return rid, plan.label(rid), None
    if rid in plan.concept_by_id and plan.concept_by_id[rid]['unit'] in plan.unit_by_id:
        return plan.concept_by_id[rid]['unit'], plan.concept_by_id[rid]['term'], plan.concept_by_id[rid].get('gloss') or None
    return None, None, None


# ---------------------------------------------------------------- build


def read_units(d):
    srcs = []
    if os.path.isdir(os.path.join(d, 'units')):
        srcs = [open(os.path.join(d, 'units', f), encoding='utf-8').read() for f in sorted(os.listdir(os.path.join(d, 'units'))) if f.endswith('.html')]
    elif os.path.exists(os.path.join(d, 'units.html')):
        srcs = [open(os.path.join(d, 'units.html'), encoding='utf-8').read()]
    out = {}
    for s in srcs:
        for m in re.finditer(r'<section\s+data-u="([^"]+)"[^>]*>(.*?)</section>', s, re.DOTALL):
            out[m.group(1)] = m.group(2)
    return out


def fill_refs(plan, page):
    """Fill data-ref links (text, href, gloss) and data-v facts from the plan."""
    def fill_ref(m):
        attrs = m.group(1)
        rid = re.search(r'data-ref="([^"]+)"', attrs).group(1)
        uid, txt, gloss = ref_target(plan, rid)
        if uid is None:
            return m.group(0)
        anchor = rid.split('#')[1] if '#' in rid else 'u-' + uid
        attrs = re.sub(r'\s*(href|data-gloss)="[^"]*"', '', attrs)
        g = f' data-gloss="{esc(gloss)}"' if gloss else ''
        return f'<a href="#{esc(anchor)}"{attrs}{g}>{esc(txt)}</a>'
    page = re.sub(r'<a((?:\s+[\w-]+(?:="[^"]*")?)*?\s+data-ref="[^"]+"(?:\s+[\w-]+(?:="[^"]*")?)*)\s*>.*?</a>', fill_ref, page, flags=re.DOTALL)
    return re.sub(r'<span data-v="([^"]+)"\s*>.*?</span>', lambda m: f'<span data-v="{m.group(1)}">{esc(fact_text(plan, m.group(1)))}</span>' if fact_text(plan, m.group(1)) is not None else m.group(0), page, flags=re.DOTALL)


def build(d, shell=None):
    plan = Plan(os.path.join(d, 'book.json'))
    parts = read_units(d)
    shell = open(shell or os.path.join(TEMPLATES, 'book.html'), encoding='utf-8').read()
    figdir = os.path.join(d, 'figs')
    body = []
    for u in plan.live:
        inner = __import__(__package__ + '.catalog', fromlist=['expand']).expand(d, u['id'], parts.get(u['id'], ''))  # <!--card ID--> / <!--fig ID--> from slots/U.json
        for k, fn in MARKERS.items():
            inner = inner.replace(f'<!--@{k}-->', fn(plan))
        inner = re.sub(r'<!--svg ([\w.-]+)-->', lambda m: open(os.path.join(figdir, m.group(1) + '.svg'), encoding='utf-8').read() if os.path.exists(os.path.join(figdir, m.group(1) + '.svg')) else m.group(0), inner)
        inner = dress(inner, plan, u['id'])
        loc = f' style="--loc:var(--loc-{esc(u["part"])})"' if u.get('part') in plan.part_by_id else ''
        body.append(f'<section id="u-{esc(u["id"])}" data-u="{esc(u["id"])}" data-role="{esc(u["role"])}"{loc}>{g_head(plan, u)}{inner}{g_pn(plan, u)}</section>')
    extra = sorted(set(parts) - {u['id'] for u in plan.live})
    if extra:
        print(f'warning: unit files not live in the plan were skipped: {", ".join(extra)}', file=sys.stderr)
    page = fill_refs(plan, '\n'.join(body))
    ui = json.dumps(dict({k: rs(plan, k) for k in READER_UI}, **{k: plan.s[k] for k in UI_KEYS}), ensure_ascii=False).replace('</', '<\\/')
    out = shell
    for k, v in {'lang': esc(plan.book.get('lang', 'en')), 'doc_title': esc(plan.book.get('doc_title') or plan.book.get('title', '')), 'title': esc(plan.book.get('title', '')),
                 'font_css': plan.pack['fonts']['css'], 'font_sans': plan.pack['fonts']['sans'], 'font_serif': plan.pack['fonts']['serif'],
                 'tokens': g_tokens(plan), 'ui': ui, 'terms': g_terms(plan), 'hero': g_hero(plan), 'nav': g_nav(plan), 'units': page,
                 'bookjs': ('<script>' + read_js(d).replace('</', '<\\/') + '</script>') if read_js(d) else ''}.items():
        out = out.replace('{{' + k + '}}', v)
    out = prerender_math(out)
    dst = os.path.join(d, 'book.html')
    open(dst, 'w', encoding='utf-8').write(out)
    return dst


KATEX_VERSION = '0.16.9'
MATH_RE = re.compile(r'<(span|div)((?:\s+[\w-]+(?:="[^"]*")?)*?\s+data-m(?:="display")?(?:\s+[\w-]+(?:="[^"]*")?)*)\s*>(.*?)</\1>', re.DOTALL)


def katex_module():
    """Path of a KaTeX node module: $KATEX_NODE, else ~/.cache/paperwork-book, installed there once with npm."""
    env = os.environ.get('KATEX_NODE')
    if env and os.path.exists(os.path.join(env, 'package.json')):
        return env
    cache = os.path.join(os.path.expanduser('~'), '.cache', 'paperwork-book')
    mod = os.path.join(cache, 'node_modules', 'katex')
    if not os.path.exists(os.path.join(mod, 'package.json')):
        os.makedirs(cache, exist_ok=True)
        r = subprocess.run(['npm', 'install', '--silent', '--prefix', cache, f'katex@{KATEX_VERSION}'], capture_output=True, text=True)
        if r.returncode:
            raise PlanError('math needs KaTeX: npm install failed; set KATEX_NODE to a katex module directory\n' + r.stderr[-400:])
    return mod


def prerender_math(page):
    """Replace every data-m TeX with KaTeX MathML at build time: no stylesheet or script from another host, and raw < in TeX is safe."""
    items = [(m.group(2), html.unescape(m.group(3))) for m in MATH_RE.finditer(page) if 'data-tex=' not in m.group(2)]
    if not items:
        return page
    js = ("const k=require(process.argv[1]);const it=JSON.parse(require('fs').readFileSync(0,'utf8'));"
          "console.log(JSON.stringify(it.map(([a,t])=>{try{return k.renderToString(t,{displayMode:/display/.test(a),output:'mathml',throwOnError:true})}"
          "catch(e){return '<span class=\\'katex-error\\'>'+String(e.message).replace(/</g,'&lt;')+'</span>'}})))")
    try:
        r = subprocess.run(['node', '-e', js, katex_module()], input=json.dumps(items), capture_output=True, text=True)
    except FileNotFoundError:
        raise PlanError('math needs node on PATH')
    if r.returncode:
        raise PlanError('KaTeX failed: ' + r.stderr[-400:])
    out = iter(json.loads(r.stdout))

    def sub(m):
        if 'data-tex=' in m.group(2):
            return m.group(0)
        tex = html.unescape(m.group(3))
        return f'<{m.group(1)}{m.group(2)} data-tex="{esc(tex)}">{next(out)}</{m.group(1)}>'
    return MATH_RE.sub(sub, page)
