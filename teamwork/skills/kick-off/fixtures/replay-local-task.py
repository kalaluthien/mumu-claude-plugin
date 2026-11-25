#!/usr/bin/env python3
"""Run a team's whole path on the git board in a scratch repository whose `origin` is a bare repository beside it, with the `gh` stand-in, which logs each call and fails,
and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-local-task.py [--case <name>]   (no argument: every one in turn)
- whole: file a part and a root that names it, route the part by `hold`, branch, change, judge-approved merge and push of a worker's change, `resolve` the part so the root closes,
  the task pane and the heartbeat's one poll, writing and reading the real hooks and scripts, and require an empty gh log.
- layout: `file --scope probe` puts a task at `probe/<n>/` of the one ref `refs/teamwork-blackboard` and a filing with no scope puts it at `<n>/`, each url names its folder, a `--scope` that names no folder of the repository is refused with no commit, `read` finds a task by number alone, and the pane of `probe` reads its folder only while a project with no folder reads the root's own tasks only
- old-setting: a leftover `TEAMWORK_BOARD` or `TEAMWORK_LANDING` in the environment and in the project's settings changes nothing, and the whole path still calls no gh
- base-required: `use-board.py edit` with no `--base` exits 2 and adds no commit, and with the board's `body sha` it adds one
- cloud-refused: a comment whose teamwork fence holds a `cloud:` line is refused and adds no commit, and `start-session.py` with `set remote` exits 2
- atomic: `use-board.py edit`, `board.edit` that reopens a closed root, `resolve` of a part whose parent then closes and `resolve --not-planned` of a task with an open part each add exactly one commit to the board's ref, and a diff handed over as the new body, or an edit whose `--base` names an older body, adds none"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
HOOKS = HERE.parents[2] / "hooks"
MONITORS = HERE.parents[2] / "monitors"
REF = "refs/teamwork-blackboard"
PART = "Probe the part.\n"
ROOT = "Probe the root.\n\n## Definition of done\n\n1. [task] #1 Probe the part\n"
TEAM = (replay_probe.agent("probe-manager", 1, "working"), replay_probe.agent("probe-worker", 2, "working"))


def setup(work):
    """A sandbox whose repository holds `a.txt` and `probe/a.txt`, pushed to a bare `origin` at `sandbox.origin`."""
    sandbox = replay_probe.Sandbox(work, TEAM, commit=False)
    sandbox.origin = work / "origin.git"
    replay_probe.write_text(sandbox.repository, "a.txt", "base\n")
    (sandbox.repository / "probe").mkdir()
    replay_probe.write_text(sandbox.repository / "probe", "a.txt", "base\n")
    sandbox.git("add", "-A")
    sandbox.git("commit", "-q", "-m", "base")
    sandbox.git("init", "-q", "--bare", sandbox.origin, cwd=work)
    sandbox.git("remote", "add", "origin", sandbox.origin)
    sandbox.git("push", "-q", "-u", "origin", "main")
    return sandbox


def use(sandbox, script, *argv, cwd=None, check=True):
    return replay_probe.sh(sys.executable, SCRIPTS / script, *argv, cwd=cwd or sandbox.repository, environment=sandbox.environment, check=check)


def commits(sandbox):
    return int(replay_probe.sh("git", "rev-list", "--count", REF, cwd=sandbox.repository, environment=sandbox.environment, check=False).stdout.strip() or 0)


def state(sandbox, number):
    """The `state:` line `read` prints for NUMBER, without its wait."""
    return [line.split(",")[0] for line in use(sandbox, "use-board.py", "read", number, check=False).stdout.splitlines()[1:2]]


def case_whole(sandbox):
    use(sandbox, "use-board.py", "file", "--title", "Probe the part", "--body", replay_probe.write_text(sandbox.work, "part.md", PART), "--scope", "probe")
    use(sandbox, "use-board.py", "file", "--title", "Probe the root", "--body", replay_probe.write_text(sandbox.work, "root.md", ROOT), "--scope", "probe")
    use(sandbox, "use-board.py", "file", "--title", "Probe the late task", "--body", replay_probe.write_text(sandbox.work, "late.md", "Unrouted.\n"), "--scope", "probe")
    use(sandbox, "use-board.py", "hold", "1", "--holders", "probe-worker")
    beat = sandbox.python(MONITORS / "print-team-gaps.py", "--polls", "1", pane="w1:p1", timeout=60, TEAMWORK_MONITOR_POLL=0)
    if "route #3" not in beat.stdout:
        return replay_probe.fail(f"the heartbeat routed no unrouted task on the git board: exit {beat.returncode}, {(beat.stdout + beat.stderr)[-300:]}")
    tree = pathlib.Path(use(sandbox, "add-worktree.py", "probe-worker", "main").stdout.strip())
    (tree / "b.txt").write_text("work\n")
    sandbox.git("add", "-A", cwd=tree)
    sandbox.git("commit", "-q", "-m", "work", cwd=tree)
    head = sandbox.git("rev-parse", "HEAD", cwd=tree).strip()
    use(sandbox, "../references/adapters/landing-git/scripts/use-landing.py", "change", "probe-worker", "Probe change", replay_probe.write_text(sandbox.work, "change.md", "Probe change. Closes #1.\n"), cwd=tree)
    merged = use(sandbox, "../references/adapters/landing-git/scripts/use-landing.py", "merge", "1", head, cwd=tree).stdout.strip()
    if sandbox.git("rev-parse", "refs/heads/main", cwd=sandbox.origin).strip() != merged:
        return replay_probe.fail("the merge did not reach origin's main")
    use(sandbox, "use-board.py", "resolve", "1", "--summary", "Probe part done.")
    if state(sandbox, "2") != ["state: CLOSED"]:
        return replay_probe.fail(f"the root did not close with its last part: {state(sandbox, '2')}")
    pane = sandbox.python(HOOKS / "list-task-board.py", "probe", "--json")
    if pane.returncode or "Probe the late task" not in pane.stdout:
        return replay_probe.fail(f"the pane: exit {pane.returncode} {pane.stdout[:200]} {pane.stderr[-200:]}")
    if sandbox.gh_calls():
        return replay_probe.fail(f"gh was called: {sandbox.gh_calls()[:300]}")
    return 0


def case_old_setting(sandbox):
    """A leftover TEAMWORK_BOARD or TEAMWORK_LANDING, in the environment and in the project's settings, changes nothing: the whole path still calls no gh."""
    (sandbox.repository / ".claude").mkdir(exist_ok=True)
    (sandbox.repository / ".claude" / "settings.local.json").write_text(json.dumps({"env": {"TEAMWORK_BOARD": "github", "TEAMWORK_LANDING": "github"}}))
    sandbox.environment.update({"TEAMWORK_BOARD": "files", "TEAMWORK_LANDING": "github"})
    return case_whole(sandbox)


