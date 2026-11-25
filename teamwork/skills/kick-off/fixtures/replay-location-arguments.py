#!/usr/bin/env python3
"""Run a worker's flow on a scratch repository from a folder outside every repository, each script naming the repository it acts on with `--repository`, print `ok <case>`
or `fail <case>: <what differed>` per case, then `PASS location arguments` as the last line when every case holds, else `FAIL location arguments`, and exit 1 on any failure.

usage: replay-location-arguments.py
- flow: `use-board.py` file, read and comment, `add-worktree.py`, `run-criteria.py` on a task whose `[check]` passes only in that worktree, and `remove-worktree.py` each act on the
  repository or worktree they name, `--repository=<folder>` with options after it included, the board of the repository holds the writes, the check fails when it runs in the main checkout, and a folder in no repository, or none given, is refused with exit 2
- names: `remove-worktree.py` and `add-worktree.py` refuse a name holding `/` or `..` or opening with `-`, or one that is a link out of the worktrees or to another worktree, a refused name beside a good one removes nothing, and the repository's other worktree stays
- removal: a worker removing its own worktree and another's from inside its own, on a repository with an `origin`, loses both worktrees, both branches and both `origin` branches that
  the base holds, and `git fetch` runs once
- squash: two workers whose branches a pull request merged as a squash are removed with their worktrees, branches and `origin` branches, one whose merge only the newest closed pull requests list and one whose merge only a lookup by its branch finds
- every: each other script whose `usage:` line takes `--repository` (`use-landing.py`, `backtest-estimate.py`, `estimate-task-time.py`, `list-task-durations.py`, `print-scope-folder.py`,
  `recall-work.py`, `run-on-refs.py`, `list-additions.py`, `print-task-markdown.py`, `list-task-board.py`, `check-criteria.py`, `close-session.py` and `start-session.py`, which also refuses a folder outside the repository and a call that names none, and takes the repository through a link and from a folder below a worktree) runs once from a folder outside every repository, on the scratch repository it names, with
  the exit and the text that repository gives, and none reports that it found no repository
- forms: no playbook (`teamwork/**/*.md`), `hooks.json`, `monitors.json`, fixture or open task body of the board, read when the runner sits in a repository, holds a teamwork script run after a `cd` in the same command line,
  each hit listed with its file and line, or its task number and line"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = HERE.parent / "scripts"
REFERENCES = HERE.parent / "references"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe runs in its worktree**: `sh -c 'git branch --show-current | sed s/probe-worker/PASS/'` prints `PASS`; on base `FAIL`.\n")
failed = []


def step(name, case, *argv):
    """Runs CASE with ARGV and prints its result; a call of the case that exits nonzero, which `replay_probe.sh` raises, is the case's failure."""
    try:
        problem = case(*argv)
    except (RuntimeError, OSError, ValueError) as e:
        problem = e
    print(f"fail {name}: {' '.join(str(problem).split())[:900]}" if problem else f"ok {name}", flush=True)
    failed.extend([name] if problem else [])


