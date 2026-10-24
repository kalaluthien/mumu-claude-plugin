# Agents

The working rules of this repository and of every plugin in it. Each rule carries a bold name, so a review or another file can cite it. A plugin's own rules live in its skills, never here.

## Repository

- **Live checkout**: sessions load the plugins straight from this checkout, so a merge reaches them once the checkout pulls. Refresh by what changed: a script or a `references/` file works at once; a `SKILL.md` or a `hooks.json` at `/reload-plugins`, which the session that merges it prompts to each running session once it has pulled the checkout with `git pull --ff-only`, before any other step when a hook's script moved or was renamed, since that hook stays off until then; a monitor's code when the monitor starts again.
- **No CLAUDE.md**: rules sit only in `AGENTS.md`, since Claude Code reads `AGENTS.md` when no `CLAUDE.md` exists, and a second file splits them.
- **Landing**: a change lands by a pull request that cites its issue, merged once a fresh subagent that did not write it reviews the diff from the merge base and approves its head sha; its author merges it. The ruleset on `main` refuses a force-push or deletion and has no required review, since the one merging account cannot approve its own pull request; `.github/CODEOWNERS` therefore only requests the owner's review.
- **Releases**: a release bumps the `version` in `plugin.json` of every plugin it changes, then tags `v<version>` on the merge commit, since a user's cached copy updates only when `version` changes; nothing else changes `version`.
- **Plugin manifests**: each plugin carries `.claude-plugin/plugin.json` and is listed in the root `.claude-plugin/marketplace.json`, which is how Claude Code finds it.
- **Moving a plugin folder**: uninstall the old plugin with `--keep-data`, since an uninstall without it deletes the plugin's data folder, and check each hook path after the move, since a stale one stays broken.
- **Every line acts**: keep a line in a rule, skill or document only when it changes the reader's next action.

## Plugin layout

- **Main parts**: build a plugin from `hooks/`, `monitors/` and `skills/`. Each is a module that works alone and reaches another only through a file or a command it names, never through its internals.
- **Plugins stand alone**: a plugin never depends on another plugin: it names none of their files, commands or skills, and works with every other plugin removed; shared code is copied or dropped, never imported across plugins.
- **No agents**: a plugin has no `agents/` folder; a role is a skill.
- **Scripts beside their user**: a script sits in the folder of the hook, monitor, skill or playbook that runs it, such as `skills/<skill>/scripts/` or `skills/<skill>/references/<playbook>/scripts/`, one script per use, never in a `scripts/` folder at the repository's or a plugin's root. Code two parts share is a module in the plugin's `lib/`, which a script reaches by putting that `lib/` on `sys.path`, and a script imports no other script.
- **bin for PATH only**: `bin/` holds only a command that must be found on `PATH`, such as one a document or a settings file names bare.
- **No tests or evals**: no `tests/` or `evals/` folder; check a change by running it and by Evaluation below. A hook tuned on past inputs may keep them in `fixtures/` beside it, with the script that replays them, and a checker script the documents it must accept or reject in `fixtures/` beside its `scripts/`.
- **Names**: a file name is lowercase words joined by `-`, saying what the file does or prints, never a verdict, state or measurement, with its language extension, except a Python module imported by name, whose words join with `_`; a new file follows its siblings' pattern.
- **Paths**: a `SKILL.md` names a command's path, or a file outside its skill, as `${CLAUDE_PLUGIN_ROOT}/<path>`, substituted when the skill loads; every other link is relative to the file that holds it, since a file opened with Read is read verbatim.

## Mods

Every plugin's panes share one frame as tabs, the latest opened one shown, and every plugin's hook receives every pane's events.

- **Prefixed names**: name each pane id `<plugin>-<noun>`, such as `teamwork-issues`, since every plugin's panes share one frame.
- **Own panes only**: match each pane hook on its own id (`requestId` for `ui.render`, `id` for `ui.close`), or hand any other pane on by `next(e)`.
- **Raise when asked**: open a pane unasked only once per session, since each new open takes the shown tab from the pane the person reads; bring it forward on the person's ask by closing and opening it again, since a plain open of an open id leaves it behind and `focus: true`, which raises it too, may take the prompt's keys.
- **Prose as Markdown**: draw a pane's prose, such as a goal or a detail, as `Markdown` and its labels and status as `Text`, since `Markdown` keeps the paragraphs, lists and links the writer wrote.

## Skills

- **Description**: `Use when …`, then optionally `Not for …`, as short as it can be.
- **Body**: the task or use case the skill serves, its vocabulary (domain concepts and protocols), in the body or in a reference its routing table sends the reader to first, and only the sections the case needs, such as Gotchas, How to learn or Priorities.
- **Routing table**: `SKILL.md` routes each case to a mode or playbook in `references/<case>.md`, named after the case it serves and shaped like a part of `SKILL.md`; it does not hold every case itself.
- **Skill folders**: beside `references/` and `scripts/`, a skill or playbook may keep files a script or page loads unchanged, such as a schema or a template, in `assets/`, and finished samples to imitate in `examples/`.
- **Named rules**: give each major instruction a short name.
- **Code computes**: calculation, aggregation and control go to `scripts/<verb>-<noun>.py`; the script prints predefined prose that says what its result means, so prose carries only definitions and judgement.
- **Comments say why**: a comment holds no knowledge the reader needs; it says only why the code is so, kept current, and names and design carry the rest.

## Design

- **Three layers**: split a design into control structure, abstract domain and rules. The control core rarely changes and depends only on interfaces; the domain depends on no policy, entity type or tool, such as a terminal multiplexer, that may change; those are rules. Use the split only while designing: its names stay out of code and folders.
- **Concept check**: check each concept you invent as a concept, its meaning, its boundary and what it replaces, before you build it.

## Evaluation

Use it to judge a change to an agent system, such as option A against option B.

- **Fresh evaluator**: the evaluator is a subagent with a fresh context. Give it every input as links (files, urls, shas), never your opinion.
- **Scores, not fixes**: it returns a score and a reason per criterion, and suggests no fix.
- **Binary criteria**: split the judgement into yes-or-no questions, yes 2, ambiguous 1, no 0, mutually exclusive and together exhaustive within the change's intent, the regressions to guard and the prior research found.
- **Pass mark**: scale so the current system scores about 50 on average and the ideal about 100. Set the pass mark from 70 for a very hard change to 90 for a very easy one, and revise until the mean of several runs passes it.
