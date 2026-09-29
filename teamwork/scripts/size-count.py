#!/usr/bin/env python3
"""Print teamwork's size: files, features and lines by code, then instructions, duplicates, elaboration and
terms by Sonnet against lib/size-rubric.md, each Sonnet item with its `path:line`.

usage: size-count.py [<plugin-dir>] [--model <model>] [--samples <n>] [--jobs <n>] [--json <file>] [--out <dir>]

<plugin-dir> defaults to this plugin. Features: skills, agents, hook registrations, monitors, `bin/`
executables and eval cases, each listed by name. Sonnet reads every `.md` file outside `tests/` and `evals/`,
the rubric excepted, cut by code into numbered sentences. Each ask runs --samples times (3) and the majority
stands: per file, each sentence's instructions and elaboration by their median and the terms most name; for
each instruction-bearing sentence and the NEAR sentences sharing the most words, whether the pair is one
directive, the pairs joined into duplicate groups; over every term, the variant groups. --json also
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
CHUNK = 60
NEAR = 3
PAIRS = 80
QUERIES = 40
WORD = re.compile(r"[a-z0-9_:./<>-]{3,}")
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
DUPLICATE_ASK = """Below are pairs of sentences of teamwork that state instructions, one pair per line as
`pair | path:line | sentence || path:line | sentence`. Score each pair 1 when its two sentences state one directive, a
duplicate by the rubric, else 0.
Reply with only one fenced json block that scores every pair: {{"pairs": {{"<pair>": 0, ...}}}}

{items}"""
VARIANT_ASK = """Below is every term of teamwork, one per line as `term | path:line | the line where it is first used`,
then some of them as queries. For each query, find by the rubric every other term that names the same entity.
Reply with only one fenced json block: {{"variants": {{"<query>": ["<term>", ...], ...}}}}, an empty list for a
query with none.

<terms>
{items}
</terms>

