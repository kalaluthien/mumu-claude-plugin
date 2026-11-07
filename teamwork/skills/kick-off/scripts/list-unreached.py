#!/usr/bin/env python3
"""List each tracked teamwork file no entry point reaches, each Python function nothing calls and each import nothing uses.

usage: list-unreached.py [plugin-folder]

Entry points are plugin.json, hooks/hooks.json, monitors/monitors.json and each skill's SKILL.md. A file is reached when
a reached file names its path or its unique base name, or for a lib module imports it. A fixture is live when a reached
or live file names it, or when it is a replay or render script that runs a reached hook, monitor or skill script; `KEPT`
names the files a live caller keeps that no text names. Prints `kept <path>: <reason>`, `unreached <path>` and
`unused <path>:<line> <name>` lines, then a summary, and exits 1 when it printed an unreached or unused line, else 0.
"""

import ast
import pathlib
import re
import subprocess
import sys

GENERIC_FOLDERS = {"fixtures", "scripts", "references", "hooks", "lib", "skills", "monitors", "types", "kick-off", "issues"}
REPLAY_NAME = re.compile(r"(^|/)(replay|check|probe|compare|render)-[^/]*\.(py|ts)$")
# What no text names but a live caller keeps; each reason names that caller.
KEPT = {
    "lib/agent_claude.py": "lib/agent.py imports it as agent_<TEAMWORK_AGENT>, default claude",
    "hooks/fixtures/count-start-text.py": "criterion 3 of open #1254 runs it",
    "skills/kick-off/fixtures/check-deletion.py": "the criteria of a deletion task run it, #1256's included",
    "skills/kick-off/scripts/list-unreached.py": "criterion 2 of #1256 runs it",
    "skills/kick-off/fixtures/replay-kept-fixtures.py": "criterion 3 of #1256 runs it",
    "skills/kick-off/fixtures/deep-decision-nodes.json": "the nodes file render-task-pane.ts reads for the decisions pane",
    "skills/kick-off/fixtures/deep-task-nodes.json": "the nodes file render-task-pane.ts reads for the task pane",
}
# A replay is live when it runs a hook, a monitor or a skill script, not a lib module alone.
RUNNABLE = re.compile(r"^(hooks/[^/]+|monitors/[^/]+|skills/[^/]+/scripts/[^/]+)$")
DUNDER = re.compile(r"^__\w+__$")