def setup():
    """(work, the folder every call is made from, the scratch repository, the environment): the repository holds one commit and a second worktree of another worker."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="location-arguments-")).resolve()
    stub = replay_probe.stub_gh(work)
    replay_probe.write_git_config(work)
    environment = {**{key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "TEAMWORK_"))}, "PATH": f"{stub}:{os.environ['PATH']}", "HOME": str(work),
                   "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(work / "gitconfig")}
    elsewhere, repository = work / "elsewhere", work / "repository"
    elsewhere.mkdir()
    replay_probe.sh("git", "init", "-q", repository, cwd=work, environment=environment)
    (repository / "a.txt").write_text("base\n")
    replay_probe.sh("git", "add", "-A", cwd=repository, environment=environment)
    replay_probe.sh("git", "commit", "-q", "-m", "base", cwd=repository, environment=environment)
    replay_probe.sh("git", "worktree", "add", "-q", "-b", "other-worker", repository / ".claude" / "worktrees" / "other-worker", cwd=repository, environment=environment)
    return work, elsewhere, repository, environment


def trees(repository, environment):
    """The paths of the worktrees git lists for REPOSITORY, the main checkout first."""
    listed = replay_probe.sh("git", "worktree", "list", "--porcelain", cwd=repository, environment=environment).stdout.splitlines()
    return [pathlib.Path(line.split(" ", 1)[1]).resolve() for line in listed if line.startswith("worktree ")]


def case_flow(work, elsewhere, repository, environment):
    def call(script, *argv, check=True):
        return replay_probe.sh(sys.executable, SCRIPTS / script, *argv, cwd=elsewhere, environment=environment, check=check)

    body = replay_probe.write_text(work, "body.md", BODY)
    url = call("use-board.py", "file", "--title", "Print ok from the probe", "--body", body, "--repository", repository).stdout.strip()
    held = replay_probe.sh("git", "rev-parse", "--verify", "-q", "refs/teamwork-blackboard", cwd=repository, environment=environment, check=False)
    if not url.endswith("/1") or held.returncode:
        return f"file printed {url!r} and the board ref of the repository gave exit {held.returncode}"
    shown = call("use-board.py", "read", "1", "--repository", repository).stdout
    if "Print ok from the probe" not in shown:
        return f"read did not show the filed task: {shown[:200]}"
    call("use-board.py", "comment", "1", "--reported", "Probe reports.", "--repository", repository)
    if "Probe reports." not in call("use-board.py", "read", "1", "--full", "--repository", repository).stdout:
        return "the comment is not on the task"
    neighbour = work / "neighbour"  # another repository the call stands in, whose board must stay empty
    replay_probe.sh("git", "init", "-q", neighbour, cwd=work, environment=environment)
    replay_probe.sh(sys.executable, SCRIPTS / "use-board.py", "comment", "1", f"--repository={repository}", "--reported", "Joined form.", cwd=neighbour, environment=environment)
    none_here = replay_probe.sh("git", "rev-parse", "--verify", "-q", "refs/teamwork-blackboard", cwd=neighbour, environment=environment, check=False)
    if "Joined form." not in call("use-board.py", "read", "1", "--full", "--repository", repository).stdout or not none_here.returncode:
        return f"a comment written with `--repository=<folder>` from another repository is not on the named board only (the other board ref gave exit {none_here.returncode})"
    tree = pathlib.Path(call("add-worktree.py", "probe-worker", "main", "--repository", repository).stdout.strip())
    if tree != repository / ".claude" / "worktrees" / "probe-worker" or tree not in trees(repository, environment):
        return f"add-worktree printed {tree}; the repository lists {trees(repository, environment)}"
    from_tree = call("run-criteria.py", "--fresh", "--repository", tree, "1", check=False)
    if from_tree.returncode or "| pass | PASS |" not in from_tree.stdout:
        return f"the check did not pass in the worktree: exit {from_tree.returncode} {from_tree.stdout[-300:]} {from_tree.stderr[-300:]}"
    from_main = call("run-criteria.py", "--fresh", "--repository", repository, "1", check=False)
    if from_main.returncode != 1 or "| fail |" not in from_main.stdout:
        return f"the check ran in the main checkout, not where it was named: exit {from_main.returncode} {from_main.stdout[-300:]}"
    outside = call("use-board.py", "read", "1", "--repository", work / "no-such-folder", check=False)
    plain = call("use-board.py", "read", "1", check=False)
    if outside.returncode != 2 or outside.stdout or outside.stderr.count("\n") != 1:
        return f"a folder that does not exist gave exit {outside.returncode}, stdout {outside.stdout!r}, stderr {outside.stderr!r}"
    in_no_repository = call("use-board.py", "read", "1", "--repository", elsewhere, check=False)
    if in_no_repository.returncode != 2 or in_no_repository.stdout or in_no_repository.stderr.count("\n") != 1:
        return f"a folder in no repository gave exit {in_no_repository.returncode}, stdout {in_no_repository.stdout!r}, stderr {in_no_repository.stderr!r}"
    if plain.returncode == 0:
        return "a call with no folder named read the board from outside every repository"
    removed = call("remove-worktree.py", "probe-worker", "--repository", tree).stdout
    if tree.exists() or tree in trees(repository, environment) or "worktree" not in removed:
        return f"remove-worktree left {tree}: {removed}"
    return None


def with_origin(work, name, environment):
    """(a repository NAME of one commit pushed to a bare `origin` of its own, a function that runs `git` in it or in a folder given)."""
    shared, origin = work / name, work / f"{name}-origin.git"

    def git(*argv, cwd=shared):
        return replay_probe.sh("git", *argv, cwd=cwd, environment=environment).stdout

    git("init", "-q", shared, cwd=work)
    (shared / "a.txt").write_text("base\n")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    git("init", "-q", "--bare", origin, cwd=work)
    git("remote", "add", "origin", origin)
    git("push", "-q", "-u", "origin", "main")
    git("remote", "set-head", "origin", "main")
    return shared, git


def worker_with_commit(work, shared, git, name, environment):
    """The worktree of worker NAME, holding one commit its branch alone has."""
    tree = pathlib.Path(replay_probe.sh(sys.executable, SCRIPTS / "add-worktree.py", name, "main", "--repository", shared, cwd=work, environment=environment).stdout.strip())
    (tree / f"{name}.txt").write_text(f"{name}\n")
    git("add", "-A", cwd=tree)
    git("commit", "-q", "-m", name, cwd=tree)
    return tree


def case_squash(work, elsewhere, repository, environment):
    """Two workers whose branches a pull request merged as a squash, so `origin/HEAD` lacks their commits, are removed with their branches: one whose merge only the list of the newest closed pull requests gives, one whose merge only a lookup by its branch gives."""
    shared, git = with_origin(work, "squash", environment)
    names = ("late-worker", "recent-worker")
    trees = [worker_with_commit(work, shared, git, name, environment) for name in names]
    git("push", "-q", "origin", *names)
    stubs = work / "late-gh"
    stubs.mkdir()
    pulls = {name: json.dumps([{"number": number, "headRefName": name, "headRefOid": git("rev-parse", name).strip(), "mergedAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"}])
             for number, name in enumerate(names, 7)}
    replay_probe.write_text(stubs, "gh", f"#!/bin/sh\ncase \"$*\" in *'--head late-worker'*) echo '{pulls['late-worker']}';; *'--head'*) echo '[]';; *) echo '{pulls['recent-worker']}';; esac\n").chmod(0o755)
    done = replay_probe.sh(sys.executable, SCRIPTS / "remove-worktree.py", *names, "--repository", shared, cwd=elsewhere, check=False,
                           environment={**environment, "PATH": f"{stubs}:{environment['PATH']}", "GH_REPO": "owner/repository"})
    left = [word for word in git("for-each-ref", "--format=%(refname)").split() + git("ls-remote", "--heads", "origin").split() if word.endswith(names)]
    return None if not done.returncode and not left and not any(tree.exists() for tree in trees) else f"exit {done.returncode}, left {left}: {done.stdout[-300:]}{done.stderr[-300:]}"


def case_removal(work, elsewhere, repository, environment):
    """Two merged workers removed in one call from inside the first one's worktree, `git` counted by a stand-in first on `PATH`."""
    shared, git = with_origin(work, "removal", environment)

    def add(name):
        tree = worker_with_commit(work, shared, git, name, environment)
        git("merge", "-q", "--ff-only", name)
        return tree

    own = add("first-worker")
    add("second-worker")
    git("push", "-q", "origin", "main", "first-worker", "second-worker")
    other = work / "removal-other"  # another clone puts a commit on origin's main that this checkout lacks, so only a fast-forward pull brings it in
    git("clone", "-q", work / "removal-origin.git", other, cwd=work)
    (other / "b.txt").write_text("ahead\n")
    git("add", "-A", cwd=other)
    git("commit", "-q", "-m", "ahead", cwd=other)
    git("push", "-q", "origin", "main", cwd=other)
    log = work / "git.log"
    (work / "git-stand-in").mkdir()
    stand_in = replay_probe.write_text(work / "git-stand-in", "git", f'#!/bin/sh\necho "$1" >> {log}\nexec {shutil.which("git", path=environment["PATH"])} "$@"\n')
    stand_in.chmod(0o755)
    done = replay_probe.sh(sys.executable, SCRIPTS / "remove-worktree.py", "first-worker", "second-worker", "--repository", own, cwd=own,
                           environment={**environment, "PATH": f"{stand_in.parent}:{environment['PATH']}"}, check=False)
    fetches = log.read_text().split().count("fetch")
    left = [word for word in git("for-each-ref", "--format=%(refname)").split() + git("ls-remote", "--heads", "origin").split() + [str(path) for path in trees(shared, environment)]
            if word.endswith(("first-worker", "second-worker"))]
    tip = git("ls-remote", "origin", "refs/heads/main").split()[0]
    if done.returncode or fetches != 1 or left or done.stdout.count("origin branch") != 2 or git("rev-parse", "HEAD").strip() != tip:
        return f"exit {done.returncode}, {fetches} fetches, left {left}, the main checkout at {git('rev-parse', 'HEAD').strip()} and origin's main at {tip}: {done.stdout[-400:]}{done.stderr[-300:]}"
    return None


