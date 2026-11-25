#!/usr/bin/env python3
"""Land two workers' changes in a scratch repository with no remote, through use-landing.py, a git board and the fake herdr, and print `ok <step>` or
`fail <step>: <what differed>` for each step, then `PASS` or `FAIL`; exit 1 on any fail.

usage: replay-landing-scenario.py [--verbose]
`--verbose` also prints each command's output.
- change: two branches filed as changes 1 and 2, listed open at their tips; change-race, at the end: six filed at once get six numbers
- refuse-moved-head: change 1 merged at a sha other than its tip, or at its branch name, exits 1 and leaves the base as it was
- refuse-dirty-checkout: change 1 merged over an uncommitted file in the base's checkout exits 1 and leaves the file and the base as they were
- refuse-bare-checkout: change 1 merged while `core.bare` is true exits 1, names `core.bare`, and leaves the base and the change as they were
- bare-repository: a truly bare clone is not flagged, so the guard leaves its `update-ref` merges alone
- merge: change 1 merged at its tip after the base moved: one commit whose one parent is the old base, the merged tree, a message citing its task,
  and the base's checkout showing it
- signal: the merge touched the signal file, and the landing's change check is true since before it
- heartbeat-merged, heartbeat-rebase: the manager's heartbeat, `print-team-gaps.py --polls`, running across the merge, names change 1 merged by its worker; the worker of
  change 2, which conflicts, is told to rebase
- remove: remove-worktree.py removes the merged worker's worktree and branch, and says nothing of a pull it cannot make"""
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

PLUGIN = pathlib.Path(__file__).resolve().parents[3]
LANDING = PLUGIN / "skills" / "kick-off" / "references" / "adapters" / "landing-git" / "scripts" / "use-landing.py"
MONITOR = PLUGIN / "monitors" / "print-team-gaps.py"
TEAM = (replay_probe.agent("teamwork-manager", 1, "working"), replay_probe.agent("landing-probe-worker", 2), replay_probe.agent("clash-probe-worker", 3, "working"))
POLLS, POLL = 40, 0.25  # the heartbeat spans its first read, the second the records carry and the merge
VERBOSE = False


def run(sandbox, argv, cwd=None):
    done = sandbox.run(argv, cwd=cwd, timeout=60)
    out = done.stdout + done.stderr
    if VERBOSE:
        print(f"$ {' '.join(map(str, argv))}\n{out}", file=sys.stderr)
    return done.returncode, out


def library(sandbox, expression, cwd=None):
    """The JSON value of the lib EXPRESSION, such as `landing_git.record(1)`, read in CWD under the sandbox's environment."""
    module = expression.split(".", 1)[0]
    return sandbox.evaluate(f"import json, iso_time, {module}; print(json.dumps({expression}))", cwd=cwd)


def commit(sandbox, cwd, name, text):
    replay_probe.write_text(cwd, name, text)
    sandbox.git("add", name, cwd=cwd)
    sandbox.git("commit", "-qm", f"write {name}", cwd=cwd)


def worker_tree(sandbox, name, text):
    tree = sandbox.repository / ".claude" / "worktrees" / name
    sandbox.git("worktree", "add", "-q", "-b", name, tree, "main")
    commit(sandbox, tree, "a.txt", text)
    return sandbox.git("rev-parse", name).strip()


def printed(log, text, seconds=20):
    """Whether the running heartbeat's LOG shows TEXT within SECONDS."""
    end = time.time() + seconds
    while time.time() < end and text not in log.read_text():
        time.sleep(0.2)
    return text in log.read_text()