def tracked_files(plugin):
    out = subprocess.run(
        ["git", "-C", str(plugin), "ls-files", "-z", "--full-name", "."],
        capture_output=True, text=True, check=True,
    ).stdout
    top = subprocess.run(
        ["git", "-C", str(plugin), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    prefix = str(plugin.resolve().relative_to(pathlib.Path(top).resolve()))
    return sorted(p[len(prefix) + 1:] for p in out.split("\0") if p)


def read(plugin, path):
    try:
        return (plugin / path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def build_references(plugin, files):
    """Map each file to the set of other files its text names."""
    texts = {path: read(plugin, path) for path in files}
    by_base = {}
    for path in files:
        by_base.setdefault(path.rsplit("/", 1)[-1], []).append(path)
    modules = {path.rsplit("/", 1)[-1][:-3]: path for path in files if path.startswith("lib/") and path.endswith(".py")}
    folders = {}
    for path in files:
        for folder in path.split("/")[:-1]:
            if folder not in GENERIC_FOLDERS and not folder.startswith("."):
                folders.setdefault(folder, set()).add(path)
    references = {}
    for path, text in texts.items():
        found = set()
        for base, owners in by_base.items():
            if len(owners) == 1 and re.search(r"(?<![\w.-])" + re.escape(base) + r"(?![\w-])", text):
                found.update(owners)
        for module, owner in modules.items():
            if re.search(r"^\s*(from|import)\s+" + re.escape(module) + r"\b", text, re.M):
                found.add(owner)
        for folder, members in folders.items():
            if re.search(r"(?<![\w-])" + re.escape(folder) + r"/", text):
                found.update(members)
        found.discard(path)
        references[path] = found
    return references


def reach(roots, references, allowed):
    seen = set(roots)
    queue = list(roots)
    while queue:
        for target in references.get(queue.pop(), ()):
            if target in allowed and target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def unused_functions(plugin, files, dead_files):
    """Top-level functions and methods whose name no live code mentions but their own def."""
    definitions = []
    sources = {}
    for path in files:
        if not path.endswith(".py") or path in dead_files:
            continue
        text = read(plugin, path)
        sources[path] = text
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not DUNDER.match(node.name) and node.name != "main":
                definitions.append((path, node))
    other_text = "\n".join(read(plugin, path) for path in files if not path.endswith(".py") and path not in dead_files)
    dead = []
    remaining = list(definitions)
    changed = True
    while changed:
        changed = False
        for path, node in list(remaining):
            pattern = re.compile(r"(?<![\w])" + re.escape(node.name) + r"(?![\w])")
            uses = len(pattern.findall(other_text))
            for text in sources.values():
                uses += len(pattern.findall(text))
            own = sum(1 for p, n in remaining if n.name == node.name)
            own_dead = sum(1 for p, n in dead if n.name == node.name)
            inside_dead = 0
            for p, n in dead:
                body = ast.get_source_segment(sources[p], n) or ""
                inside_dead += len(pattern.findall(body))
            # each definition of the name is one mention of it
            if uses - own - own_dead - inside_dead <= 0:
                dead.append((path, node))
                remaining.remove((path, node))
                changed = True
    return sorted(dead, key=lambda item: (item[0], item[1].lineno))


def unused_imports(plugin, files, dead_files):
    """Top-level imports of live Python files whose name no code in the file uses; a docstring or comment does not count."""
    found = []
    for path in files:
        if not path.endswith(".py") or path in dead_files:
            continue
        text = read(plugin, path)
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)) or "noqa" in lines[node.lineno - 1]:
                continue
            for alias in node.names:
                name = (alias.asname or alias.name).split(".")[0]
                if name != "*" and name not in used:
                    found.append((path, node.lineno, name))
    return found


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    plugin = pathlib.Path(args[0] if args else pathlib.Path(__file__).resolve().parents[3]).resolve()
    files = tracked_files(plugin)
    references = build_references(plugin, files)
    fixtures = {path for path in files if "/fixtures/" in path or path.startswith("fixtures/")}
    product = set(files) - fixtures
    entries = {path for path in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", path) or path == ".claude-plugin/plugin.json" or path in ("hooks/hooks.json", "monitors/monitors.json")}
    live = reach(entries, references, product)
    # a fixture is live when a live file names it, or it replays a live runnable file; what a live fixture names is live too
    live_fixtures = set()
    changed = True
    while changed:
        changed = False
        alive = live | live_fixtures | set(KEPT)
        for path in sorted(set(files) - alive):
            named_by_live = any(path in references[source] for source in alive)
            replays_live = path in fixtures and bool(REPLAY_NAME.search(path)) and any(RUNNABLE.match(target) for target in references[path] & alive)
            if named_by_live or replays_live:
                live_fixtures.add(path)
                changed = True
    alive = live | live_fixtures | set(KEPT)
    unreached = sorted(set(files) - alive)
    for path in sorted(KEPT):
        if path in files:
            print("kept {}: {}".format(path, KEPT[path]))
    for path in unreached:
        print("unreached " + path)
    dead_functions = unused_functions(plugin, files, set(unreached))
    for path, node in dead_functions:
        print("unused {}:{} {}".format(path, node.lineno, node.name))
    dead_imports = unused_imports(plugin, files, set(unreached))
    for path, line, name in dead_imports:
        print("unused {}:{} import {}".format(path, line, name))
    print("{} files, {} unreached, {} unused functions, {} unused imports".format(
        len(files), len(unreached), len(dead_functions), len(dead_imports)))
    return 1 if unreached or dead_functions or dead_imports else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
