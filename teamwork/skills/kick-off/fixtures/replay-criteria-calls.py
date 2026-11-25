#!/usr/bin/env python3
"""Call run-criteria.py and check-criteria.py on a scratch git board with words they can and cannot read. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `task-words`: a task named by its number, `#n` or url gives each script the same answer, and check-criteria.py's is the one `--task <n> <body-file>` gives;
- `no-file`: a missing file, a folder, a file that is no text, or a `--task` word that is no task answers each script in one line that names the word, with exit 1, nothing on stdout and no traceback;
- `no-task`: a number the board does not hold answers in one line that names it;
- `no-repository`: a task named outside a git repository answers in one line;
- `base`: `--base` with no `origin/HEAD` and no `--ref` runs on `main`;
- `limit`: a check that outlasts `--timeout` fails with a row that names `--timeout`.

usage: replay-criteria-calls.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `PASS`; on base `FAIL`.\n")
LINE = 200


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("criteria-calls-") as work:
        return replay(work)


def replay(work):
    box, cases = replay_probe.Sandbox(work), replay_probe.Cases()
    step = cases.step

    def call(script, *argv, cwd=None):
        done = box.python(SCRIPTS / script, *map(str, argv), cwd=cwd)
        return done.returncode, done.stdout, done.stderr

    def one_line(answer, word):
        code, out, error = answer
        return code == 1 and not out and error.count("\n") == 1 and len(error) < LINE and word in error and "Traceback" not in error

    quick, slow, binary = work / "quick.md", work / "slow.md", work / "binary.md"
    binary.write_bytes(b"\xff\xfe\x00")
    quick.write_text(BODY.format(command="basename PASS"))
    slow.write_text(BODY.format(command="sh -c 'sleep 5 && echo PASS'"))
    url = call("use-board.py", "file", "--title", "Print ok from the probe", "--body", quick)[1].strip()
    call("use-board.py", "file", "--title", "Print ok after a while", "--body", slow)

    ran = [call("run-criteria.py", "--fresh", word) for word in ("1", "#1", url)]
    linted = [call("check-criteria.py", *argv) for argv in (["1"], ["#1"], [url], ["--task", "1", quick], ["--task", url, quick])]
    step("task-words", url.endswith("/1") and ran[0][0] == 0 and "| pass | PASS |" in ran[0][1] and ran.count(ran[0]) == 3 and linted[0][0] == 0 and linted.count(linted[0]) == 5, ran + linted)

    missing = [(word, call(script, *argv, word)) for script, argv in (("run-criteria.py", []), ("check-criteria.py", []), ("check-criteria.py", ["--task", "1"]))
               for word in ("no-such-body.md", work, binary)]
    missing.append(("no-task-word", call("check-criteria.py", "--task", "no-task-word", quick)))
    step("no-file", all(one_line(answer, str(word)) for word, answer in missing), missing)

    absent = [call(script, "77") for script in ("run-criteria.py", "check-criteria.py")]
    step("no-task", all(one_line(answer, "#77") for answer in absent), absent)

    outside = [call(script, "1", cwd=work) for script in ("run-criteria.py", "check-criteria.py")]
    step("no-repository", all(one_line(answer, "git repository") for answer in outside), outside)

    based = call("run-criteria.py", "--base", "1")
    step("base", based[1].startswith("REPORTED: base outputs at main ") and "Traceback" not in based[2], based)

    cut = call("run-criteria.py", "--timeout", "1", "2")
    step("limit", cut[0] == 1 and "| fail | timed out after 1 s" in cut[1] and "--timeout" in cut[1], cut)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
