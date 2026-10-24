#!/usr/bin/env python3
"""usage: compare-session-calls.py [--ref <ref>]

Run start-session.py and close-session.py over one scenario against a fake herdr (fake-herdr/herdr beside this file),
in the current checkout and in an export of REF (default origin/main), and print `same` when the herdr calls and the
printed lines match, else a unified diff and `differ`."""
import argparse, difflib, json, os, pathlib, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
K = "teamwork/skills/kick-off/scripts/"
STEPS = [
    [K + "start-session.py", "alpha-worker", "/tmp", "worker alpha-worker manager teamwork-manager https://example.com/1", "--model", "haiku", "--effort", "medium"],
    [K + "start-session.py", "beta-worker", "/tmp", "worker beta-worker manager teamwork-manager https://example.com/2", "--model", "sonnet", "--effort", "medium", "--allow", "Artifact"],
    [K + "start-session.py", "other-manager", "/tmp", "other", "--model", "opus", "--effort", "low", "--team"],
    [K + "start-session.py", "teamwork-manager-next", "/tmp", "succeed teamwork-manager", "--model", "opus", "--effort", "low", "--beside", "teamwork-manager"],
    [K + "start-session.py", "alpha-worker", "/tmp", "worker alpha-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [K + "start-session.py", "gamma-worker", "/tmp", "worker gamma-worker manager m x", "--model", "haiku", "--effort", "medium", "--allow", "Bash"],
    [K + "close-session.py", "beta-worker"],
    [K + "start-session.py", "trust-worker", ".", "worker trust-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [K + "start-session.py", "slow-worker", "/tmp", "worker slow-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [K + "close-session.py", "nobody-worker"],
    [K + "close-session.py", "stuck-worker"],
    [K + "list-agents.py"],
    ["teamwork/hooks/route-event.py", "gh issue comment 1 --body hi"],
    ["teamwork/hooks/route-event.py", "ls"],
]


def scenario(tree):
    work = pathlib.Path(tempfile.mkdtemp(prefix="session-calls-")).resolve()
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)  # the trust dialog is accepted only inside the repository the steps run in
    state, log = work / "state.json", work / "log"
    state.write_text(json.dumps({"n": 10, "tabs": [{"tab_id": "w1:t1", "workspace_id": "w1", "label": "protocol-split-worker"}],
                                 "agents": [{"name": "protocol-split-worker", "pane_id": "w1:p1", "tab_id": "w1:t1", "workspace_id": "w1", "agent": "claude",
                                             "agent_status": "working", "interactive_ready": True},
                                            {"name": "teamwork-manager", "pane_id": "w1:p2", "tab_id": "w1:t2", "workspace_id": "w1", "agent": "claude",
                                             "agent_status": "idle", "interactive_ready": True},
                                            {"name": "stuck-worker", "pane_id": "w1:p3", "tab_id": "w1:t3", "workspace_id": "w1", "agent": "claude",
                                             "agent_status": "blocked", "interactive_ready": True, "screen": "Background work is running"}]}))
    env = {**os.environ, "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "FAKE_HERDR_STATE": str(state), "FAKE_HERDR_LOG": str(log),
           "HERDR_PANE_ID": "w1:p1", "START_SESSION_TIMEOUT": "3", "CLOSE_SESSION_TIMEOUT": "3"}
    out = []
    for step in STEPS:
        log.open("a").write(f"$ {' '.join(step[1:])}\n")
        hook = step[0].endswith("route-event.py")  # the hook reads its event, a Bash call of the command named
        event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": step[1]}, "cwd": "."}) if hook else None
        p = subprocess.run([str(tree / step[0]), *([] if hook else step[1:])], cwd=work, env=env, input=event, capture_output=True, text=True)
        log.open("a").write(f"exit {p.returncode}: {(p.stdout + p.stderr).strip()}\n")
    return log.read_text().replace(str(tree), "<root>").replace(str(work), "<work>")


parser = argparse.ArgumentParser()
parser.add_argument("--ref", default="origin/main")
a = parser.parse_args()
root = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
base = pathlib.Path(tempfile.mkdtemp(prefix="session-base-")).resolve()
archive = subprocess.Popen(["git", "archive", a.ref, "teamwork"], cwd=root, stdout=subprocess.PIPE)
subprocess.run(["tar", "-x", "-C", str(base)], stdin=archive.stdout, check=True)
there, here = scenario(base), scenario(root)
if "-v" in sys.argv[1:] or os.environ.get("SHOW"):
    print(here)
sys.stdout.writelines(difflib.unified_diff(there.splitlines(True), here.splitlines(True), a.ref, "head"))
print("same" if here == there else "differ")
