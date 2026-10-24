# Run recipe

A recipe is a project skill at `.claude/skills/run-<name>/` that tells `/run`, `/verify` and any agent how to build, launch and check the repository, so none rediscovers it. `/run-skill-generator` writes it.

1. **Recipe state**: read the signal's recipe:
   - `missing`: this session worked out by trial how to build, run or test,
     and the repository has no recipe;
   - `failed`: a recorded recipe failed.
2. **Recipe or code**: for `failed`, first find whether the recipe or the code broke: a code fault is the session's work, not the recipe's; stop here.
3. **Send it to yourself**: `/run-skill-generator` is never called through the Skill tool, since it runs only as a typed prompt. When `HERDR_PANE_ID` is set, run `herdr agent prompt $HERDR_PANE_ID "/run-skill-generator <missing|failed: what changed>"`, naming for `failed` what changed in the build or launch; it runs once this turn ends. Else end the report with one line asking the owner to type it in this repository, with the same words.
