#!/usr/bin/env python3
"""Print mumu-team's size: files, features and lines by code, then instructions, duplicates, elaboration and
terms by Sonnet against lib/size-rubric.md, each Sonnet item with its `path:line`.

usage: count-units.py [<plugin-dir>] [--model <model>] [--jobs <n>] [--json <file>] [--out <dir>]

<plugin-dir> defaults to this plugin. Features: skills, agents, hook registrations, monitors, `bin/`
executables and eval cases, each listed by name. Sonnet reads every `.md` file outside `tests/` and `evals/`,
the rubric excepted: one call per file for its instructions, elaboration and terms, then one call over every
instruction for duplicates and one over every term for variants. --json also writes the whole result,
and --out keeps each reply.
Exit 0 counted, 2 could not run.
"""
import argparse
import concurrent.futures
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = PLUGIN / "lib" / "size-rubric.md"
OUT = None
SKIPPED = ("tests", "evals", "__pycache__")
FILE_ASK = """Count the file {path} by the rubric: its instructions, elaboration and terms. Its lines are numbered `N| `.
Reply with only one fenced json block:
{{"instructions": [{{"line": N, "text": "<the directive, in a few words>"}}],
 "elaboration": [{{"line": N, "text": "<the sentence or clause, in a few words>"}}],
 "terms": [{{"line": N, "name": "<the name as written>"}}]}}
List a term once, at its first line in this file.

<file path="{path}">
{text}
</file>"""
DUPLICATE_ASK = """Below is every instruction counted in mumu-team, one per line as `id | path:line | directive`.
Find the duplicates by the rubric: each group of two or more instructions that state one directive.
Reply with only one fenced json block: {{"groups": [["<id>", "<id>", ...], ...]}}, an empty list when none.

{items}"""
VARIANT_ASK = """Below is every term counted in mumu-team, one per line as `name | path:line | the line where it is first used`.
Find the variants by the rubric: each group of two or more names for one entity.
Reply with only one fenced json block: {{"variants": [["<name>", "<name>", ...], ...]}}, an empty list when none.

{items}"""


def features(root):
    """{kind: [name, ...]} of the harness features the plugin registers."""
    hooks = root / "hooks" / "hooks.json"
    registrations = []
    for event, entries in (json.loads(hooks.read_text())["hooks"] if hooks.exists() else {}).items():
        for entry in entries:
            for hook in entry["hooks"]:
                command = pathlib.PurePosixPath(hook.get("command", "").split()[0].strip('"')).name
                registrations.append(f"{event}" + (f"[{entry['matcher']}]" if "matcher" in entry else "") + f" {command}")
    monitors = root / "monitors" / "monitors.json"
    return {
        "skills": sorted(p.parent.name for p in root.glob("skills/*/SKILL.md")),
        "agents": sorted(p.stem for p in root.glob("agents/*.md")),
        "hook registrations": registrations,
        "monitors": [m["name"] for m in json.loads(monitors.read_text())] if monitors.exists() else [],
        "bin executables": sorted(p.name for p in root.glob("bin/*") if p.is_file()),
        "eval cases": sorted(p.parent.name for p in root.glob("evals/*/prompt.md")),
    }


def tree(root):
    """Every file under the plugin, caches left out."""
    return sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def lines(files, root):
    """{extension: line count} and the total."""
    by = {}
    for path in files:
        by[path.suffix or path.name] = by.get(path.suffix or path.name, 0) + len(path.read_text(errors="replace").splitlines())
    return dict(sorted(by.items(), key=lambda kv: -kv[1])), sum(by.values())


def texts(root):
    """The `.md` files Sonnet counts, relative to the plugin."""
    return [p for p in tree(root) if p.suffix == ".md" and p.relative_to(root).parts[0] not in SKIPPED
            and p.relative_to(root) != RUBRIC.relative_to(PLUGIN)]


