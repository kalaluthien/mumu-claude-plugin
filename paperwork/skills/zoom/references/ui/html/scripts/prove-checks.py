#!/usr/bin/env python3
"""Each drawing check must be able to fail: one small mutation of a worked example per check, and the examples
must pass. The Schema's own checks are proved beside the Schema (../../../schema/scripts/check-schema.py).

When a check refuses something legitimate or the engine draws badly, change the one file that owns it, never a
single example, then run this and `build` every example.

usage: prove-checks.py
"""
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLES = HERE.parents[3] / "examples"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "lib"))
from page import view  # noqa: E402
from schema.model import levels_of  # noqa: E402

EXAMPLE_DOCUMENTS = {directory.name: view.merge(*(json.loads((directory / file_name).read_text(encoding="utf-8")) for file_name in ("schema.json", "view.json")))
      for directory in EXAMPLES.iterdir() if directory.is_dir()}


def find_level(document, level_id):
    return next(level for level, opener in levels_of(document) if (opener or "root") == level_id)


def find_node(document, node_id):
    return next(node for level, _ in levels_of(document) for node in level["nodes"] if node["id"] == node_id)


MUTATIONS = {
    "form": [("pull-request", lambda document: document.update(next="")),
             ("pull-request", lambda document: document["plan"].pop("views")),
             ("pull-request", lambda document: document["plan"]["views"].append({"name": "x", "level": "nowhere"}))],
    "size": ("pull-request", lambda document: find_level(document, "root")["nodes"].extend({"id": f"x{i}", "label": f"Extra{i}", "x": 5, "y": i} for i in range(4))),
    "phone": ("ai-native-company", lambda document: find_level(document, "root")["edges"].extend({"from": "lead", "to": target, "label": "steer", "what": "x"} for target in ("brain", "factory", "platform"))),
    "depth": ("self", lambda document: document.update(plan={"depth": "overview", "views": [{"name": "levels", "level": "level"}], "why": {"depth": "x"}})),
    "names": [("pull-request", lambda document: find_node(document, "push").update(label="밀어 넣기")),
              ("pull-request", lambda document: find_node(document, "push").setdefault("media", []).append({"type": "facts", "items": [["기준 커밋", "x"]]})),
              ("pull-request", lambda document: find_node(document, "push").setdefault("media", []).append({"type": "code", "title": "명령", "text": "x"})),
              ("pull-request", lambda document: document["screens"]["conversation"].update(title="대화"))],
    "facts": ("pull-request", lambda document: find_node(document, "push").setdefault("media", []).append({"type": "facts", "items": [["Question", document["plan"]["intent"]]]})),
    "prose": [("pull-request", lambda document: document.update(lang="ko", next="요청을 검사해요")),
              ("pull-request", lambda document: document.update(lang="ko", next="Alloy이 규칙을 풉니다.")),
              ("pull-request", lambda document: document.update(lang="ko", next="Alloy 가 규칙을 풉니다.")),
              ("pull-request", lambda document: document.update(lang="ko", next="위 그림을 봅니다."))],
}


def failing(document):
    return {name for name, problems, _ in view.run(*view.split(document)) if problems}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    bad = [f"example {name} fails {sorted(failed_checks)}" for name, document in sorted(EXAMPLE_DOCUMENTS.items()) if (failed_checks := failing(document))]
    for rule in ["form"] + [name for name, _, _ in view.RULES]:
        if rule not in MUTATIONS:
            bad.append(f"{rule}: no mutation shows it can fail")
            continue
        cases = MUTATIONS[rule] if isinstance(MUTATIONS[rule], list) else [MUTATIONS[rule]]
        for k, (example, mutate) in enumerate(cases):
            document = copy.deepcopy(EXAMPLE_DOCUMENTS[example])
            mutate(document)
            if rule not in failing(document):
                bad.append(f"{rule}: not caught by its mutation {k + 1} of {example}")
    bad += [f"{name}: no such check" for name in MUTATIONS if name not in view.CHECKS | {"form"}]   # a mutation of no check proves nothing
    print("\n".join(bad) if bad else f"ok: {len(view.RULES) + 1} drawing checks, each caught its mutation")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
