#!/usr/bin/env python3
"""Run start-session.py and close-session.py over one scenario against a fake herdr (fake-herdr/herdr beside this file),
in the current checkout and in an export of REF (default origin/main), and print `same` when the herdr calls and the
printed lines match, else a unified diff and `differ`.

usage: compare-session-calls.py [--ref <ref>]"""
import argparse, difflib, json, os, pathlib, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = "teamwork/skills/kick-off/scripts/"
STEPS = [
    [SCRIPTS + "start-session.py", "alpha-worker", "/tmp", "worker alpha-worker manager teamwork-manager https://example.com/1", "--model", "haiku", "--effort", "medium"],
    [SCRIPTS + "start-session.py", "beta-worker", "/tmp", "worker beta-worker manager teamwork-manager https://example.com/2", "--model", "sonnet", "--effort", "medium", "--allow", "Artifact"],
    [SCRIPTS + "start-session.py", "other-manager", "/tmp", "other", "--model", "opus", "--effort", "low"],
    [SCRIPTS + "start-session.py", "teamwork-manager-next", "/tmp", "succeed teamwork-manager", "--model", "opus", "--effort", "low"],
    [SCRIPTS + "start-session.py", "alpha-worker", "/tmp", "worker alpha-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [SCRIPTS + "start-session.py", "gamma-worker", "/tmp", "worker gamma-worker manager m x", "--model", "haiku", "--effort", "medium", "--allow", "Bash"],
    [SCRIPTS + "close-session.py", "beta-worker"],
    [SCRIPTS + "start-session.py", "trust-worker", ".", "worker trust-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [SCRIPTS + "start-session.py", "slow-worker", "/tmp", "worker slow-worker manager teamwork-manager x", "--model", "haiku", "--effort", "medium"],
    [SCRIPTS + "close-session.py", "nobody-worker"],
    [SCRIPTS + "close-session.py", "stuck-worker"],
    [SCRIPTS + "list-sessions.py"],
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
        script = tree / step[0]
        if not script.exists():  # a ref older than the rename of the session list (#1039) keeps it under its old name
            script = script.with_name(script.name.replace("sessions", "-".join(["", "agents"])[1:]))
        p = subprocess.run([str(script), *([] if hook else step[1:])], cwd=work, env=env, input=event, capture_output=True, text=True)
        log.open("a").write(f"exit {p.returncode}: {(p.stdout + p.stderr).strip()}\n")
    return log.read_text().replace(str(tree), "<root>").replace(str(work), "<work>")


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="origin/main")
    a = parser.parse_args(args)
    root = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
    base = pathlib.Path(tempfile.mkdtemp(prefix="session-base-")).resolve()
    archive = subprocess.Popen(["git", "archive", a.ref, "teamwork"], cwd=root, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(base)], stdin=archive.stdout, check=True)
    there, here = scenario(base), scenario(root)
    if "-v" in args or os.environ.get("SHOW"):
        print(here)
    sys.stdout.writelines(difflib.unified_diff(there.splitlines(True), here.splitlines(True), a.ref, "head"))
    print("same" if here == there else "differ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
