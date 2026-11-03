# Habit

Learn, across recent sessions in every project, how the owner instructs, asks, answers and gives feedback, and keep the preference behind each where agents meet it, so they read the owner right the first time. Haiku agents read the sessions in parallel (map); a script and one haiku agent find the preferences that recur (reduce); this session keeps them.

## Domain

- `<h>` is `${CLAUDE_PLUGIN_DATA}/habit`, where every file habit keeps lives.
- **Habit item**: one owner line or answer and what it shows, of kind `instruct` (a request the agent read otherwise, or a short form), `ask` (what something the agent made means, or why), `answer` (a pick other than the recommended one, or the owner's own words), `feedback` (on how the agent explained, proposed, asked or reported) or `rule` (a standing rule), written by a haiku agent from the session's digest.
- **Preference**: a group of habit items in 2+ sessions that show one rule for the agent, as `list-habits.py` prints it; its `name` is the text after the line's first `: `.
- **Cadence**: weekly over 28 days, inside the 30-day transcript retention, since a preference needs more sessions to show than a mistake and changes slowly; dejavu runs daily over 14.

## Steps

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-sessions.py map <h> --window-days 28 --limit 120`.
2. For each `batch` line, start one `Agent` with `model: haiku`, all in one message so they run in parallel, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/habit/facet-brief.md, then facet these digests into <h>/facets: <the batch's paths>`.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-habits.py <h>`, which writes `<h>/habits.jsonl`.
4. Start one `Agent` with `model: haiku`, prompted: `Read <h>/habits.jsonl and <h>/kept.json if it exists. Group the items that show the same preference of the owner, such as "explain a made-up name before using it", across sessions and projects. Write <h>/preferences.json as a JSON list of {"name": "<the preference as one plain rule, under 100 chars, distinct from every other name; a kept.json key verbatim when it means the same>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.`
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-habits.py <h> --groups <h>/preferences.json`.
6. **Pick**: for each preference line: with no `kept`, keep it by the steps below; with `kept` and `seen since`, take it to **Go stronger**; else skip it.
7. **Dig**: take each picked preference through 5 whys, each answer the cause of the one before, read from its `quote` lines, the items' `before` and its `memory` lines: why did the agent not do it unasked, and why did nothing it reads tell it to? Stop at a cause a memory file, a skill line, an instruction line or a hook could change, such as a missing lesson, an index line whose situation misses the moment, or a skill step that says otherwise; a branch, dig each.
8. **Keep memory**: a cause a memory file fixes, write it yourself, routed by [retro.md](retro.md) steps 4-6: a memory file in `<home>` when true for every project, else in `<home>/<repo>/`, confirmed, extended or added there, its `When it applies:` line naming the moment from the quotes, citing the quotes' ids.
9. **Hand over**: a cause in a skill, a hook, a script or an instruction file goes by the **Hand over** rule of [SKILL.md](../SKILL.md), its change named as the preference, its quotes and why chain cited.
10. **Go stronger**: a preference `seen since` its kept form reached no agent in time, so dig why it did not, then move it one step stronger by **Hand over**: a memory file to a skill line or an instruction line where the moment starts, a written line to a hook or script when a check can decide it.
11. **Record**: after each, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-habits.py <h> --record <where it went: the memory file, a url, or `owner`> <the preference's last seen number> "<name>"`.
12. **Report** each preference kept: its name, sessions, where it went, and each one dropped with why.

## Rules

- **Owner's ways only**: habit keeps how the owner instructs, asks, answers and gives feedback on how the agent speaks; a wrong result or action in the work is dejavu's, so leave it.
- **Every preference**: keep every preference the steps reach; no cap per run.
- **First time**: write each preference as what the agent should do the first time, never as the mistake, since an agent acts on the rule it reads.
- **Check a change**: after editing `list-sessions.py` or `list-habits.py`, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/fixtures/probe-habit.py`; it must print `probe: 10 of 10 steps pass`.
