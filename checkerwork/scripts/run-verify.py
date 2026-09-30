#!/usr/bin/env python3
"""PreToolUse on Bash, PostToolUse on Bash and Stop: in a repo holding a `spec/` model, run the contract skill's gate before
a `git commit` and before a stop that leaves changes, refusing either while it fails, with its FAIL lines. A repo
without one is commit-nudge.py's.
The gate runs at most once per working tree (tracked and untracked content): a tree it passed, or that the session's
own `verify.sh` Bash call passed, goes through at once. While the homeops machine gate reports no free slot the hook
does not queue behind it, it denies with "run verify.sh yourself". The busy reading is `gate.sh status`, found by
$HOMEOPS_GATE or the `subjects/gate/hook.sh` registered in ~/.claude/settings.json; with neither, the hook only runs.
A stop already held once goes on, so a gate the session cannot turn green never traps it. Exit 0 always.
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
GATE = pathlib.Path(os.environ.get("VERIFY_GATE") or PLUGIN / "skills" / "contract" / "scripts" / "verify.sh")  # tests stub it
sys.path.insert(0, str(PLUGIN / "lib"))
from fit import COMMIT  # noqa: E402

OWN_RUN = re.compile(r"^(cd\s+\S+\s*&&\s*)?(\w+=\S+\s+)*(bash\s+)?\S*verify\.sh\s*$")
BUSY_WAIT = 4  # seconds: the hook answers a busy machine gate well inside 5


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout.strip()


def tree_id(root):
    """The tree tracked and untracked content makes, by a scratch index: a one-byte change makes another id."""
    index = git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")
    with tempfile.TemporaryDirectory() as tmp:
        scratch = os.path.join(tmp, "index")
        if os.path.exists(index):
            with open(index, "rb") as src, open(scratch, "wb") as dst:
                dst.write(src.read())
        env = {**os.environ, "GIT_INDEX_FILE": scratch}
        subprocess.run(["git", "-C", root, "add", "-A"], env=env, capture_output=True)
        return subprocess.run(["git", "-C", root, "write-tree"], env=env, capture_output=True, text=True).stdout.strip()


def passed_file(root):
    return git(root, "rev-parse", "--path-format=absolute", "--git-path", "verify-passed")


def passed(root, tree):
    try:
        return tree in pathlib.Path(passed_file(root)).read_text().split()
    except OSError:
        return False


def record(root, tree):
    if tree:
        pathlib.Path(passed_file(root)).write_text(tree + "\n")


def machine_gate():
    path = os.environ.get("HOMEOPS_GATE")
    if not path:
        try:
            m = re.search(r"'?([^'\s]*/subjects/gate)/hook\.sh", (pathlib.Path.home() / ".claude/settings.json").read_text())
        except OSError:
            return None
        path = m and m.group(1) + "/gate.sh"
    return path if path and os.access(path, os.X_OK) else None


def busy():
    """True when the machine gate reports every slot held or no room; an unreadable status is not busy."""
    gate = machine_gate()
    if not gate:
        return False
    try:
        out = subprocess.run([gate, "status"], capture_output=True, text=True, timeout=BUSY_WAIT)
    except (subprocess.TimeoutExpired, OSError):
        return False
    text = out.stdout + out.stderr
    held = re.search(r"(\d+)/(\d+) held", text)
    return bool(re.search(r"\broom no\b", text) or held and int(held.group(1)) >= int(held.group(2)))


def refuse(stop, why):
    print(json.dumps({"decision": "block", "reason": why} if stop else {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


def main():
    call = json.load(sys.stdin)
    event = call.get("hook_event_name")
    stop = event == "Stop"
    cwd = call.get("cwd") or os.getcwd()
    command = (call.get("tool_input") or {}).get("command", "")
    m = None if stop else COMMIT.search(command)
    if m and m.group(3):
        cwd = os.path.join(cwd, os.path.expanduser(shlex.split(m.group(3))[0]))
    root = git(cwd, "rev-parse", "--show-toplevel")
    if not (root and any(pathlib.Path(root, "spec").rglob("*.als"))):
        return
    if event == "PostToolUse":  # a PostToolUse call means the Bash call exited 0
        if OWN_RUN.match(command.strip()):
            record(root, tree_id(root))
        return
    if not (m or stop and not call.get("stop_hook_active") and git(root, "status", "--porcelain")):
        return
    tree = tree_id(root)
    if passed(root, tree):
        return
    if busy():
        return refuse(stop, "The machine gate has no free slot, so the hook did not wait for it. Run verify.sh yourself "
                            "as a Bash call; once it exits 0, run this again.")
    p = subprocess.run([str(GATE)], cwd=root, capture_output=True, text=True)
    fails = [l for l in (p.stdout + p.stderr).splitlines() if l.startswith("FAIL")] or p.stderr.splitlines()[-5:]
    if p.returncode:
        refuse(stop, "verify.sh fails:\n" + "\n".join(fails) + "\nFix the change or the model until it passes; never loosen an expect.")
    else:
        record(root, tree)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a crash refuses nothing
        print(f"run-verify.py: {type(e).__name__}: {e}; gate not run", file=sys.stderr)
    sys.exit(0)
