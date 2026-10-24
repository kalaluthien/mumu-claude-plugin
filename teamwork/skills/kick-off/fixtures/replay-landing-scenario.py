#!/usr/bin/env python3
"""usage: replay-landing-scenario.py [-v]

Land two workers' changes in a temporary repository with no remote, through use-landing.py, a files board and the fake herdr beside this file, and
print `ok <step>` or `fail <step>: <what differed>` for each step; exit 1 on any fail. `-v` also prints each command's output.
- change: two branches filed as changes 1 and 2, listed open at their tips
- refuse-moved-head: change 1 merged at a sha other than its tip exits 1 and leaves the base as it was
- merge: change 1 merged at its tip after the base moved: one commit whose one parent is the old base, the merged tree, a message citing its task,
  and the base's checkout showing it
- signal: the merge touched the signal file, and the landing's change check is true since before it
- heartbeat-merged, heartbeat-rebase: the manager's heartbeat names change 1 merged by its worker; the worker of change 2, which conflicts, is told to rebase
- remove: remove-worktree.py removes the merged worker's worktree and branch, and says nothing of a pull it cannot make"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
K = HERE.parent / "scripts"
VERBOSE = "-v" in sys.argv[1:]
work = pathlib.Path(tempfile.mkdtemp(prefix="landing-scenario-"))
repo = work / "repo"
os.environ.update({"TEAMWORK_BOARD": "files", "TEAMWORK_BOARD_DIR": str(work / "board"), "TEAMWORK_LANDING": "git",
                   "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@example.com", "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com"})
sys.path.insert(0, str(ROOT / "lib"))
import landing_git  # noqa: E402
import team_signal  # noqa: E402

failed = []


def run(argv, cwd=repo, seconds=60, **env):
    try:
        p = subprocess.run([str(a) for a in argv], cwd=cwd, env={**os.environ, **env}, capture_output=True, text=True, timeout=seconds)
        out, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:  # the heartbeat runs until killed
        out, code = (e.stdout or b"").decode() + (e.stderr or b"").decode(), None
    if VERBOSE:
        print(f"$ {' '.join(map(str, argv))}\n{out}", file=sys.stderr)
    return code, out


def git(*argv, cwd=repo):
    return run(["git", *argv], cwd)[1].strip()


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
    if not ok:
        failed.append(name)


def commit(cwd, name, text):
    (cwd / name).write_text(text)
    git("add", name, cwd=cwd)
    git("commit", "-qm", f"write {name}", cwd=cwd)


def worker_tree(name, text):
    tree = repo / ".claude" / "worktrees" / name
    git("worktree", "add", "-q", "-b", name, str(tree), "main")
    commit(tree, "a.txt", text)
    return git("rev-parse", name)


def agent(name, pane, status):
    return {"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status,
            "interactive_ready": True}


def heartbeat(pane):
    team = [agent("teamwork-manager", 1, "working"), agent("landing-probe-worker", 2, "working"), agent("clash-probe-worker", 3, "working")]
    state = work / "herdr.json"
    state.write_text(json.dumps({"n": 10, "agents": team, "tabs": [{"tab_id": a["tab_id"], "workspace_id": "w1", "label": a["name"]} for a in team]}))
    return run([ROOT / "monitors" / "print-team-gaps.py"], seconds=15, PATH=f"{HERE / 'fake-herdr'}:{os.environ['PATH']}",
               FAKE_HERDR_STATE=str(state), HERDR_PANE_ID=pane, MONITOR_POLL="1000")[1]


repo.mkdir()
git("init", "-q", "-b", "main")
commit(repo, "a.txt", "one\n")
probe, clash = worker_tree("landing-probe-worker", "two\n"), worker_tree("clash-probe-worker", "three\n")
commit(repo, "b.txt", "moved on\n")  # the base moves after both branches start, so a merge must merge, not just copy the head
os.chdir(repo)
(work / "body.md").write_text("Closes #1\n")
filed = [run([K / "use-landing.py", "change", n, f"Probe {n}", work / "body.md"])[1].strip() for n in ("landing-probe-worker", "clash-probe-worker")]
heads = {p["number"]: p["headRefOid"] for p in landing_git.pulls("open") or []}
step("change", [u.rsplit("/", 1)[-1] for u in filed] == ["1.json", "2.json"] and heads == {1: probe, 2: clash}, f"{filed} {heads}")

base = git("rev-parse", "main")
code, out = run([K / "use-landing.py", "merge", "1", base])
step("refuse-moved-head", code == 1 and git("rev-parse", "main") == base and landing_git.record(1)["state"] == "OPEN", f"exit {code}: {out}")

time.sleep(1.1)  # the records filed above carry this second, which must not count as the merge
before, signal = landing_git.stamp(), team_signal.stamp()
code, out = run([K / "use-landing.py", "merge", "1", probe])
merged = out.strip()
want = run(["git", "merge-tree", "--write-tree", base, probe])[1].split()[:1]
step("merge", code == 0 and git("rev-parse", "main") == merged and git("rev-list", "--parents", "-1", merged).split()[1:] == [base]
     and [git("rev-parse", f"{merged}^{{tree}}")] == want and "Closes #1" in git("log", "-1", "--format=%B", merged)
     and (repo / "a.txt").read_text() == "two\n" and (repo / "b.txt").exists() and landing_git.record(1)["headRefOid"] == probe,
     f"exit {code}: {out}")
step("signal", team_signal.stamp() != signal and landing_git.changed_since(before), f"stamp {signal} -> {team_signal.stamp()}")

beat = heartbeat("w1:p1")
step("heartbeat-merged", "merged #1 by landing-probe-worker:" in beat, beat)
beat = heartbeat("w1:p3")
step("heartbeat-rebase", "rebase #2: it conflicts with its base" in beat, beat)

code, out = run([K / "remove-worktree.py", "landing-probe-worker"])
step("remove", "landing-probe-worker: worktree, branch removed" in out and "fast-forward" not in out
     and not git("branch", "--list", "landing-probe-worker"), out)
sys.exit(1 if failed else 0)
