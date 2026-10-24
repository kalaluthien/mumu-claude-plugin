#!/usr/bin/env python3
"""Land two workers' changes in a temporary repository with no remote, through use-landing.py, a files board and the fake herdr beside this file, and
print `ok <step>` or `fail <step>: <what differed>` for each step; exit 1 on any fail.

usage: replay-landing-scenario.py [-v]
`-v` also prints each command's output.
- change: two branches filed as changes 1 and 2, listed open at their tips; change-race, at the end: six filed at once get six numbers
- refuse-moved-head: change 1 merged at a sha other than its tip, or at its branch name, exits 1 and leaves the base as it was
- refuse-dirty-checkout: change 1 merged over an uncommitted file in the base's checkout exits 1 and leaves the file and the base as they were
- merge: change 1 merged at its tip after the base moved: one commit whose one parent is the old base, the merged tree, a message citing its task,
  and the base's checkout showing it
- signal: the merge touched the signal file, and the landing's change check is true since before it
- heartbeat-merged, heartbeat-rebase: the manager's heartbeat, running before the merge, names change 1 merged by its worker; the worker of change 2, which conflicts, is told to rebase
- remove: remove-worktree.py removes the merged worker's worktree and branch, and says nothing of a pull it cannot make"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = HERE.parent / "scripts"
VERBOSE = False
work = pathlib.Path(tempfile.mkdtemp(prefix="landing-scenario-"))
repo = work / "repo"
os.environ.update({"TEAMWORK_BOARD": "files", "TEAMWORK_BOARD_DIR": str(work / "board"), "TEAMWORK_LANDING": "git",
                   "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@example.com", "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com"})
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
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


def heartbeat_env(pane, poll):
    team = [agent("teamwork-manager", 1, "working"), agent("landing-probe-worker", 2, "idle"), agent("clash-probe-worker", 3, "working")]
    state = work / "herdr.json"
    state.write_text(json.dumps({"n": 10, "agents": team, "tabs": [{"tab_id": a["tab_id"], "workspace_id": "w1", "label": a["name"]} for a in team]}))
    return {"PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "FAKE_HERDR_STATE": str(state), "HERDR_PANE_ID": pane, "MONITOR_POLL": poll}


def heartbeat(pane):
    return run([ROOT / "monitors" / "print-team-gaps.py"], seconds=15, **heartbeat_env(pane, "1000"))[1]


def printed(log, text, seconds=20):
    """Whether the running heartbeat's LOG shows TEXT within SECONDS."""
    end = time.time() + seconds
    while time.time() < end and text not in log.read_text():
        time.sleep(0.2)
    return text in log.read_text()


def main(args):
    global VERBOSE
    if any(a != "-v" for a in args):
        print(__doc__, file=sys.stderr)
        return 2
    VERBOSE = "-v" in args
    repo.mkdir()
    git("init", "-q", "-b", "main")
    commit(repo, "a.txt", "one\n")
    probe, clash = worker_tree("landing-probe-worker", "two\n"), worker_tree("clash-probe-worker", "three\n")
    commit(repo, "b.txt", "moved on\n")  # the base moves after both branches start, so a merge must merge, not just copy the head
    os.chdir(repo)
    (work / "body.md").write_text("Closes #1\n")
    filed = [run([SCRIPTS / "use-landing.py", "change", n, f"Probe {n}", work / "body.md"])[1].strip() for n in ("landing-probe-worker", "clash-probe-worker")]
    heads = {p["number"]: p["headRefOid"] for p in landing_git.pulls("open") or []}
    step("change", [u.rsplit("/", 1)[-1] for u in filed] == ["1.json", "2.json"] and heads == {1: probe, 2: clash}, f"{filed} {heads}")

    base = git("rev-parse", "main")
    code, out = run([SCRIPTS / "use-landing.py", "merge", "1", base])
    named, _ = run([SCRIPTS / "use-landing.py", "merge", "1", "landing-probe-worker"])  # a branch name follows the tip, so it never stands for an approved head
    step("refuse-moved-head", code == named == 1 and git("rev-parse", "main") == base and landing_git.record(1)["state"] == "OPEN", f"exit {code}: {out}")

    (repo / "a.txt").write_text("dirty\n")
    code, out = run([SCRIPTS / "use-landing.py", "merge", "1", probe])
    step("refuse-dirty-checkout", code == 1 and (repo / "a.txt").read_text() == "dirty\n" and git("rev-parse", "main") == base
         and landing_git.record(1)["state"] == "OPEN", f"exit {code}: {out}")
    git("checkout", "--", "a.txt")

    # the manager's heartbeat runs before the merge, so only its change check, not its first read, can bring the merged line
    log = work / "heartbeat.log"
    live = subprocess.Popen([str(ROOT / "monitors" / "print-team-gaps.py")], cwd=repo, env={**os.environ, **heartbeat_env("w1:p1", "1")},
                            stdout=log.open("w"), stderr=subprocess.STDOUT)
    first = printed(log, "idle landing-probe-worker")
    time.sleep(1.1)  # the records filed above carry this second, which must not count as the merge
    before, signal = landing_git.stamp(), team_signal.stamp()
    code, out = run([SCRIPTS / "use-landing.py", "merge", "1", probe])
    merged = out.strip()
    want = run(["git", "merge-tree", "--write-tree", base, probe])[1].split()[:1]
    step("merge", code == 0 and git("rev-parse", "main") == merged and git("rev-list", "--parents", "-1", merged).split()[1:] == [base]
         and [git("rev-parse", f"{merged}^{{tree}}")] == want and "Closes #1" in git("log", "-1", "--format=%B", merged)
         and (repo / "a.txt").read_text() == "two\n" and (repo / "b.txt").exists() and landing_git.record(1)["headRefOid"] == probe,
         f"exit {code}: {out}")
    step("signal", team_signal.stamp() != signal and landing_git.changed_since(before), f"stamp {signal} -> {team_signal.stamp()}")

    step("heartbeat-merged", first and printed(log, "merged #1 by landing-probe-worker:"), log.read_text())
    live.kill()
    beat = heartbeat("w1:p3")
    step("heartbeat-rebase", "rebase #2: it conflicts with its base" in beat, beat)

    code, out = run([SCRIPTS / "remove-worktree.py", "landing-probe-worker"])
    step("remove", "landing-probe-worker: worktree, branch removed" in out and "fast-forward" not in out
         and not git("branch", "--list", "landing-probe-worker"), out)
    racers = [subprocess.Popen([str(SCRIPTS / "use-landing.py"), "change", "clash-probe-worker", "Race", str(work / "body.md")], stdout=subprocess.PIPE, text=True)
              for _ in range(6)]
    urls = sorted(r.communicate()[0].strip() for r in racers)
    step("change-race", len(set(urls)) == 6 and len(landing_git.records()) == 8, f"{urls}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
