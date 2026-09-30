# Probe

What `claude plugin eval` cannot reach is shown in live herdr sessions, main beside branch:

1. Sides: main's plugin dir is `git -C <checkout> worktree add --detach <scratch>/main origin/<default>`, the branch's its worktree; edit neither while its probe runs.
2. Start each side with the block below. The pane is `result.root_pane.pane_id`; names are lowercase; `agent_pane_busy` means the shell's rc still runs, so retry every 2 s. `--env` shortens a timer or puts a fake `gh` first on PATH. An untrusted cwd's folder dialog takes `herdr agent send-keys <pane> down`, then `enter`.
3. Drive with `herdr agent prompt <pane> "<text>"`, reading the pane and resending when a prompt right after start vanished. The `/` menu: `herdr pane send-text <pane> "/<plugin>:"` without enter, then `herdr pane read <pane>`: a hidden skill reads "No commands match", against a prefix that still lists one. A lead: cwd a scratch `git init` repo whose origin is `https://github.com/o/r.git`, so no GitHub write lands. A worker: the branch's `worker-start.py <checkout> probe-<x> low <issue-url>`, ended by `session-close.py probe-<x>`.
4. Read `herdr agent read <pane> --lines 30`, a monitor by `ps`, and tool calls in the session's transcript ([runner-playbook.md](../eval/runner-playbook.md) § Transcripts).
5. End: `escape` a busy session, prompt `/exit`, close both tabs and remove main's copy.

```sh
herdr tab create --cwd <trusted dir> --label probe-<side> --no-focus [--env KEY=VALUE]
herdr agent start probe-<side> --kind claude --pane <pane> -- --name probe-<side> --plugin-dir <dir> [--agent <plugin>:<agent>] --model opus --effort low
```
