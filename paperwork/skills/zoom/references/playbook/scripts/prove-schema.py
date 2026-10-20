#!/usr/bin/env python3
"""zoom: prove a Schema document's rules with Alloy 6.

  prove-schema.py doc.json [--als out.als]   write the document as an Alloy module (by default in the system's temp
                                             folder, its path on stderr), check each rule there, and print one line
                                             per rule, in the document's order:
      <rule>: pass                     no run within the scope breaks it
      <rule>: counterexample <trace>   a run breaks it; the trace names Schema node and edge ids
      <rule>: unproved: <reason>       no Alloy here, Alloy refused the module, or the check ran past the time limit

Exit status 0 once every rule has a line, 2 when the document cannot be read.
"""
import json
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from schema import prover as A  # noqa: E402
from schema.model import Model, shape  # noqa: E402


def lines(M, als_path):
    als, W, C = A.translate(M)
    als_path.write_text(als, encoding="utf-8")
    print(f"wrote {als_path}", file=sys.stderr)
    try:
        res = A.run(als)
    except RuntimeError as e:
        res = {"_refused": str(e).splitlines()[0]}
    out = []
    for name, _, _, _, slug in C:
        if res is None:
            why = "no Alloy (java and alloy.jar)"
        elif "_refused" in res:
            why = f"Alloy refused the module: {res['_refused']}"
        elif name in res.get("_slow", []) or name not in res:
            why = f"past {A.SECONDS} s"
        else:
            r = res[name]
            out.append(f"{slug}: counterexample {A.trace(W, r['instances'], slug)}" if r["sat"] else f"{slug}: pass")
            continue
        out.append(f"{slug}: unproved: {why}")
    return out


def main(args):
    if len(args) not in (1, 3) or (len(args) == 3 and args[1] != "--als"):
        print(__doc__, file=sys.stderr)
        return 2
    doc = pathlib.Path(args[0])
    data = json.loads(doc.read_text(encoding="utf-8"))
    if wrong := shape(data):
        print("\n".join(f"{rule}: {text}" for rule, text in wrong), file=sys.stderr)
        return 2
    als = pathlib.Path(args[2]) if len(args) == 3 else pathlib.Path(tempfile.gettempdir()) / f"{re.sub(r'[^A-Za-z0-9]+', '-', doc.resolve().parent.name + '-' + doc.stem)}.als"
    print("\n".join(lines(Model(data), als)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
