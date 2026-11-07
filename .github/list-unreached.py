#!/usr/bin/env python3
"""List each file, function and import of a plugin that no entry point reaches.

usage: list-unreached.py [root]

A plugin is each folder of root (default: this repository) that holds `.claude-plugin/plugin.json`. Its entry points are
that manifest, `hooks/hooks.json`, `monitors/monitors.json`, each `skills/*/SKILL.md` and each file at the plugin's root.
A file is reached when a reached file names its path or file name, links its folder as `[x/](x/)`, or imports it from
`lib/`. A reached program that lists folders (`glob`, `iterdir`, `listdir`, `walk`) and names one reaches the data files
below it under `fixtures/`. A file under a `fixtures/` folder is reached only when a reached file reaches it, or when it is
a script that names a reached file, and it reaches nothing outside `fixtures/`. A function nothing live calls
and an import nothing uses are unused; a file that calls `getattr` with a computed name keeps every function it defines.
Prints `unreached <path>`, `unused <path>:<line> <name>` and `unused <path>:<line> import <name>` lines, then a summary,
and exits 1 when it printed any of them, else 0. Standard library only, Python 3.9."""

import ast
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

TOKEN = re.compile(r"[\w.\-/]+")
PIECES = re.compile(r"[\"']\s*/\s*[\"']")  # "skills" / "kick-off" names one path
PROGRAMS = (".py", ".ts", ".js", ".sh")
FOLDER_LINK = re.compile(r"\]\(([^)\s#]+)/\)")  # [examples/](examples/) links a folder
LISTS = re.compile(r"\b(?:glob|rglob|iterdir|listdir|scandir|walk|readdirSync)\(")


def list_files(folder):
    """Paths under folder, relative to it: the tracked and the untracked-but-not-ignored when git lists them, else all."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=folder, capture_output=True, text=True, check=True,
        ).stdout
        return sorted(path for path in out.split("\0") if path and (folder / path).is_file())
    except (OSError, subprocess.CalledProcessError):
        found = []
        for where, dirs, names in os.walk(folder):
            dirs[:] = [name for name in dirs if name != ".git"]
            found += [os.path.relpath(os.path.join(where, name), folder) for name in names]
        return sorted(found)


def read_text(folder, path):
    try:
        return (folder / path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def parse(text):
    try:
        return ast.parse(text)
    except SyntaxError:
        return None


def is_fixture(path):
    return "fixtures" in path.split("/")[:-1]


def find_imports(trees, files):
    """Map each Python file to the files it imports: the module's file and the `__init__.py` of each package above it."""
    imports = {path: set() for path in files}
    for path, tree in trees.items():
        here = path.rsplit("/", 1)[0] if "/" in path else ""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.replace(".", "/") for alias in node.names]
                modules = ["lib/" + module for module in modules]
            elif isinstance(node, ast.ImportFrom):
                base = os.path.normpath(os.path.join(here, *[".."] * (node.level - 1))) if node.level else "lib"
                base = os.path.join(base, (node.module or "").replace(".", "/"))
                modules = [base] + [base + "/" + alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                parts = os.path.normpath(module).split("/")
                for end in range(1, len(parts) + 1):
                    imports[path].update({"/".join(parts[:end]) + ".py", "/".join(parts[:end]) + "/__init__.py"} & set(files))
        imports[path].discard(path)
    return imports


def find_references(texts):
    """Map each file to the other files its text names, or reads as a folder of data."""
    by_name, folders = {}, {}
    for path in texts:
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)
        for end in [at for at, char in enumerate(path) if char == "/"]:
            folders.setdefault(path[:end], []).append(path)
    references = {}
    for path, text in texts.items():
        found = set()
        here = path.rsplit("/", 1)[0] if "/" in path else ""
        reads_folders = path.endswith(PROGRAMS) and bool(LISTS.search(text))
        for link in FOLDER_LINK.findall(text):
            found.update(folders.get(os.path.normpath(os.path.join(here, link)), ()))
        for token in {re.sub(r"^(\.{0,2}/)+", "", word).rstrip("./-") for word in TOKEN.findall(PIECES.sub("/", text))}:
            last = token.rsplit("/", 1)[-1]
            if "." in last or "/" in token:
                found.update(file for file in by_name.get(last, ()) if file == token or file.endswith("/" + token) or token.endswith("/" + file))
            if reads_folders:
                for folder, members in folders.items():
                    parent = folder.rsplit("/", 1)[0] if "/" in folder else ""
                    near = "/" in token or not parent or path.startswith(parent + "/")
                    if near and folder.rsplit("/", 1)[-1] == last and (folder == token or folder.endswith("/" + token)):
                        found.update(member for member in members if is_fixture(member) and not member.endswith(PROGRAMS))
        found.discard(path)
        references[path] = found
    return references


