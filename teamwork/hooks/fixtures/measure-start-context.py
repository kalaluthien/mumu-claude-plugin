#!/usr/bin/env python3
"""Print how many tokens each layer of a session's starting context adds, by one-turn `claude -p` runs that switch the
layers on one at a time, from a clean run to this machine's full setup.

usage: measure-start-context.py [--model <model>] [--cwd <dir>] [--plugin-dir <dir>]... [--dry-run]

Each run asks for one word, so its first turn's context (uncached input, cache writes and cache reads) is the starting
context. Layers, each run adding one to the one before: `clean` (no settings, CLAUDE.md, memory, MCP server or plugin, in an
empty folder); `repository` (in `--cwd` with its project and local settings, so its `AGENTS.md` loads, which it does only
with the project source); `plugins` (each `--plugin-dir`); `user-settings` (the user's settings with the plugins they
install and their hooks, in place of `--plugin-dir`); `claude-md` (the user's CLAUDE.md and rules, which load only with
the user source); `memory` (auto-memory); `full` (MCP servers too, as a session starts here). A run costs about one first turn of the model.
`--dry-run` prints each layer's environment switches and command line instead of running it."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

LAYERS = ["clean", "repository", "plugins", "user-settings", "claude-md", "memory", "full"]


def first_context(command, env, cwd):
    out = subprocess.run(command, env=env, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600).stdout
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "assistant" and event["message"].get("usage"):
            usage = event["message"]["usage"]
            return (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0))
    return None


def main(args):
    model, cwd, plugins, dry = "sonnet", os.getcwd(), [], False
    while args:
        if args[0] == "--dry-run":
            dry, args = True, args[1:]
        elif args[0] in ("--model", "--cwd", "--plugin-dir") and len(args) > 1:
            if args[0] == "--model":
                model = args[1]
            elif args[0] == "--cwd":
                cwd = args[1]
            else:
                plugins.append(args[1])
            args = args[2:]
        else:
            print(__doc__, file=sys.stderr)
            return 2
    empty = tempfile.mkdtemp(prefix="start-context-")
    if not dry:
        print("| layer added | first-turn context tokens | added by the layer |")
        print("| --- | --- | --- |")
    previous = None
    for depth, layer in enumerate(LAYERS):
        on = set(LAYERS[:depth + 1])
        env = dict(os.environ)
        command = ["claude", "-p", "Reply with the single word: ok", "--model", model, "--output-format", "stream-json",
                   "--verbose", "--no-session-persistence"]
        if "full" not in on:
            command += ["--strict-mcp-config"]
        sources = (["user"] if "user-settings" in on else []) + (["project", "local"] if "repository" in on else [])
        command += ["--setting-sources", ",".join(sources)]
        for key, layer_on in (("CLAUDE_CODE_DISABLE_CLAUDE_MDS", "claude-md" in on), ("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "memory" in on)):
            env.pop(key, None) if layer_on else env.update({key: "1"})
        if "plugins" in on and "user-settings" not in on:
            for plugin in plugins:
                command += ["--plugin-dir", plugin]
        if dry:
            switches = [f"{key}=1" for key in ("CLAUDE_CODE_DISABLE_CLAUDE_MDS", "CLAUDE_CODE_DISABLE_AUTO_MEMORY") if key in env]
            print(f"{layer}: {' '.join(switches)} {subprocess.list2cmdline(command)}")
            continue
        tokens = first_context(command, env, cwd if "repository" in on else empty)
        added = "" if previous is None or tokens is None else f"{tokens - previous:+,}"
        print(f"| {layer} | {tokens if tokens is not None else 'no answer'} | {added} |")
        previous = tokens if tokens is not None else previous
    if not dry:
            print("Reading: each layer's tokens are re-read by every turn of a session; the largest added is the first to cut.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