def case_names(work, elsewhere, repository, environment):
    def call(script, *argv):
        return replay_probe.sh(sys.executable, SCRIPTS / script, *argv, "--repository", repository, cwd=elsewhere, environment=environment, check=False)

    good = pathlib.Path(call("add-worktree.py", "good-worker", "main").stdout.strip())
    other = repository / ".claude" / "worktrees" / "other-worker"
    before = trees(repository, environment)
    if good != repository / ".claude" / "worktrees" / "good-worker" or good not in before or other not in before:
        return f"a good name gave {good}, and the repository lists {before}"
    for name in ("../x", "a/b", "-x", "../../other-worker", "other-worker/..", ".hidden"):
        for script, argv in (("remove-worktree.py", [name]), ("remove-worktree.py", ["good-worker", name]), ("add-worktree.py", [name, "main"])):
            done = call(script, *argv)
            if done.returncode == 0 or (not name.startswith("-") and "is no worktree name" not in done.stderr) or trees(repository, environment) != before:
                return f"{script} {argv} gave exit {done.returncode} and left {trees(repository, environment)}: {done.stdout}{done.stderr}"
    for argv in (["good-worker", "-x"], ["good-worker", "main", "-x"]):  # a flag as the base or the branch is refused before git reads it as an option
        done = call("add-worktree.py", *argv)
        if done.returncode != 2 or "usage: add-worktree.py" not in done.stderr or trees(repository, environment) != before:
            return f"add-worktree.py {argv} gave exit {done.returncode}, stderr {done.stderr[:200]!r} and left {trees(repository, environment)}"
    if (repository / ".claude" / "x").exists() or (work / "x").exists() or not other.is_dir() or not good.is_dir():
        return "a refused name still made or removed a folder"
    call("remove-worktree.py", "good-worker")
    if good.exists() or other not in trees(repository, environment):
        return f"removing the good name left {good} or took the other worker's worktree: {trees(repository, environment)}"
    return names_refused(work, elsewhere, repository, environment, call)


