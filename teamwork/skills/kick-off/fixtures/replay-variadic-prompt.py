#!/usr/bin/env python3
"""Check that check-criteria.py refuses a live `[check]` whose prompt a variadic flag swallows, and print `PASS` as the last line when it does, else `FAIL: <what differed>` and exit 1.

usage: replay-variadic-prompt.py
- refused: a prompt after `--allowedTools` or `--disallowedTools`, alone or with other values, prints a defect naming the flag; a command ending in a bare `--` prints one naming it
- accepted: a prompt first, or after `--`, prints nothing"""
import pathlib
import sys

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
BODY = "## Goal\n\nProbe the lint.\nPath: caller: probe-worker; before: filing; after: judging; meets: teamwork-manager\n\n## Definition of done\n\n1. [check] **The live session answers the greeting prompt**: `{command}` prints `PASS`; watches: app; on base `FAIL`.\n"
CASES = (
    ("claude -p --model sonnet --allowedTools Read \"say hi\" | grep -c hi", "--allowedTools"),
    ("claude -p --disallowedTools Bash Edit \"say hi\" | grep -c hi", "--disallowedTools"),
    ("claude -p --allowedTools Read \"say hi\" --model sonnet | grep -c hi", "--allowedTools"),
    ("claude --allowedTools Read \"say hi\" -p | grep -c hi", "--allowedTools"),
    ("claude -p --allowedTools \"say hi\" | grep -c hi", "--allowedTools"),
    ("claude -p --allowedTools Read -- | grep -c hi", "--"),
    ("claude -p --allowedTools=Read \"say hi\" | grep -c hi", None),
    ("claude -p \"say hi\" --allowedTools Read Edit | grep -c hi", None),
    ("claude -p --allowedTools Read Edit --model sonnet -- \"say hi\" | grep -c hi", None),
    ("claude -p --allowedTools Read Edit -- \"say hi\" | grep -c hi", None),
)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("variadic-prompt-") as work:
        environment = replay_probe.isolated(work)
        for number, (command, flag) in enumerate(CASES):
            body = replay_probe.write_text(work, f"body-{number}.md", BODY.format(command=command))
            done = replay_probe.sh(sys.executable, SCRIPTS / "check-criteria.py", "--task", "99999", body, cwd=work, environment=environment, check=False)
            out = done.stdout
            if done.stderr or done.returncode != (1 if flag else 0):
                return replay_probe.fail(f"{command!r} gave exit {done.returncode} and stderr {done.stderr!r}")
            if flag and flag != "--" and "put the prompt first or after `--`" not in out:
                return replay_probe.fail(f"{command!r} printed no hint: {out!r}")
            if flag == "--" and "no prompt after --" not in out:
                return replay_probe.fail(f"{command!r} should be refused for its bare --: {out!r}")
            if flag and flag != "--" and f"prompt swallowed by {flag}" not in out:
                return replay_probe.fail(f"{command!r} should be refused naming {flag}: {out!r}")
            if not flag and "swallowed" in out:
                return replay_probe.fail(f"{command!r} should pass: {out!r}")
    return replay_probe.Cases().finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
