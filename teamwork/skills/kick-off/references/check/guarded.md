# Guarded

Build and judge a change to a hook, monitor, live pane, guard, the landing or the board's writes, where a fault reaches every session.

## Domain

- **Sweep**: [run-criteria.py](../../scripts/run-criteria.py) `--hunks`, which reverts each hunk and tries each condition, comparison, number, codec name, list or tuple element and `and` or `or` operand a Python hunk adds against the criteria.
- **Probe**: one subagent the judge briefs with every outcome's text and the head tree without the worker's scenario files, asked to combine behaviours as the user would and to reply `PASS` or `FAIL` with its steps per outcome.

## Steps

1. Build: write the failing test or probe first, through the code's own interface, so it fails when the behaviour breaks; where the repository keeps none, keep it in the scratchpad, run it by [run-on-refs.py](../../scripts/run-on-refs.py) `'<command>' origin/<base> <head sha>` until it fails on the base and passes at the head, and quote it in the criterion.
2. Build: run the fixture runners of the parts you changed, leaving the repository's whole check to the one run worker.md's **Land** names.
3. Build, a hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture; a monitor reads everything on its first loop, so to probe that it notices a change, start the real monitor, wait for its first line, make the change, and check the probe fails with the call under test removed; for a change in looks, the owner checks how it looks on the live pane or page.
4. Build, a live pane (`teamwork/hooks/draw-task-pane.tsx`): compile it first by `bun build <file> --external claude-code --external 'react*' --outdir <scratchpad>`, which checks syntax and imports, not types; list the owner's layout words (colors, spacing, symbols, format; their screenshots too) from the task and the tasks it follows, and quote beside each the live row that meets it. The owner's word beats your taste, and an unclear word is a `BLOCKED:`.
5. Build, a live pane in a narrow width: no text is cut, hidden or shrunk; a link and a fold mark keep full width (`flexShrink={0}`), long text wraps, and each fold row presses over its whole text but the link.
6. Judge: run the sweep, with `--since <sha>` when your brief names `Last judged: <sha>`, then make mutants of the rest, such as a changed call, string or path, and an input of each form a caller meets, all in this round.
7. Judge: delegate one probe at `mid`, `medium` for every outcome at once, and rerun one of its steps yourself before you count its verdicts.

## Rules

- **Cheap first**: fixtures, `run-criteria.py` and the sweep before the probe, since a probe is a model call.
- **One probe**: one probe subagent serves every outcome of a round; start another only for an outcome whose part changed since.
- **Judge tier**: `mid`, `high`.
