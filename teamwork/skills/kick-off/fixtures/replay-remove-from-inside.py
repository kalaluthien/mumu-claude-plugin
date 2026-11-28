#!/usr/bin/env python3
"""Check that remove-worktree.py never deletes the folder its caller stands in, in a scratch repository with no remote, and print `ok <case>` or `fail <case>: <what it saw>`
per case, then `PASS remove from inside` or `FAIL remove from inside`; exit 1 on any failure:
- `inside`: called from inside the worktree it removes, it removes nothing, exits 2 and prints a call that starts with `cd ~`, names the main checkout by `--repository`
  and the script by its path;
- `printed-call`: that printed call, run from the worktree, removes the worktree;
- `subfolder`: called from a folder under the worktree, it removes nothing and exits 2;
- `linked`: called from inside the worktree with `--repository` a symbolic link to the main checkout, it removes nothing and exits 2;
- `outside`: called from the main checkout, it removes the worktree.

usage: replay-remove-from-inside.py"""
import pathlib
import shlex
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = SKILL / "scripts"


def worktree(box, name="probe-worker"):
    return pathlib.Path(box.python(SCRIPTS / "add-worktree.py", name, "main").stdout.strip())


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("remove from inside")
    with replay_probe.scratch("remove-from-inside-") as work:
        box = replay_probe.Sandbox(work)
        tree = worktree(box)
        inside = box.python(SCRIPTS / "remove-worktree.py", "probe-worker", cwd=tree)
        main_checkout = box.repository.resolve()
        cases.step("inside", inside.returncode == 2 and tree.is_dir() and 'cd ~ && python3 ' in inside.stderr
                   and f"--repository {main_checkout}" in inside.stderr and "remove-worktree.py --repository" in inside.stderr, [inside.returncode, inside.stderr])
        call = inside.stderr.split("Run: ", 1)[-1].strip()
        # the stand-in shell is at $HOME of the sandbox, which is where the printed call moves to
        ran = replay_probe.sh("sh", "-c", call, cwd=tree, environment={**box.environment}, check=False)
        cases.step("printed-call", ran.returncode == 0 and not tree.exists(), [ran.returncode, ran.stdout, ran.stderr, shlex.quote(call)])
        tree = worktree(box, "probe-sub-worker")
        (tree / "sub").mkdir()
        sub = box.python(SCRIPTS / "remove-worktree.py", "probe-sub-worker", cwd=tree / "sub", check=False)
        cases.step("subfolder", sub.returncode == 2 and tree.is_dir(), [sub.returncode, sub.stderr])
        link = work / "linked-checkout"
        link.symlink_to(box.repository)
        linked = box.python(SCRIPTS / "remove-worktree.py", "probe-sub-worker", "--repository", link, cwd=tree, check=False)
        cases.step("linked", linked.returncode == 2 and tree.is_dir(), [linked.returncode, linked.stderr])
        box.python(SCRIPTS / "remove-worktree.py", "probe-sub-worker", cwd=box.repository)
        tree = worktree(box, "probe-other-worker")
        outside = box.python(SCRIPTS / "remove-worktree.py", "probe-other-worker", cwd=box.repository)
        cases.step("outside", outside.returncode == 0 and not tree.exists(), [outside.returncode, outside.stdout, outside.stderr])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
