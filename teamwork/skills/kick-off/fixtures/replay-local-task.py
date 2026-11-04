#!/usr/bin/env python3
"""Run a team's whole path on the git board in a temporary repository whose `origin` is a bare repository beside it, with a `gh` on PATH that logs each call and fails,
and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-local-task.py [--case <name>]
With no case: file a part and a root that names it, route the part by `decide`, branch, change, judge-approved merge and push of a worker's change, `resolve` the part so the root closes,
the issue pane and the heartbeat, writing and reading the real hooks and scripts, and require an empty gh log.
- layout: `file --scope probe` puts an issue at `probe/<n>/` of the one ref `refs/teamwork-blackboard` and a filing with no scope puts it at `<n>/`, each url names its folder, a `--scope` that names no folder of the repository is refused with no commit, `read` finds an issue by number alone, and the pane of `probe` reads its folder only while a project with no folder reads the root's own issues only
- old-setting: a leftover `TEAMWORK_BOARD` or `TEAMWORK_LANDING` in the environment and in the project's settings changes nothing, and the whole path still calls no gh
- base-required: `edit-issue-body.py` with no `--base` exits 2 and adds no commit, and with the board's `body sha` it adds one
- cloud-refused: a `cloud:` line in a comment's teamwork fence is refused as no key and adds no commit, and `start-session.py` with `set remote` exits 2
- atomic: `edit-issue-body.py`, `board.edit` that reopens a closed root, `resolve` of a part whose parent then closes and `resolve --not-planned` of a task with an open part each add exactly one commit to the board's ref, and a diff that does not apply, or whose `--base` names an older body, adds none"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
HOOKS = HERE.parents[2] / "hooks"
MONITORS = HERE.parents[2] / "monitors"
REF = "refs/teamwork-blackboard"
PART = "Probe the part.\n"
ROOT = "Probe the root.\n\n## Definition of done\n\n1. [task] #1 Probe the part\n"
HOLD = "DECIDED: probe-worker holds this.\n\n```teamwork\nholders: probe-worker\n```\n"


def sh(*argv, cwd, env, check=True, timeout=120):
    run = subprocess.run([str(word) for word in argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if check and run.returncode:
        raise RuntimeError(f"{' '.join(map(str, argv))}: {run.stdout}{run.stderr}")
    return run


def setup():
    work = pathlib.Path(tempfile.mkdtemp(prefix="local-task-"))
    (work / "bin").mkdir()
    (work / "gh.log").write_text("")
    stub = work / "bin" / "gh"
    stub.write_text(f"#!/bin/sh\necho \"$@\" >> {work / 'gh.log'}\nexit 1\n")
    stub.chmod(0o755)
    (work / "gitconfig").write_text("[user]\n\tname = probe\n\temail = probe@example.com\n[init]\n\tdefaultBranch = main\n")
    kept = {key: value for key, value in os.environ.items() if key not in ("TEAMWORK_BOARD", "TEAMWORK_LANDING", "TEAMWORK_BOARD_DIR")}
    env = {**kept, "PATH": f"{work / 'bin'}:{HERE / 'fake-herdr'}:{os.environ['PATH']}", "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig")}
    repo, origin = work / "repo", work / "origin.git"
    sh("git", "init", "-q", repo, cwd=work, env=env)
    (repo / "a.txt").write_text("base\n")
    (repo / "probe").mkdir()
    (repo / "probe" / "a.txt").write_text("base\n")
    sh("git", "add", "-A", cwd=repo, env=env)
    sh("git", "commit", "-q", "-m", "base", cwd=repo, env=env)
    sh("git", "init", "-q", "--bare", origin, cwd=work, env=env)
    sh("git", "remote", "add", "origin", origin, cwd=repo, env=env)
    sh("git", "push", "-q", "-u", "origin", "main", cwd=repo, env=env)
    return work, repo, origin, env


def use(env, repo, script, *argv, check=True):
    return sh(sys.executable, SCRIPTS / script, *argv, cwd=repo, env=env, check=check)


def text_file(work, name, text):
    path = work / name
    path.write_text(text)
    return path


def commits(env, repo):
    return int(sh("git", "rev-list", "--count", REF, cwd=repo, env=env, check=False).stdout.strip() or 0)


def gh_calls(work):
    return (work / "gh.log").read_text().strip()


def fail(why):
    print(f"FAIL: {why}")
    return 1


def state(env, repo, number):
    return use(env, repo, "use-board.py", "read", number, check=False).stdout.splitlines()[1:2]


def case_whole(work, repo, origin, env):
    use(env, repo, "use-board.py", "file", "Probe the part", text_file(work, "part.md", PART), "--scope", "probe")
    use(env, repo, "use-board.py", "file", "Probe the root", text_file(work, "root.md", ROOT), "--scope", "probe")
    use(env, repo, "use-board.py", "file", "Probe the late issue", text_file(work, "late.md", "Unrouted.\n"), "--scope", "probe")
    use(env, repo, "use-board.py", "decide", "1", text_file(work, "hold.md", HOLD))
    herdr = work / "herdr.json"
    team = [{"name": "probe-manager", "pane_id": "w1:p1", "tab_id": "w1:t1", "workspace_id": "w1", "agent": "claude", "agent_status": "working", "interactive_ready": True}]
    herdr.write_text(json.dumps({"n": 10, "agents": team, "tabs": [{"tab_id": "w1:t1", "workspace_id": "w1", "label": "probe-manager"}]}))
    log = work / "heartbeat.log"
    live = subprocess.Popen([str(MONITORS / "print-team-gaps.py")], cwd=repo, stdout=log.open("w"), stderr=subprocess.STDOUT,
                            env={**env, "FAKE_HERDR_STATE": str(herdr), "HERDR_PANE_ID": "w1:p1", "MONITOR_POLL": "1"})
    try:
        end = time.time() + 30
        while time.time() < end and "route #3" not in log.read_text():
            time.sleep(0.3)
        if "route #3" not in log.read_text():
            return fail(f"the heartbeat routed no unrouted issue on the git board: {log.read_text()[-300:]}")
    finally:
        live.kill()
    tree = pathlib.Path(sh(sys.executable, SCRIPTS / "add-worktree.py", "probe-worker", "main", cwd=repo, env=env).stdout.strip())
    (tree / "b.txt").write_text("work\n")
    sh("git", "add", "-A", cwd=tree, env=env)
    sh("git", "commit", "-q", "-m", "work", cwd=tree, env=env)
    head = sh("git", "rev-parse", "HEAD", cwd=tree, env=env).stdout.strip()
    use(env, tree, "use-landing.py", "change", "probe-worker", "Probe change", text_file(work, "change.md", "Probe change. Closes #1.\n"))
    merged = use(env, tree, "use-landing.py", "merge", "1", head).stdout.strip()
    if sh("git", "rev-parse", "refs/heads/main", cwd=origin, env=env).stdout.strip() != merged:
        return fail("the merge did not reach origin's main")
    use(env, repo, "use-board.py", "resolve", "1", text_file(work, "done.md", "Probe part done.\n"))
    if state(env, repo, "2") != ["state: CLOSED"]:
        return fail(f"the root did not close with its last part: {state(env, repo, '2')}")
    pane = sh(sys.executable, HOOKS / "list-issue-board.py", "probe", "--json", cwd=repo, env=env, check=False)
    if pane.returncode or "Probe the late issue" not in pane.stdout:
        return fail(f"the pane: exit {pane.returncode} {pane.stdout[:200]} {pane.stderr[-200:]}")
    if gh_calls(work):
        return fail(f"gh was called: {gh_calls(work)[:300]}")
    return 0


def case_old_setting(work, repo, origin, env):
    """A leftover TEAMWORK_BOARD or TEAMWORK_LANDING, in the environment and in the project's settings, changes nothing: the whole path still calls no gh."""
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "settings.local.json").write_text(json.dumps({"env": {"TEAMWORK_BOARD": "github", "TEAMWORK_LANDING": "github"}}))
    return case_whole(work, repo, origin, {**env, "TEAMWORK_BOARD": "files", "TEAMWORK_LANDING": "github"})


