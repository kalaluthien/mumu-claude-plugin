# Buckets

Sort each failure, a fresh subagent reading its transcript, before any edit meant to fix it:

| bucket | sign | instead |
| --- | --- | --- |
| artifact gap | the model lacked a fact or rule and guessed | change the artifact |
| grader | the output looks right and failed, or prompt and grader ask different things | fix the grader and regrade every run it scored |
| harness | the run died before a scorable output: its `error` field names a crash, a turn limit or an expired login | fix it, excluding those runs meanwhile |
| structure | the fact is in the artifact and was never reached | reorganise: split, route or merge, rather than add text |
| variance | identical runs flip as much as a change moves | more runs, last: read the failing runs' evidence first, then rerun the case alone with the fewest runs that answer the question, on the committed copy and on the default branch's, reusing a count already taken on the same default-branch commit, before calling it flake |