def names_refused(work, elsewhere, repository, environment, call):
    """The calls `names` refuses beyond a bad name: a worktree folder that is a link to a folder elsewhere, a flag with no folder, two folders or a folder opening with `-`, and a
    call from outside every repository that names none."""
    outside = work / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("kept\n")
    before = trees(repository, environment)
    for target, name in ((outside, "escape-worker"), (repository / ".claude" / "worktrees" / "other-worker", "alias-worker")):  # a link out of the worktrees, and one to another worktree
        link = repository / ".claude" / "worktrees" / name
        link.symlink_to(target)
        for script, argv in (("add-worktree.py", [name, "main"]), ("remove-worktree.py", [name]), ("remove-worktree.py", ["other-worker", name])):
            done = call(script, *argv)
            if done.returncode == 0 or "is a link" not in done.stderr or not link.is_symlink() or trees(repository, environment) != before or sorted(path.name for path in outside.iterdir()) != ["keep.txt"]:
                return f"{script} {argv} through the link {name} gave exit {done.returncode}: {done.stdout}{done.stderr}; the folder holds {sorted(path.name for path in outside.iterdir())}, the repository {trees(repository, environment)}"
        link.unlink()
    for argv in (["read", "1", "--repository", repository, "--repository", repository], ["read", "1", "--repository", work / "no-such-folder", "--repository", repository], ["read", "1", "--repository"], ["read", "1", "--repository", "--full"], ["read", "1", "--repository="], ["read", "1", "--repository=--full"]):
        done = replay_probe.sh(sys.executable, SCRIPTS / "use-board.py", *argv, cwd=elsewhere, environment=environment, check=False)
        if done.returncode != 2 or done.stdout or "usage: use-board.py" not in done.stderr or "is in no" in done.stderr or "No such" in done.stderr:
            return f"use-board.py {' '.join(map(str, argv))} gave exit {done.returncode}, stdout {done.stdout!r}, stderr {done.stderr[:200]!r}, not the usage text alone"
    for script, argv in (("add-worktree.py", ["good-worker", "main"]), ("remove-worktree.py", ["good-worker"])):
        done = replay_probe.sh(sys.executable, SCRIPTS / script, *argv, cwd=elsewhere, environment=environment, check=False)
        if done.returncode != 1 or "run it inside the repository" not in done.stderr or "Traceback" in done.stderr or done.stderr.count("\n") != 1:
            return f"{script} {argv} from a folder in no repository gave exit {done.returncode}, stderr {done.stderr!r}"
    return None