def case_base_required(work, repo, origin, env):
    use(env, repo, "use-board.py", "file", "Probe the part", text_file(work, "part.md", PART), "scope:probe")
    (work / "edit.diff").write_text("--- a/body\n+++ b/body\n@@ -1 +1 @@\n-Probe the part.\n+Probe the part, edited.\n")
    before = commits(env, repo)
    run = use(env, repo, "edit-issue-body.py", "1", work / "edit.diff", "DECIDED: probe the edit", check=False)
    if run.returncode != 2 or commits(env, repo) != before:
        return fail(f"an edit with no --base exited {run.returncode} and added {commits(env, repo) - before} commits")
    sha = next(line.split(": ", 1)[1] for line in use(env, repo, "use-board.py", "read", "1").stdout.splitlines() if line.startswith("body sha: "))
    run = use(env, repo, "edit-issue-body.py", "1", work / "edit.diff", "DECIDED: probe the edit", "--base", sha, check=False)
    if run.returncode or commits(env, repo) != before + 1:
        return fail(f"an edit with --base exited {run.returncode} and added {commits(env, repo) - before} commits: {run.stderr[-200:]}")
    return 0


def case_layout(work, repo, origin, env):
    part = use(env, repo, "use-board.py", "file", "Probe the part", text_file(work, "part.md", PART), "--scope", "probe").stdout.strip()
    root = use(env, repo, "use-board.py", "file", "Probe the root", text_file(work, "root.md", ROOT)).stdout.strip()
    held = set(sh("git", "ls-tree", "-r", "--name-only", REF, cwd=repo, env=env).stdout.split())
    if not {"probe/1/issue.json", "probe/1/body.md", "2/issue.json", "2/body.md"} <= held:
        return fail(f"the ref holds {sorted(held)}")
    if sh("git", "rev-parse", "--verify", "-q", "refs/teamwork/board", cwd=repo, env=env, check=False).returncode == 0:
        return fail("the old ref refs/teamwork/board was written")
    if not part.endswith(f"/{REF}/probe/1") or not root.endswith(f"/{REF}/2"):
        return fail(f"the urls are {part} and {root}")
    before = commits(env, repo)
    refused = use(env, repo, "use-board.py", "file", "Probe the typo", text_file(work, "typo.md", "Typo.\n"), "--scope", "nowhere", check=False)
    if refused.returncode == 0 or commits(env, repo) != before or "nowhere" not in refused.stderr:
        return fail(f"a scope that names no folder: exit {refused.returncode}, {commits(env, repo) - before} commits, {refused.stderr.strip()[-200:]}")
    read = {number: use(env, repo, "use-board.py", "read", number).stdout for number in ("1", "2")}
    if "scope: probe\n" not in read["1"] or "scope: (repository root)\n" not in read["2"]:
        return fail(f"read gives {read['1'][:80]!r} and {read['2'][:80]!r}")
    for project, wanted in (("probe", {1}), ("nofolder", {2})):
        pane = sh(sys.executable, HOOKS / "list-issue-board.py", project, "--json", cwd=repo, env=env, check=False)
        shown = {row["number"] for row in json.loads(pane.stdout)} if pane.returncode == 0 else None
        if shown != wanted:
            return fail(f"the pane of {project} shows {shown}, wanted {wanted}: {pane.stderr[-200:]}")
    folders = [use(env, repo, "print-scope-folder.py", name).stdout for name in ("probe-manager", "nofolder-manager")]
    if folders != ["probe\n", "\n"]:
        return fail(f"print-scope-folder.py gave {folders}")
    return 0


