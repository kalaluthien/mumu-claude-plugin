#!/usr/bin/env python3
"""Replay the calls a reader makes of check-contract.py and make-page.py, and the checker's `fixtures` call on broken fixture folders.

usage: replay-script-calls.py

Each call runs in a scratch folder of its own:
  breaks     `check <copy> --root <skill folder>` on chosen broken copies of `contract-copies.json` exits 1, prints the line that
             names where and what broke, and on stderr the count of the lines it printed
  passes     the same call on the copy `cited-lines`, whose evidence cites lines of the skill's own SKILL.md, prints `ok` and exits 0
  catalogue  `tags` and `rules` exit 0, printing a tag's line and a rule's line
  usage      a call with no word or an unknown `--x` exits 2 with `usage:` on stderr and nothing on stdout, for both scripts
  fixtures   in a copy of the skill and lib, `fixtures` exits 1 with a FAIL last line when a copy breaks no rule its name claims, and
             when no copy breaks one rule
  page       `make-page.py` writes a page from a copy whose title holds `&` and `<` and whose purpose holds `</script>`: the title
             escaped, every script element closed by its own end tag and the page data the contract itself
It prints `FAIL <call>: <reason>` per miss, then PASS or FAIL; exit 1 on a miss."""
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_copies import copies  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
CHECKER = SKILL / "scripts" / "check-contract.py"
BUILDER = SKILL / "scripts" / "make-page.py"
BREAKS = {  # each copy and the words of the line it must print: where it broke, and the words the checker builds from the contract
    "text-plain": "/nodes/1/purpose: text-plain: ",
    "milestone-order-interaction": "level lookup: milestone-order: checks-name then resolves-name then reads-shard then gives-up then returns-record"
                                   " then name-resolved then asks-owner then checks-name crosses the milestone `name-resolved` backwards",
    "order-acyclic": "level release: order-acyclic: publish-package then write-notes then publish-package come each before the next",
    "fragment-span-overlap": "fragment each-shard: fragment-span: overlaps `store-down` ",
    "text-plain-guard": "fragments/each-shard/operands/1/guard: text-plain: ",
    "name-form-claim-title": "claims one-owner: name-form: the title `One Owner` is no slug",
    "work-area": "edges asks-owner: work-area: a `work` row names `nowhere`, which is no area",
    "term-words-meaning": "terms/1/meaning: term-words: ",
    "name-english-term": "terms/1/term: name-english: `소유자 record` holds Korean",
}
TITLE = "Name lookup & owners < 5 s"


def run(script, words, folder):
    return subprocess.run([sys.executable, str(script), *words], cwd=folder, capture_output=True, text=True, timeout=120)


def breaks(held, folder):
    """Misses of the break lines and of the passing call."""
    missed = []
    for name, words in BREAKS.items():
        path = folder / f"{name}.json"
        path.write_text(json.dumps(held[name], ensure_ascii=False))
        done = run(CHECKER, ["check", str(path), "--root", str(SKILL)], folder)
        lines = done.stdout.splitlines()
        if done.returncode != 1 or not any(line.startswith(words) for line in lines) or not done.stderr.startswith(f"{len(lines)} breaks;"):
            missed.append(f"breaks {name}: exit {done.returncode}, no line opening `{words}` in {done.stdout[:300]!r}, stderr {done.stderr[:80]!r}")
    path = folder / "cited-lines.json"
    path.write_text(json.dumps(held["cited-lines"], ensure_ascii=False))
    done = run(CHECKER, ["check", str(path), "--root", str(SKILL)], folder)
    if done.returncode or done.stdout != "ok\n":
        missed.append(f"passes cited-lines: exit {done.returncode}, stdout {done.stdout[:300]!r}")
    return missed


def catalogue(folder):
    missed = []
    for word, line in (("tags", re.compile(r"^edge call: ", re.M)), ("rules", re.compile(r"^call-failure: a `call` between nodes of two areas", re.M))):
        done = run(CHECKER, [word], folder)
        if done.returncode or not line.search(done.stdout):
            missed.append(f"catalogue {word}: exit {done.returncode}, stdout {done.stdout[:120]!r}")
    return missed


def usage(folder):
    missed = []
    for script, words in ((CHECKER, []), (CHECKER, ["--x"]), (CHECKER, ["check", "--x"]), (CHECKER, ["order", "--x"]),
                          (BUILDER, []), (BUILDER, ["--x"]), (BUILDER, [str(SKILL / "fixtures" / "name-lookup.json"), "--x"])):
        done = run(script, words, folder)
        if done.returncode != 2 or done.stdout or "usage:" not in done.stderr:
            missed.append(f"usage {script.name} {' '.join(words) or '(no word)'}: exit {done.returncode}, stdout {done.stdout[:80]!r}")
    return missed


def fixtures(folder):
    """Misses of the `fixtures` call on two broken copies of the skill's fixtures."""
    missed = []
    for case, change, wanted in (("a copy breaking nothing it claims", lambda held: held["name-lookup"].update({"form-unchanged": []}),
                                  "FAIL form-unchanged: broke nothing, expected form"),
                                 ("no copy breaking call-failure", lambda held: held["name-lookup"].pop("call-failure"),
                                  "FAIL no fixture breaks call-failure")):
        copy = folder / case.replace(" ", "-") / "paperwork"
        shutil.copytree(SKILL, copy / "skills" / SKILL.name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(SKILL.parents[1] / "lib", copy / "lib", ignore=shutil.ignore_patterns("__pycache__"))
        held_path = copy / "skills" / SKILL.name / "fixtures" / "contract-copies.json"
        held = json.loads(held_path.read_text())
        change(held)
        held_path.write_text(json.dumps(held, ensure_ascii=False))
        done = run(copy / "skills" / SKILL.name / "scripts" / CHECKER.name, ["fixtures"], folder)
        lines = done.stdout.splitlines()
        if done.returncode != 1 or wanted not in lines or lines[-1:] != ["FAIL"]:
            missed.append(f"fixtures with {case}: exit {done.returncode}, no line `{wanted}`, last line {lines[-1:]}")
    return missed


def page(folder):
    contract = json.loads((SKILL / "fixtures" / "name-lookup.json").read_text())
    contract["title"] = TITLE
    contract["purpose"] += " It never ends a script with `</script>`."
    source, target = folder / "escaped.json", folder / "escaped.html"
    source.write_text(json.dumps(contract, ensure_ascii=False))
    done = run(BUILDER, [str(source), str(target)], folder)
    if done.returncode or not target.is_file():
        return [f"page: exit {done.returncode}, stderr {done.stderr[:200]!r}"]
    text = target.read_text()
    missed = []
    if f"<title>{html.escape(TITLE, quote=False)}</title>" not in text:
        missed.append(f"page: the title reads {re.search(r'<title>.*?</title>', text, re.S).group(0)[:120]!r}")
    if text.count("</script>") != text.count("<script"):
        missed.append(f"page: {text.count('<script')} script elements but {text.count('</script>')} end tags")
    data = re.search(r'<script type="application/json" id="page-data">(.*?)</script>', text, re.S)
    if not data or json.loads(data.group(1)) != contract:
        missed.append("page: the page data is not the contract")
    return missed


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    held = dict(copies(HERE))
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        missed = breaks(held, folder) + catalogue(folder) + usage(folder) + fixtures(folder) + page(folder)
    for line in missed:
        print(f"FAIL {line}")
    print("FAIL" if missed else "PASS")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