def scenario(sandbox, cases):
    git = sandbox.git
    repository, work = sandbox.repository, sandbox.work
    commit(sandbox, repository, "a.txt", "one\n")
    probe, clash = worker_tree(sandbox, "landing-probe-worker", "two\n"), worker_tree(sandbox, "clash-probe-worker", "three\n")
    commit(sandbox, repository, "b.txt", "moved on\n")  # the base moves after both branches start, so a merge must merge, not just copy the head
    body = replay_probe.write_text(work, "body.md", "Closes #1\n")
    filed = [run(sandbox, [LANDING, "change", name, f"Probe {name}", body])[1].strip() for name in ("landing-probe-worker", "clash-probe-worker")]
    heads = {pull["number"]: pull["headRefOid"] for pull in library(sandbox, "landing_git.pulls('open')") or []}
    cases.step("change", [url.rsplit("/", 1)[-1] for url in filed] == ["1.json", "2.json"] and heads == {1: probe, 2: clash}, f"{filed} {heads}")

    def state():
        return library(sandbox, "landing_git.record(1)")["state"]

    base = git("rev-parse", "main").strip()
    code, out = run(sandbox, [LANDING, "merge", "1", base])
    named, _ = run(sandbox, [LANDING, "merge", "1", "landing-probe-worker"])  # a branch name follows the tip, so it never stands for an approved head
    cases.step("refuse-moved-head", code == named == 1 and git("rev-parse", "main").strip() == base and state() == "OPEN", f"exit {code}: {out}")

    (repository / "a.txt").write_text("dirty\n")
    code, out = run(sandbox, [LANDING, "merge", "1", probe])
    cases.step("refuse-dirty-checkout", code == 1 and (repository / "a.txt").read_text() == "dirty\n" and git("rev-parse", "main").strip() == base and state() == "OPEN",
               f"exit {code}: {out}")
    git("checkout", "--", "a.txt")

    git("config", "core.bare", "true")
    code, out = run(sandbox, [LANDING, "merge", "1", probe])
    git("config", "core.bare", "false")
    cases.step("refuse-bare-checkout", code == 1 and "core.bare" in out and git("rev-parse", "main").strip() == base and state() == "OPEN", f"exit {code}: {out}")
    git("clone", "-q", "--bare", repository, work / "bare.git")
    cases.step("bare-repository", library(sandbox, "landing_git.bare_flagged()", work / "bare.git") is False
               and git("config", "--bool", "core.bare", cwd=work / "bare.git").strip() == "true")

    # the manager's heartbeat runs before the merge, so only its change check, not its first read, can bring the merged line
    log = work / "heartbeat.log"
    live = sandbox.start([sys.executable, MONITOR, "--polls", POLLS], log, pane="w1:p1", TEAMWORK_MONITOR_POLL=POLL)
    first = printed(log, "idle landing-probe-worker")
    time.sleep(1.1)  # the records filed above carry this second, which must not count as the merge
    before, signal = library(sandbox, "iso_time.stamp()"), library(sandbox, "team_signal.stamp()")
    code, out = run(sandbox, [LANDING, "merge", "1", probe])
    merged = out.strip()
    want = run(sandbox, ["git", "merge-tree", "--write-tree", base, probe])[1].split()[:1]
    cases.step("merge", code == 0 and git("rev-parse", "main").strip() == merged and git("rev-list", "--parents", "-1", merged).split()[1:] == [base]
               and [git("rev-parse", f"{merged}^{{tree}}").strip()] == want and "Closes #1" in git("log", "-1", "--format=%B", merged)
               and (repository / "a.txt").read_text() == "two\n" and (repository / "b.txt").exists() and library(sandbox, "landing_git.record(1)")["headRefOid"] == probe,
               f"exit {code}: {out}")
    now = library(sandbox, "team_signal.stamp()")
    cases.step("signal", now != signal and library(sandbox, f"landing_git.changed_since({before!r})"), f"stamp {signal} -> {now}")

    try:
        ended = live.wait(POLLS * POLL + 60)
    except subprocess.TimeoutExpired:
        live.kill()
        ended = None
    cases.step("heartbeat-merged", first and ended == 0 and "merged #1 by landing-probe-worker:" in log.read_text(), f"exit {ended}: {log.read_text()}")
    done = sandbox.python(MONITOR, "--polls", "1", pane="w1:p3", timeout=60, TEAMWORK_MONITOR_POLL=0)
    cases.step("heartbeat-rebase", "rebase #2: it conflicts with its base" in done.stdout, f"exit {done.returncode}: {done.stdout}{done.stderr}")

    code, out = run(sandbox, [PLUGIN / "skills" / "kick-off" / "scripts" / "remove-worktree.py", "landing-probe-worker"])
    cases.step("remove", "landing-probe-worker: worktree, branch landing-probe-worker removed" in out and "fast-forward" not in out
               and not git("branch", "--list", "landing-probe-worker").strip(), out)
    racers = [replay_probe.Group([str(LANDING), "change", "clash-probe-worker", "Race", str(body)], cwd=repository, env=sandbox.environment, stdout=subprocess.PIPE, text=True)
              for _ in range(6)]
    urls = sorted(racer.communicate(timeout=60)[0].strip() for racer in racers)
    cases.step("change-race", len(set(urls)) == 6 and len(library(sandbox, "landing_git.records()")) == 8, f"{urls}")


def main(args):
    global VERBOSE
    if any(argument != "--verbose" for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    VERBOSE = "--verbose" in args
    cases = replay_probe.Cases()
    with replay_probe.scratch("landing-scenario-") as work:
        try:
            scenario(replay_probe.Sandbox(work, TEAM, commit=False), cases)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            cases.step("scenario", False, str(e)[-400:])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
