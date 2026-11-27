#!/usr/bin/env python3
"""Check that `use-board.py file --parent` adds a part under a root whose body has no `## Definition of done`, through a scratch git repository, and print
`ok <case>` or `fail <case>: <what it saw>`, then `PASS part section` or `FAIL part section`; exit 1 on any failure:
- `added`: the call exits 0, and the parent's body ends with its old text, a blank line, `## Definition of done` and `1. [task] #<part> <title>`.

usage: replay-part-section.py"""
import pathlib
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
SUMMARY = "A root with no done section."


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("part section")
    with replay_probe.scratch("part-section-") as work:
        box = replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1)])
        repository = box.init(work / "repository")
        root = box.python(USE, "file", "--title", "Probe a bare root", "--body", replay_probe.write_text(work, "root.md", f"{SUMMARY}\n"), cwd=repository)
        part = box.python(USE, "file", "--title", "Probe a part", "--body", replay_probe.write_text(work, "part.md", replay_probe.BODY), "--parent", "1", cwd=repository)
        number = part.stdout.strip().rsplit("#", 1)[0].rsplit("/", 1)[-1]
        body = box.evaluate("import board, json; print(json.dumps(board.fresh(1)['body']))", cwd=repository) if part.returncode == 0 else None
        cases.step("added", root.returncode == 0 and part.returncode == 0 and body == f"{SUMMARY}\n\n## Definition of done\n1. [task] #{number} Probe a part\n",
                   [root.stderr, part.stderr, body])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
