---
name: issues
description: Use when the owner wants the Issues pane shown again after closing it, or its board refreshed.
disable-model-invocation: true
---

# issues

The `draw-issue-pane` hook answers this command by showing the Issues pane (opened if closed) and refreshing its board, so this body reaches a session only when that hook is off: then say the pane needs Claude Code's function hooks.
