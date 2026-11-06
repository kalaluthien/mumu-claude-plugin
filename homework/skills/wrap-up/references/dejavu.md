# Dejavu

Find what keeps going wrong across recent sessions, in every project, and hand each repeat to the project that owns its cause, so a guard, rule, skill or script gets fixed instead of the same mistake recurring. Haiku agents read the sessions in parallel (map); scripts and one haiku agent find what repeats (reduce); this session hands them over.

## Domain

- `<d>` is `${CLAUDE_PLUGIN_DATA}/dejavu`, where every file dejavu keeps lives.
- **Facet**: one session's friction items (the owner objecting to what the agent did), written by a haiku agent from the session's digest.
- **Repeat**: a `tool` failure signature or a grouped `mistake` that recurs, as `list-repeats.py` prints it; its `key` is the text after the line's first `: `.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-sessions.py map <d>`.
2. For each `batch` line, start one `Agent` with `model: haiku`, all in one message so they run in parallel, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/dejavu/facet-brief.md, then facet these digests into <d>/facets: <the batch's paths>`.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d>`, which writes `<d>/friction.jsonl`.
4. Start one `Agent` with `model: haiku`, prompted: `Read <d>/friction.jsonl. Group the items that describe the same concrete mistake by the agent, such as "stopped to ask when the rule said act", across sessions and projects. Write <d>/mistakes.json as a JSON list of {"name": "<the mistake in one plain line, under 100 chars, distinct from every other name>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.`
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d> --mistakes <d>/mistakes.json`.
6. For each repeat line: with no `filed`, hand it over; with `filed` and `seen since`, hand it over again only when the owner says the earlier hand-over is closed; else skip it.
7. Dig each repeat to its root cause by 5 whys, each answer the cause of the one before, read from its `Examples:` and `memory` lines: why does it recur, and why did what should have stopped it not? Stop at a cause a guard, rule, skill line or script could change, and hand over that cause, not the symptom; a branch, dig each. Skip a repeat whose why ends in a guard working as intended, such as a classifier refusal, and tell the owner in one line.
8. A cause that is a missing or wrong lesson is fixed by **Memory in place** at once, since the owner lets dejavu fix memory directly. Handing over asks first: show the owner each other repeat's title and project, and hand over only those they approve. Any other cause, in the tool, hook, script, skill or instruction file the repeat comes from, goes by `SKILL.md`'s **Hand over** and **Foreign repositories** to the project that owns it; a cause in no project is reported to the owner in your reply. Title the hand-over as the fix, verb first. It holds one line per field. The fields are `Cause in:` (the project that owns the cause), `Kind:`, `Why chain:` (the whys, one line), `Repeat:` (the key, verbatim), `Sessions:`, `Repositories:`, `First seen:`, `Last seen:`, `Examples:` (the `example` lines' `transcript:line`s), `Check first:` (for a tool failure, the example's full Bash command line: rerun the script alone with `echo $?` and close as a false positive at 0, since the detector counts the whole Bash call's exit code), `Already in memory:` (the `memory` lines, else `none found`) and `Fix kind:` (a guard, a rule, a skill line or a script).
9. After each fix or hand-over, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-repeats.py <d> --record <where it went: the memory file, the session it went to, the commit or pull request url, the patch path, or `owner`> <the repeat's last seen number> "<key>"`.

## Rules

- **Every repeat**: offer every repeat the steps reach; no cap per run.
- **Memory in place**: a repeat whose root cause is a missing or wrong lesson gets that lesson written or corrected by dejavu itself, in `<home>`, or the project's `<home>/<repo>/` only when wrong or harmful outside it, one memory file with its index line, since a memory fix needs no other hand; every other output is a hand-over, a report to the owner, or the files in `<d>`.
- **Check a change**: after editing `list-sessions.py`, `list-repeats.py` or `homework/lib/repeats.py`, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/fixtures/probe-dejavu.py`; it must print `probe: 18 of 18 steps pass`; after editing `list-sessions.py` or `repeats.py`, run [habit.md](habit.md)'s probe too.
- **Measure repeats**: before tuning a signature, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/measure-repeats.py [days]` to count how many failures repeat across sessions.
