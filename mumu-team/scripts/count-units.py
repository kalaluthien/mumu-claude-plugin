#!/usr/bin/env python3
"""Print mumu-team's size: files, features and lines by code, then instructions, duplicates, elaboration and
terms by Sonnet against lib/size-rubric.md, each Sonnet item with its `path:line`.

usage: count-units.py [<plugin-dir>] [--model <model>] [--samples <n>] [--jobs <n>] [--json <file>] [--out <dir>]

<plugin-dir> defaults to this plugin. Features: skills, agents, hook registrations, monitors, `bin/`
executables and eval cases, each listed by name. Sonnet reads every `.md` file outside `tests/` and `evals/`,
the rubric excepted, cut by code into numbered sentences. Each ask runs --samples times (3) and the majority
stands: per file, each sentence's instructions and elaboration by their median and the terms most name; over
every instruction-bearing sentence, the duplicate groups; over every term, the variant groups. --json also
writes the whole result, and --out keeps each reply, reused by a rerun into it. Exit 0 counted, 2 could not run.
"""
import argparse
import concurrent.futures
import json
import pathlib
import re
import statistics
import subprocess
import sys
import tempfile
import time

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = PLUGIN / "lib" / "size-rubric.md"
SKIPPED = ("tests", "evals", "__pycache__")
END = re.compile(r"(?<=[.?!])\s+(?=[A-Z`(\[*])|(?<=;)\s+")
FILE_ASK = """Count the file {path} by the rubric. It is cut into sentences, each on a line as `id| sentence`, the id
being its line number, a dot and its place in the line.
Reply with only one fenced json block that scores every sentence id as [instructions, elaboration] and lists the
file's terms, each once, at the line of its first use:
{{"sentences": {{"<id>": [0, 0], ...}}, "terms": [{{"name": "<the term>", "line": N}}, ...]}}

<file path="{path}">
{text}
</file>"""
DUPLICATE_ASK = """Below is every sentence of mumu-team that states an instruction, one per line as `id | path:line | sentence`.
Find the duplicates by the rubric: each group of two or more sentences that state one directive.
Reply with only one fenced json block: {{"groups": [["<id>", "<id>", ...], ...]}}, an empty list when none.

{items}"""
VARIANT_ASK = """Below is every term of mumu-team, one per line as `term | path:line | the line where it is first used`.
Find the variants by the rubric: each group of two or more terms that name one entity.
Reply with only one fenced json block: {{"variants": [["<term>", "<term>", ...], ...]}}, an empty list when none.

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


def lines(files):
    """{extension: line count} and the total."""
    by = {}
    for path in files:
        kind = path.suffix or path.name
        by[kind] = by.get(kind, 0) + len(path.read_text(errors="replace").splitlines())
    return dict(sorted(by.items(), key=lambda kv: -kv[1])), sum(by.values())


def texts(root):
    """The `.md` files Sonnet counts."""
    return [p for p in tree(root) if p.suffix == ".md" and p.relative_to(root).parts[0] not in SKIPPED
            and p.relative_to(root) != RUBRIC.relative_to(PLUGIN)]


def sentences(text):
    """[(id, line, sentence)] of a Markdown file's prose: fences, headings, table rules and blank lines left out,
    of the front matter only its description, each line cut after a sentence's end or a semicolon."""
    out, fenced, front = [], False, text.startswith("---\n")
    for n, line in enumerate(text.splitlines(), 1):
        if front:
            front = not (n > 1 and line == "---")
            if not line.startswith("description:"):
                continue
            line = line.removeprefix("description:")
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line.strip() or line.lstrip().startswith("#") or re.match(r"^\s*\|?\s*:?-{3}", line):
            continue
        for k, part in enumerate(END.split(line.strip()), 1):
            out.append((f"{n}.{k}", n, part))
    return out


def ask(prompt, model, name, out):
    """The last fenced json block of one fresh `claude -p` reply, the rubric as its system prompt; one retry.
    Each call's time goes to stderr, and its reply to `name` in `out` when given, which a rerun into the same
    folder reuses."""
    kept = out / f"{name.replace('/', '__')}.txt" if out else None
    if kept and kept.exists():
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", kept.read_text(), re.S)
        if blocks:
            return json.loads(blocks[-1])
    system = "You count text by this rubric, exactly and the same way every time.\n\n" + RUBRIC.read_text()
    for attempt in (1, 2):
        start = time.monotonic()
        with tempfile.TemporaryDirectory() as cwd:
            run = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--setting-sources", "",
                                  "--strict-mcp-config", "--no-session-persistence", "--system-prompt", system],
                                 input=prompt, capture_output=True, text=True, cwd=cwd, timeout=1800)
        print(f"{name}: {time.monotonic() - start:.0f}s, exit {run.returncode}", file=sys.stderr, flush=True)
        if kept:
            kept.write_text(run.stdout)
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", run.stdout, re.S)
        try:
            if not run.returncode and blocks:
                return json.loads(blocks[-1])
        except json.JSONDecodeError:
            pass
        if attempt == 2:
            raise RuntimeError(f"{name}: claude exited {run.returncode}: {(run.stderr or run.stdout)[-300:]}")


def term(name):
    """A term's name as counted: no quotes or backticks, no annotation, a command's arguments cut."""
    name = re.sub(r"\s*\(.*\)$", "", name.strip().strip("`'\"").strip())
    return re.split(r"\s+(?=[-<\[])", name)[0].strip("`").lower()


def votes(samples, name):
    """The name of each of `samples` asks: `name`, then `name.2` and on."""
    return [name if k == 1 else f"{name}.{k}" for k in range(1, samples + 1)]


