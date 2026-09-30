# Graders

One grader checks one mode and answers pass or fail; for degrees of severity, write two binary graders, since a 1-to-5 scale has no line labellers hold steady.

A case's input and environment come from a trace that showed the mode, trimmed to what reproduces it. Pick cases by what users send and by confirmed failures, never by where the current model happens to fail: a set chosen by today's misses measures today's model. The regression set also holds a case per core workflow and known edge case, and gains one per confirmed failure. A plugin's case is `evals/<case>/prompt.md`, its front matter the options (`max_turns`, `allowed_tools`, `scaffold_script`) and its body the prompt, with each grader in `graders/<check>.md`, front matter its type and body a judge's pass and fail.

Code first: many modes that sound subjective reduce to a pattern, a parse or an execution. Grade the outcome the user sees, not the path, unless the path is the defect; for an agent that edits files, the files it left.

A repository's instruction files (`CLAUDE.md`, `AGENTS.md`, skills, agents, hooks, and the documents they link) are checked by code, with no setup: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/instruction-graph.py [<repo or plugin dir>]` names each reference to a missing file or section, each instruction file no root reaches and each term two term tables define, and exits 1 on any; `--edges` prints the graph. An optional `.instruction-graph.json` at the repository's root adds `roots` and `ignore` globs and `outside` names.

| runner | code graders | judge |
| --- | --- | --- |
| `claude plugin eval` | `regex`, `tool_used`, `tool_order`, `file_exists` | `llm` |
| promptfoo | `regex`, `javascript`, `python` | `llm-rubric` |

- An unknown key fails the load, shown as `0 case(s)`: "never used" is `tool_used` with `min: 0` and `max: 0`, and its tool must be in `allowed_tools`.
- Under ablation a `with-only` grader (`tool_used: Skill` by default) reports whether the plugin fired instead of scoring: give each case one grader that scores both arms.
- A skill's trigger is its `description`: about 20 prompts, half that should fire it and half near misses sharing its words, each graded by `tool_used: Skill`, 3 runs each. Report the fire rate on the first half and the quiet rate on the near misses apart, never one pass rate that hides a trade between them; raise either by a climb, the `eval-optimize` mode. `plugin eval` fires skills more readily than a live session: confirm a trigger change live, beside the plugins a session really loads, with `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/replay.py <plugin> <case>... --with <plugin dir>... [--agent <agent>]`. How often past sessions whose change fitted a checkerwork playbook called the skill: `skill-use.py`, beside it.

A judge, only for a mode that needs reading, once it has about 20 labelled traces on each side: [judge-playbook.md](judge-playbook.md).
