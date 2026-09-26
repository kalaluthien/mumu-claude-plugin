"""Run one external command, and every `gh` command mumu-team runs, each raising `RuntimeError` when it fails, but `held`, which answers None."""
import json
import subprocess

HELD = ["issue", "list", "--state", "open", "--search", "no:parent-issue label:kind:goal,kind:task", "--json", "url"]


def run(*argv, cwd=None, stdin=None):
    """stdout of `argv`, raising with its stderr and stdout when it cannot start or exits non-zero."""
    try:
        done = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True)
    except OSError as e:
        raise RuntimeError(f"{argv[0]}: {e}") from e
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {' '.join(s.strip() for s in (done.stderr, done.stdout) if s.strip())}")
    return done.stdout


def gh(*argv, cwd=None, stdin=None):
    """stdout of `gh <argv>`."""
    return run("gh", *argv, cwd=cwd, stdin=stdin)


def repo(field, cwd=None):
    """One field of `gh repo view` in `cwd`: `name`, or `defaultBranchRef` read as its name."""
    return gh("repo", "view", "--json", field, "-q", f".{field}" + (".name" if field == "defaultBranchRef" else ""), cwd=cwd).strip()


def held(cwd):
    """The urls of the open root goals and root tasks of `cwd`'s repository, or None when `gh` cannot read them."""
    try:
        return [i["url"] for i in json.loads(gh(*HELD, cwd=cwd))]
    except (RuntimeError, ValueError, KeyError, TypeError):
        return None
