#!/usr/bin/env python3
"""Start sessions against a fake herdr (fake-herdr/herdr beside this file) and read the command each `herdr agent start` carries. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `fresh`: a manager for a project with no live manager runs `--model opus --effort low`, though the caller asked for sonnet, high;
- `handover`: a successor `<manager>-next` of `succeed <manager>` runs `--model opus --effort low`, though the caller asked for sonnet, high;
- `restart`: a peer manager's successor, started from another manager's session, runs `--model opus --effort low`;
- `worker`, `sentinel`: a worker and a sentinel keep the model and effort their manager passes.

usage: replay-manager-effort.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="manager-effort-")).resolve()
    state, log = work / "state.json", work / "log"
    environment = {**os.environ, "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(log)}

    def start(name, args, model, effort):
        """The words after `--model` and `--effort` of the one `agent start` this start sends."""
        state.write_text(json.dumps({"n": 10, "tabs": [], "agents": [
            {"name": peer, "pane_id": f"w{n}:p2", "tab_id": f"w{n}:t2", "workspace_id": f"w{n}", "agent": "claude", "agent_status": "idle", "interactive_ready": True}
            for n, peer in ((1, "teamwork-manager"), (2, "other-manager"))]}))
        log.write_text("")
        done = subprocess.run([str(ROOT / "skills/kick-off/scripts/start-session.py"), name, "/tmp", args, "--model", model, "--effort", effort], cwd=work, env=environment, capture_output=True, text=True)
        starts = [call for call in (json.loads(line) for line in log.read_text().splitlines()) if call[:2] == ["agent", "start"]]
        words = [word for call in starts for word in call]
        pick = lambda flag: words[words.index(flag) + 1] if flag in words else None  # noqa: E731
        return done, (pick("--model"), pick("--effort"))

    for case, name, args in (("fresh", "newproject-manager", "newproject"), ("handover", "teamwork-manager-next", "succeed teamwork-manager"),
                             ("restart", "other-manager-next", "succeed other-manager")):
        done, picked = start(name, args, "sonnet", "high")
        step(case, done.returncode == 0 and picked == ("opus", "low"), [picked, done.stderr])
    for case, name, args, passed in (("worker", "some-work-worker", "worker some-work-worker manager teamwork-manager https://example.com/1", ("sonnet", "medium")),
                                     ("sentinel", "some-duty-sentinel", "sentinel some-duty-sentinel manager teamwork-manager the duty", ("haiku", "high"))):
        done, picked = start(name, args, *passed)
        step(case, done.returncode == 0 and picked == passed, [picked, done.stderr])
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
