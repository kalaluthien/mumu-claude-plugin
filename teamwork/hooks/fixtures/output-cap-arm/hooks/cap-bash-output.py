#!/usr/bin/env python3
"""Rewrite a Bash call so an output over 50 lines shows its first 40 and last 10 lines and a note naming a file that holds
all of it, and an output of 50 lines or fewer passes whole, the exit status kept.

usage: cap-bash-output.py < <PreToolUse event JSON>

A call run in the background is left as it is, since its output already goes to a file."""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
# the whole shell's output goes to a file and an EXIT trap shows it, so a command that calls `exit` is still shown; the
# wrapper holds no brace, since Claude Code refuses a brace near a quote as expansion obfuscation
WRAP = """__cap_out=$(mktemp -t bash-output)
exec 3>&1 4>&2 >"$__cap_out" 2>&1
trap '"{show}" $? "$__cap_out" >&3 2>&4' EXIT
"""


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command")
    if event.get("tool_name") != "Bash" or not command or tool_input.get("run_in_background"):
        return 0
    wrapped = WRAP.replace("{show}", str(HERE / "show-capped-output.sh")) + command + "\n"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {**tool_input, "command": wrapped}}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
