#!/usr/bin/env python3
"""Read a task on a throwaway board as each role and print `PASS` as the last line when a worker sees the criteria and no `Judge note:` and a judge sees the decision, its `Judge note:` and the report but no `BLOCKED:` comment, and each playbook names its read form, else `FAIL: <what it saw>`.

usage: replay-visibility.py"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
NOTE = "Run the probe at head and base; try zero rows."
ASK = "which of the two layouts does the owner want?"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("visibility-") as work:
        sandbox = replay_probe.Sandbox(work)

        def use(*argv, claude=None):
            return sandbox.python(USE, *map(str, argv), claude=claude)

        def post(verb, number, key, line, rest="", claude=None):
            done = use(verb, number, key, line, *(["--text", replay_probe.write_text(work, "text.md", rest)] if rest else []), claude=claude)
            if done.returncode:
                raise SystemExit(f"replay-visibility: {verb} refused: {done.stderr}")

        filed = use("file", "--title", "Probe visibility", "--body", replay_probe.write_text(work, "body.md", replay_probe.BODY))
        if filed.returncode:
            return replay_probe.fail(f"cannot file the task: {filed.stderr}")
        number = filed.stdout.strip().rsplit("/", 1)[1]
        post("decide", number, "--decision", "probe routing", f"Judge note: {NOTE}\n", ["--name", "probe-manager"])
        post("comment", number, "--blocked", ASK)
        post("comment", number, "--reported", "probe findings")
        seen = {role: use("read", number, "--as", role) for role in ("worker", "judge")}
    worker, judge = seen["worker"].stdout, seen["judge"].stdout
    wrong = [text for ok, text in (
        (all(seen[role].returncode == 0 for role in seen), f"read --as exited non-zero: {[seen[role].stderr for role in seen]}"),
        ("Definition of done" in worker and "[check]" in worker, "the worker lacks the criteria"),
        (NOTE not in worker, "the worker sees the Judge note"),
        ("probe routing" in judge and NOTE in judge and "REPORTED: probe findings" in judge, "the judge lacks the decision, its note or the report"),
        (ASK not in judge, "the judge sees the BLOCKED comment"),
        ("--as worker" in (HERE.parent / "references" / "worker.md").read_text(), "worker.md does not name `--as worker`"),
        ("--as judge" in (HERE.parent / "references" / "judge.md").read_text(), "judge.md does not name `--as judge`"),
    ) if not ok]
    if wrong:
        return replay_probe.fail("; ".join(wrong))
    return replay_probe.Cases().finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
