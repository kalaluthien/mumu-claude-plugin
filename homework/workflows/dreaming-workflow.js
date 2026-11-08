export const meta = {
  name: 'dreaming-workflow',
  description: 'Dream: back up memory, map recent sessions, dig the most repeated mistakes and owner preferences, and tidy every memory folder in place',
  whenToUse: 'Run from the homework wrap-up dream playbook, which passes the folders and what list-sessions.py due <data>/habit printed as args: {root, data, config, home, today, habit}',
  phases: [
    { title: 'Set up', detail: 'one agent runs the scripts: lock, back up, map sessions, list projects' },
    { title: 'Map', detail: 'one haiku agent per batch of session digests, at once' },
    { title: 'Dig', detail: 'one agent groups repeats and, weekly, habits, then digs the top ones' },
    { title: 'Tidy', detail: 'one agent finds the drift in memory and config and fixes memory in place' },
  ],
}

if (!args?.data) throw new Error('args.data is missing; pass {root, data, config, home, today, habit}')
const ROOT = args.root
const SCRIPTS = `${ROOT}/skills/wrap-up/scripts`
const BRIEFS = `${ROOT}/skills/wrap-up/references/dream`
const LAYOUT = `${ROOT}/skills/wrap-up/references/dream.md`
const DATA = args.data
const DEJAVU = `${DATA}/dejavu`
const HABIT = `${DATA}/habit`
const CONFIG = args.config
const HOME = args.home
const TODAY = args.today

const BATCHES = {
  type: 'object',
  properties: { batches: { type: 'array', items: { type: 'object', properties: { k: { type: 'string' }, items: { type: 'array', items: { type: 'string' } } }, required: ['k', 'items'] } } },
  required: ['batches'],
}
const MEMORY_RULES = `A memory file covers one situation: a frontmatter of name, description (the same words as its index line) and, under metadata:, type, confirmed and last-confirmed; its lessons; a 'When it applies:' line and a 'When it is wrong:' line. Its index line in MEMORY.md reads '- [<title>](<file>.md) — <when it applies>', and MEMORY.md holds a title and index lines only; edit MEMORY.md only over a fresh read, since other agents write it now.`

const STEP = `You do one step of the dream this workflow already runs for the request above, which this step alone serves: never load the homework:wrap-up skill, follow its dream playbook, run start-dreamer.py or call Workflow.

`
function step(prompt, opts) {
  return agent(STEP + prompt, opts)
}


const TOP_REPEATS = 3  // the repeats seen in the most sessions; the rest wait for a later run
const TOP_PREFERENCES = 2

