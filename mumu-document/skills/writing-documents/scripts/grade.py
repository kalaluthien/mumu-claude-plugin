#!/usr/bin/env python3
"""Grade documents with rubric.md's judge procedure, each by fresh `claude -p` graders, and print the agreement.

usage: grade.py [<dir>] [--key <file>] [--write-key] [--out <dir>] [--without <step>]... [--only <file>]...
                [--model <model>] [--jobs <n>]

<dir> defaults to the plugin's tests/rubric/, its answer key to answer-key.json there. Each document is graded by
two graders under a neutral name, its first-line comment stripped (steps 1 and 2); a criterion they split on goes
to a third, and the median of three stands (step 5). Printed: per criterion, grader A against B (exact, within
one level, Cohen's kappa) and the settled score against the key (exact, within one); each dimension's profile of
every document; each `<base>-<dimension>-weakened` copy against its base. Last line `pass`, or `FAIL` when a
criterion is under the bar against the key: exact on under half the documents it applies to, or within one on
under 80%. --without drops a judge step from the graders' rubric, by its number, for an arm without it. --out
keeps each grader's reply, and a rerun into the same folder reuses them. Exit 0 pass, 1 FAIL, 2 could not run.
"""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import re
import statistics
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = SKILL / "references" / "rubric.md"
ANCHORS = SKILL.parents[1] / "tests" / "rubric"
KEY = "answer-key.json"
LEVELS = (0, 1, 2, 3)
EXACT_BAR, WITHIN_BAR = 0.5, 0.8
GRADERS = ("a", "b")
THIRD = "c"
REPLY = ("End your reply with one fenced json block that maps every criterion's name, exactly as its heading, "
         'to its score: 0, 1, 2, 3 or "n/a".')
BARE = 'Reply with only one fenced json block that maps every criterion\'s name to its score: 0, 1, 2, 3 or "n/a".'


def dimensions(rubric):
    """{criterion: dimension} in the rubric's order, up to the judge procedure."""
    out, dimension = {}, None
    for line in rubric.split("## Judge procedure", 1)[0].splitlines():
        if line.startswith("## "):
            dimension = line[3:].strip()
        elif line.startswith("### "):
            out[line[4:].strip()] = dimension
    return out


def without(rubric, steps):
    """The rubric with each numbered judge step in `steps` removed, heading and body."""
    head, _, procedure = rubric.partition("## Judge procedure")
    blocks = re.split(r"(?m)^(?=\d+\. \*\*)", procedure)
    kept = [b for b in blocks if not (m := re.match(r"(\d+)\. ", b)) or int(m.group(1)) not in steps]
    return head + "## Judge procedure" + "".join(kept)


def blind(path):
    """The document's text with a first-line comment (its provenance) stripped, and its neutral name."""
    text = path.read_text()
    text = re.sub(r"\A<!--.*?-->\n", "", text, flags=re.S)
    return text, f"doc-{int(hashlib.sha1(path.name.encode()).hexdigest(), 16) % 900 + 100}{path.suffix}"


def scores(reply, names):
    """{criterion: 0-3 or 'n/a'} from the reply's last json block; a name it lacks is None."""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", reply, re.S)
    raw = json.loads(blocks[-1]) if blocks else {}
    out = {}
    for name in names:
        value = raw.get(name)
        out[name] = "n/a" if str(value).strip().lower() in ("n/a", "na") else value if value in LEVELS else None
    return out


def grade(path, rubric, names, model, bare):
    text, name = blind(path)
    ask = f"Grade the document {name} against the rubric in your instructions.\n\n{BARE if bare else REPLY}\n\n" \
          f"<document name=\"{name}\">\n{text}\n</document>"
    system = "You are a grader. You grade one document against this rubric and its judge procedure.\n\n" + rubric
    with tempfile.TemporaryDirectory() as cwd:
        run = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--setting-sources", "",
                              "--strict-mcp-config", "--no-session-persistence", "--system-prompt", system],
                             input=ask, capture_output=True, text=True, cwd=cwd, timeout=1800)
    if run.returncode:
        raise RuntimeError(f"{path.name}: claude exited {run.returncode}: {run.stderr[-300:]}")
    found = scores(run.stdout, names)
    if None in found.values():
        raise RuntimeError(f"{path.name}: no score for {[n for n, v in found.items() if v is None]}")
    return run.stdout, found


def settle(values):
    """The settled score of one criterion from its graders' scores: `n/a` by two or more, else the median, the
    lower middle of an even count."""
    if values.count("n/a") * 2 >= len(values) and values.count("n/a") >= 2:
        return "n/a"
    numbers = sorted(v for v in values if v != "n/a")
    return statistics.median_low(numbers)


def kappa(pairs):
    """Cohen's kappa of paired labels, `n/a` a label of its own; None when chance agreement is total."""
    n = len(pairs)
    labels = {x for pair in pairs for x in pair}
    observed = sum(a == b for a, b in pairs) / n
    chance = sum(sum(a == x for a, _ in pairs) * sum(b == x for _, b in pairs) for x in labels) / n / n
    return None if chance == 1 else (observed - chance) / (1 - chance)


