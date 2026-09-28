#!/usr/bin/env python3
"""PreToolUse hook on Edit, Write and NotebookEdit: a worker, a session whose cwd lies under `.claude/worktrees/<name>`,
writes files only inside that worktree, never elsewhere in the checkout that holds it; any other session passes."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import sessions  # noqa: E402


def refuse(reason):
    print(f"worktree-guard: {reason}", file=sys.stderr)
    sys.exit(2)


def worktree(cwd):
    """`(checkout, worktree)` when `cwd` lies under `<checkout>/.claude/worktrees/<name>`, else None."""
    parts, marker = cwd.parts, sessions.WORKTREES.parts
    found = [i for i in range(len(parts) - len(marker)) if parts[i:i + len(marker)] == marker]
    if not found:
        return None
    i = found[-1]
    return pathlib.Path(*parts[:i]), pathlib.Path(*parts[:i + len(marker) + 1])


def main():
    try:
        payload = json.loads(sys.stdin.read())
        cwd = pathlib.Path(payload["cwd"]).resolve()
        tool_input = payload.get("tool_input") or {}
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        refuse(f"could not read the payload ({type(err).__name__}: {err})")
    found = worktree(cwd)
    if not found or not isinstance(path, str) or not path:
        sys.exit(0)
    checkout, tree = found
    target = (cwd / pathlib.Path(path).expanduser()).resolve()
    if target.is_relative_to(checkout) and not target.is_relative_to(tree):
        refuse(f"{target} is outside your worktree {tree}: a worker edits files only there, never in the leader's checkout {checkout}")


if __name__ == "__main__":
    main()
