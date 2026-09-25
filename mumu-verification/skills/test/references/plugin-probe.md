# Plugin probe

Show a Claude plugin change that `claude plugin eval` cannot reach - a hook, a dialog, a monitor, the `/` menu - in live herdr sessions, main beside branch.

## 1. Sides

`git -C <checkout> worktree add --detach <scratch>/main origin/<default>` gives main's plugin dir; the branch's is its worktree's. Edit neither while its probe runs.

## 2. Start

Per side:

```sh
herdr tab create --cwd <trusted dir> --label probe-<side> --no-focus [--env KEY=VALUE]
herdr agent start probe-<side> --kind claude --pane <pane> -- --name probe-<side> --plugin-dir <dir> [--agent <plugin>:<agent>] --model opus --effort low
```

- `tab create` prints the pane at `result.root_pane.pane_id`; `agent start` prints the session id at `agent_session.value`. Pass one `--plugin-dir` per changed plugin.
- `--env` shortens a timer or puts a fake `gh` first on `PATH`.
- Names are lowercase only (`invalid_agent_name`).
- `agent_pane_busy` right after `tab create` means the shell's rc still runs: retry every 2 s, showing the output.
- An untrusted cwd shows the folder dialog: `herdr agent send-keys <pane> down`, then `enter`.

## 3. Drive

`herdr agent prompt <pane> "<text>"`. A prompt sent seconds after `agent start` can vanish: `herdr agent read <pane>` and resend.

| probe | how |
| --- | --- |
| `/` menu | `herdr pane send-text <pane> "/<plugin>:"`, no enter, then `herdr pane read <pane>`: a hidden skill reads "No commands match". Control: a prefix that still lists a skill (`/mumu-team:` lists `kickoff`); clear with `herdr agent send-keys <pane> ctrl+u`. Then prompt the model to load each changed skill with the Skill tool |
| a hook that reads a mission | write it yourself to `~/.claude/plugins/data/<plugin>-inline/mission/<session id>.md`, since auto mode refuses a probe that writes its own or arms monitors; delete it before `/exit` |
| a lead | cwd a scratch `git init` repo whose `origin` is `https://github.com/o/r.git`, so no `gh` write lands |
| a worker | the branch's `worker-start.py <checkout> probe-<x> low <issue-url> --prompt "<text>"`, ended by `worker-close.py probe-<x>` and `git worktree remove` |

A scratch plugin whose parts each answer with a marker token, one numbered line per part, is read faster than a transcript.

## 4. Read

`herdr agent read <pane> --lines 30`; a monitor, by `ps` for the side's plugin-dir scripts; tool calls, from `~/.claude/projects/*/<session id>.jsonl` ([transcripts](../../eval/references/transcripts.md)). `agent_not_found` means the session exited: `herdr pane read <pane>`.

## 5. End

A busy session gets `herdr agent send-keys <pane> escape` first. `herdr agent prompt <pane> "/exit"`, answer a left dialog with `herdr agent send-keys <pane> enter`, `herdr tab close` both tabs, and `git worktree remove` main's copy. Report each side's result, main beside branch.
