#!/usr/bin/env python3
"""Read a task on a throwaway board as each role and print `PASS` as the last line when a worker sees the criteria and no `Judge note:` and a judge sees the decision, its `Judge note:` and the report but no `BLOCKED:` comment, and each playbook names its read form, else `FAIL: <what it saw>`.

usage: replay-visibility.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
NOTE = "Run the probe at head and base; try zero rows."
ASK = "which of the two layouts does the owner want?"
BODY = f"## Goal\n\nProbe visibility.\nPath: caller: probe-worker; before: filing; after: reading; meets: teamwork-manager\n\n## Definition of done\n\n{replay_probe.CHECK}"


def use(*argv):
    return subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True)


def post(verb, number, text, work, *options):
    path = work / f"text-{abs(hash(text))}.md"
    path.write_text(text)
    done = use(verb, number, path, *options)
    if done.returncode:
        raise SystemExit(f"replay-visibility: {verb} refused: {done.stderr}")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="visibility-"))
    os.environ.update({"HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "config")})
    subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
    os.chdir(work / "repo")
    path = work / "body.md"
    path.write_text(BODY)
    filed = use("file", "Probe visibility", path)
    if filed.returncode:
        return replay_probe.fail(f"cannot file the task: {filed.stderr}")
    number = filed.stdout.strip().rsplit("/", 1)[1]
    post("decide", number, f"DECIDED: probe routing\n\nJudge note: {NOTE}\n", work, "--by", "probe-manager")
    post("comment", number, f"BLOCKED: {ASK}\n", work)
    post("comment", number, "REPORTED: probe findings\n", work)
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
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
