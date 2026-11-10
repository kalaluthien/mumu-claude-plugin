#!/usr/bin/env python3
"""Set up a scratch repository whose rules name how a change lands, then check what a worker's landing left, so a live session proves the landing adapter that `adapters.md` picks follows the repository's rules.

usage: replay-landing-choice.py setup pull-request|local
usage: replay-landing-choice.py check pull-request|local

`setup` prints the folder of a repository with a pushed `main`, a local branch `feature` and a stand-in `gh` in `bin/` that logs each call to `gh.log`.
`check` prints `PASS` when a `pull-request` repository's `gh.log` holds `pr create`, the read-back `pr view` and `pr merge 1 --squash`, the calls the adapter names, and `main` did not take the branch, or a `local` repository's `main` took the branch by a merge in local git and `gh.log` is empty, else `FAIL`."""
import pathlib
import subprocess
import sys

RULES = {
    "pull-request": "# Agents\n\n- **Landing**: land every change by a GitHub pull request into `main`; never push `main`.\n",
    "local": "# Agents\n\n- **Landing**: land every change by a merge in local git; open no GitHub pull request.\n",
}


def folder(kind):
    """A fixed path under /tmp, since a live session's own TMPDIR differs from the one `check` sees."""
    return pathlib.Path("/tmp") / f"landing-choice-{kind}"


def git(*argv, cwd):
    return subprocess.run(["git", "-c", "user.name=probe", "-c", "user.email=probe@example.com", *argv], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def setup(kind):
    work = folder(kind)
    subprocess.run(["rm", "-rf", str(work)], check=True)
    repository, bare = work / "repo", work / "origin.git"
    (work / "bin").mkdir(parents=True)
    repository.mkdir()
    gh = work / "bin" / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {work / "gh.log"}\necho https://github.com/example/repo/pull/1\n')
    gh.chmod(0o755)
    (work / "gh.log").write_text("")
    git("init", "-q", "-b", "main", cwd=repository)
    (repository / "AGENTS.md").write_text(RULES[kind])
    git("add", ".", cwd=repository)
    git("commit", "-q", "-m", "base", cwd=repository)
    git("init", "-q", "--bare", str(bare), cwd=work)
    git("remote", "add", "origin", str(bare), cwd=repository)
    git("push", "-q", "-u", "origin", "main", cwd=repository)
    git("checkout", "-q", "-b", "feature", cwd=repository)
    (repository / "note.txt").write_text("a note\n")
    git("add", ".", cwd=repository)
    git("commit", "-q", "-m", "Add a note", cwd=repository)
    git("push", "-q", "-u", "origin", "feature", cwd=repository)
    git("checkout", "-q", "main", cwd=repository)
    print(repository)


def check(kind):
    work = folder(kind)
    log = (work / "gh.log").read_text()
    merged = "note.txt" in git("ls-tree", "--name-only", "main", cwd=work / "repo").split()
    if kind == "pull-request":
        return all(call in log for call in ("pr create", "pr view", "pr merge 1 --squash")) and not merged
    return not log and merged


def main(args):
    if len(args) != 2 or args[0] not in ("setup", "check") or args[1] not in RULES:
        print(__doc__, file=sys.stderr)
        return 2
    if args[0] == "setup":
        setup(args[1])
    else:
        sys.stdin.read()  # the session writes to this pipe, so its end is the end of the landing
        print("PASS" if check(args[1]) else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
