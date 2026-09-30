# Test: probe

A plugin change `claude plugin eval` cannot reach (a hook, a dialog, a monitor, the `/` menu, a skill's trigger in a real session) is checked in live sessions, the default branch beside the change.

1. Run both sides and read each: [test/probe-playbook.md](test/probe-playbook.md).
2. A trigger change is also replayed beside the plugins a session really loads: `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/replay.py` ([eval/graders-playbook.md](eval/graders-playbook.md)).
3. Report each side's result, main beside branch, quoting the pane or transcript lines that show it.
