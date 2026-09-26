"""The names of a project's sessions and the folders they work in; it runs no command.

A worker is `<topic>-<n>-<k>` for task `<n>`, attempt `<k>`, in the worktree
`<checkout>/.claude/worktrees/<name>`; a lead is `<repo>-lead`.
"""
import pathlib
import re

TOPIC = r"[a-z0-9]+(?:-[a-z0-9]+)*"
WORKER = re.compile(rf"{TOPIC}-(\d+)-(\d+)")
WORKTREES = pathlib.PurePosixPath(".claude", "worktrees")
IGNORE = f"/{WORKTREES}/"  # the line in the checkout's `info/exclude`


def worker(topic, n, k):
    return f"{topic}-{n}-{k}"


def attempt(name, topic=None, n=None):
    """`k` of a worker `name`, restricted to `topic` and task `n` when given, or None."""
    m = WORKER.fullmatch(name or "")
    if not m or n is not None and m[1] != str(n) or topic is not None and name != worker(topic, m[1], m[2]):
        return None
    return int(m[2])


def lead(repo):
    """The lead of the repository named `repo`: lowercased, each run of other than letters, digits, `-` and `_` one `-`, cut to 22 characters."""
    return re.sub(r"[^a-z0-9_-]+", "-", repo.lower())[:22].strip("-") + "-lead"


def checkout(path):
    """`path` made absolute, raising `RuntimeError` unless it is a git checkout's root (it holds `.git`)."""
    repo = pathlib.Path(path).resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"{path}: not the root of a git checkout")
    return repo


def worktrees(checkout):
    """The folder of `checkout`'s workers' worktrees."""
    return pathlib.Path(checkout).resolve() / WORKTREES


def workers(listed, checkout):
    """`{name: agent_status}` of the agents in herdr's `listed` that are workers of the lead of `checkout`."""
    root = worktrees(checkout)
    return {a["name"]: a.get("agent_status") for a in listed
            if attempt(a.get("name")) is not None and pathlib.Path(a.get("cwd") or "/").resolve().is_relative_to(root)}
