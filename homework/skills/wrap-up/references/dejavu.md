# Dejavu

Find what keeps going wrong across recent sessions, in every project, and hand each repeat to the project that owns its cause, so a guard, rule, skill or script gets fixed instead of the same mistake recurring. Haiku agents read the sessions in parallel (map); scripts and one haiku agent find what repeats (reduce); this session hands them over.

## Domain

- `<d>` is `${CLAUDE_PLUGIN_DATA}/dejavu`, where every file dejavu keeps lives.
- **Facet**: one session's friction items (the owner objecting to what the agent did) and standing instructions, written by a haiku agent from the session's digest.
- **Repeat**: a `tool` failure signature, an owner `instruction` or a grouped `mistake` that recurs, as `list-repeats.py` prints it; its `key` is the text after the line's first `: `.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-sessions.py map <d>`.
2. For each `batch` line, start one `Agent` with `model: haiku`, all in one message so they run in parallel, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/dejavu-facet.md, then facet these digests into <d>/facets: <the batch's paths>`.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d>`, which writes `<d>/friction.jsonl`.
4. Start one `Agent` with `model: haiku`, prompted: `Read <d>/friction.jsonl. Group the items that describe the same concrete mistake by the agent, such as "stopped to ask when the rule said act", across sessions and projects. Write <d>/mistakes.json as a JSON list of {"name": "<the mistake in one plain line, under 100 chars, distinct from every other name>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.`
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d> --mistakes <d>/mistakes.json`.
6. For each repeat line: with no `filed`, hand it over; with `filed` and `seen since`, hand it over again only when the owner says the earlier hand-over is closed; else skip it.
7. Handing over asks first: show the owner each repeat's title and project, and hand over only those they approve. Hand each to the project that owns the cause, the tool, hook, script, skill or instruction file the repeat comes from, by that project's own channel, the way its `AGENTS.md` takes an issue. If a project names none, or the cause is in no project, report it to the owner in your reply. Title it as the fix, verb first. Its body holds one line per field. The fields are `Cause in:` (the project that owns the cause), `Kind:`, `Repeat:` (the key, verbatim), `Sessions:`, `Repositories:`, `First seen:`, `Last seen:`, `Examples:` (the `example` lines' `transcript:line`s), `Check first:` (for a tool failure, the example's full Bash command line: rerun the script alone with `echo $?` and close as a false positive at 0, since the detector counts the whole Bash call's exit code), `Already in memory:` (the `memory` lines, else `none found`) and `Fix kind:` (a guard, a rule, a skill line or a script).
8. After each hand-over, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d> --record <where it went: the issue url, a path, or `owner`> <the repeat's last seen number> "<key>"`.

## Rules

- **Every repeat**: offer every repeat the steps reach; no cap per run.
- **Hand over only**: dejavu's output is a hand-over by a project's own channel, a report to the owner, and the files in `<d>`, nothing else, since lessons kept as notes did not stop these repeats; name no tracker beyond what a project's `AGENTS.md` says.
- **Check a change**: after editing `list-sessions.py` or `list-repeats.py`, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/fixtures/probe-dejavu.py`; it must print `17 of 17 steps pass`.
- **Measure repeats**: before tuning a signature, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/measure-repeats.py [days]` to count how many failures repeat across sessions.
