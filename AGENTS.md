# Agents

The working rules of this repository and of every plugin in it. Each rule carries a bold name, so a review or another file can cite it. A plugin's own rules live in its skills, never here. A rule a check enforces names that check, whose docstring holds the mechanics; change the check, not this file.

## Repository

- **Live checkout**: sessions load the plugins straight from this checkout, so a merge reaches them once the checkout pulls. A script or a `references/` file works at once; a `SKILL.md` or a `hooks.json` at `/reload-plugins`, which the merging session prompts to each running session after `git pull --ff-only`, first when a hook's script moved, since that hook stays off until then; a monitor's code when the monitor restarts.
- **No CLAUDE.md**: rules sit only in `AGENTS.md`, since a second file splits them.
- **Landing**: a change lands by a merge in local git that cites its task, once a fresh subagent that did not write it reviews the diff from the merge base and approves its head sha, which a rebase that leaves that diff the same keeps; its author merges and pushes `main`, releasing as **Releases** says, with no GitHub pull request. The ruleset on `main` refuses a force-push or deletion and holds no `pull_request` rule, since that rule would refuse the push of `main` and the one merging account cannot approve its own change; `.github/CODEOWNERS` only requests the owner's review.
- **Releases**: every merge that changes a plugin bumps its `version` in `plugin.json` and pushes the tag `<plugin>-v<version>` with `main`, since a user's cached copy updates only when `version` changes, and nothing else changes `version`; `.github/plan-release.py` refuses a merge that breaks this and prints the tags, and `.github/list-unreleased.py` lists a plugin no tag covers.
- **Plugin manifests**: each plugin carries `.claude-plugin/plugin.json` and is listed in the root `.claude-plugin/marketplace.json`, which is how Claude Code finds it.
- **Moving a plugin folder**: uninstall the old plugin with `--keep-data`, since an uninstall without it deletes the plugin's data folder, and check each hook path after the move.
- **Every line acts**: keep a line in a rule, skill or document only when it changes the reader's next action.
- **Nothing unreached**: reach every file, function and import of a plugin from an entry point (the manifest, `hooks/hooks.json`, `monitors/monitors.json`, a `SKILL.md`, a file at the plugin's root) or remove it, since dead code is read and kept in step for nothing; `.github/list-unreached.py` defines reach and lists what fails it.
- **Repository checks**: a check that serves every plugin sits in `.github/` and names no plugin; `.github/check-repository.py` runs them all with every fixture runner and is the repository's whole check, its docstring naming what each enforces and how a passed runner is replayed.

## Plugin layout

- **Main parts**: build a plugin from `hooks/`, `monitors/`, `skills/` and `workflows/` (a workflow script `<name>.js`, offered as `<plugin>:<name>`); each part works alone and reaches another only through a file or command it names.
- **Plugins stand alone**: a plugin names no other plugin's files, commands or skills and works with every other plugin removed; shared code is copied or dropped. `.github/list-cross-plugin-names.py` lists a breach.
- **No agents**: a plugin has no `agents/` folder; a role is a skill.
- **Scripts beside their user**: a script sits in the folder of the hook, monitor, skill or reference domain that runs it, one per use, never in a root `scripts/` folder; code two parts share is a module in the plugin's `lib/`, and a script imports no other script.
- **bin for PATH only**: `bin/` holds only a command that must be found on `PATH`.
- **No tests or evals**: no `tests/` or `evals/` folder; check a change by running it and by Evaluation below. A part may keep in `fixtures/` what a runner replays, and a fixture no runner replays is removed, since nothing would show it broken; `.github/list-unreached.py` defines a runner.
- **Names**: a file name says what the file does or prints, never a verdict, state or measurement, a script's opening with a verb, `<verb>-<noun>`; a new file follows its siblings' pattern. `.github/list-misnamed.py` holds the forms and their exceptions.
- **Environment names**: an environment variable a plugin reads is `<PLUGIN>_<WORDS>`, since every plugin's scripts share one environment; `.github/list-misnamed.py` checks it.
- **State homes**: a plugin keeps one repository's state in `<repo>/.<plugin>/` and one person's in `${CLAUDE_PLUGIN_DATA}`, since the first follows the repository and the second the person.
- **Hook command**: a `hooks.json` or `monitors.json` command is `"\"${CLAUDE_PLUGIN_ROOT}\"/hooks/<script>"`, the root alone quoted, `monitors/` for a monitor, so every command reads alike.
- **Script form**: a Python script's docstring opens with a purpose sentence, then a `usage:` line per call; a call it cannot read prints that docstring on stderr, nothing on stdout, and exits 2, except a hook, since Claude Code reads exit 2 as a block. Its body is `def main(args)` run by `sys.exit(main(sys.argv[1:]))`; it reaches `lib/` by `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[<n>] / "lib"))` and its own folder by `HERE = pathlib.Path(__file__).resolve().parent`, or `ROOT = …parents[<n>]` above it; its flags are lowercase words joined by `-`. `.github/check-repository.py` checks the answer to an unknown flag.
- **Script structure**: judge a script by simplicity, minimal dependencies (the standard library or its own plugin's `lib/`) and consistency with its siblings, since a script that reads like them is the cheapest to change.
- **Word names**: a Python name is the whole word it stands for, snake_case, UPPER_CASE for a constant, CapWords for a class, never a lone capital; `n`, `k`, `e` or `i` for a count, key, error or index stays.
- **Paths**: a `SKILL.md` names a command or a file outside its skill as `${CLAUDE_PLUGIN_ROOT}/<path>`, substituted when the skill loads; every other link is relative to its file, since a file opened with Read is read verbatim.

## Mods

Every plugin's panes share one frame as tabs, the latest opened one shown, and every plugin's hook receives every pane's events.

- **Prefixed names**: name each pane id `<plugin>-<noun>`, since every plugin's panes share one frame.
- **Own panes only**: match each pane hook on its own id (`requestId` for `ui.render`, `id` for `ui.close`), or hand any other pane on by `next(e)`.
- **Raise when asked**: open a pane unasked only once per session, since each open takes the shown tab; bring it forward on the person's ask by closing and opening it again, since a plain open leaves it behind and `focus: true` may take the prompt's keys.
- **Prose as Markdown**: draw a pane's prose as `Markdown` and its labels and status as `Text`, since `Markdown` keeps the writer's paragraphs, lists and links.

## Skills

- **Description**: `Use when …`, then optionally `Not for …`, as short as it can be.
- **Body**: the task the skill serves, its vocabulary (domain concepts and protocols), in the body or in a reference its routing table sends the reader to first, and only the sections the case needs.
- **Routing table**: `SKILL.md` routes each case to a playbook `references/<case>.md`, titled by its file name's words, a purpose line, then Domain, Steps, Rules, one file per case.
- **Skill folders**: a skill may keep files a script or page loads unchanged in `assets/`, and finished samples to imitate in `examples/`.
- **Reference layout**: a skill's folder holds `SKILL.md`, `references/`, `assets/`, `examples/`, `scripts/` and `fixtures/` only, a playbook's parts beside it as `references/<case>-<part>.md` or in `references/<domain>/`, since one place per kind lets a reader find each file; `.github/list-misplaced-references.py` holds the layout and lists a breach.
- **Named rules**: give each major instruction a short name.
- **Code computes**: calculation, aggregation and control go to `scripts/<verb>-<noun>.py`, which prints prose saying what its result means, so prose carries only definitions and judgement.
- **Comments say why**: a comment says only why the code is so, kept current; names and design carry the rest.

## Design

- **Three layers**: split a design into a control core that depends only on interfaces, a domain that depends on no changeable policy, entity type or tool, and rules that hold those; the split's names stay out of code and folders.
- **Concept check**: check each concept you invent, its meaning, boundary and what it replaces, before you build it.

## Evaluation

Use it to judge a change to an agent system, such as option A against option B.

- **Fresh evaluator**: the evaluator is a subagent with a fresh context, given every input as links (files, urls, shas), never your opinion.
- **Scores, not fixes**: it returns a score and a reason per criterion, and suggests no fix.
- **Binary criteria**: split the judgement into yes-or-no questions, yes 2, ambiguous 1, no 0, mutually exclusive and together exhaustive within the change's intent, the regressions to guard and the prior research found.
- **Pass mark**: scale so the current system scores about 50 and the ideal about 100; set the pass mark from 70 for a very hard change to 90 for a very easy one, and revise until the mean of several runs passes it.
