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

from .model import REFERENCE, reference_path

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
        mine = [(reference, reference_path(reference)) for reference in node.get("refs", []) if isinstance(reference, str) and REFERENCE.fullmatch(reference.strip())]
        return [citation for citation in mine if citation[1]] + [citation for k, child in node.items() if k != "refs" for citation in cited(child)]
    return [citation for child in node for citation in cited(child)] if isinstance(node, list) else []


def inside(root, path):
    """The file at path under root, or None."""
    resolved = path.resolve()
    return resolved if resolved.is_file() and resolved.is_relative_to(root) else None


def bases(root, file):
    """Where an absolute import of file may start: its folder, every lib/ above it, the root."""
    out, folder = [file.parent], file.parent
    while folder.is_relative_to(root):
        if (folder / "lib").is_dir():
            out.append(folder / "lib")
        folder = folder.parent
    return out + [root]


def module_file(base, dotted):
    path = base.joinpath(*dotted.split(".")) if dotted else base
    return next((candidate for candidate in (path.with_suffix(".py"), path / "__init__.py") if candidate.is_file()), None)


def imports(root, file):
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [next(filter(None, (module_file(start, alias.name) for start in bases(root, file))), None) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            for base in [file.parent.parents[node.level - 2] if node.level > 1 else file.parent] if node.level else bases(root, file):
                hit = [module_file(base, ".".join(filter(None, [node.module, alias.name]))) for alias in node.names]
                if hit := [module for module in hit if module] or [module_file(base, node.module or "")]:
                    out += hit
                    break
    return [path for path in out if path and path.is_relative_to(root) and path != file]


def reached(root, file):
    """(how, file) for each file inside the root that file points at."""
    text = file.read_text(encoding="utf-8", errors="replace")
    out = []
    if file.suffix == ".md":
        for target in LINK.findall(text):
            if not SCHEME.match(target) and not target.startswith("#"):
                out.append(("links to", inside(root, file.parent / target.split("#")[0])))
    if file.suffix == ".py":
        out += [("imports", path) for path in imports(root, file)]
    if file.suffix in (".md", ".py"):
        plugin = next((folder for folder in file.parents if (folder / ".claude-plugin").is_dir() and folder.is_relative_to(root)), None)
        out += [("names", inside(root, plugin / mention.rstrip(".,:;"))) for mention in MENTION.findall(text) if plugin]
    return [(how, path) for how, path in out if path and path != file]


def problems(model):
    """(the problems, the status line the check's row prints): empty when the model lists and cites no file."""
    plan = model.get("plan") or {}
    references = cited(model)
    if not plan.get("sources") and not references:
        return [], ""
    root, out = root_of(plan), []
    name = lambda file_path: file_path.relative_to(root).as_posix()
    listed = {}
    for source in plan.get("sources", []):
        if file := inside(root, root / source):
            listed[file] = source
        else:
            out.append(f"{source}: listed, but no such file under the root (list files one by one, no globs)")
    exclude = {file: why for path, why in (plan.get("exclude") or {}).items() if (file := (root / path).resolve())}
    cites = {file for _, path in references if (file := (root / path).resolve())}
    out += [f"{path}: listed but cited by no element; cite it as [name]({path}:line) or drop it from plan.sources" for source_file, path in listed.items() if source_file not in cites]
    out += [f"{reference} cites {path}, which plan.sources does not list" for reference, path in references if (root / path).resolve() not in listed]
    out += [f"{name(excluded_file)}: give its exclusion a one-line reason" for excluded_file, why in exclude.items() if not why.strip()]
    seen, todo = set(), list(listed)
    while todo:
        file = todo.pop(0)
        if file in seen or file in exclude:
            continue
        seen.add(file)
        for how, target in reached(root, file):
            if target not in listed and target not in exclude and target not in seen and target not in todo:
                out.append(f'{name(file)} {how} {name(target)}, which is neither listed nor excluded (closure): list it in plan.sources, or give plan.exclude "{name(target)}": a one-line reason')
            todo.append(target)
    return out, f"cited {len(cites & set(listed))}/{len(listed)} listed, {len(exclude)} excluded; root {root}; closure: {CLOSURE}"