Queries: {queries}"""


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


def ask(prompt, model, name, out, need):
    """The last fenced json block of one fresh `claude -p` reply that has the key `need`, the rubric as its
    system prompt; one retry.
    Each call's time goes to stderr, and its reply to `name` in `out` when given, which a rerun into the same
    folder reuses."""
    kept = out / f"{name.replace('/', '__')}.txt" if out else None
    if kept and kept.exists():
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", kept.read_text(), re.S)
        if blocks and need in (found := json.loads(blocks[-1])):
            return found
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
            if not run.returncode and blocks and need in (found := json.loads(blocks[-1])):
                return found
        except json.JSONDecodeError:
            pass
        if attempt == 2:
            raise RuntimeError(f"{name}: claude exited {run.returncode}: {(run.stderr or run.stdout)[-300:]}")


def term(name):
    """A term's name as counted: no quotes or backticks, no annotation, a command's arguments cut."""
    name = re.sub(r"\s*\(.*\)$", "", name.strip().lstrip("#").strip().strip("`'\"").strip())
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


def neighbours(by_id):
    """Each instruction sentence paired with its NEAR sentences sharing the most words, by Jaccard, each pair once in
    the order first met."""
    ids = list(by_id)
    bags = {i: set(WORD.findall(by_id[i]["text"].lower())) for i in ids}
    out = {}
    for a in ids:
        scored = sorted(((len(bags[a] & bags[b]) / len(bags[a] | bags[b]), b) for b in ids if b != a and bags[a] & bags[b]),
                        key=lambda x: -x[0])
        for _, b in scored[:NEAR]:
            out.setdefault(tuple(sorted((a, b), key=ids.index)), None)
    return list(out)


def count_file(path, root, model, out, samples, pool):
    """This file's sentences, each scored by the median of `samples` asks, and the terms more than half of them
    name, each with its path and line; a file of more than CHUNK sentences is asked in even parts."""
    rel = path.relative_to(root).as_posix()
    cut = sentences(path.read_text())
    size = -(-len(cut) // -(-len(cut) // CHUNK)) if cut else 1
    parts = [cut[k:k + size] for k in range(0, len(cut), size)]
    jobs = [(FILE_ASK.format(path=rel, text="\n".join(f"{i}| {s}" for i, _, s in part)),
             name if k == 1 else f"{name}@{k}") for name in votes(samples, rel) for k, part in enumerate(parts, 1)]
    replies = list(pool.map(lambda job: ask(job[0], model, job[1], out, "sentences"), jobs))
    found = []
    for n in range(samples):
        mine = replies[n * len(parts):(n + 1) * len(parts)]
        found.append({"sentences": {i: v for r in mine for i, v in r["sentences"].items()},
                      "terms": [t for r in mine for t in r.get("terms", [])]})
    rows = []
    for i, n, s in cut:
        scored = [(list(f["sentences"].get(i) or [0, 0]) + [0, 0])[:2] for f in found]
        rows.append({"id": f"{rel}#{i}", "path": rel, "line": n, "text": s,
                     "instructions": statistics.median_low(int(x[0]) for x in scored),
                     "elaboration": statistics.median_low(int(x[1]) for x in scored)})
    whole(rows)
    named = {}
    for f in found:
        for name, t in {term(t["name"]): t for t in f["terms"] if term(t["name"])}.items():
            named.setdefault(name, []).append(int(str(t["line"]).split(".")[0]))
    terms = [{"name": name, "path": rel, "line": min(at)} for name, at in named.items() if len(at) * 2 > samples]
    return rows, terms


def whole(rows):
    """A sentence cut only at its semicolons that directs nothing scores one elaboration, on its first part."""
    k = 0
    while k < len(rows):
        end = k
        while end + 1 < len(rows) and rows[end]["text"].endswith(";") and rows[end + 1]["line"] == rows[k]["line"]:
            end += 1
        part = rows[k:end + 1]
        if len(part) > 1 and not any(r["instructions"] for r in part) and any(r["elaboration"] for r in part):
            for r in part:
                r["elaboration"] = int(r is part[0])
        k = end + 1


def line_of(root, item):
    source = (root / item["path"]).read_text().splitlines()
    return source[item["line"] - 1].strip() if 0 < item["line"] <= len(source) else ""


def count(root, model, jobs, out=None, samples=3):
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool, concurrent.futures.ThreadPoolExecutor(jobs) as asks:
        per_file = list(pool.map(lambda p: count_file(p, root, model, out, samples, asks), texts(root)))
        rows = [r for f, _ in per_file for r in f]
        by_id = {r["id"]: r for r in rows if r["instructions"]}
        near = [f"{a}|{b}" for a, b in neighbours(by_id)]
        batches = [near[k:k + PAIRS] for k in range(0, len(near), PAIRS)]
        jobs = [(DUPLICATE_ASK.format(items="\n".join(
                    f"{pair} | {where(by_id[pair.split('|')[0]])} | {by_id[pair.split('|')[0]]['text']} || "
                    f"{where(by_id[pair.split('|')[1]])} | {by_id[pair.split('|')[1]]['text']}" for pair in batch)),
                 name if k == 1 else f"{name}@{k}") for name in votes(samples, "duplicates") for k, batch in enumerate(batches, 1)]
        replies = list(asks.map(lambda job: ask(job[0], model, job[1], out, "pairs"), jobs))
        groups = majority([[pair.split("|") for r in replies[n * len(batches):(n + 1) * len(batches)]
                            for pair, same in r["pairs"].items() if same == 1 and pair in near]
                           for n in range(samples)], samples)
        first = {}
        for t in (t for _, ts in per_file for t in ts):
            first.setdefault(t["name"], t)
        items = "\n".join(f"{name} | {t['path']}:{t['line']} | {line_of(root, t)}" for name, t in first.items())
        names = list(first)
        queries = [names[k:k + QUERIES] for k in range(0, len(names), QUERIES)]
        jobs = [(VARIANT_ASK.format(items=items, queries=", ".join(q)), name if k == 1 else f"{name}@{k}")
                for name in votes(samples, "variants") for k, q in enumerate(queries, 1)]
        replies = list(asks.map(lambda job: ask(job[0], model, job[1], out, "variants"), jobs))
        variants = majority([[[term(q), term(v)] for r in replies[n * len(queries):(n + 1) * len(queries)]
                              for q, found in r["variants"].items() for v in found
                              if term(q) in first and term(v) in first and term(v) != term(q)]
                             for n in range(samples)], samples)
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
