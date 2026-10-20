# Judge prompt

Each run grades 30 answers, the five in `answers/` and the other 25 hand-backs of #513 criterion 5 (`~/.cache/system-model-worker/c5score/`, its `key.json` naming each folder's version and example). Every answer gets a neutral id `aNN`, its folder holding `answer.md` and its model files, with every path rewritten to that folder and every name that hints at a version or a grade removed. A run is five fresh Claude Sonnet subagents at low effort, each given this prompt over a batch of six answers in a shuffled order that changes per run. The worker maps the ids back to names before saving the run in `runs/`; `verdicts.json` keeps the five named answers.

> Read `<batch>/rubric.json`, a grading spec. Grade each answer `<batch>/aNN/answer.md`, one folder per answer. An answer names its model files by paths relative to `<batch>`; the original model is `original.json` in the answer's folder. Read only the spec, the answers and those model files.
>
> For every criterion in every tier that has `criteria`, give 1 when the answer meets the criterion's text and 0 when it does not. For a criterion with polarity `-`, 1 means the answer commits the error it names. Use the criterion's anchors where it has them. Decide each criterion whose `check` is `program` from the output of a short Python script you run on the model files and the answer's stated values; recount every number from the files and never trust the answer's.
>
> Write `{"answers": {"aNN": {"<criterion id>": 0 or 1, ...}, ...}}` with every criterion for every answer to `<out>`, and reply with the path only.
