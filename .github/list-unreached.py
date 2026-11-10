#!/usr/bin/env python3
"""List each file, function and import of a plugin that no entry point reaches.

usage: list-unreached.py [root]

A plugin is each folder of root (default: this repository) that holds `.claude-plugin/plugin.json`. Its entry points are
that manifest, `hooks/hooks.json`, `monitors/monitors.json`, each `skills/*/SKILL.md` and each file at the plugin's root.
A file outside `fixtures/` is reached when a reached file outside `fixtures/` names its path or file name, links its folder as `[x/](x/)`, or imports it,
or a reached file imports it. A fixture folder is a `fixtures/` folder and all below it; its runners, each `replay-*.py` or `replay-*.ts` directly in it and
each script of the `scripts/` folder beside it whose usage lists a `fixtures` call, are run by the repository check, so each `replay-*` runner is reached,
a fixture folder with a runner keeps its data whole, and a program in it is reached only as a runner or when a reached program of that folder names it;
no other file reaches a fixture file, so every file of a fixture folder with no runner is listed. A function nothing live calls
and an import nothing uses are unused; a string that spells a function's name calls it, a `__future__` import is used, and a file that calls `getattr` with a computed name keeps every function it defines.
Prints `unreached <path>`, `unreached <path>:<line> <name>` and `unreached <path>:<line> import <name>` lines, then a summary,
and exits 1 when it printed any of them, else 0. Standard library only, Python 3.9."""

import ast
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

TOKEN = re.compile(r"[\w.\-/]+")
PIECES = re.compile(r"[\"']\s*/\s*[\"']")  # "a" / "b" names one path
PROGRAMS = (".py", ".ts", ".tsx", ".js", ".sh")
IMPORTABLE = (".ts", ".tsx", ".js")  # a relative import in these leaves the extension off
FOLDER_LINK = re.compile(r"\]\(([^)\s#]+)/\)")  # [examples/](examples/) links a folder
RUNNER = re.compile(r"(?:^|/)fixtures/replay-[^/]+\.(?:py|ts)$")
FIXTURES_CALL = re.compile(r"^(?:usage:)? *\S+\.py fixtures\b", re.M)  # a skill script that checks the fixtures beside it


def list_files(folder):
    """Paths under folder, relative to it: the tracked and the untracked-but-not-ignored when git lists them, else all."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=folder, capture_output=True, text=True, check=True,
        ).stdout
        return sorted(path for path in listing.split("\0") if path and (folder / path).is_file())
    except (OSError, subprocess.CalledProcessError):
        found = []
        for where, subfolders, names in os.walk(folder):
            subfolders[:] = [name for name in subfolders if name != ".git"]
            found += [os.path.relpath(os.path.join(where, name), folder) for name in names]
        return sorted(found)


def read_text(folder, path):
    try:
        return (folder / path).read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError):
        return ""


def parse(text):
    try:
        return ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):  # ValueError: a NUL byte, on Python 3.9
        return None


def is_fixture(path):
    return "fixtures" in path.split("/")[:-1]


def fixture_folder(path):
    parts = path.split("/")
    return "/".join(parts[:parts.index("fixtures") + 1])


def find_imports(modules, files):
    """Map each Python file to the files it imports: a file whose path ends in the module's path, and each package above it."""
    stems = {}
    for path in files:
        if path.endswith(".py"):
            parts = (path[:-len("/__init__.py")] if path.endswith("/__init__.py") else path[:-len(".py")]).split("/")
            for start in range(len(parts)):
                stems.setdefault("/".join(parts[start:]), set()).add(path)
    imports = {path: set() for path in files}
    for path, names in modules.items():
        for name in names:
            parts = os.path.normpath(name).split("/")
            for end in range(1, len(parts) + 1):
                imports[path].update(stems.get("/".join(parts[:end]), ()))
        imports[path].discard(path)
    return imports


def find_references(texts, across_plugins=False):
    """Map each file to the other files its text names.

    With across_plugins the paths start with their plugin's folder; only a name that holds a `/` counts, since a bare file name
    says nothing of whose it is, and a file of the text's own plugin wins over a same-named one of another."""
    by_name, folders = {}, {}
    for path in texts:
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)
        for end in [at for at, letter in enumerate(path) if letter == "/"]:
            folders.setdefault(path[:end], []).append(path)
    bare = {name for name in by_name if "." not in name}
    references = {}
    for path, text in texts.items():
        found = set()
        here = path.rsplit("/", 1)[0] if "/" in path else ""
        for link in FOLDER_LINK.findall(text):
            found.update(folders.get(os.path.normpath(os.path.join(here, link)), ()))
        for word in set(TOKEN.findall(PIECES.sub("/", text))):
            token = re.sub(r"^(\.{0,2}/)+", "", word).rstrip("./-")
            names = [token] + ([token + extension for extension in IMPORTABLE] if word.startswith(".") and path.endswith(IMPORTABLE + (".sh",)) else [])
            for name in names:
                file_name = name.rsplit("/", 1)[-1]
                if "/" in name if across_plugins else "." in file_name or "/" in name or file_name in bare:
                    named = [file for file in by_name.get(file_name, ()) if file == name or file.endswith("/" + name) or name.endswith("/" + file)]
                    own = [file for file in named if file.split("/")[0] == path.split("/")[0]]
                    found.update(own if across_plugins and own else named)
        found.discard(path)
        references[path] = found
    return references