def case_atomic(work, repo, origin, env):
    env = {**env, "TEAMWORK_BOARD": "git"}
    use(env, repo, "use-board.py", "file", "Probe the part", text_file(work, "part.md", PART), "--scope", "probe")
    use(env, repo, "use-board.py", "file", "Probe the root", text_file(work, "root.md", ROOT), "--scope", "probe")
    use(env, repo, "use-board.py", "file", "Probe the stopped part", text_file(work, "stoppart.md", "Stopped part.\n"), "--scope", "probe")
    use(env, repo, "use-board.py", "file", "Probe the stopped task", text_file(work, "stopped.md", "Stopped.\n\n## Definition of done\n\n1. [task] #3 Probe the stopped part\n"), "--scope", "probe")

    def added(why, run, want=1):
        before = commits(env, repo)
        done = run()
        got = commits(env, repo) - before
        return None if got == want else f"{why} added {got} commits, wanted {want}: {getattr(done, 'stderr', '')[-200:]}"

    def make_diff():
        (work / "new").write_text(ROOT + "\nExtra paragraph.\n")
        (work / "old").write_text(ROOT)
        diff = subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout
        (work / "edit.diff").write_text(diff)

    def body_sha():
        return next(line.split(": ", 1)[1] for line in use(env, repo, "use-board.py", "read", "2").stdout.splitlines() if line.startswith("body sha: "))

    def edit_body():
        make_diff()
        return use(env, repo, "edit-issue-body.py", "2", work / "edit.diff", "DECIDED: probe the edit", "--base", body_sha(), check=False)

    def refused_edit():
        (work / "bad.diff").write_text("--- a/body\n+++ b/body\n@@ -1 +1 @@\n-Other text.\n+Changed.\n")
        return use(env, repo, "edit-issue-body.py", "2", work / "bad.diff", "DECIDED: probe the edit", "--base", body_sha(), check=False)

    def stale_edit():
        make_diff()
        return use(env, repo, "edit-issue-body.py", "2", work / "edit.diff", "DECIDED: probe the edit", "--base", "0" * 12, check=False)

    def reopening_edit():
        # a closed root whose new body gains an open part reopens in the same write
        return sh(sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import board; board.edit(2, board.body(2) + '\\n2. [task] #5 Probe the new part\\n')",
                  HERE.parents[2] / "lib", cwd=repo, env=env, check=False)

    for why, run, want in (("a diff of a body that changed since it was read", stale_edit, 0),
                           ("edit-issue-body.py", edit_body, 1),
                           ("a diff that does not apply", refused_edit, 0),
                           ("resolve of a part whose parent closes", lambda: use(env, repo, "use-board.py", "resolve", "1", text_file(work, "r1.md", "Part done.\n")), 1),
                           ("resolve --not-planned of a task with an open part", lambda: use(env, repo, "use-board.py", "resolve", "4", text_file(work, "r3.md", "Not now.\n"), "--not-planned"), 1)):
        problem = added(why, run, want)
        if problem:
            return fail(problem)
    if state(env, repo, "2") != ["state: CLOSED"] or state(env, repo, "4") != ["state: CLOSED"]:
        return fail(f"the verbs did not close what they should: {state(env, repo, '2')} {state(env, repo, '4')}")
    # the part is filed first, so the reopening edit is the only write counted
    use(env, repo, "use-board.py", "file", "Probe the new part", text_file(work, "newpart.md", "New part.\n"), "--scope", "probe")
    problem = added("an edit that reopens a closed root", reopening_edit, 1)
    if problem:
        return fail(problem)
    if state(env, repo, "2") != ["state: OPEN"]:
        return fail(f"the root did not reopen: {state(env, repo, '2')}")
    return 0


