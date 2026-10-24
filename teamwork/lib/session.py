"""The session port: where a team's sessions run, done by the adapter `session_<TEAMWORK_SESSIONS>` (default `herdr`).

Every adapter has these functions, by the same names:
- reads: `sessions(session_id)` the live sessions and this one's own ({} when the caller is none of them), `agent(name)` one by name or None,
  `screen(pane)` the text a pane shows, `tabs(workspace)` a workspace's tabs, each with its `label`
- writes: `open_tab(workspace, cwd, label)` (workspace None: this session's) and `open_workspace(cwd, label)` each a new place,
  `rename(place, name)` its tab and pane, `start(name, pane, kind, argv, timeout)` an agent in a pane, `prompt(pane, text)` None once taken, else why not,
  `send_keys(pane, *keys)`, `wait_idle(name, timeout)` until a session is `idle` or `done`, True when it is,
  `close(session)` its tab, or its workspace when that tab is the last, returning which
- `LOOK` the command that shows a session's pane, and `EMPTY` what to say when no session is listed
A session has `name`, `pane_id`, `tab_id`, `workspace_id` and `agent_status` (`idle`, `working`, `blocked` or `done`), and `interactive_ready`;
a place has `pane_id` and `tab_id`. Functions raise RuntimeError when the host refuses a write they cannot do without."""
import importlib
import os

adapter = importlib.import_module(f"session_{os.environ.get('TEAMWORK_SESSIONS', 'herdr')}")


def __getattr__(name):
    return getattr(adapter, name)