def find_reached(files, references, imports, texts):
    """The files a plugin's entry points and its fixture runners reach."""
    run = {fixture_folder(path) for path in files if RUNNER.search(path)}
    run |= {path.rsplit("/scripts/", 1)[0] + "/fixtures" for path in files if re.search(r"(?:^|/)scripts/[^/]+\.py$", path) and FIXTURES_CALL.search(texts[path])}
    # a fixture program reaches only files of its own fixture folder by name, and fixture data none; a file outside reaches no fixture file by name
    reaches = {path: imports[path] | {target for target in references[path]
                                      if (is_fixture(target) and fixture_folder(target) == fixture_folder(path) and path.endswith(PROGRAMS)
                                          if is_fixture(path) else not is_fixture(target))}
               for path in files}
    reached = {path for path in files if "/" not in path or path in (".claude-plugin/plugin.json", "hooks/hooks.json", "monitors/monitors.json")
               or re.fullmatch(r"skills/[^/]+/SKILL\.md", path) or RUNNER.search(path)
               or is_fixture(path) and fixture_folder(path) in run and not path.endswith(PROGRAMS)}
    queue = list(reached)
    while queue:
        path = queue.pop()
        for target in reaches[path]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def read_python(path, tree, lines):
    """What one Python file imports as modules, defines as functions, calls by name, and imports as names, with its roots (dunder or decorated functions)."""
    here = path.rsplit("/", 1)[0] if "/" in path else ""
    modules, defined, roots, uses, imported = [], [], set(), {}, []
    docstrings, used, dynamic = set(), set(), []

    def visit(node, owner):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            docstrings.add(id(node.body[0].value))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.decorator_list or node.name.startswith("__") and node.name.endswith("__"):
                roots.add(node.name)
            else:
                defined.append((node.lineno, node.name))
            owner = node.name
        name = (node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else node.attr if isinstance(node, ast.Attribute)
                else node.value if isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value.isidentifier() and id(node) not in docstrings else None)
        if name:
            uses.setdefault(owner, set()).add(name)
            used.add(name)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "getattr" and len(node.args) > 1 and not isinstance(node.args[1], ast.Constant):
            dynamic.append(node)
        if isinstance(node, ast.Import):
            modules.extend(alias.name.replace(".", "/") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            base = os.path.join(os.path.join(here, *[".."] * (node.level - 1)) if node.level else "", (node.module or "").replace(".", "/"))
            modules.extend([base] + [base + "/" + alias.name for alias in node.names])
        if isinstance(node, (ast.Import, ast.ImportFrom)) and "noqa" not in lines[node.lineno - 1]:
            for alias in node.names:
                bound = (alias.asname or alias.name).split(".")[0]
                if bound != "*" and getattr(node, "module", None) != "__future__":
                    imported.append((node.lineno, bound, used))
        for child in ast.iter_child_nodes(node):
            visit(child, owner)

    try:
        visit(tree, None)
    except RecursionError:  # a deeper expression than the interpreter walks
        return [], [], set(), {}, []
    if dynamic:
        roots.update(name for _, name in defined)
        defined = []
    return modules, defined, roots, uses, imported


def find_unused(facts, reached):
    """The functions no live code calls, and the imports no code of their file uses, as (path, line, name) rows, over the reached files."""
    live, queue, roots, uses = set(), [None], set(), {}
    for path in reached:
        if path in facts:
            roots |= facts[path][2]
            for owner, names in facts[path][3].items():
                uses.setdefault(owner, set()).update(names)
    queue += roots
    while queue:
        for name in uses.get(queue.pop(), ()):
            if name not in live:
                live.add(name)
                queue.append(name)
    functions, imports = [], []
    for path in sorted(reached & facts.keys()):
        functions += [(path, line, name) for line, name in facts[path][1] if name not in live]
        imports += [(path, line, name) for line, name, used in facts[path][4] if name not in used]
    return functions, imports


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else ROOT).resolve()
    if not root.is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    printed = file_count = 0
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        files = list_files(plugin)
        texts = {path: read_text(plugin, path) for path in files}
        trees = {path: parse(text) for path, text in texts.items() if path.endswith(".py")}
        facts = {path: read_python(path, tree, texts[path].split("\n")) for path, tree in trees.items() if tree}
        reached = find_reached(files, find_references(texts), find_imports({path: fact[0] for path, fact in facts.items()}, files), texts)
        functions, imports = find_unused(facts, reached)
        lines = ["unreached {}/{}".format(plugin.name, path) for path in files if path not in reached]
        lines += ["unreached {}/{}:{} {}".format(plugin.name, path, line, name) for path, line, name in functions]
        lines += ["unreached {}/{}:{} import {}".format(plugin.name, path, line, name) for path, line, name in imports]
        for line in lines:
            print(line)
        printed += len(lines)
        file_count += len(files)
    print("{} files, {} unreached".format(file_count, printed))
    return 1 if printed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
