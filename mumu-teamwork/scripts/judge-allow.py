#!/usr/bin/env python3
"""PreToolUse hook on Agent: allow launching the `mumu-teamwork:judge` subagent, so the owner's settings need no
`Agent(mumu-teamwork:judge)` rule; any other launch gets no decision."""
import json
import sys

JUDGE = "mumu-teamwork:judge"


def main():
    try:
        agent = json.loads(sys.stdin.read())["tool_input"].get("subagent_type")
    except (ValueError, KeyError, TypeError, AttributeError):
        return
    if agent == JUDGE:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                                 "permissionDecisionReason": f"mumu-teamwork: launching {JUDGE}"}}))


if __name__ == "__main__":
    main()