def case_base_required(sandbox):
    use(sandbox, "use-board.py", "file", "--title", "Probe the part", "--body", replay_probe.write_text(sandbox.work, "part.md", PART), "--label", "scope:probe")
    (sandbox.work / "edit.md").write_text(PART.replace("Probe the part.", "Probe the part, edited."))
    before = commits(sandbox)
    run = use(sandbox, "use-board.py", "edit", "1", "--body", sandbox.work / "edit.md", "--reason", "probe the edit", check=False)
    if run.returncode != 2 or commits(sandbox) != before:
        return replay_probe.fail(f"an edit with no --base exited {run.returncode} and added {commits(sandbox) - before} commits")
    sha = next(line.split(": ", 1)[1] for line in use(sandbox, "use-board.py", "read", "1").stdout.splitlines() if line.startswith("body sha: "))
    run = use(sandbox, "use-board.py", "edit", "1", "--body", sandbox.work / "edit.md", "--reason", "probe the edit", "--base", sha, check=False)
    if run.returncode or commits(sandbox) != before + 1:
        return replay_probe.fail(f"an edit with --base exited {run.returncode} and added {commits(sandbox) - before} commits: {run.stderr[-200:]}")
    return 0


def case_layout(sandbox):
    part = use(sandbox, "use-board.py", "file", "--title", "Probe the part", "--body", replay_probe.write_text(sandbox.work, "part.md", PART), "--scope", "probe").stdout.strip()
    root = use(sandbox, "use-board.py", "file", "--title", "Probe the root", "--body", replay_probe.write_text(sandbox.work, "root.md", ROOT)).stdout.strip()
    held = set(sandbox.git("ls-tree", "-r", "--name-only", REF).split())
    if not {"probe/1/task.json", "probe/1/body.md", "2/task.json", "2/body.md"} <= held:
        return replay_probe.fail(f"the ref holds {sorted(held)}")
    if replay_probe.sh("git", "rev-parse", "--verify", "-q", "refs/teamwork/board", cwd=sandbox.repository, environment=sandbox.environment, check=False).returncode == 0:
        return replay_probe.fail("the old ref refs/teamwork/board was written")
    if not part.endswith(f"/{REF}/probe/1") or not root.endswith(f"/{REF}/2"):
        return replay_probe.fail(f"the urls are {part} and {root}")
    before = commits(sandbox)
    refused = use(sandbox, "use-board.py", "file", "--title", "Probe the typo", "--body", replay_probe.write_text(sandbox.work, "typo.md", "Typo.\n"), "--scope", "nowhere", check=False)
    if refused.returncode == 0 or commits(sandbox) != before or "nowhere" not in refused.stderr:
        return replay_probe.fail(f"a scope that names no folder: exit {refused.returncode}, {commits(sandbox) - before} commits, {refused.stderr.strip()[-200:]}")
    read = {number: use(sandbox, "use-board.py", "read", number).stdout for number in ("1", "2")}
    if "scope: probe\n" not in read["1"] or "scope: (repository root)\n" not in read["2"]:
        return replay_probe.fail(f"read gives {read['1'][:80]!r} and {read['2'][:80]!r}")
    for project, wanted in (("probe", {1}), ("nofolder", {2})):
        pane = sandbox.python(HOOKS / "list-task-board.py", project, "--json")
        shown = {row["number"] for row in json.loads(pane.stdout)} if pane.returncode == 0 else None
        if shown != wanted:
            return replay_probe.fail(f"the pane of {project} shows {shown}, wanted {wanted}: {pane.stderr[-200:]}")
    folders = [use(sandbox, "../references/manager/scripts/print-scope-folder.py", name).stdout for name in ("probe-manager", "nofolder-manager")]
    if folders != ["probe\n", "\n"]:
        return replay_probe.fail(f"print-scope-folder.py gave {folders}")
    return 0


