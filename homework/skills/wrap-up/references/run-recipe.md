# Run recipe

A recipe is a project skill at `.claude/skills/run-<name>/` that tells `/run`,
`/verify` and any agent how to build, launch and check the repository, so none
rediscovers it. `/run-skill-generator` writes it: it gets the app running from
a clean environment and commits what worked.

1. Read the signal's recipe:
   - `missing`: this session worked out by trial how to build, run or test,
     and the repository has no recipe;
   - `failed`: a recorded recipe failed.
2. For `failed`, first find whether the recipe or the code broke: a code
   fault is the session's work, not the recipe's; stop here.
3. `/run-skill-generator` is typed by a person, never called through the
   Skill tool: end the report with one line asking the owner to type it in
   this repository, saying whether the recipe is missing or failed and, for
   `failed`, what changed in the build or launch.
