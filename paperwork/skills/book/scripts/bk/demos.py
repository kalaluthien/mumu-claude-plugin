import re
from .dom import read_js
from .build import read_units

def demo_index(d):
    """[{name, doc, units, params, start}] of the demos registered as D['name'] in the book's book.js."""
    return _demo_scan(d)[0]


def _demo_scan(d):
    js = read_js(d)
    use = {}
    for uid, inner in read_units(d).items():
        for m in re.finditer(r'<[^>]*\sdata-demo="([\w-]+)"[^>]*>', inner):
            e = use.setdefault(m.group(1), [set(), set()])
            e[0].add(uid)
            e[1].update(set(re.findall(r'\s(data-[\w-]+)=', m.group(0))) - {'data-demo', 'data-c'})
    out = []
    for m in re.finditer(r"""^[ \t]*D\[\s*['"]([\w-]+)['"]\s*\]\s*=""", js, re.M):
        lines = js[:m.start()].rstrip().split('\n')
        dm = re.fullmatch(r'/\*\s*-*\s*(?:\d+\.\s*)?(.*?)\s*-*\s*\*/', lines[-1].strip() if lines else '')
        units, prm = use.get(m.group(1), [set(), set()])
        out.append(dict(name=m.group(1), doc=dm.group(1) if dm else '', units=sorted(units), params=sorted(prm), start=m.start()))
    return out, js, use


def demos(d, name=None):
    """Demos registered as D['name'] in the book's book.js: doc line, units using each, data-* params; --name prints the source."""
    idx, js, use = _demo_scan(d)
    if not idx:
        print("no D['name'] demos in book.js")
        return 1
    if name:
        m = next((x for x in idx if x['name'] == name), None)
        if m is None:
            print(f'no demo {name}; demos: {", ".join(x["name"] for x in idx)}')
            return 1
        e = re.compile(r"""\n[ \t]*(/\*\s*-{3,}|D\[\s*['"])""").search(js, m['start'] + 3)
        print(js[m['start']:e.start() if e else len(js)].rstrip())
        return 0
    for x in idx:
        print(f'{x["name"]:16} {x["doc"] or "-"} | units: {", ".join(x["units"]) or "-"} | params: {", ".join(x["params"]) or "-"}')
    for k in sorted(set(use) - {x['name'] for x in idx}):
        print(f'{k:16} used in {", ".join(sorted(use[k][0]))} but not defined in book.js')
    return 0