def old_form_hits(repository, environment):
    """Each `<file>:<line>` or `#<task> line <line>` that holds a teamwork script run after a `cd` in the same command line."""
    scripts = sorted({path.name for path in PLUGIN.rglob("*.py") if re.fullmatch(r"[a-z]+-[a-z-]+\.py", path.name) and "fixtures" not in path.parts})
    old = re.compile(r"(?:^|[^\w-])(?:cd|pushd)[ \t]+[^;&|\n]+?[ \t]*(?:&&|;)[^\n]*?(?:" + "|".join(map(re.escape, scripts)) + ")")
    hits = []
    files = [path for path in PLUGIN.rglob("*") if path.is_file() and "__pycache__" not in path.parts
             and (path.suffix == ".md" or path.name in ("hooks.json", "monitors.json") or "fixtures" in path.relative_to(PLUGIN).parts)]
    for path in sorted(files):
        hits += [f"{path.relative_to(PLUGIN.parent)}:{number}" for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1) if old.search(line)]
    if repository is None:  # an exported copy, such as the hunk sweep's, has no board to read
        return hits
    listed = replay_probe.sh(sys.executable, "-c", "import json, sys; sys.path.insert(0, sys.argv[1]); import board; print(json.dumps([task['number'] for task in board.tasks('open', comments=False)]))",
                             PLUGIN / "lib", cwd=repository, environment=environment).stdout
    for number in json.loads(listed):
        text = replay_probe.sh(sys.executable, SCRIPTS / "use-board.py", "read", number, "--body", "--repository", repository, cwd=repository, environment=environment).stdout
        hits += [f"#{number} line {at}" for at, line in enumerate(text.splitlines(), 1) if old.search(line)]
    return hits


def case_forms(work, elsewhere, repository, environment):
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    hits = old_form_hits(pathlib.Path(top) if top else None, environment)
    return f"{len(hits)} calls run after a cd: {', '.join(hits)}" if hits else None