def case_cloud_refused(work, repo, origin, env):
    use(env, repo, "use-board.py", "file", "Probe the part", text_file(work, "part.md", PART), "--scope", "probe")
    before = commits(env, repo)
    held = text_file(work, "cloud.md", "REPORTED: probe\n\n```teamwork\ncloud: probe-worker\n```\n")
    run = use(env, repo, "use-board.py", "comment", "1", held, check=False)
    if run.returncode == 0 or commits(env, repo) != before or "is no key the teamwork fence takes" not in run.stdout + run.stderr:
        return fail(f"a `cloud:` holder line exited {run.returncode} and added {commits(env, repo) - before} commits: {(run.stdout + run.stderr)[-200:]}")
    run = use(env, repo, "start-session.py", "probe-worker", repo, "worker probe-worker manager probe-manager set remote #1", "--model", "m", "--effort", "e", check=False)
    if run.returncode != 2 or "set remote" not in run.stderr:
        return fail(f"start-session.py with `set remote` exited {run.returncode}: {run.stderr[-200:]}")
    return 0


CASES = {"whole": case_whole, "cloud-refused": case_cloud_refused, "layout": case_layout, "old-setting": case_old_setting, "base-required": case_base_required, "atomic": case_atomic}


def main(args):
    if args not in ([], *(["--case", name] for name in CASES)):
        print(__doc__, file=sys.stderr)
        return 2
    name = args[1] if args else "whole"
    try:
        if CASES[name](*setup()):
            return 1
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return fail(str(e)[-400:])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