let result
try {
  for (const key of ['root', 'config', 'home', 'today', 'habit']) {
    if (!args[key]) throw new Error(`args.${key} is missing; pass {root, data, config, home, today, habit}`)
  }
  if (!['due', 'not due'].includes(args.habit)) throw new Error(`args.habit is '${args.habit}'; pass what list-sessions.py due <data>/habit printed`)
  phase('Set up')
  const SETUP = {
    type: 'object',
    properties: {
      backup: { type: 'array', items: { type: 'string' } },
      batches: BATCHES.properties.batches,
      projects: { type: 'array', items: { type: 'string' } },
    },
    required: ['backup', 'batches', 'projects'],
  }
  const setup = await step(`Run each with Bash, in order, and change nothing else:
1. mkdir -p ${DATA} && touch ${DATA}/dream.lock
2. Back up the memory folders before a dream changes them. The memory home is ${HOME}; the other memory folders are each folder under it and each ${CONFIG}/projects/*/memory/. For each that exists and whose files git does not track (git -C <folder> ls-files prints nothing, as outside a work tree or when ignored there), copy it with cp -R to ${DATA}/backup/${TODAY}/, keeping its path below / as the copy's path, so ${HOME} lands at ${DATA}/backup/${TODAY}${HOME}.
3. python3 ${SCRIPTS}/list-sessions.py map ${DEJAVU} --window-days 28
4. python3 ${SCRIPTS}/list-projects.py ${CONFIG}
Return backup = one line per folder copied, batches = each line of step 3 that opens with 'batch <k>:', as k = '<k>' and items = the words after the colon, and projects = the path after 'project ' on each line of step 4 that opens with it.`, { label: 'set up', phase: 'Set up', schema: SETUP, model: 'haiku', effort: 'low' })
  if (!setup) throw new Error('the set-up agent returned nothing, so no memory was changed')

  phase('Map')
  const facets = await parallel(setup.batches.map((batch) => () =>
    step(`Read ${BRIEFS}/facet-brief.md, then facet these digests into ${DEJAVU}/facets: ${batch.items.join(' ')}`, { label: `facet ${batch.k}`, phase: 'Map', model: 'haiku', effort: 'low' })))
  log(`${facets.filter(Boolean).length} of ${facets.length} facet batches done`)

  phase('Dig')
  const DUG = {
    type: 'object',
    properties: {
      repeats: { type: 'array', items: { type: 'object', properties: {
        key: { type: 'string' }, project: { type: 'string' }, why_chain: { type: 'string' }, fix_kind: { type: 'string' },
        outcome: { type: 'string', enum: ['memory written', 'hand over', 'guard worked', 'already handed over'] },
        memory_file: { type: 'string' }, title: { type: 'string' }, fields: { type: 'string' },
      }, required: ['key', 'outcome'] } },
      preferences: { type: 'array', items: { type: 'object', properties: {
        name: { type: 'string' }, why_chain: { type: 'string' },
        outcome: { type: 'string', enum: ['memory written', 'hand over', 'skipped'] },
        memory_file: { type: 'string' }, title: { type: 'string' }, file: { type: 'string' }, fields: { type: 'string' },
      }, required: ['name', 'outcome'] } },
      left: { type: 'integer' },
    },
    required: ['repeats', 'preferences', 'left'],
  }
  const habitSteps = args.habit !== 'due' ? '' : `
Preferences, this week's turn:
5. Run with Bash: mkdir -p ${HABIT} && python3 ${SCRIPTS}/list-repeats.py habits ${HABIT} --sessions ${DEJAVU}
6. Read ${HABIT}/habits.jsonl and ${HABIT}/kept.json if it exists. Group the items that show the same preference of the owner, such as "explain a made-up name before using it", across sessions and projects. Write ${HABIT}/preferences.json as a JSON list of {"name": "<the preference as one plain rule, under 100 chars, distinct from every other name; a kept.json key verbatim when it means the same>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.
7. Run with Bash: python3 ${SCRIPTS}/list-repeats.py habits ${HABIT} --sessions ${DEJAVU} --groups ${HABIT}/preferences.json, then touch ${HABIT}/last-map. A preference is a rule for the agent that the owner's words show in several sessions; it is one unindented line of this output with the indented lines below it, and its name is the text after its first line's first ': '.
8. Dig the first ${TOP_PREFERENCES} preferences that have no 'kept dropped' and are not 'kept' without 'seen since'; return each preference skipped this way with outcome 'skipped', and add the rest to left. For each one you dig: read ${CONFIG}/CLAUDE.md, ${CONFIG}/rules/ and the AGENTS.md or CLAUDE.md of each repository in its repos line (a repo is a project key: one of the roots ${setup.projects.join(' ')} with each non-alphanumeric character as '-'); a line there that already states it counts as 'seen since', citing that file. Dig it by 5 whys, each answer the cause of the one before, read from its quote lines, the items' before and its memory lines (open the example transcript lines it cites): why did the agent not do it unasked, and why did nothing it reads tell it to? Stop at a cause a memory file, a skill line, an instruction line or a hook could change; a branch, dig each. Not 'seen since', and a cause a memory file fixes: write it in ${HOME}, or in ${HOME}/<repo>/ only when it is wrong or harmful outside that repository, extending the entry on its subject before adding a file, written as what the agent should do the first time, its 'When it applies:' line naming the moment from the quotes, citing the example lines' transcript:line; then run with Bash: python3 ${SCRIPTS}/list-repeats.py habits ${HABIT} --record <the memory file> <the preference's last seen number> "<name>", and return outcome 'memory written' and memory_file. Any other cause, or 'seen since', so its fix moves one step stronger (a memory file to a skill or instruction line, a written line to a hook or script): change nothing and return outcome 'hand over', title = the change, verb first, file = the file it would change, and fields = one line each: 'Preference:' (the name verbatim), 'Kept in:', 'Why chain:', 'Sessions:', 'Repositories:', 'Last seen:' (the number on its first line), 'Examples:'. Return name and why_chain for each.`
  const dug = await step(`Repeats:
1. Run with Bash: python3 ${SCRIPTS}/list-repeats.py mistakes ${DEJAVU}
2. Read ${DEJAVU}/friction.jsonl. Group the items that describe the same concrete mistake by the agent, such as "stopped to ask when the rule said act", across sessions and projects. Write ${DEJAVU}/mistakes.json as a JSON list of {"name": "<the mistake in one plain line, under 100 chars, distinct from every other name>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.
3. Run with Bash: python3 ${SCRIPTS}/list-repeats.py mistakes ${DEJAVU} --groups ${DEJAVU}/mistakes.json. A repeat is one unindented line of this output with the indented lines below it, seen in the most sessions first; its key is the text after its first line's first ': '.
4. Return each repeat with 'filed' and no 'seen since' on its first line as outcome 'already handed over'. Dig the first ${TOP_REPEATS} of the others and add the rest to left. Dig each one to its root cause by 5 whys, each answer the cause of the one before, read from its example and memory lines (open the example transcript lines it cites): why does it recur, and why did what should have stopped it not? Stop at a cause a guard, rule, skill line or script could change; a branch, dig each; a why that ends in a guard working as intended, such as a classifier refusal, is outcome 'guard worked'. A missing or wrong lesson: write or correct it in ${HOME}, or in ${HOME}/<repo>/ only when it is wrong or harmful outside that repository, extending the entry on its subject before adding a file; then run with Bash: python3 ${SCRIPTS}/list-repeats.py mistakes ${DEJAVU} --record <the memory file> <the repeat's last seen number> "<key>", and return outcome 'memory written' and memory_file. Any other cause: change nothing and return outcome 'hand over', title = the fix, verb first, and fields = one line each: 'Cause in:' (the project that owns the cause), 'Kind:', 'Why chain:', 'Repeat:' (the key verbatim), 'Sessions:', 'Repositories:', 'First seen:', 'Last seen:', 'Examples:', 'Check first:' (for a tool failure, the example's full Bash command: rerun the script alone with echo $? and close as a false positive at 0), 'Already in memory:' and 'Fix kind:' (a guard, a rule, a skill line or a script). Return key, project, why_chain and fix_kind for each.
${habitSteps}
${MEMORY_RULES} Return preferences = [] when there are no preference steps above.`, { label: 'dig', phase: 'Dig', schema: DUG, model: 'sonnet' })
  if (dug?.left) log(`${dug.left} repeats and preferences left for a later run`)

  phase('Tidy')
  const TIDY = {
    type: 'object',
    properties: {
      applied: { type: 'array', items: { type: 'string' } },
      contradictions: { type: 'array', items: { type: 'string' } },
      other_fixes: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, fix: { type: 'string' }, reason: { type: 'string' }, check: { type: 'string' } }, required: ['file', 'fix', 'reason'] } },
    },
    required: ['applied', 'contradictions', 'other_fixes'],
  }
  const tidy = await step(`You find the drift in the memory folders and config and tidy every memory folder in place: ${HOME}, each folder under it and each ${CONFIG}/projects/*/memory/; a backup sits in ${DATA}/backup/${TODAY}/. Read the Domain section of ${LAYOUT}: it defines the memory layout and, per target, the drift to look for.
1. Find: run with Bash python3 ${SCRIPTS}/list-drift.py ${CONFIG} and python3 ${SCRIPTS}/measure-rules.py ${CONFIG} ${setup.projects.join(' ')}, and read the memory folders, ${CONFIG}/CLAUDE.md and ${CONFIG}/rules/. List what exists with a glob, never assume a layout. Check each path, command, flag or package an entry names with a read-only probe (ls, grep, --help, git log -S); count it as dead only when a project's files or history show it was there and is gone, since a tool merely not installed on this machine may live on another.
2. Fix memory, reading each file afresh before you change it, in this order, so each conflict is judged once:
  a. Duplicates: one lesson in several places is kept in one; two entries on one subject or mechanism become one, keeping the shared procedure and dropping one-off ids, dates and paths.
  b. Contradictions: of two entries that conflict, keep one when the other's evidence is older or its reason no longer holds; write one entry that holds both intents when both hold in the same situation; or draw a boundary, each entry naming the situation it governs, when each holds in its own. Return each pair as '<files>: <way>, <reason>' in contradictions.
  c. Generalize: lessons that share one cause become one lesson that names the class, its cause and its fix in general words; the specific ones stay only as one-line examples, or go.
  d. Superseded: an entry a later one restates, narrows or reverses is rewritten or deleted.
  e. Stale: fix a dead path, command, flag or package when the new target is plain, else delete the entry; keep an entry whose tool is merely not installed here.
  f. Placement: a lesson in the wrong memory folder moves by python3 ${SCRIPTS}/move-memory.py <file> <folder>; a lesson that belongs in an instruction file, a document or a skill stays in memory and goes to other_fixes.
  g. Promote and demote, by the Placement test in ${ROOT}/skills/wrap-up/SKILL.md: a lesson a repeat shows was needed before its situation was visible goes to other_fixes as a move into the instruction file that test names; an instruction-file line whose situation is plainly visible when it arises becomes a memory file here, its cut going to other_fixes; a lesson list-drift.py lists as never found again is weakened, its index line narrowed to the situation it came from, or moved down to the one project it came from.
  h. Size: an index past its load limit is cut to one line per entry.
${MEMORY_RULES} Change no file outside the memory folders: return each other fix (an instruction file, document, skill, hook, script or rules file) in other_fixes, with its reason and, for a skill, hook or script, the check that must still pass. Return in applied one line per memory fix made.`, { label: 'tidy', phase: 'Tidy', schema: TIDY, model: 'sonnet' })

  result = {
    backup: setup.backup,
    map: { batches: facets.length, done: facets.filter(Boolean).length },
    repeats: dug?.repeats ?? [],
    habits: { due: args.habit === 'due', preferences: dug?.preferences ?? [] },
    left: dug?.left ?? null,
    dig_failed: !dug,
    drift: { applied: tidy?.applied ?? [], contradictions: tidy?.contradictions ?? [], other_fixes: tidy?.other_fixes ?? [] },
    tidy_failed: !tidy,
  }
} finally {
  const reset = result ? `python3 ${ROOT}/hooks/signal-wrap-up.py dreamed ${DATA}; ` : ''  // only a dream that ended starts the memory count again
  const unlocked = await step(`Run with Bash: ${reset}rm -f ${DATA}/dream.lock && echo removed
Return its output.`, { label: 'unlock', phase: 'Tidy', model: 'haiku', effort: 'low' }).catch(() => null)
  if (!/\bremoved\b/.test(String(unlocked ?? ''))) {
    const unlock = `could not remove ${DATA}/dream.lock: remove it, or no dream runs on ${DATA} for 6 hours`
    log(unlock)
    if (result) result.unlock = unlock
  }
}
return result