def ask(prompt, model, name):
    """The last fenced json block of one fresh `claude -p` reply, the rubric as its system prompt; one retry.
    Each call's time goes to stderr, and its reply to `name` in --out when given."""
    system = "You count text by this rubric, exactly and the same way every time.\n\n" + RUBRIC.read_text()
    for attempt in (1, 2):
        start = time.monotonic()
        with tempfile.TemporaryDirectory() as cwd:
            run = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--setting-sources", "",
                                  "--strict-mcp-config", "--no-session-persistence", "--system-prompt", system],
                                 input=prompt, capture_output=True, text=True, cwd=cwd, timeout=1800)
        print(f"{name}: {time.monotonic() - start:.0f}s, exit {run.returncode}", file=sys.stderr, flush=True)
        if OUT:
            (OUT / f"{name.replace('/', '__')}.txt").write_text(run.stdout)
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", run.stdout, re.S)
        try:
            if not run.returncode and blocks:
                return json.loads(blocks[-1])
        except json.JSONDecodeError:
            pass
        if attempt == 2:
            raise RuntimeError(f"claude exited {run.returncode}: {(run.stderr or run.stdout)[-300:]}")


def count_file(path, root, model):
    rel = path.relative_to(root).as_posix()
    numbered = "\n".join(f"{n}| {line}" for n, line in enumerate(path.read_text().splitlines(), 1))
    found = ask(FILE_ASK.format(path=rel, text=numbered), model, rel)
    return {kind: [dict(item, path=rel) for item in found.get(kind, [])] for kind in ("instructions", "elaboration", "terms")}


def line_of(root, item):
    source = (root / item["path"]).read_text().splitlines()
    return source[item["line"] - 1].strip() if 0 < item["line"] <= len(source) else ""


def count(root, model, jobs):
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
        per_file = list(pool.map(lambda p: count_file(p, root, model), texts(root)))
    items = {kind: [i for f in per_file for i in f[kind]] for kind in ("instructions", "elaboration", "terms")}
    for n, item in enumerate(items["instructions"]):
        item["id"] = f"i{n}"
    listing = "\n".join(f"{i['id']} | {i['path']}:{i['line']} | {i['text']}" for i in items["instructions"])
    by_id = {i["id"]: i for i in items["instructions"]}
    groups = [[by_id[x] for x in dict.fromkeys(g) if x in by_id] for g in ask(DUPLICATE_ASK.format(items=listing), model, "duplicates")["groups"]]
    groups = [g for g in groups if len(g) > 1]
    first = {}
    for term in items["terms"]:
        first.setdefault(term["name"], term)
    listing = "\n".join(f"{name} | {t['path']}:{t['line']} | {line_of(root, t)}" for name, t in first.items())
    variants = [[first[n] for n in dict.fromkeys(v) if n in first] for v in ask(VARIANT_ASK.format(items=listing), model, "variants")["variants"]]
    variants = [v for v in variants if len(v) > 1]
    return {"instructions": items["instructions"], "duplicates": groups, "elaboration": items["elaboration"],
            "terms": list(first.values()), "variants": variants}


def where(item):
    return f"{item['path']}:{item['line']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("dir", nargs="?", type=pathlib.Path, default=PLUGIN)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    global OUT
    OUT = args.out
    if OUT:
        OUT.mkdir(parents=True, exist_ok=True)
    root = args.dir.resolve()
    files = tree(root)
    by_kind, total = lines(files, root)
    found = features(root)
    print(f"files {len(files)}")
    print(f"features {sum(len(v) for v in found.values())}")
    for kind, names in found.items():
        print(f"  {kind} {len(names)}: {', '.join(names)}")
    print(f"lines {total}: " + ", ".join(f"{k} {v}" for k, v in by_kind.items()))
    try:
        units = count(root, args.model, args.jobs)
    except (RuntimeError, subprocess.TimeoutExpired, KeyError, TypeError) as error:
        print(f"could not count: {error}", file=sys.stderr)
        return 2
    duplicates = sum(len(g) - 1 for g in units["duplicates"])
    print(f"instructions {len(units['instructions'])}")
    print(f"duplicates {duplicates}")
    for group in units["duplicates"]:
        print("  " + " = ".join(f"{where(i)} {i['text']}" for i in group))
    print(f"elaboration {len(units['elaboration'])}")
    print(f"terms {len(units['terms'])}, variants {len(units['variants'])}")
    for group in units["variants"]:
        print("  " + " = ".join(f"{t['name']} {where(t)}" for t in group))
    print("\nitems:")
    for kind in ("instructions", "elaboration"):
        for item in units[kind]:
            print(f"  {kind[:-1] if kind == 'instructions' else kind} {where(item)} {item['text']}")
    for term in units["terms"]:
        print(f"  term {where(term)} {term['name']}")
    if args.json:
        args.json.write_text(json.dumps({"files": len(files), "features": found, "lines": by_kind, **units},
                                        indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
