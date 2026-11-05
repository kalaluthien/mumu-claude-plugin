# Protocol, sessions

The session operations, the sentinel's and judge's authority, and the probe term a judge uses beyond a worker's; [protocol.md](protocol.md) holds the rest.

## Domain

- **probe**: a subagent the judge briefs per outcome with the owner's quoted words and the head tree, the worker's scenario files removed, which tries the outcome; private to the judge until its verdict

## Operations

| port | operation | does |
| --- | --- | --- |
| message | `watch` | waits until a session is idle, and says so |
| session | `start` | opens a session `<name>` at a folder with its kick-off arguments, tier and effort, placed by its role, which those arguments name: a worker or sentinel in a tab of its manager's workspace, a successor `<p>-next` of `succeed <p>` in a tab of `<p>`'s, any other manager in a workspace of its own; `--allow <tool>` keeps on a tool its role has off |
| session | `close` | ends a session, yours included |
| session | `screen` | the text a session's pane shows |
| session | `answer` | picks a choice of a tool prompt a session waits at, by [answer-prompt.py](../scripts/answer-prompt.py), which answers only a listed kind with a choice that allows no more than that one action |
| landing | `remove` | removes a closed worker's worktree and merged branches |

## Authority

| role, session | decides alone | asks first | never |
| --- | --- | --- | --- |
| sentinel, `<duty>-sentinel`, at the checkout's root | how to run its one endless duty; whether to stop once its manager ends | its manager, by `tell`, on any change to its duty | edits, files, judges or merges anything |
| judge, a subagent | `approve` or `fix`, by running each scenario and probe itself | | edits, posts, or picks among options |
