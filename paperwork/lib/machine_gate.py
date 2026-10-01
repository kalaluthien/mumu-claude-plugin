"""Queue a heavy paperwork job at the machine gate (homeops `subjects/gate/gate.sh`) before it starts.

queue() takes a slot for this process through `gate.sh hold <own pid>` and exports HOMEOPS_GATE_HELD, so the job's
children nest under it. It takes none when HOMEOPS_GATE_HELD already names a live holder (the gate's own nesting rule)
or when no gate is found; a `hold` that fails other than 75 lets the job run, since a broken gate must not stop work.
The gate is found as checkerwork/scripts/run-verify.py finds it: $HOMEOPS_GATE, else the subjects/gate/hook.sh
registered in ~/.claude/settings.json.
"""
import os
import pathlib
import re
import subprocess

EXIT_GAVE_UP = 75


def find():
    """The gate.sh to call, or None."""
    path = os.environ.get("HOMEOPS_GATE")
    if not path:
        try:
            m = re.search(r"'?([^'\s]*/subjects/gate)/hook\.sh", (pathlib.Path.home() / ".claude/settings.json").read_text())
        except OSError:
            return None
        path = m and m.group(1) + "/gate.sh"
    return path if path and os.access(path, os.X_OK) else None


def holder_alive():
    """True when HOMEOPS_GATE_HELD names a live pid."""
    try:
        os.kill(int(os.environ.get("HOMEOPS_GATE_HELD", "")), 0)
    except (ValueError, OSError):
        return False
    return True


def queue(label):
    """Wait for a slot held by this process, asking again each time the gate gives up (exit 75)."""
    gate = None if holder_alive() else find()
    if not gate:
        return
    while True:
        try:
            code = subprocess.run([gate, "hold", str(os.getpid()), label]).returncode
        except OSError:
            return
        if code != EXIT_GAVE_UP:
            break
    if code == 0:
        os.environ["HOMEOPS_GATE_HELD"] = str(os.getpid())
