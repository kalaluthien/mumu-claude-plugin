"""The session port: where a team's sessions run, done by the herdr adapter.

Every adapter has these functions, by the same names:
- reads: `live_names()` the live sessions' names, None when the host gave no list, `sessions(session_id)` the live sessions and this one's own ({} when the caller is none of them), as the pane's record says, which `own()` and `own_interactive()` narrow to a session started or renamed as its name, or a person types into, and `own_name()` reads, `agent(name)` one by name or None,
  `screen(pane, styled=False)` the text a pane shows, with its color codes when `styled`, `tabs(workspace)` a workspace's tabs, each with its `label`
- writes: `open_tab(workspace, cwd, label)` and `open_workspace(cwd, label)` each a new place,
  `rename(place, name)` its tab and pane, `start(name, pane, kind, argv, timeout)` an agent in a pane, `prompt(pane, text)` None once taken, else why not,
  `send_keys(pane, *keys)`, `answer(pane, choice)` a tool prompt's choice by its number, `wait_idle(name, timeout)` until a session is `idle` or `done`, True when it is,
  `close(session)` its pane, found again by the session's name, while another pane shares its tab, else its tab, or its workspace when that tab is the last, returning which, or None, closing nothing, when that pane is already gone
- `LOOK` the command that shows a pane by its `pane_id`, with or without a session in it, `EMPTY` what to say when no session is listed, and `NEEDS` the commands it runs
A session has `name`, `agent` (its kind, as the agent port's `KIND` names it), `pane_id`, `tab_id`, `workspace_id` and `agent_status` (`idle`, `working`, `blocked` or `done`), and `interactive_ready`;
a place has `pane_id` and `tab_id`. A `pane` argument may be a session's name, which the host resolves on each call, since it may move the pane. Functions raise RuntimeError when the host refuses a write they cannot do without."""
import agent as coding_agent  # not `agent`, which the host's `agent(name)` answers
import session_herdr as adapter


def own():
    """(the live sessions, this one's own) as `sessions()` gives them, with the own {} unless this session was started or renamed as its recorded name, since herdr names the pane's session after the pane, so a `claude -p` run there would act as its worker."""
    listed, me = adapter.sessions()
    return listed, me if coding_agent.named(me.get("name"), coding_agent.own_transcript()) else {}


def own_interactive():
    """(the live sessions, this one's own) as `sessions()` gives them, with the own {} unless a person types into this session, for a script that renames it."""
    listed, me = adapter.sessions()
    return listed, me if coding_agent.interactive() else {}


def own_name():
    """This session's name; None when it is none of the live sessions or was not started or renamed as that name, since herdr names the pane's session after the pane, so a `claude -p` run there would write as its worker."""
    name = adapter.sessions()[1].get("name")
    return name if coding_agent.named(name, coding_agent.own_transcript()) else None


def __getattr__(name):
    return getattr(adapter, name)
