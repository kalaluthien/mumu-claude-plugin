# Handoff worker prompt

The steering lines a manager hands a worker, one row per case, which [print-steering.py](../scripts/print-steering.py) and `start-session.py --steer` load by `key`; a row marked `alone` takes no other row, since its product differs.

| key | with | the task is | the line |
| --- | --- | --- | --- |
| research | alone | a research ask, whose product is a report | Count by script, start from the raw material and check each idea as new against the repository and its prior work. |
| visible-change | any | a change a person sees, not a research ask | Show the owner a drawn sample of the changed rows before you build. |
| shared-files | any | holding files another open task touches | `BLOCKED:` at once, and start the part whose files that task never touches. |
| new-mechanism | any | using a mechanism new to the repository | Read its official docs before you design. |
| piped-check | any | a `[check]` that pipes a producer into a tool | Run `run-criteria.py` with `--pass <n>=<sample-file>`, since the base run never reaches its pass path. |
| cleanup | any | a cleanup or wrap-up task | Exercise abstract thinking: look for the same goal with fewer moving parts, surface implicit state machines and check them against intent, and surface relied-on but unenforced invariants and enforce those a short check can guard. |
