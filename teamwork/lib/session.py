"""The session port: where a team's sessions run, done by the herdr adapter.

Every adapter has these functions, by the same names:
- reads: `sessions(session_id)` the live sessions and this one's own ({} when the caller is none of them), which the port's `own_name()` reads, `agent(name)` one by name or None,
  `screen(pane, styled=False)` the text a pane shows, with its color codes when `styled`, `tabs(workspace)` a workspace's tabs, each with its `label`
- writes: `open_tab(workspace, cwd, label)` and `open_workspace(cwd, label)` each a new place,
  `rename(place, name)` its tab and pane, `start(name, pane, kind, argv, timeout)` an agent in a pane, `prompt(pane, text)` None once taken, else why not,
  `send_keys(pane, *keys)`, `answer(pane, choice)` a tool prompt's choice by its number, `wait_idle(name, timeout)` until a session is `idle` or `done`, True when it is,
  `close(session)` its tab, or its workspace when that tab is the last, returning which
- `LOOK` the command that shows a pane by its `pane_id`, with or without a session in it, `EMPTY` what to say when no session is listed, and `NEEDS` the commands it runs
A session has `name`, `agent` (its kind, as the agent port's `KIND` names it), `pane_id`, `tab_id`, `workspace_id` and `agent_status` (`idle`, `working`, `blocked` or `done`), and `interactive_ready`;
a place has `pane_id` and `tab_id`. A `pane` argument may be a session's name, which the host resolves on each call, since it may move the pane. Functions raise RuntimeError when the host refuses a write they cannot do without."""
import agent
import session_herdr as adapter


def own_name():
    """This session's name; None when it is none of the live sessions or was not started or renamed as that name, since herdr names the pane's session after the pane, so a `claude -p` run there would write as its worker."""
    name = adapter.sessions()[1].get("name")
    return name if agent.named(name, agent.own_transcript()) else None


def __getattr__(name):
    return getattr(adapter, name)