def case_every(work, elsewhere, repository, environment):
    """Each script `flow` leaves out, run from ELSEWHERE as `<script> <arguments> --repository REPOSITORY`: its exit and a text only that repository's files or board give."""
    state = work / "herdr-state.json"
    state.write_text(json.dumps({"n": 10, "tabs": [], "agents": [
        {"name": name, "pane_id": f"w1:p{at}", "tab_id": f"w1:t{at}", "workspace_id": "w1", "agent": "claude", "agent_status": "idle", "interactive_ready": True}
        for at, name in ((2, "held-worker"), (3, "probe-manager"))]}))
    environment = {**environment, "PATH": f"{HERE / 'fake-herdr'}:{environment['PATH']}", "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_START_SESSION_TIMEOUT": "4"}
    (repository / "scopeprobe").mkdir()
    (repository / "scopeprobe" / "f.txt").write_text("in the scope folder\n")
    body = replay_probe.write_text(work, "change.md", "A change to land.\n")
    tree = repository / ".claude" / "worktrees" / "other-worker"
    (tree / "below").mkdir()
    url = f"git+file://{repository}/.git/refs/teamwork-blackboard/1"
    prepare = (("hold", "1", "--holders", "held-worker"), ("comment", "1", "--blocked", "Which way?"))
    for verb, *argv in prepare:
        replay_probe.sh(sys.executable, SCRIPTS / "use-board.py", verb, *argv, "--repository", repository, cwd=elsewhere, environment=environment)
    # (script, arguments, whether it names the repository, the exit it gives, the text its output must hold)
    kickoff = "worker {} manager probe-manager https://example.com/1"
    start = [SCRIPTS / "start-session.py"]
    options = ["--model", "haiku", "--effort", "medium"]
    refused = "outside this repository and its worktrees"
    link = work / "repository-link"  # a repository named through a link, whose folder and worktrees start-session must still find under their real paths
    link.symlink_to(repository)
    calls = ((REFERENCES / "adapters/landing-git/scripts/use-landing.py", ["change", "other-worker", "A change", body], True, 0, f"file://{repository}/.teamwork/changes/1.json"),
             (REFERENCES / "estimation/scripts/backtest-estimate.py", [], True, 0, f"{repository}/.git\ttoo few closed tasks"),
             (REFERENCES / "estimation/scripts/estimate-task-time.py", [url], True, 0, "#1\t"),
             (REFERENCES / "estimation/scripts/list-task-durations.py", [], True, 0, "rows: 0"),
             (REFERENCES / "manager/scripts/print-scope-folder.py", ["scopeprobe-manager"], True, 0, "scopeprobe"),
             (REFERENCES / "recall/scripts/recall-work.py", ["probe"], True, 0, "#1 task open: Print ok from the probe"),
             (REFERENCES / "worker-build/scripts/run-on-refs.py", ["cat a.txt", "main", "main"], True, 0, "base\nmain "),
             (REFERENCES / "worker/scripts/list-additions.py", ["1"], True, 0, "#1 body sha:"),
             (PLUGIN / "hooks/print-task-markdown.py", ["1"], True, 0, "# #1 Print ok from the probe"),
             (PLUGIN / "hooks/list-task-board.py", ["probe"], True, 0, "Print ok from the probe"),
             (SCRIPTS / "check-criteria.py", ["1"], True, 0, ""),
             (SCRIPTS / "close-session.py", ["held-worker"], True, 2, "Which way?"),
             (*start, ["trust-worker", tree, kickoff.format("trust-worker"), *options], True, 0, "took its kick-off"),
             (*start, ["trust-root-worker", repository, kickoff.format("trust-root-worker"), *options], True, 0, "took its kick-off"),
             (*start, ["trust-below-worker", tree / "below", kickoff.format("trust-below-worker"), *options], True, 0, "took its kick-off"),
             (*start, ["trust-out-worker", elsewhere, kickoff.format("trust-out-worker"), *options], True, 1, refused),
             (*start, ["trust-bare-worker", tree, kickoff.format("trust-bare-worker"), *options], False, 1, refused),
             (*start, ["trust-link-worker", tree, kickoff.format("trust-link-worker"), *options], link, 0, "took its kick-off"),
             (*start, ["trust-link-root-worker", repository, kickoff.format("trust-link-root-worker"), *options], link, 0, "took its kick-off"))
    wrong = []
    for script, argv, named, status, text in calls:
        done = replay_probe.sh(sys.executable, script, *argv, *(["--repository", repository if named is True else named] if named else []), cwd=elsewhere, environment=environment, check=False)
        if done.returncode != status or text not in done.stdout + done.stderr or "git repository" in done.stderr or "Traceback" in done.stderr:
            wrong.append(f"{script.name} {argv[:1]} gave exit {done.returncode}, stdout {done.stdout[-150:]!r}, stderr {done.stderr[-150:]!r}")
    return "; ".join(wrong) or None


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work, elsewhere, repository, environment = setup()
    for name, case in (("flow", case_flow), ("names", case_names), ("removal", case_removal), ("squash", case_squash), ("forms", case_forms), ("every", case_every)):
        step(name, case, work, elsewhere, repository, environment)
    print("FAIL location arguments" if failed else "PASS location arguments")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