def agreement(pairs):
    """(exact, within one, applicable) over the pairs where either score is a number; a number against `n/a`
    agrees on neither."""
    scored = [(a, b) for a, b in pairs if "n/a" not in (a, b) or a != b]
    if not scored:
        return None, None, 0
    exact = sum(a == b for a, b in scored) / len(scored)
    within = sum("n/a" not in (a, b) and abs(a - b) <= 1 for a, b in scored) / len(scored)
    return exact, within, len(scored)


def profile(settled, names):
    """{dimension: mean of its scored criteria, or 'n/a'}."""
    out = {}
    for dimension in dict.fromkeys(names.values()):
        values = [settled[c] for c, d in names.items() if d == dimension and settled[c] != "n/a"]
        out[dimension] = round(sum(values) / len(values), 2) if values else "n/a"
    return out


def percent(x):
    return "—" if x is None else f"{x:.0%}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("dir", nargs="?", type=pathlib.Path, default=ANCHORS)
    parser.add_argument("--key", type=pathlib.Path)
    parser.add_argument("--write-key", action="store_true")
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--without", type=int, action="append", default=[])
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--model", default="opus")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    key_path = args.key or args.dir / KEY
    out = args.out or pathlib.Path(tempfile.mkdtemp(prefix="grade-"))
    out.mkdir(parents=True, exist_ok=True)
    rubric = without(RUBRIC.read_text(), set(args.without))
    names = dimensions(rubric)
    docs = sorted(p for p in args.dir.iterdir() if p.suffix in (".md", ".html") and (not args.only or p.name in args.only))
    if not docs:
        print(f"no .md or .html document in {args.dir}", file=sys.stderr)
        return 2
    bare = 3 in args.without

    def run(doc, grader):
        cached = out / f"{doc.name}.{grader}.txt"
        if cached.exists():
            return doc, grader, scores(cached.read_text(), names)
        reply, found = grade(doc, rubric, names, args.model, bare)
        cached.write_text(reply)
        return doc, grader, found

    graded = {d.name: {} for d in docs}
    try:
        with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
            for doc, grader, found in pool.map(lambda job: run(*job), [(d, g) for d in docs for g in GRADERS]):
                graded[doc.name][grader] = found
            split = [d for d in docs if any(graded[d.name]["a"][c] != graded[d.name]["b"][c] for c in names)]
            for doc, grader, found in pool.map(lambda d: run(d, THIRD), split):
                graded[doc.name][grader] = found
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"could not grade: {error}", file=sys.stderr)
        return 2
    settled = {}
    for doc, by in graded.items():
        settled[doc] = {c: by["a"][c] if by["a"][c] == by["b"][c] else settle([by[g][c] for g in "abc"])
                        for c in names}
    (out / "settled.json").write_text(json.dumps(settled, indent=1, ensure_ascii=False) + "\n")
    print(f"replies in {out}")
    if args.write_key:
        key_path.write_text(json.dumps(settled, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {key_path}")
    key = json.loads(key_path.read_text()) if key_path.exists() else {}

    print("\n| criterion | A vs B exact | within one | kappa | settled vs key exact | within one | n | bar |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    under = []
    for c in names:
        ab = [(graded[d]["a"][c], graded[d]["b"][c]) for d in graded]
        e, w, _ = agreement(ab)
        k = kappa(ab)
        vs = [(settled[d][c], key[d][c]) for d in graded if d in key and c in key[d]]
        ke, kw, n = agreement(vs) if vs else (None, None, 0)
        bar = "—" if not n else "pass" if ke >= EXACT_BAR and kw >= WITHIN_BAR else "under"
        if bar == "under":
            under.append(c)
        print(f"| {c} | {percent(e)} | {percent(w)} | {'—' if k is None else f'{k:.2f}'} | {percent(ke)} "
              f"| {percent(kw)} | {n} | {bar} |")

    profiles = {d: profile(settled[d], names) for d in settled}
    dims = list(dict.fromkeys(names.values()))
    print(f"\n| document | {' | '.join(dims)} |\n| --- |{' --- |' * len(dims)}")
    for d, p in profiles.items():
        print(f"| {d} | {' | '.join(str(p[x]) for x in dims)} |")

    pairs = [(d, re.sub(r"-[a-z]+-weakened(?=\.)", "", d)) for d in settled if "-weakened." in d]
    for weak, base in pairs:
        if base in settled:
            moved = [f"{c} {settled[base][c]}→{settled[weak][c]}" for c in names if settled[base][c] != settled[weak][c]]
            print(f"\n{base} → {weak}: " + ", ".join(f"{x} {profiles[base][x]}→{profiles[weak][x]}" for x in dims))
            print("  criteria moved: " + ("; ".join(moved) or "none"))

    for c in under:
        print(f"under the bar: {c}")
    print("FAIL" if under else "pass")
    return 1 if under else 0


if __name__ == "__main__":
    sys.exit(main())
