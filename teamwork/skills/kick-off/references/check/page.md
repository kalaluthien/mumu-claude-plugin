# Page

Build and judge a change to a page or artifact a person looks at.

## Domain

- **Capture**: a screenshot of a page at 390 px and at 1200 px, saved under the scratchpad with the sha-256 of the page's file in its name.
- **Render check**: the page skill's script that loads a page and prints `ok` or each fault.

## Steps

1. Build: change a fixture page first, then what uses it.
2. Build: run the render check on every changed page in one run until it prints `ok`; a run over a few minutes goes to a subagent.
3. Build: start one browser per round and take every capture of every changed page in it; look at each until it shows the change, taken past 3 pages by one read-only subagent per page. For a page behind a login, such as claude.ai, use a signed-in browser: check one is connected (`list_connected_browsers`) before building, `BLOCKED:` at once when none is, since only the owner connects one, save each screenshot by `save_to_disk: true`, and scroll a claude.ai Artifact once first, since its frame stays blank until then.
4. Judge: read the worker's captures of each page whose sha-256 is unchanged, and capture only the pages whose file changed, in one browser start.
5. Judge: try each outcome yourself at the head, delegating no probe.
6. Judge: when the change also holds a script, run the sweep [run-criteria.py](../../scripts/run-criteria.py) `--hunks`, with `--since <sha>` when your brief names `Last judged: <sha>`, then make mutants of the rest, such as a changed call, string or path, all in this round.

## Rules

- **Cheap first**: the render check before any browser start, and a browser start before any subagent that reads captures.
- **Reuse by sha**: a capture whose file sha-256 is unchanged is never taken again.
- **One browser**: one browser start per round serves every page and both widths.
- **Judge tier**: `mid`, `high`; under 10 changed lines, `mid`, `medium`.
