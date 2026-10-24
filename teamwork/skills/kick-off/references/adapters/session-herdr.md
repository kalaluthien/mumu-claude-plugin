# Session: herdr

Each session is a herdr agent in a herdr pane, shown by a herdr tab, and a team's tabs share one herdr workspace; `$HERDR_PANE_ID` is your pane.

| operation | how |
| --- | --- |
| `start` | [start-session.py](../../scripts/start-session.py) `<name> <cwd> "<kick-off arguments>" --model <m> --effort <e> [--team \| --beside <agent>] [--allow <tool>]`, the model of the tier as the agent adapter says |
| `close` | [close-session.py](../../scripts/close-session.py) `<name>`, yours included |
| `rename` | `herdr tab rename <tab> <name>` (tab from `herdr pane get $HERDR_PANE_ID`), then `herdr pane rename`, `herdr agent rename` and `herdr agent prompt … "/rename <name>"` on `$HERDR_PANE_ID`; a manager also `herdr workspace rename <workspace> <project>` |
| `list` | [list-agents.py](../../scripts/list-agents.py), since a hand-written parse of `herdr agent list` raises `KeyError: 'name'` on an unnamed session |
| `screen` | `herdr agent read <pane> --source visible` |
| `answer` | `herdr pane send-text <pane> <choice number>`, since `send-keys Enter` leaves it open |
| `reload` | `herdr agent prompt <name> /reload-plugins` to each name `list` prints |