def case_atomic(sandbox):
    sandbox.environment["TEAMWORK_BOARD"] = "git"
    use(sandbox, "use-board.py", "file", "--title", "Probe the part", "--body", replay_probe.write_text(sandbox.work, "part.md", PART), "--scope", "probe")
    use(sandbox, "use-board.py", "file", "--title", "Probe the root", "--body", replay_probe.write_text(sandbox.work, "root.md", ROOT), "--scope", "probe")
    use(sandbox, "use-board.py", "file", "--title", "Probe the stopped part", "--body", replay_probe.write_text(sandbox.work, "stoppart.md", "Stopped part.\n"), "--scope", "probe")
    use(sandbox, "use-board.py", "file", "--title", "Probe the stopped task", "--body", replay_probe.write_text(sandbox.work, "stopped.md", "Stopped.\n\n## Definition of done\n\n1. [task] #3 Probe the stopped part\n"), "--scope", "probe")

    def added(why, run, want=1):
        before = commits(sandbox)
        done = run()
        got = commits(sandbox) - before
        return None if got == want else f"{why} added {got} commits, wanted {want}: {getattr(done, 'stderr', '')[-200:]}"

    def make_body():
        (sandbox.work / "edit.md").write_text(ROOT + "\nExtra paragraph.\n")

    def body_sha():
        return next(line.split(": ", 1)[1] for line in use(sandbox, "use-board.py", "read", "2").stdout.splitlines() if line.startswith("body sha: "))

    def edit_body():
        make_body()
        return use(sandbox, "use-board.py", "edit", "2", "--body", sandbox.work / "edit.md", "--reason", "probe the edit", "--base", body_sha(), check=False)

    def refused_edit():
        (sandbox.work / "bad.diff").write_text("--- a/body\n+++ b/body\n@@ -1 +1 @@\n-Other text.\n+Changed.\n")
        return use(sandbox, "use-board.py", "edit", "2", "--body", sandbox.work / "bad.diff", "--reason", "probe the edit", "--base", body_sha(), check=False)

    def stale_edit():
        make_body()
        return use(sandbox, "use-board.py", "edit", "2", "--body", sandbox.work / "edit.md", "--reason", "probe the edit", "--base", "0" * 12, check=False)

    def reopening_edit():
        # a closed root whose new body gains an open part reopens in the same write
        return replay_probe.sh(sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import board; board.edit(2, board.body(2) + '\\n2. [task] #5 Probe the new part\\n')",
                  HERE.parents[2] / "lib", cwd=sandbox.repository, environment=sandbox.environment, check=False)

    for why, run, want in (("a new body made from one that changed since it was read", stale_edit, 0),
                           ("use-board.py edit", edit_body, 1),
                           ("a diff handed over as the new body", refused_edit, 0),
                           ("resolve of a part whose parent closes", lambda: use(sandbox, "use-board.py", "resolve", "1", "--summary", "Part done."), 1),
                           ("resolve --not-planned of a task with an open part", lambda: use(sandbox, "use-board.py", "resolve", "4", "--summary", "Not now.", "--not-planned"), 1)):
        problem = added(why, run, want)
        if problem:
            return replay_probe.fail(problem)
    if state(sandbox, "2") != ["state: CLOSED"] or state(sandbox, "4") != ["state: CLOSED"]:
        return replay_probe.fail(f"the verbs did not close what they should: {state(sandbox, '2')} {state(sandbox, '4')}")
    # the part is filed first, so the reopening edit is the only write counted
    use(sandbox, "use-board.py", "file", "--title", "Probe the new part", "--body", replay_probe.write_text(sandbox.work, "newpart.md", "New part.\n"), "--scope", "probe")
    problem = added("an edit that reopens a closed root", reopening_edit, 1)
    if problem:
        return replay_probe.fail(problem)
    if state(sandbox, "2") != ["state: OPEN"]:
        return replay_probe.fail(f"the root did not reopen: {state(sandbox, '2')}")
    return 0


