"""book.py: plan checks, build, lint, mutation tests and figure helpers for book-authoring.

Python standard library, plus node and KaTeX for math (fetched once into ~/.cache/book-authoring). A book directory holds book.json (the model), units.html or units/*.html
(one <section data-u="ID"> per unit), optional figs/*.svg and facts.json, and receives book.html.

  book.py init DIR [--lang L]      copy the sample model and units into DIR
  book.py check [DIR]              plan rules (B) on book.json
  book.py build [DIR]              assemble book.html: chrome, references, facts, figures, review clones, math
  book.py lint [DIR] [--unit ID] [--quick]
  book.py mutate [DIR]             plant one defect per rule and pattern; fail if any is missed
  book.py stats FILE.html [--sel .CLASS|TAG]   per-unit size distribution, for bands and baselines
  book.py rules                    rule and policy tables
  book.py render [DIR] [--out DIR] [--quick]   book-wide #check plus element checks; prints failures only (needs playwright)
  book.py text [DIR] [--unit ID [--section N-M | --concept ID]] [--only prose|stems|cards|claims|figs]   flat reviewer text
  book.py snippet KIND | --list    markup snippet from templates/units.html
  book.py outline [DIR] UNIT       one line per block: L<line> #<id> <kind> <meta> "<first 50>" <chars>
  book.py show [DIR] UNIT SEL [--html]   blocks by #id, data-c kind, L120 or L120-L180
  book.py edit [DIR] UNIT --patch F.json   all-or-none ops on the unit source; backup in .work/, rebuild, lint delta
  book.py shot [DIR] UNIT [--sel CSS] [--section N-M] [--solve] [--steps F.json] [--sheet] [--quick] [--out DIR]
  book.py demos [DIR] [--name N]   D['name'] demos in book.js: doc line, units, params; --name prints the source
  book.py pattern list [--family problem|visual] [--dir BOOK] | pattern show P | pattern promote P --dir BOOK [--as-variant-of Q]
  book.py element show E           an element's slots, checks and example
  book.py card new [DIR] --unit U --after SEL [--kind K] [--elements a,b] [--id ID] [--label P]   placeholder + slots/U.json stub (fig new: --kind fig|frames)
  book.py card lift [DIR] U ID     a hand card into slots/U.json, rendering back identical
  brief, agents, note, round, approve: see scripts/agents.py
  Every command that takes DIR also takes --dir DIR (default .); a .work/ path in --patch, --out, --steps or --score resolves inside DIR.

Figure scripts: sys.path.insert(0, SKILL/scripts); from book import glob, Fig, fact
"""
import argparse, json, os, shutil, sys
from .const import HERE, POLICIES, RULES, TEMPLATES
from .lang import _load, pack
from .text import ONLY, cards, sections, stats, text
from .plan import Plan, PlanError, check_plan, settle
from .build import build
from .demos import demos
from .edit import edit, outline, show, snippet
from .lint import lint, report
from .mutate import mutate
from .qa import render, shot
from . import catalog

# ---------------------------------------------------------------- CLI


def dir_args(s, default='.'):
    """The book directory, given either as an optional positional DIR or as --dir (default .)."""
    s.add_argument('dir_pos', nargs='?', metavar='DIR', help='book directory (same as --dir)')
    s.add_argument('--dir', dest='dir_opt', metavar='DIR', help=f'book directory (default {default})')
    s.set_defaults(dir_default=default)
    return s


def resolve_dir(a):
    """Set a.dir from DIR or --dir; commands with free positionals resolve them in their own handler."""
    if hasattr(a, 'pos'):
        return
    if not hasattr(a, 'dir_opt'):
        return
    p, o = getattr(a, 'dir_pos', None), a.dir_opt
    if p and o and os.path.abspath(p) != os.path.abspath(o):
        raise PlanError(f'two book directories given: {p} and --dir {o}')
    a.dir = p or o or a.dir_default


def parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    dir_args(sub.add_parser('init'), None).add_argument('--lang', default='en')
    for name in ('check', 'build'):
        dir_args(sub.add_parser(name))
    s = dir_args(sub.add_parser('lint'))
    s.add_argument('--unit'); s.add_argument('--quick', action='store_true')
    dir_args(sub.add_parser('mutate'), None)
    s = sub.add_parser('stats'); s.add_argument('file'); s.add_argument('--sel')
    sub.add_parser('rules')
    s = dir_args(sub.add_parser('cards')); s.add_argument('--units'); s.add_argument('--out', default='cards.json'); s.add_argument('--score')
    s = dir_args(sub.add_parser('text')); s.add_argument('--unit'); s.add_argument('--only', choices=ONLY)
    s.add_argument('--section', help='only sections N, N-M or N,M of --unit (0 = before the first section heading)'); s.add_argument('--concept', help='only the section of --unit that defines this concept')
    s = dir_args(sub.add_parser('render')); s.add_argument('--out'); s.add_argument('--quick', action='store_true')
    s = sub.add_parser('snippet'); s.add_argument('kind', nargs='?'); s.add_argument('--list', action='store_true')
    s = dir_args(sub.add_parser('outline')); s.add_argument('unit')
    s = dir_args(sub.add_parser('show')); s.add_argument('unit'); s.add_argument('sel'); s.add_argument('--html', action='store_true')
    s = dir_args(sub.add_parser('edit')); s.add_argument('unit'); s.add_argument('--patch', required=True)
    s = dir_args(sub.add_parser('shot')); s.add_argument('unit'); s.add_argument('--sel'); s.add_argument('--section', help='only sections N, N-M or N,M (as in text)')
    s.add_argument('--solve', action='store_true'); s.add_argument('--steps'); s.add_argument('--sheet', action='store_true'); s.add_argument('--quick', action='store_true'); s.add_argument('--out')
    s = dir_args(sub.add_parser('demos')); s.add_argument('--name')
    catalog.register(sub)
    try:  # brief, agents, note, round, approve live in agents.py; book.py works without it
        sys.path.insert(0, HERE)
        import agents
        agents.register(sub)
    except Exception as e:
        if not isinstance(e, ImportError):
            print(f'warning: scripts/agents.py not loaded ({e.__class__.__name__}: {e})', file=sys.stderr)
    return ap


