#!/usr/bin/env python3
"""Prove a Schema document's rules with Alloy 6.

usage: prove-schema.py doc.json [--als out.als] [--mutate]
      write the document as an Alloy module (by default in the system's temp folder, its path on stderr), check each
      rule there, and print one line per rule, in the document's order:
      <rule>: pass                     no run within the scope breaks it
      <rule>: counterexample <trace>   a run breaks it; the trace names Schema node and edge ids
      <rule>: unproved: <reason>       no Alloy here, Alloy refused the module, or the check ran past the time limit
      With --mutate, each passing `must` is checked again on copies of the document that each drop one restriction (a
      sync by its name, an operation's `<Op>:pre` or `<Op>:post`, or a `must` by its slug, the rule's own when it is a
      guard on an edge and so holds by construction), and its line ends:
      <rule>: pass, fails without <id>, ...   the restrictions whose loss breaks it: the pass can fail
      <rule>: pass, unfalsified                no single loss breaks it: it holds by the structure alone, or is vacuous
      a copy Alloy gives no answer for is named after either, as `(no answer without <id>, ...)`.
usage: prove-schema.py --fetch   download the pinned Alloy 6.2.0 jar to ~/.cache/paperwork-alloy/alloy.jar

Exit status 0 once every rule has a line, 2 when the document cannot be read.
"""
import copy
import json
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from schema import prover  # noqa: E402
from schema.model import Model, shape  # noqa: E402


def lines(model, als_path):
    als, world, checks = prover.translate(model)
    als_path.write_text(als, encoding="utf-8")
    print(f"wrote {als_path}", file=sys.stderr)
    try:
        res = prover.run(als)
    except RuntimeError as e:
        res = {"_refused": str(e).splitlines()[0]}
    out = []
    for name, _, _, _, slug in checks:
        if res is None:
            why = "no Alloy (java and alloy.jar); run prove-schema.py --fetch"
        elif "_refused" in res:
            why = f"Alloy refused the module: {res['_refused']}"
        elif name in res.get("_slow", []) or name not in res:
            why = f"past {prover.SECONDS} s"
        else:
            r = res[name]
            out.append(f"{slug}: counterexample {prover.trace(world, r['instances'], slug)}" if r["sat"] else f"{slug}: pass")
            continue
        out.append(f"{slug}: unproved: {why}")
    return out


def restrictions(data):
    """Each restriction the document places on its runs: (id, the document without it)."""
    for i, r in enumerate(data["rules"]):
        if r["kind"] == "must":   # a rule on an edge is a guard, so its own slug is among them
            d = copy.deepcopy(data)
            d["rules"][i]["kind"] = "should"   # still checked, no longer assumed or a guard
            yield r["slug"], d
    for i, op in enumerate(data.get("operations", [])):
        for part in ("pre", "post"):
            if part in op:
                d = copy.deepcopy(data)
                del d["operations"][i][part]
                yield f"{op['slug']}:{part}", d
    for path, sync in syncs(data):
        d = copy.deepcopy(data)
        at = d
        for k in path:
            at = at[k]
        at.remove(sync)
        yield sync["name"], d


def syncs(x, path=()):
    """Every sync of every level, with the path to its list."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "syncs" and isinstance(v, list):
                yield from ((path + (k,), s) for s in v)
            else:
                yield from syncs(v, path + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from syncs(v, path + (i,))


def broken_by(data, slugs):
    """For each rule in `slugs`, the restrictions whose loss alone gives it a counterexample, and those whose copy
    Alloy gave no answer for."""
    out = {s: ([], []) for s in slugs}
    for s in slugs:
        for rid, d in restrictions(data):
            als, _, checks = prover.translate(Model(d))
            name = next(n for n, _, _, _, slug in checks if slug == s)
            head, cmds, _, name_of = prover._split(als)
            # only the rule under test runs, so each copy costs one Alloy call
            try:
                res = prover.run(head + "-- what Alloy checks\n" + next(c for c in cmds if name_of(c) == name) + "\n")
            except RuntimeError:
                res = None
            if not res or name not in res:
                out[s][1].append(rid)
            elif res[name]["sat"]:
                out[s][0].append(rid)
    return out


def verdict(broken, unanswered):
    tail = f" (no answer without {', '.join(unanswered)})" if unanswered else ""
    return (f", fails without {', '.join(broken)}" if broken else ", unfalsified") + tail


def main(args):
    if args == ["--fetch"]:
        print(f"fetched {prover.fetch()}")
        return 0
    mutate = "--mutate" in args
    args = [a for a in args if a != "--mutate"]
    if len(args) not in (1, 3) or args[0].startswith("--") or (len(args) == 3 and args[1] != "--als"):
        print(__doc__, file=sys.stderr)
        return 2
    doc = pathlib.Path(args[0])
    data = json.loads(doc.read_text(encoding="utf-8"))
    if wrong := shape(data):
        print("\n".join(f"{rule}: {text}" for rule, text in wrong), file=sys.stderr)
        return 2
    als = pathlib.Path(args[2]) if len(args) == 3 else pathlib.Path(tempfile.gettempdir()) / f"{re.sub(r'[^A-Za-z0-9]+', '-', doc.resolve().parent.name + '-' + doc.stem)}.als"
    out = lines(Model(data), als)
    if mutate:
        musts = {r["slug"] for r in data["rules"] if r["kind"] == "must"}
        passed = [x.split(": ")[0] for x in out if x.endswith(": pass") and x.split(": ")[0] in musts]
        found = broken_by(data, passed)
        out = [x + verdict(*found[x.split(": ")[0]]) if x.split(": ")[0] in found else x for x in out]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