def find_reached(files, references, imports):
    """The files a plugin's entry points reach, and the fixtures that stay alive beside them."""
    reached = {path for path in files if "/" not in path or path in (".claude-plugin/plugin.json", "hooks/hooks.json", "monitors/monitors.json")
               or re.fullmatch(r"skills/[^/]+/SKILL\.md", path)}
    changed = True
    while changed:
        changed = False
        for path in files:
            if path in reached:
                continue
            fixture = is_fixture(path)
            named = any(path in references[source] and (fixture or not is_fixture(source)) or path in imports[source] for source in reached)
            replays = fixture and path.endswith(PROGRAMS) and any(target in reached for target in references[path] | imports[path])
            if named or replays:
                reached.add(path)
                changed = True
    return reached


def read_python(trees, texts, paths):
    """The functions defined, the roots (dunder or decorated), the names each function (None: module level) uses, and the imports of the Python files."""
    defined, roots, uses, imported = [], set(), {}, []
    for path in sorted(paths):
        tree = trees.get(path)
        if tree is None:
            continue
        lines = texts[path].splitlines()
        docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                      if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                      and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
        used, dynamic = set(), []

        def visit(node, owner):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.decorator_list or node.name.startswith("__") and node.name.endswith("__"):
                    roots.add(node.name)
                else:
                    defined.append((path, node.lineno, node.name))
                owner = node.name
            name = (node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else node.attr if isinstance(node, ast.Attribute)
                    else node.value if isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value.isidentifier() and id(node) not in docstrings else None)
            if name:
                uses.setdefault(owner, set()).add(name)
                used.add(name)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "getattr" and len(node.args) > 1 and not isinstance(node.args[1], ast.Constant):
                dynamic.append(node)
            if isinstance(node, (ast.Import, ast.ImportFrom)) and "noqa" not in lines[node.lineno - 1]:
                for alias in node.names:
                    bound = (alias.asname or alias.name).split(".")[0]
                    if bound != "*" and getattr(node, "module", None) != "__future__":
                        imported.append((path, node.lineno, bound, used))
            for child in ast.iter_child_nodes(node):
                visit(child, owner)

        visit(tree, None)
        if dynamic:
            roots.update(name for file, _, name in defined if file == path)
            defined[:] = [row for row in defined if row[0] != path]
    return defined, roots, uses, imported


def find_unused(trees, texts, paths):
    """The functions no live code calls, and the imports no code of their file uses, as (path, line, name) rows."""
    defined, roots, uses, imported = read_python(trees, texts, paths)
    live, queue = set(), [None, *roots]
    while queue:
        for name in uses.get(queue.pop(), ()):
            if name not in live:
                live.add(name)
                queue.append(name)
    functions = [row for row in defined if row[2] not in live]
    imports = [(path, line, name) for path, line, name, used in imported if name not in used]
    return functions, imports


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else ROOT).resolve()
    printed = file_count = 0
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        files = list_files(plugin)
        texts = {path: read_text(plugin, path) for path in files}
        trees = {path: parse(text) for path, text in texts.items() if path.endswith(".py")}
        reached = find_reached(files, find_references(texts), find_imports(trees, files))
        functions, imports = find_unused(trees, texts, reached)
        lines = ["unreached {}/{}".format(plugin.name, path) for path in files if path not in reached]
        lines += ["unused {}/{}:{} {}".format(plugin.name, path, line, name) for path, line, name in functions]
        lines += ["unused {}/{}:{} import {}".format(plugin.name, path, line, name) for path, line, name in imports]
        for line in lines:
            print(line)
        printed += len(lines)
        file_count += len(files)
    print("{} files, {} unreached or unused".format(file_count, printed))
    return 1 if printed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