def main(argv=None):
    try:  # piping into head must not print a traceback
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    ap = parser()
    a = ap.parse_args(argv)
    try:
        resolve_dir(a)
    except PlanError as e:
        ap.error(str(e))
    for k in ('patch', 'out', 'steps', 'score'):  # agent scratch paths (.work/ID/...) live inside the book directory
        v = getattr(a, k, None)
        if isinstance(v, str) and v.startswith('.work/') and getattr(a, 'dir', None) and not (a.cmd == 'cards' and k == 'out'):  # cards joins --out with DIR itself
            setattr(a, k, os.path.join(a.dir, v))
    try:
        if a.cmd == 'init':
            if not a.dir:
                raise PlanError('init needs DIR or --dir')
            os.makedirs(a.dir, exist_ok=True)
            for f in ('book.json', 'units.html', 'book.js'):
                dst = os.path.join(a.dir, f)
                if os.path.exists(dst):
                    sys.exit(f'{dst} exists; not overwritten')
                shutil.copy(os.path.join(TEMPLATES, f), dst)
            j = json.load(open(os.path.join(a.dir, 'book.json'), encoding='utf-8'))
            if j.pop('gates', None) is not None or j.pop('rounds', None) is not None:  # a new book starts unapproved, with its own interview
                j.pop('rounds', None)
                json.dump(j, open(os.path.join(a.dir, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            if a.lang != 'en':  # content language; lang/<code>.json supplies its strings and rules
                j = json.load(open(os.path.join(a.dir, 'book.json'), encoding='utf-8'))
                j['book']['lang'] = a.lang
                for k in (_load(a.lang) or {}).get('strings', {}):  # the sample's English labels give way to the pack's
                    j['book'].get('strings', {}).pop(k, None)
                json.dump(j, open(os.path.join(a.dir, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                if not pack(a.lang)['has_pack']:
                    print(f'warning: no lang/{a.lang}.json; English rules apply until one is added (copy lang/en.json)', file=sys.stderr)
            print(f'sample copied to {a.dir}; edit book.json first, then the units')
            return 0
        if a.cmd == 'check':
            P = Plan(os.path.join(a.dir, 'book.json'))
            return report(settle(P, check_plan(P)))
        if a.cmd == 'build':
            print(build(a.dir))
            return 0
        if a.cmd == 'lint':
            return report(lint(a.dir, a.unit, a.quick))
        if a.cmd == 'mutate':
            return mutate(a.dir)
        if a.cmd == 'stats':
            return stats(a.file, a.sel)
        if a.cmd == 'rules':
            print('| ID | Level | Checks | Known false positives |\n|---|---|---|---|')
            for k, (lv, what, fp) in RULES.items():
                print(f'| {k} | {lv} | {what} | {fp or "-"} |')
            print('\n| Policy | Values (first is default) |\n|---|---|')
            for k, v in POLICIES.items():
                print(f'| {k} | ' + '; '.join(f'`{x}`: {y}' for x, y in v.items()) + ' |')
            return 0
        if a.cmd == 'cards':
            return cards(a.dir, a.units.split(',') if a.units else None, a.out, a.score)
        if a.cmd == 'text':
            return text(a.dir, a.unit, a.only, a.section, a.concept)
        if a.cmd == 'render':
            return render(a.dir, a.out, a.quick)
        if a.cmd == 'snippet':
            return snippet(None if a.list else a.kind)
        if a.cmd == 'outline':
            return outline(a.dir, a.unit)
        if a.cmd == 'show':
            return show(a.dir, a.unit, a.sel, a.html)
        if a.cmd == 'edit':
            return edit(a.dir, a.unit, a.patch)
        if a.cmd == 'shot':
            ws, sc = ((390,), ('light',)) if a.quick else ((390, 1200), ('light', 'dark'))
            return shot(a.dir, a.unit, a.sel, ws, sc, a.solve, a.steps, a.sheet, a.out, section=sections(a.section))
        if a.cmd in ('pattern', 'element', 'card', 'fig'):
            return catalog.run(a)
        if a.cmd == 'demos':
            return demos(a.dir, a.name)
        if getattr(a, 'func', None):
            return a.func(a)
    except PlanError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
