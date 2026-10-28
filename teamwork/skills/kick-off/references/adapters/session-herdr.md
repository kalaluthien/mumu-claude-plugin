# Session: herdr

Each session is a herdr agent in a herdr pane, shown by a herdr tab, and a team's tabs share one herdr workspace. herdr may move a pane, as from `w9:p1` to `w4:pF`, and a shell's `$HERDR_PANE_ID` keeps the pane it started in, so name a session, never a pane id kept from an earlier read: herdr resolves the name on each call, and the scripts find your own session by its session id.

| operation | how |
| --- | --- |
| `start` | [start-session.py](../../scripts/start-session.py) `<name> <cwd> "<kick-off arguments>" --model <m> --effort <e> [--allow <tool>]`, the model of the tier as the agent adapter says; it places the session by its role, a worker or sentinel in its manager's workspace, and takes no flag for the place |
| `close` | [close-session.py](../../scripts/close-session.py) `<name>`, yours included |
| `rename` | [rename-session.py](../../scripts/rename-session.py) `<name>`, which renames tab, pane and agent, sends `/rename <name>`, and sends it again until the transcript records exactly `<name>`, since one typed prompt landed as `teamwork-manager teamwork-`; a manager also `herdr workspace rename <workspace> <project>` |
| `list` | [list-sessions.py](../../scripts/list-sessions.py), since a hand-written parse of `herdr agent list` raises `KeyError: 'name'` on an unnamed session |
| `screen` | `herdr agent read <pane> --source visible` |
| `answer` | [answer-prompt.py](../../scripts/answer-prompt.py) `<name> <choice number>`, which sends `herdr pane send-text <pane> <choice number>`, since `send-keys Enter` leaves it open; then read its `screen`, and clear a digit left in the input box by `herdr pane send-keys <pane> BSpace`, before the session sends it as a prompt |
| `reload` | `herdr agent prompt <name> /reload-plugins` to each name `list` prints |
