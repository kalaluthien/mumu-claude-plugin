#!/usr/bin/env python3
"""Write the briefs of one grading: the target once, in delimiters, and one brief per judge call.

usage: write-briefs.py RUBRIC.json SOURCE_DIR OUT_DIR   SOURCE_DIR is a local copy of the target

It writes OUT_DIR/target.txt and OUT_DIR/run-<r>-call-<c>.md, each asking for OUT_DIR/run-<r>-call-<c>.json; a short
target takes one call per run, a long one at most 3 criteria per call, and each run shuffles the order.
"""
import math
import pathlib
import random
import secrets
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rubric.check import Refused, read_rubric  # noqa: E402
from rubric.verdict import RUNS  # noqa: E402

BRIEF = pathlib.Path(__file__).resolve().parents[1] / "assets" / "judge-brief.md"
# About 20,000 tokens: between the outputs of 7,000 tokens where batching changed little and 49,000 where it cost
# double digits (https://arxiv.org/abs/2606.29920); the cut itself is not measured.
LONG_CHARACTERS = 80_000
CALL_SIZE = 3


def files(source):
    root = pathlib.Path(source)
    for path in sorted(path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts):
        try:
            yield path.relative_to(root), path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def target_text(source, delimiter):
    numbered = [f"=== {name}\n" + "".join(f"{i}: {text}\n" for i, text in enumerate(body.splitlines(), 1)) for name, body in files(source)]
    return f"<{delimiter}>\n{''.join(numbered)}</{delimiter}>\n"


def criterion_block(criterion):
    notes = [f"Means here: {criterion['anchors']}"] if criterion.get("anchors") else []
    notes += ["Absence: list every item first, then check each."] if criterion.get("absence") else []
    return "\n".join([f"### {criterion['id']}", criterion["text"], *notes])


def write(rubric, source, folder):
    folder.mkdir(parents=True, exist_ok=True)
    delimiter = f"target-{secrets.token_hex(4)}"
    text = target_text(source, delimiter)
    (folder / "target.txt").write_text(text, encoding="utf-8")
    judged = [criterion for criterion in rubric["criteria"] if criterion["check"] == "judge"]
    if not judged:
        raise Refused("no criterion needs a judge; run merge-runs.py on an empty folder")
    size = min(CALL_SIZE, len(judged)) if sum(len(body) for _, body in files(source)) > LONG_CHARACTERS else len(judged)
    calls = math.ceil(len(judged) / size)
    brief = BRIEF.read_text(encoding="utf-8").replace("__TARGET__", str(folder / "target.txt")).replace("__DELIMITER__", delimiter)
    for run in range(1, RUNS + 1):
        shuffled = random.Random(run).sample(judged, len(judged))
        for call in range(calls):
            part = shuffled[call * size:(call + 1) * size]
            name = f"run-{run}-call-{call + 1}"
            (folder / f"{name}.md").write_text(
                brief.replace("__RESULT__", str(folder / f"{name}.json")).replace("__CRITERIA__", "\n\n".join(map(criterion_block, part))), encoding="utf-8")
    print(f"Hand each run-*.md to its own fresh judge: {RUNS * calls} calls.")
    return f"{RUNS} runs, {calls} calls per run, at most {size} criteria per call" if calls > 1 else f"{RUNS} runs, 1 call per run, {size} criteria per call"


def main(args):
    if len(args) != 3 or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(write(read_rubric(args[0])[0], args[1], pathlib.Path(args[2])))
    except (Refused, OSError, ValueError) as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
