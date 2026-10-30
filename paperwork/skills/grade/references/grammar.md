# Grammar

The three files of a grading: the rubric, a run and the grades. `check-rubric.py` checks them by the rules it lists with `rules`.

## Rubric: `rubric.json`

| key | value |
| --- | --- |
| `target` | `name`, `where` (a url or path), `version` |
| `subject` | `kind`, `purpose`, `reader`, `frameworks` (strings) |
| `promises` | each `text` and `where` |
| `flaws` | the flaw candidates, as strings |
| `criteria` | each `id`, `text`, `check` (`judge` or `program`), `from` (the framework or flaw it came from); optional `critical`, `absence`, `anchors` (what a vague word means here), and for `program` `fix` and `command`, run in the source folder, exit 0 meaning met |

## Run: `run-<run>-call-<call>.json`, by a judge

| key | value |
| --- | --- |
| `judge` | the model |
| `grades` | per criterion id: `met` (1, 0 or null), then `quote` and `where` (`path:line` or `path:first-last`), `searched` when a failure has nothing to quote, `fix` on a failure, `reason` on null, and on an absence criterion `items`, each `item`, `found`, and `quote` and `where` when found |
| `grader_text` | each passage that speaks to a grader, as `quote` and `where` |

## Grades

`grades.json`, written by `merge-runs.py`: `rubric_sha`, `judge` (`model`, `runs`), `grader_text`, and `grades` per criterion id, as a run's, with `runs`, the verdict of each run. `met` is their majority, null when there is none.

`merge-runs.py` turns a verdict to not judged when its quote is not at its place or an absence verdict does not follow from its items, and scans the source for `grader_text` itself.
