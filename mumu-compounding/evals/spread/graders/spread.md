---
type: llm
focus: last_message
criteria: The sandbox blocks writes, so the reply may report the edits as done or print them as commands; judge only what they would do. Pass if all three hold. (1) A user-wide CLAUDE.md file (a path ending in CLAUDE.md that is ~/.claude/CLAUDE.md or sits directly in a config directory, not inside a project) gets a line stating to name the recommended option when laying out options, with the reason about wanting a decision rather than a survey. (2) No line added to that file consists only of a link or url. (3) The file feedback-recommend-one.md in this project's memory folder (a path containing projects/<key>/memory/) is deleted, for example by an rm command. Extra suggestions, such as checks of other projects, do not matter.
---
