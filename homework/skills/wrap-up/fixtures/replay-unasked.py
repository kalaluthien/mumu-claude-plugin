#!/usr/bin/env python3
"""Build a projects folder of sessions that were never asked, run list-unasked-sessions.py on it, and print one line per step
and `probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: replay-unasked.py"""
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
LIST = str(HERE.parent / "scripts/list-unasked-sessions.py")
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"{'pass' if ok else 'FAIL'}: {name}" + ("" if ok else f" ({detail})"))


def session(path, commands, calls=30, entrypoint="cli"):
    """A transcript of `calls` tool calls and one stop entry whose hooks ran `commands`."""
    entries = [{"entrypoint": entrypoint}]
    entries += [{"message": {"content": [{"type": "tool_use", "id": f"t{n}", "input": {}}]}} for n in range(calls)]
    if commands is not None:
        entries.append({"subtype": "stop_hook_summary", "hookInfos": [{"command": command} for command in commands]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        session(root / "a/absent.jsonl", ["python3 other.py"])
        session(root / "a/ran.jsonl", ['"${CLAUDE_PLUGIN_ROOT}"/hooks/signal-wrap-up.py'])
        session(root / "a/nostop.jsonl", None)
        session(root / "b/short.jsonl", ["python3 other.py"], calls=5)
        session(root / "b/headless.jsonl", ["python3 other.py"], entrypoint="sdk-cli")
        run = subprocess.run([sys.executable, LIST, str(root)], capture_output=True, text=True)
        lines = run.stdout.splitlines()
        step("a session with no homework hook in its stop summary is named hook absent", any(line.startswith("hook absent:") and "absent.jsonl" in line for line in lines), run.stdout)
        step("a session whose hook ran with no ask is named, and a short or headless one is left out",
             any(line.startswith("hook ran, no ask:") for line in lines) and not any("short" in line or "headless" in line for line in lines), run.stdout)
        step("the last line counts the sessions by cause",
             lines[-1:] == ["unasked: 3 sessions, hook absent 1, hook ran, no ask 1, no stop 1"], lines[-1:])
    print(f"probe: {sum(results)} of {len(results)} steps pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
