#!/usr/bin/env python3
"""Start workers against a fake herdr (fake-herdr/herdr beside this file) whose start times out. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `late`: an agent that comes up in its pane after herdr stopped waiting is given its name and its kick-off, and the start exits 0;
- `never`: with no agent in the pane the start exits 1, says the session is not live and got no kick-off, and sends no prompt;
- `unsent`: a live session whose kick-off was refused is called live with no kick-off, and the answer holds the kick-off to send;
- `untaken`: a live session that took the text but never started on it is called live with its kick-off typed;
- `lookup`: the pane lookup each failed start names exits 0;
- `limit`: every `herdr agent start` carries a `--timeout` herdr takes, above 3000 ms and at most 300000 ms;
- `subfolder`: `.github/plan-release.py`, when the repository has one, names the same tags from a plugin's folder as from the top.

usage: replay-start-timeout.py"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
KICKOFF = "Run the teamwork:kick-off skill with these arguments: "
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="start-timeout-")).resolve()
    state, log = work / "state.json", work / "log"
    environment = {**os.environ, "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(log),
                   "TEAMWORK_START_SESSION_TIMEOUT": "4"}

    def start(name, limit="4"):
        state.write_text(json.dumps({"n": 10, "tabs": [], "agents": [
            {"name": "teamwork-manager", "pane_id": "w1:p2", "tab_id": "w1:t2", "workspace_id": "w1", "agent": "claude", "agent_status": "idle", "interactive_ready": True}]}))
        log.write_text("")
        done = subprocess.run([str(ROOT / "skills/kick-off/scripts/start-session.py"), name, "/tmp", f"worker {name} manager teamwork-manager https://example.com/1", "--model", "haiku", "--effort", "medium"],
                              cwd=work, env={**environment, "TEAMWORK_START_SESSION_TIMEOUT": limit}, capture_output=True, text=True)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        return done, calls, json.loads(state.read_text())["agents"]

    def looked(done):
        """Whether the pane lookup a failed start names runs."""
        command = re.search(r"`(herdr [^`]+)`", done.stderr)
        return bool(command) and subprocess.run(command[1].split(), env=environment, capture_output=True, text=True).returncode == 0

    done, calls, agents = start("late-worker")
    prompts = [call[3] for call in calls if call[:2] == ["agent", "prompt"]]
    step("late", done.returncode == 0 and "took its kick-off" in done.stdout and [agent["name"] for agent in agents] == ["teamwork-manager", "late-worker"]
         and prompts == [KICKOFF + "worker late-worker manager teamwork-manager https://example.com/1"], [done, agents, prompts])
    limits = [int(call[call.index("--timeout") + 1]) for call in calls if call[:2] == ["agent", "start"] and "--timeout" in call]
    limits += [int(call[call.index("--timeout") + 1]) for call in start("plain-worker", "900")[1] if call[:2] == ["agent", "start"] and "--timeout" in call]
    step("limit", len(limits) == 2 and all(3000 < limit <= 300000 for limit in limits), limits)

    lookups = []
    done, calls, agents = start("never-worker")
    lookups.append(looked(done))
    step("never", done.returncode == 1 and not done.stdout and "never-worker is not live and got no kick-off" in done.stderr and len(agents) == 1
         and not any(call[:2] == ["agent", "prompt"] for call in calls), [done, agents])

    done, calls, agents = start("refuse-worker")
    lookups.append(looked(done))
    step("unsent", done.returncode == 1 and "refuse-worker is live and got no kick-off" in done.stderr and KICKOFF + "worker refuse-worker" in done.stderr, done)

    done, calls, agents = start("unseen-worker")
    lookups.append(looked(done))
    step("untaken", done.returncode == 1 and "unseen-worker is live and its kick-off was typed" in done.stderr and "start no second one" in done.stderr, done)
    step("lookup", lookups == [True, True, True], lookups)

    plan = ROOT.parent / ".github" / "plan-release.py"
    if plan.exists():
        revisions = subprocess.run(["git", "log", "--format=%H", "-2", "--", ROOT.name + "/.claude-plugin/plugin.json"], cwd=ROOT.parent, capture_output=True, text=True).stdout.split()
        answers = [subprocess.run([sys.executable, str(plan), *reversed(revisions)], cwd=folder, capture_output=True, text=True) for folder in (ROOT.parent, ROOT)]
        told = [(answer.returncode, answer.stdout, answer.stderr) for answer in answers]
        step("subfolder", len(revisions) == 2 and told[0] == told[1] and ROOT.name in told[0][1] + told[0][2], told)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
