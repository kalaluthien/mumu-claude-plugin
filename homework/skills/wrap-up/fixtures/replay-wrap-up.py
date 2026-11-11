#!/usr/bin/env python3
"""Run the real Stop hook for two sessions that use two plugin data folders over one memory home, and print one line per step
and `probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: replay-wrap-up.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
HOOK = str(HERE.parents[2] / "hooks/signal-wrap-up.py")
CALLS = 25  # the hook's first retro limit, so each session is asked
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"{'pass' if ok else 'FAIL'}: {name}" + ("" if ok else f" ({detail})"))


def transcript(folder, session, names):
    """A session of CALLS tool calls, each of the first ones writing one memory file, then a stop entry."""
    entries = [{"entrypoint": "cli"}]
    for number in range(CALLS):
        path = f"/home/me/.claude/memory/{names[number]}.md" if number < len(names) else "/tmp/x"
        entries.append({"message": {"content": [{"type": "tool_use", "id": f"t{number}", "input": {"file_path": path}}]}})
    entries.append({"type": "system", "subtype": "stop_hook_summary"})
    path = folder / f"{session}.jsonl"
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    return path


def stop(env, session, path, repository):
    """The hook's reason for a Stop payload, empty when it did not ask."""
    payload = json.dumps({"session_id": session, "transcript_path": str(path), "cwd": str(repository)})
    run = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=env)
    return json.loads(run.stdout)["reason"] if run.stdout.strip() else ""


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        config, home, repository = root / "config", root / "memory", root / "repository"
        config.mkdir()
        home.mkdir()
        repository.mkdir()
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        (config / "settings.json").write_text(json.dumps({"autoMemoryDirectory": str(home)}))
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config)}
        env.pop("HOMEWORK_WRAP_UP", None)
        env.pop("HOMEWORK_WRAP_UP_THRESHOLD", None)
        first = dict(env, CLAUDE_PLUGIN_DATA=str(root / "data-inline"))
        second = dict(env, CLAUDE_PLUGIN_DATA=str(root / "data-installed"))
        folder = root / "sessions"
        folder.mkdir()
        reason = stop(first, "s1", transcript(folder, "s1", ["a", "b"]), repository)
        step("a session of the first data folder counts its 2 memory files", "2 memory files changed" in reason, reason)
        reason = stop(second, "s2", transcript(folder, "s2", ["c", "d", "e"]), repository)
        step("a session of the second data folder reads 5 memory files, not 3", "5 memory files changed" in reason, reason)
        step("the state sits beside the memory home", (root / "memory.wrap-up.json").is_file())
        step("no state sits in a data folder", not list(root.glob("data-*/wrap-up.json")))
        subprocess.run([sys.executable, HOOK, "dreamed", str(home)], check=True, capture_output=True, env=second)
        reason = stop(first, "s3", transcript(folder, "s3", ["f"]), repository)
        step("a dream ended by one data folder starts the count again for the other", "1 memory files changed" in reason, reason)
    print(f"probe: {sum(results)} of {len(results)} steps pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
