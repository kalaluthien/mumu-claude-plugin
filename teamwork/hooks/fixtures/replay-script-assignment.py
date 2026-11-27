#!/usr/bin/env python3
"""Check that route-event.py reads a shell assignment `NAME=<path>` as the path it holds, and print `ok <case>` or `fail <case>: <what it saw>` per case,
then `PASS script assignment` or `FAIL script assignment`; exit 1 on any failure:
- `existing`: `<NAME>=<this plugin's route-event.py>; grep -n x "$<NAME>"` in a worker's Bash call is allowed, for `F`, `B` and `X_1`;
- `missing`: `<NAME>=<a script of this plugin that does not exist>; grep -n x "$<NAME>"` is denied, naming that path, for the same names.

usage: replay-script-assignment.py"""
import json
import pathlib
import sys

PLUGIN = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / "lib"))
import replay_probe  # noqa: E402

ROUTE = PLUGIN / "hooks" / "route-event.py"
GONE = PLUGIN / "skills" / "kick-off" / "scripts" / "gone-script.py"
TIMEOUT = 60


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("script assignment")
    with replay_probe.scratch("script-assignment-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("t-worker", 1)])
        for name, script, denied, variable in [(case, path, flag, word) for word in ("F", "B", "X_1") for case, path, flag in (("existing", ROUTE, False), ("missing", GONE, True))]:
            event = {"hook_event_name": "PreToolUse", "cwd": str(work), "tool_input": {"command": f'{variable}={script}; grep -n x "${variable}"'}}
            done = sandbox.run([ROUTE], "w1:p1", cwd=PLUGIN, input=json.dumps(event), timeout=TIMEOUT)
            answer = (json.loads(done.stdout) if done.stdout.strip() else {}).get("hookSpecificOutput", {})
            said = answer.get("permissionDecision") == "deny"
            cases.step(f"{name} {variable}", done.returncode == 0 and said == denied and (not denied or str(script) in answer.get("permissionDecisionReason", "")),
                       f"status {done.returncode}, {answer}, {done.stderr.strip()[-200:]}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
