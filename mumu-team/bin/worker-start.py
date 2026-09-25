#!/usr/bin/env python3
"""Start a worker in one call: its worktree, its tab, its Claude session, the folder-trust dialog, its first prompt, and its mission line.

usage: worker-start.py <checkout> <name> <effort> <issue-url> [--continue] [--prompt <text>]

The worktree is `<checkout>/.claude/worktrees/<name>`, added detached at
`origin/<default>` when missing and reused when present; the git guard is
copied into the checkout's hooks, and `/.claude/worktrees/` is added
to the checkout's `info/exclude` so worktrees never show as untracked. The tab
sets `MUMU_ROLE=worker`, on which the lead monitors exit at once (`lib/team.py`). Claude runs as `--agent mumu-team:worker`, whose Stop hook
holds it until its issue lands or is blocked. `--continue` resumes the worktree's
last Claude session. The trust dialog defaults to "No, exit", so it is
answered `down enter`. Once the session is ready, `SUBSCRIBE: <name> <issue-url>`
is appended to this session's mission (`team.mission_file`) unless a line for
`<name>` is there, and `<name>@<pane> <worktree>` printed; with no mission it
fails before anything starts. `<name>` must be `<topic>-<n>`, `<n>` the issue number in `<issue-url>`
and `<topic>` lowercase words joined by `-`, or it fails before anything starts. `agent start` is retried while herdr answers `agent_pane_busy`.
`WORKER_START_TIMEOUT` (60) and `WORKER_START_POLL` (1) are seconds.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

TRUST = "Yes, I trust this folder"
IGNORE = "/.claude/worktrees/"


def run(*argv, cwd=None):
    """stdout of `argv`, raising with its stderr when it fails."""
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def checkout(repo, name):
    """The worktree for `name`, added at the default branch unless it exists, with the guard in the checkout's hooks."""
    tree = pathlib.Path(repo, ".claude", "worktrees", name)
    if not tree.exists():
        run("git", "-C", repo, "fetch", "origin")
        default = run("gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name", cwd=repo).strip()
        run("git", "-C", repo, "worktree", "add", "--detach", str(tree), f"origin/{default}")
    exclude = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").strip())
    text = exclude.read_text() if exclude.exists() else ""
    if IGNORE not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text + ("\n" if text and not text.endswith("\n") else "") + IGNORE + "\n")
    if subprocess.run(["git", "-C", repo, "config", "core.hooksPath"], capture_output=True).returncode != 0:
        hooks = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
        guard = shutil.which("default-branch-guard.sh")
        for hook in ("pre-commit", "pre-push"):
            if guard and not (hooks / hook).exists():
                hooks.mkdir(parents=True, exist_ok=True)
                shutil.copy(guard, hooks / hook)
    return tree


def agent(name):
    """herdr's entry for `name`, or None when not listed."""
    for a in json.loads(run("herdr", "agent", "list"))["result"]["agents"]:
        if a.get("name") == name:
            return a
    return None


def await_ready(name, pane, timeout, poll):
    """Answer the trust dialog once it shows, and return when the session is ready for a prompt."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        a = agent(name)
        if a and a.get("interactive_ready") and a.get("agent_status") != "blocked":
            return
        if TRUST in run("herdr", "agent", "read", pane, "--lines", "40"):
            run("herdr", "agent", "send-keys", pane, "down", "enter")
        time.sleep(poll)
    raise RuntimeError(f"{name} not ready after {timeout:g}s; see `herdr agent read {pane}`")


def start(name, pane, claude_args, timeout, poll):
    """`herdr agent start`, retried while the new tab's shell is still busy (`agent_pane_busy`).

    `agent_not_ready` means a trust dialog, which await_ready answers; any other error raises.
    """
    deadline = time.time() + timeout
    while True:
        done = subprocess.run(["herdr", "agent", "start", name, "--kind", "claude", "--pane", pane, "--"] + claude_args,
                              capture_output=True, text=True)
        out = (done.stdout + done.stderr).strip()
        try:
            code = json.loads(out.splitlines()[-1]).get("error", {}).get("code") if out else None
        except (ValueError, AttributeError):
            code = None
        if code is None and done.returncode == 0 or code == "agent_not_ready":
            return
        if code != "agent_pane_busy" or time.time() >= deadline:
            raise RuntimeError(f"herdr agent start {name}: {out}")
        time.sleep(poll)


def main(argv):
    args, resume, prompt = [], False, None
    it = iter(argv)
    for a in it:
        if a == "--continue":
            resume = True
        elif a == "--prompt":
            prompt = next(it, None)
        else:
            args.append(a)
    if len(args) != 4 or (prompt is None and "--prompt" in argv):
        print("usage: worker-start.py <checkout> <name> <effort> <issue-url> [--continue] [--prompt <text>]", file=sys.stderr)
        return 2
    repo, name, effort, url = args
    number = re.search(r"/issues/(\d+)/?$", url)
    if not number or not re.fullmatch(rf"[a-z0-9]+(-[a-z0-9]+)*-{number[1]}", name):
        print(f"worker-start.py: name {name!r} must be <topic>-{number[1] if number else '<issue>'}", file=sys.stderr)
        return 2
    mission = team.mission_file()
    if mission is None:
        print("worker-start.py: no mission for this session; write its GOAL: line first", file=sys.stderr)
        return 1
    try:
        tree = checkout(repo, name)
        pane = json.loads(run("herdr", "tab", "create", "--cwd", str(tree), "--label", name, "--env", "MUMU_ROLE=worker", "--no-focus"))["result"]["root_pane"]["pane_id"]
        timeout, poll = float(os.environ.get("WORKER_START_TIMEOUT", 60)), float(os.environ.get("WORKER_START_POLL", 1))
        start(name, pane, ["--name", name, "--agent", "mumu-team:worker", "--model", "opus", "--effort", effort] + (["--continue"] if resume else []), timeout, poll)
        await_ready(name, pane, timeout, poll)
        if prompt:
            run("herdr", "agent", "prompt", pane, prompt)
        team.subscribe(mission, name, url)
    except RuntimeError as e:
        print(f"worker-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane} {tree}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
