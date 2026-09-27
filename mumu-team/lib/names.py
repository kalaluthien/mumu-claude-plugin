"""The names of a project's sessions and the folders they work in; it runs no command."""
import pathlib
import re

TOPIC = r"[a-z0-9]+(?:-[a-z0-9]+)*"
WORKER = re.compile(rf"({TOPIC})-(\d+)-(\d+)")
WORKTREES = pathlib.PurePosixPath(".claude", "worktrees")
IGNORE = f"/{WORKTREES}/"  # the checkout's `info/exclude` line


def worker(topic, n, k):
    return f"{topic}-{n}-{k}"


def attempt(name, topic=None, n=None):
    """`k` of the worker `name`, of `topic` and task `n` when given, else None."""
    m = WORKER.fullmatch(name or "")
    return int(m[3]) if m and topic in (None, m[1]) and (n is None or int(n) == int(m[2])) else None


def shares(body):
    """`{share: [after rows]}` of the body's `## Shares` table, or None when the task is not split."""
    m = re.search(r"^## Shares[ \t]*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        return None
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))] for line in m[1].splitlines() if line.strip().startswith("|")]
    return {r[0]: re.findall(TOPIC, r[2]) for r in rows[2:] if len(r) >= 3}


def lead(repo):
    """`<repo>-lead`, `repo` lowercased, each run of other than letters, digits, `-` and `_` one `-`, cut to 22."""
    return re.sub(r"[^a-z0-9_-]+", "-", repo.lower())[:22].strip("-") + "-lead"


def checkout(path):
    """`path` made absolute, raising `RuntimeError` unless it is a git checkout's root."""
    repo = pathlib.Path(path).resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"{path}: not the root of a git checkout")
    return repo


def worktrees(checkout):
    return pathlib.Path(checkout).resolve() / WORKTREES


def workers(listed, checkout):
    """`{name: agent_status}` of the agents in herdr's `listed` that are workers in `checkout`'s worktrees."""
    return {a["name"]: a.get("agent_status") for a in listed if attempt(a.get("name")) is not None
            and pathlib.Path(a.get("cwd") or "/").resolve().is_relative_to(worktrees(checkout))}
