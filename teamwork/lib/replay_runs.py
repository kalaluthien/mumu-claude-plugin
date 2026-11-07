"""What a clean replay in `claude -p` needs: an environment with stand-ins for GitHub, herdr and Claude, the run itself, and
its stream read back into tool uses."""
import json
import os
import subprocess

BLOCKED_TOOLS = ("gh", "herdr", "claude")
RUN_TIMEOUT = 3600
SWITCHES = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def blocked_path(folder):
    """A folder of stand-ins for GitHub, herdr and Claude, first on PATH, so a replay writes to no live board or session."""
    folder.mkdir(parents=True, exist_ok=True)
    for tool in BLOCKED_TOOLS:
        stand_in = folder / tool
        stand_in.write_text(f"#!/bin/sh\necho '{tool} is off in this replay' >&2\nexit 1\n")
        stand_in.chmod(0o755)
    return folder


def clean_environment(scratch):
    """The environment of a clean run: the stand-ins first on PATH, no GitHub login, no herdr session, no CLAUDE.md or memory."""
    empty_gh = scratch / "gh-config"
    empty_gh.mkdir()
    environment = {**os.environ, **SWITCHES, "PATH": f"{blocked_path(scratch / 'blocked')}:{os.environ['PATH']}",
                   "GH_TOKEN": "off-in-replay", "GH_CONFIG_DIR": str(empty_gh)}
    for key in [key for key in environment if key.startswith("HERDR")]:
        environment.pop(key)
    return environment


def run_claude(command, cwd, environment):
    """The stream and the errors of a `claude -p` COMMAND, cut off at RUN_TIMEOUT."""
    try:
        done = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        return done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        return expired.stdout.decode() if isinstance(expired.stdout, bytes) else expired.stdout or "", f"timed out after {RUN_TIMEOUT} s"


def read_tool_uses(stream):
    """The tool uses of a run's stream by id, each with its name and input."""
    uses = {}
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "assistant" or event.get("parent_tool_use_id") is not None:
            continue
        for part in event["message"].get("content", []):
            if isinstance(part, dict) and part.get("type") == "tool_use":
                uses[part["id"]] = {"name": part["name"], "input": part.get("input") or {}}
    return uses