def case_cloud_refused(sandbox):
    use(sandbox, "use-board.py", "file", "--title", "Probe the part", "--body", replay_probe.write_text(sandbox.work, "part.md", PART), "--scope", "probe")
    before = commits(sandbox)
    held = replay_probe.write_text(sandbox.work, "cloud.md", "```teamwork\ncloud: probe-worker\n```\n")
    run = use(sandbox, "use-board.py", "comment", "1", "--reported", "probe", "--text", held, check=False)
    if run.returncode == 0 or commits(sandbox) != before or "opens a `teamwork` fence" not in run.stdout + run.stderr:
        return replay_probe.fail(f"a `cloud:` holder line exited {run.returncode} and added {commits(sandbox) - before} commits: {(run.stdout + run.stderr)[-200:]}")
    run = use(sandbox, "start-session.py", "probe-worker", sandbox.repository, "worker probe-worker manager probe-manager set remote #1", "--model", "m", "--effort", "e", check=False)
    if run.returncode != 2 or "set remote" not in run.stderr:
        return replay_probe.fail(f"start-session.py with `set remote` exited {run.returncode}: {run.stderr[-200:]}")
    return 0


CASES = {"whole": case_whole, "cloud-refused": case_cloud_refused, "layout": case_layout, "old-setting": case_old_setting, "base-required": case_base_required, "atomic": case_atomic}


def main(args):
    if not args:
        return replay_probe.run_every(__file__, "--case", CASES)
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("local-task-") as work:
        try:
            if CASES[args[1]](setup(work)):
                return 1
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            return replay_probe.fail(str(e)[-400:])
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
