#!/usr/bin/env python3
"""Prove a Schema document's rules with Alloy 6.

usage: prove-schema.py doc.json [--als out.als] [--mutate] [--proofs out.json]
      write the document as an Alloy module (by default in the system's temp folder, its path on stderr), check each
      rule there, and print one line per rule, in the document's order:
      <rule>: pass                     no run within the scope breaks it
      <rule>: counterexample <trace>   a run breaks it; the trace names Schema node and edge ids
      <rule>: unproved: <reason>       no Alloy here, Alloy refused the module, or the check ran past the time limit
      With --mutate, each passing `must` is checked again on copies of the document that each drop one restriction (a
      sync by its name, or a `must` by its slug, the rule's own when it is a guard on an edge and so holds by
      construction), and its line ends:
      <rule>: pass, fails without <id>, ...   the restrictions whose loss breaks it: the pass can fail
      <rule>: pass, unfalsified                no single loss breaks it: it holds by the structure alone, or is vacuous
      a copy Alloy gives no answer for is named after either, as `(no answer without <id>, ...)`.
      With --proofs, it also writes the same verdicts as data for make-page.py: {"rules": [{slug, verdict, nodes, steps}]},
      verdict pass, counterexample or unproved, nodes the ids the rule concerns, and steps a counterexample's, each
      {nodes, edges} by id.
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


def lines(model, alloy_path):
    """One line per rule, and the same verdicts as data."""
    alloy_source, world, checks = prover.translate(model)
    alloy_path.write_text(alloy_source, encoding="utf-8")
    print(f"wrote {alloy_path}", file=sys.stderr)
    try:
        results = prover.run(alloy_source)
    except RuntimeError as e:
        results = {"_refused": str(e).splitlines()[0]}
    report, proofs = [], []
    for name, _, _, _, slug in checks:
        if results is None:
            why = "no Alloy (java and alloy.jar); run prove-schema.py --fetch"
        elif "_refused" in results:
            why = f"Alloy refused the module: {results['_refused']}"
        elif name in results.get("_slow", []) or name not in results:
            why = f"past {prover.SECONDS} s"
        elif results[name]["sat"]:
            report.append(f"{slug}: counterexample {prover.trace(world, results[name]['instances'], slug)}")
            proofs.append({"slug": slug, "verdict": "counterexample", **prover.proof(world, results[name]["instances"], slug)})
            continue
        else:
            report.append(f"{slug}: pass")
            proofs.append({"slug": slug, "verdict": "pass", "nodes": model.concerns(slug)})
            continue
        report.append(f"{slug}: unproved: {why}")
        proofs.append({"slug": slug, "verdict": "unproved", "why": why, "nodes": model.concerns(slug)})
    return report, proofs


def restrictions(data):
    """Each restriction the document places on its runs: (id, the document without it)."""
    for index, rule in enumerate(data["rules"]):
        if rule["kind"] == "must":   # a rule on an edge is a guard, so its own slug is among them
            variant = copy.deepcopy(data)
            variant["rules"][index]["kind"] = "should"   # still checked, no longer assumed or a guard
            yield rule["slug"], variant
    for path, sync in syncs(data):
        variant = copy.deepcopy(data)
        at = variant
        for key in path:
            at = at[key]
        at.remove(sync)
        yield sync["name"], variant


def syncs(value, path=()):
    """Every sync of every level, with the path to its list."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "syncs" and isinstance(child, list):
                yield from ((path + (key,), sync) for sync in child)
            else:
                yield from syncs(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from syncs(child, path + (index,))


def broken_by(data, slugs):
    """For each rule in `slugs`, the restrictions whose loss alone gives it a counterexample, and those whose copy
    Alloy gave no answer for."""
    outcome = {target_slug: ([], []) for target_slug in slugs}
    for target_slug in slugs:
        for restriction_id, variant in restrictions(data):
            alloy_source, _, checks = prover.translate(Model(variant))
            name = next(candidate_name for candidate_name, _, _, _, slug in checks if slug == target_slug)
            head, commands, _, name_of = prover._split(alloy_source)
            # only the rule under test runs, so each copy costs one Alloy call
            try:
                results = prover.run(head + "-- what Alloy checks\n" + next(command for command in commands if name_of(command) == name) + "\n")
            except RuntimeError:
                results = None
            if not results or name not in results:
                outcome[target_slug][1].append(restriction_id)
            elif results[name]["sat"]:
                outcome[target_slug][0].append(restriction_id)
    return outcome


def verdict(broken, unanswered):
    tail = f" (no answer without {', '.join(unanswered)})" if unanswered else ""
    return (f", fails without {', '.join(broken)}" if broken else ", unfalsified") + tail


def main(args):
    if args == ["--fetch"]:
        print(f"fetched {prover.fetch()}")
        return 0
    mutate = "--mutate" in args
    args = [argument for argument in args if argument != "--mutate"]
    paths = dict(zip(args[1::2], args[2::2]))
    if len(args) % 2 == 0 or args[0].startswith("--") or set(paths) - {"--als", "--proofs"} or len(paths) != len(args) // 2:
        print(__doc__, file=sys.stderr)
        return 2
    document = pathlib.Path(args[0])
    data = json.loads(document.read_text(encoding="utf-8"))
    if wrong := shape(data):
        print("\n".join(f"{rule}: {text}" for rule, text in wrong), file=sys.stderr)
        return 2
    alloy_path = pathlib.Path(paths["--als"]) if "--als" in paths else pathlib.Path(tempfile.gettempdir()) / f"{re.sub(r'[^A-Za-z0-9]+', '-', document.resolve().parent.name + '-' + document.stem)}.als"
    report, proofs = lines(Model(data), alloy_path)
    if "--proofs" in paths:
        pathlib.Path(paths["--proofs"]).write_text(json.dumps({"rules": proofs}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if mutate:
        musts = {rule["slug"] for rule in data["rules"] if rule["kind"] == "must"}
        passed = [line.split(": ")[0] for line in report if line.endswith(": pass") and line.split(": ")[0] in musts]
        found = broken_by(data, passed)
        report = [line + verdict(*found[line.split(": ")[0]]) if line.split(": ")[0] in found else line for line in report]
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