def majority(groupings, samples):
    """The groups of items that fall in one group together in more than half of `samples` groupings, joined
    where they share an item, in the order first seen."""
    together, order = {}, {}
    for groups in groupings:
        for group in groups:
            for x in group:
                order.setdefault(x, len(order))
            for a in group:
                for b in group:
                    if order[a] < order[b]:
                        together[a, b] = together.get((a, b), 0) + 1
    parent = {x: x for x in order}

    def top(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for (a, b), n in together.items():
        if n * 2 > samples:
            parent[top(b)] = top(a)
    out = {}
    for x in sorted(order, key=order.get):
        out.setdefault(top(x), []).append(x)
    return [g for g in out.values() if len(g) > 1]


def count_file(path, root, model, out, samples, pool):
    """This file's sentences, each scored by the median of `samples` asks, and the terms more than half of them
    name, each with its path and line."""
    rel = path.relative_to(root).as_posix()
    cut = sentences(path.read_text())
    prompt = FILE_ASK.format(path=rel, text="\n".join(f"{i}| {s}" for i, _, s in cut))
    found = list(pool.map(lambda name: ask(prompt, model, name, out), votes(samples, rel)))
    rows = []
    for i, n, s in cut:
        scored = [(list(f["sentences"].get(i) or [0, 0]) + [0, 0])[:2] for f in found]
        rows.append({"id": f"{rel}#{i}", "path": rel, "line": n, "text": s,
                     "instructions": statistics.median_low(int(x[0]) for x in scored),
                     "elaboration": statistics.median_low(int(x[1]) for x in scored)})
    named = {}
    for f in found:
        for name, t in {term(t["name"]): t for t in f["terms"] if term(t["name"])}.items():
            named.setdefault(name, []).append(int(str(t["line"]).split(".")[0]))
    terms = [{"name": name, "path": rel, "line": min(at)} for name, at in named.items() if len(at) * 2 > samples]
    return rows, terms


def line_of(root, item):
    source = (root / item["path"]).read_text().splitlines()
    return source[item["line"] - 1].strip() if 0 < item["line"] <= len(source) else ""


def count(root, model, jobs, out=None, samples=3):
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool, concurrent.futures.ThreadPoolExecutor(jobs) as asks:
        per_file = list(pool.map(lambda p: count_file(p, root, model, out, samples, asks), texts(root)))
        rows = [r for f, _ in per_file for r in f]
        by_id = {r["id"]: r for r in rows if r["instructions"]}
        prompt = DUPLICATE_ASK.format(items="\n".join(f"{i} | {r['path']}:{r['line']} | {r['text']}" for i, r in by_id.items()))
        groups = majority([[[x for x in dict.fromkeys(g) if x in by_id] for g in reply["groups"]]
                           for reply in asks.map(lambda name: ask(prompt, model, name, out), votes(samples, "duplicates"))],
                          samples)
        first = {}
        for t in (t for _, ts in per_file for t in ts):
            first.setdefault(t["name"], t)
        prompt = VARIANT_ASK.format(items="\n".join(f"{name} | {t['path']}:{t['line']} | {line_of(root, t)}"
                                                     for name, t in first.items()))
        variants = majority([[[term(n) for n in dict.fromkeys(v) if term(n) in first] for v in reply["variants"]]
                             for reply in asks.map(lambda name: ask(prompt, model, name, out), votes(samples, "variants"))],
                            samples)
    return {"sentences": rows, "duplicates": [[by_id[x] for x in g] for g in groups], "terms": list(first.values()),
            "variants": [[first[n] for n in v] for v in variants]}


def where(item):
    return f"{item['path']}:{item['line']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("dir", nargs="?", type=pathlib.Path, default=PLUGIN)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--jobs", type=int, default=24)
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    root = args.dir.resolve()
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
    files = tree(root)
    by_kind, total = lines(files)
    found = features(root)
    print(f"files {len(files)}")
    print(f"features {sum(len(v) for v in found.values())}")
    for kind, names in found.items():
        print(f"  {kind} {len(names)}: {', '.join(names)}")
    print(f"lines {total}: " + ", ".join(f"{k} {v}" for k, v in by_kind.items()))
    try:
        units = count(root, args.model, args.jobs, args.out, args.samples)
    except (RuntimeError, subprocess.TimeoutExpired, KeyError, TypeError, ValueError, AttributeError) as error:
        print(f"could not count: {error}", file=sys.stderr)
        return 2
    rows = units["sentences"]
    totals = {"instructions": sum(r["instructions"] for r in rows),
              "duplicates": sum(len(g) - 1 for g in units["duplicates"]),
              "elaboration": sum(r["elaboration"] for r in rows), "terms": len(units["terms"]),
              "variants": len(units["variants"])}
    print(f"instructions {totals['instructions']}")
    print(f"duplicates {totals['duplicates']}")
    for group in units["duplicates"]:
        print("  " + " = ".join(f"{where(r)} {r['text'][:60]}" for r in group))
    print(f"elaboration {totals['elaboration']}")
    print(f"terms {totals['terms']}, variants {totals['variants']}")
    for group in units["variants"]:
        print("  " + " = ".join(f"{t['name']} {where(t)}" for t in group))
    print("\nitems:")
    for kind in ("instructions", "elaboration"):
        for r in rows:
            if r[kind]:
                print(f"  {kind[:-1] if kind == 'instructions' else kind} {r[kind]} {where(r)} {r['text'][:80]}")
    for t in units["terms"]:
        print(f"  term {where(t)} {t['name']}")
    if args.json:
        args.json.write_text(json.dumps({"files": len(files), "features": found, "lines": by_kind, "totals": totals,
                                         **units}, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
