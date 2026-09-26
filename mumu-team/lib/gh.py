"""Every `gh` command mumu-team runs, each raising `RuntimeError` when gh fails, but `held`, which answers None."""
import json

from command import run

HELD = ["issue", "list", "--state", "open", "--search", "no:parent-issue label:kind:goal,kind:task", "--json", "url"]


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
