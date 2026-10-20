"""The sources check: the files an analysed system's model rests on are listed, cited, and closed under what they reach.

A listed file's closure is every file inside the root that it links to (markdown), imports (Python) or names as
${CLAUDE_PLUGIN_ROOT}/<path> (markdown and Python). Limits: a file a script only reads (json, html, js) is not followed;
a file without a .md or .py suffix is not read; a script that puts a folder other than an ancestor lib/ on sys.path is
missed; links inside code fences are followed.
"""
import ast
import pathlib
import re
import subprocess

from .model import REF, ref_path

CLOSURE = ("every file inside the root that a listed file links to (markdown), imports (Python) or names as "
           "${CLAUDE_PLUGIN_ROOT}/<path> is listed, or excluded with a one-line reason")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
SCHEME = re.compile(r"[a-z][a-z0-9+.-]*:")
MENTION = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s)`\"'\]>*<]+)")


def root_of(plan):
    """plan.root, else the git top-level of the current directory, else the current directory."""
    if plan.get("root"):
        return pathlib.Path(plan["root"]).expanduser().resolve()
    git = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(git.stdout.strip() if git.returncode == 0 else ".").resolve()


def cited(node):
    """Every local ref anywhere in the model: (the ref, the file it cites)."""
    if isinstance(node, dict):
        mine = [(r, ref_path(r)) for r in node.get("refs", []) if isinstance(r, str) and REF.fullmatch(r.strip())]
        return [x for x in mine if x[1]] + [c for k, v in node.items() if k != "refs" for c in cited(v)]
    return [c for v in node for c in cited(v)] if isinstance(node, list) else []


def inside(root, p):
    """The file at p under root, or None."""
    q = p.resolve()
    return q if q.is_file() and q.is_relative_to(root) else None


def bases(root, f):
    """Where an absolute import of f may start: its folder, every lib/ above it, the root."""
    out, d = [f.parent], f.parent
    while d.is_relative_to(root):
        if (d / "lib").is_dir():
            out.append(d / "lib")
        d = d.parent
    return out + [root]


def module_file(base, dotted):
    p = base.joinpath(*dotted.split(".")) if dotted else base
    return next((c for c in (p.with_suffix(".py"), p / "__init__.py") if c.is_file()), None)


def imports(root, f):
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [next(filter(None, (module_file(b, a.name) for b in bases(root, f))), None) for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            for b in [f.parent.parents[n.level - 2] if n.level > 1 else f.parent] if n.level else bases(root, f):
                hit = [module_file(b, ".".join(filter(None, [n.module, a.name]))) for a in n.names]
                if hit := [h for h in hit if h] or [module_file(b, n.module or "")]:
                    out += hit
                    break
    return [p for p in out if p and p.is_relative_to(root) and p != f]


def reached(root, f):
    """(how, file) for each file inside the root that f points at."""
    text = f.read_text(encoding="utf-8", errors="replace")
    out = []
    if f.suffix == ".md":
        for t in LINK.findall(text):
            if not SCHEME.match(t) and not t.startswith("#"):
                out.append(("links to", inside(root, f.parent / t.split("#")[0])))
    if f.suffix == ".py":
        out += [("imports", p) for p in imports(root, f)]
    if f.suffix in (".md", ".py"):
        plugin = next((d for d in f.parents if (d / ".claude-plugin").is_dir() and d.is_relative_to(root)), None)
        out += [("names", inside(root, plugin / t.rstrip(".,:;"))) for t in MENTION.findall(text) if plugin]
    return [(how, p) for how, p in out if p and p != f]


def problems(m):
    """(the problems, the status line the check's row prints): empty when the model lists and cites no file."""
    plan = m.get("plan") or {}
    refs = cited(m)
    if not plan.get("sources") and not refs:
        return [], ""
    root, out = root_of(plan), []
    name = lambda f: f.relative_to(root).as_posix()
    listed = {}
    for p in plan.get("sources", []):
        if f := inside(root, root / p):
            listed[f] = p
        else:
            out.append(f"{p}: listed, but no such file under the root (list files one by one, no globs)")
    exclude = {f: why for p, why in (plan.get("exclude") or {}).items() if (f := (root / p).resolve())}
    cites = {f for _, p in refs if (f := (root / p).resolve())}
    out += [f"{p}: listed but cited by no element; cite it as [name]({p}:line) or drop it from plan.sources" for f, p in listed.items() if f not in cites]
    out += [f"{r} cites {p}, which plan.sources does not list" for r, p in refs if (root / p).resolve() not in listed]
    out += [f"{name(f)}: give its exclusion a one-line reason" for f, why in exclude.items() if not why.strip()]
    seen, todo = set(), list(listed)
    while todo:
        f = todo.pop(0)
        if f in seen or f in exclude:
            continue
        seen.add(f)
        for how, g in reached(root, f):
            if g not in listed and g not in exclude and g not in seen and g not in todo:
                out.append(f'{name(f)} {how} {name(g)}, which is neither listed nor excluded (closure): list it in plan.sources, or give plan.exclude "{name(g)}": a one-line reason')
            todo.append(g)
    return out, f"cited {len(cites & set(listed))}/{len(listed)} listed, {len(exclude)} excluded; root {root}; closure: {CLOSURE}"
