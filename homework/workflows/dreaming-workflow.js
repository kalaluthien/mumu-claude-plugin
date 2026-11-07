export const meta = {
  name: 'dreaming-workflow',
  description: 'Dream: back up memory, map recent sessions, dig each repeated mistake and each owner preference, tidy every memory folder, and keep the memory that best replays owner corrections',
  whenToUse: 'Run from the homework wrap-up dream playbook, which passes the folders and what list-sessions.py due <data>/habit printed as args: {root, data, config, home, today, habit}',
  phases: [
    { title: 'Back up', detail: 'copy each memory folder outside version control' },
    { title: 'Map', detail: 'one facet agent per batch of session digests' },
    { title: 'Repeats', detail: 'group friction, then dig each repeat to its cause' },
    { title: 'Habits', detail: 'weekly: group habit items, then dig each preference' },
    { title: 'Drift', detail: 'one finder per project root, then one tidier' },
    { title: 'Replay', detail: 'pick and mark each candidate memory, revise twice, keep the best, after Dream-RSI (https://arxiv.org/html/2609.14858v1)' },
  ],
}

for (const key of ['root', 'data', 'config', 'home', 'today', 'habit']) {
  if (!args || !args[key]) throw new Error(`args.${key} is missing; pass {root, data, config, home, today, habit}`)
}
if (!['due', 'not due'].includes(args.habit)) throw new Error(`args.habit is '${args.habit}'; pass what list-sessions.py due <data>/habit printed`)
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
const LINES = { type: 'object', properties: { lines: { type: 'array', items: { type: 'string' } } }, required: ['lines'] }
const MEMORY_RULES = `A memory file holds a frontmatter of name, description and metadata.type, one lesson, a 'When it applies:' line and a 'When it is wrong:' line, and its index line in MEMORY.md reads '- [<title>](<file>.md) — <when it applies>'; edit MEMORY.md only over a fresh read, since other agents write it now.`

const STEP = `You do one step of the dream this workflow already runs for the request above, which this step alone serves: never load the homework:wrap-up skill, follow its dream playbook, run start-dreamer.py or call Workflow.

`
function step(prompt, opts) {
  return agent(STEP + prompt, opts)
}

function runner(command, what) {
  return `Run with Bash: ${command}
Return in 'batches' each line of its output that opens with 'batch <k>:', as k = '<k>' and items = the words after the colon. ${what}`
}

phase('Back up')
const backup = await step(`First run with Bash: mkdir -p ${DATA} && touch ${DATA}/dream.lock
Then back up the memory folders before a dream changes them. The memory home is ${HOME}; the other memory folders are each folder under it and each ${CONFIG}/projects/*/memory/. For each that exists and whose files git does not track (git -C <folder> ls-files prints nothing, as outside a work tree or when ignored there), copy it with cp -R to ${DATA}/backup/${TODAY}/, keeping its path below / as the copy's path, so ${HOME} lands at ${DATA}/backup/${TODAY}${HOME}. Change nothing else. Reply with one line per folder copied.`, { label: 'back up', phase: 'Back up', model: 'haiku', effort: 'low' })
if (!backup) throw new Error('the backup agent returned nothing, so no memory was changed')

phase('Map')
const mapped = await step(runner(`python3 ${SCRIPTS}/list-sessions.py map ${DEJAVU} --window-days 28`, 'Return an empty list when there is none.'), { label: 'list sessions', phase: 'Map', schema: BATCHES, model: 'haiku', effort: 'low' })
const facets = await parallel((mapped?.batches ?? []).map((batch) => () =>
  step(`Read ${BRIEFS}/facet-brief.md, then facet these digests into ${DEJAVU}/facets: ${batch.items.join(' ')}`, { label: `facet ${batch.k}`, phase: 'Map', model: 'haiku', effort: 'low' })))
log(`${facets.filter(Boolean).length} of ${facets.length} facet batches done`)

const PREFERENCE = {
  type: 'object',
  properties: {
    name: { type: 'string' }, why_chain: { type: 'string' },
    outcome: { type: 'string', enum: ['memory written', 'hand over', 'skipped'] },
    memory_file: { type: 'string' }, title: { type: 'string' }, file: { type: 'string' }, fields: { type: 'string' },
  },
  required: ['name', 'outcome'],
}
async function learnHabits() {
  if (args.habit !== 'due') return { due: false, preferences: [] }
  const grouped = await step(`1. Run with Bash: mkdir -p ${HABIT} && python3 ${SCRIPTS}/list-habits.py ${HABIT} --sessions ${DEJAVU}
2. Read ${HABIT}/habits.jsonl and ${HABIT}/kept.json if it exists. Group the items that show the same preference of the owner, such as "explain a made-up name before using it", across sessions and projects. Write ${HABIT}/preferences.json as a JSON list of {"name": "<the preference as one plain rule, under 100 chars, distinct from every other name; a kept.json key verbatim when it means the same>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.
3. Run with Bash: python3 ${SCRIPTS}/list-habits.py ${HABIT} --sessions ${DEJAVU} --groups ${HABIT}/preferences.json
4. Run with Bash: touch ${HABIT}/last-map
Return in 'lines' each preference of step 3's output as one string: its unindented line, then its indented lines below it, verbatim, joined by newlines.`, { label: 'group habits', phase: 'Habits', schema: LINES, model: 'haiku', effort: 'medium' })
  const preferences = await pipeline(grouped?.lines ?? [], (preference) => step(`A preference is a rule for the agent that the owner's words show in several sessions: how the owner instructs, asks, answers or gives feedback; its name is the text after its first line's first ': '. Here it is:
${preference}

1. With 'kept dropped', or with 'kept' and no 'seen since', return outcome 'skipped' and stop.
2. With no 'kept': read ${CONFIG}/CLAUDE.md, ${CONFIG}/rules/ and the AGENTS.md or CLAUDE.md of each repository in its repos line (a repo is a project key: the root python3 ${SCRIPTS}/list-projects.py ${CONFIG} prints whose path, each non-alphanumeric character as '-', equals it). When a line there already states it, treat it as 'seen since' below, citing that file.
3. Dig it by 5 whys, each answer the cause of the one before, read from its quote lines, the items' before and its memory lines (open the example transcript lines it cites): why did the agent not do it unasked, and why did nothing it reads tell it to? Stop at a cause a memory file, a skill line, an instruction line or a hook could change; a branch, dig each.
4. Not 'seen since', and a cause a memory file fixes: write it yourself in ${HOME}, or in ${HOME}/<repo>/ only when it is wrong or harmful outside that repository, extending the entry on its subject before adding a file, written as what the agent should do the first time, never as the mistake, its 'When it applies:' line naming the moment from the quotes, citing the example lines' transcript:line. ${MEMORY_RULES} Then run with Bash: python3 ${SCRIPTS}/list-habits.py ${HABIT} --record <the memory file> <the preference's last seen number> "<name>". Return outcome 'memory written' and memory_file.
5. Any other cause, or 'seen since' (its kept form reached no agent in time, so its fix moves one step stronger: a memory file to a skill line or an instruction line where the moment starts, a written line to a hook or script when a check can decide it): change nothing and return outcome 'hand over', title = the change, verb first, file = the file it would change, and fields = one line each: 'Preference:' (the name verbatim), 'Kept in:' (the kept or stating file, else 'none'), 'Why chain:', 'Sessions:', 'Repositories:', 'Last seen:' (the number on its first line), 'Examples:' (the example lines' transcript:line).
Always return name and why_chain.`, { label: `dig ${preference.slice(0, 40)}`, phase: 'Habits', schema: PREFERENCE }))
  return { due: true, preferences }
}

async function digRepeats() {
const grouped = await step(`1. Run with Bash: python3 ${SCRIPTS}/list-repeats.py ${DEJAVU}
2. Read ${DEJAVU}/friction.jsonl. Group the items that describe the same concrete mistake by the agent, such as "stopped to ask when the rule said act", across sessions and projects. Write ${DEJAVU}/mistakes.json as a JSON list of {"name": "<the mistake in one plain line, under 100 chars, distinct from every other name>", "ids": ["<item id>", ...]}. Leave out items that fit no group. Count nothing.
3. Run with Bash: python3 ${SCRIPTS}/list-repeats.py ${DEJAVU} --mistakes ${DEJAVU}/mistakes.json
Return in 'lines' each repeat of step 3's output as one string: its unindented line, then its indented lines below it, verbatim, joined by newlines.`, { label: 'group repeats', phase: 'Repeats', schema: LINES, model: 'haiku', effort: 'medium' })
const REPEAT = {
  type: 'object',
  properties: {
    key: { type: 'string' }, project: { type: 'string' }, why_chain: { type: 'string' }, fix_kind: { type: 'string' },
    outcome: { type: 'string', enum: ['memory written', 'hand over', 'guard worked', 'already handed over'] },
    memory_file: { type: 'string' }, title: { type: 'string' }, fields: { type: 'string' },
  },
  required: ['key', 'outcome'],
}
const repeats = await pipeline(grouped?.lines ?? [], (repeat) => step(`A repeat is a mistake that recurs across sessions; its key is the text after its first line's first ': '. Here it is:
${repeat}

1. With 'filed' and no 'seen since' on its first line, return outcome 'already handed over' and stop.
2. Dig it to its root cause by 5 whys, each answer the cause of the one before, read from its example and memory lines (open the example transcript lines it cites): why does it recur, and why did what should have stopped it not? Stop at a cause a guard, rule, skill line or script could change; a branch, dig each. A why that ends in a guard working as intended, such as a classifier refusal, returns outcome 'guard worked'.
3. A cause that is a missing or wrong lesson: write or correct that lesson yourself in ${HOME}, or in ${HOME}/<repo>/ only when it is wrong or harmful outside that repository, extending the entry on its subject before adding a file. ${MEMORY_RULES} Then run with Bash: python3 ${SCRIPTS}/list-repeats.py ${DEJAVU} --record <the memory file> <the repeat's last seen number> "<key>". Return outcome 'memory written' and memory_file.
4. Any other cause: change nothing and return outcome 'hand over', title = the fix, verb first, and fields = one line each: 'Cause in:' (the project that owns the cause), 'Kind:', 'Why chain:', 'Repeat:' (the key verbatim), 'Sessions:', 'Repositories:', 'First seen:', 'Last seen:', 'Examples:' (the example lines' transcript:line), 'Check first:' (for a tool failure, the example's full Bash command: rerun the script alone with echo $? and close as a false positive at 0), 'Already in memory:' (the memory lines, else 'none found') and 'Fix kind:' (a guard, a rule, a skill line or a script).
Always return key, project, why_chain and fix_kind.`, { label: `dig ${repeat.slice(0, 40)}`, phase: 'Repeats', schema: REPEAT }))
  return repeats
}

phase('Repeats')
const [repeats, habits] = await Promise.all([digRepeats(), learnHabits()])

phase('Drift')
const projects = await step(`Run with Bash: python3 ${SCRIPTS}/list-projects.py ${CONFIG}
Return in 'lines' the path after 'project ' on each line that opens with it.`, { label: 'list projects', phase: 'Drift', schema: LINES, model: 'haiku', effort: 'low' })
const FINDINGS = {
  type: 'object',
  properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, drift: { type: 'string' }, fix: { type: 'string' }, memory: { type: 'boolean' } }, required: ['file', 'drift', 'fix', 'memory'] } } },
  required: ['findings'],
}
const scopes = [`the memory folders and config: ${HOME} with each folder under it, ${CONFIG}/projects/*/memory/, ${CONFIG}/CLAUDE.md and ${CONFIG}/rules/; also run with Bash python3 ${SCRIPTS}/list-drift.py ${CONFIG} and python3 ${SCRIPTS}/measure-rules.py ${CONFIG} ${(projects?.lines ?? []).join(' ')}, and report each line they print as a finding`,
  ...(projects?.lines ?? []).map((root) => `the project root ${root}`)]
const found = await pipeline(scopes, (scope) => step(`Read the Domain section of ${LAYOUT}: it defines the memory layout and, per target, the drift to look for. Find the drift in ${scope}. List what exists with git ls-files and a glob, never assume a layout. Check each path, command, flag or package an entry names with a read-only probe (ls, grep, --help, git log -S); report it as dead only when a project's files or history show it was there and is gone, since a tool merely not installed on this machine may live on another. Change no file. Return each finding: the file, the drift, the fix that removes it, and memory = true when the fix changes only a memory folder (${HOME}, a folder under it, or ${CONFIG}/projects/*/memory/).`, { label: `find ${scope.slice(0, 50)}`, phase: 'Drift', schema: FINDINGS }))
const findings = found.filter(Boolean).flatMap((result) => result.findings)
log(`${findings.length} drift findings, ${findings.filter((finding) => finding.memory).length} in memory`)
const TIDY = {
  type: 'object',
  properties: {
    applied: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
    other_fixes: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, fix: { type: 'string' }, reason: { type: 'string' }, check: { type: 'string' } }, required: ['file', 'fix', 'reason'] } },
  },
  required: ['applied', 'contradictions', 'other_fixes'],
}
const tidy = await step(`You tidy every memory folder in place: ${HOME}, each folder under it and each ${CONFIG}/projects/*/memory/; a backup sits in ${DATA}/backup/${TODAY}/. First check with ls that ${DATA}/backup/${TODAY}${HOME} exists; when it does not, change no file and return applied = ['no backup, nothing changed'] with the other lists empty. Read the Domain section of ${LAYOUT} for the layout. The findings below come from read-only finders; read each file afresh before you change it. Apply each memory fix at once, in this order, so each conflict is judged once:
1. Duplicates: one lesson in several places is kept in one; two entries on one subject or mechanism become one, keeping the shared procedure and dropping one-off ids, dates and paths.
2. Contradictions: of two entries that conflict, keep one when the other's evidence is older or its reason no longer holds; write one entry that holds both intents when both hold in the same situation; or draw a boundary, each entry naming the situation it governs, when each holds in its own. Return each pair as '<files>: <way>, <reason>' in contradictions.
3. Generalize: lessons that share one cause become one lesson that names the class, its cause and its fix in general words; the specific ones stay only as one-line examples, or go.
4. Superseded: an entry a later one restates, narrows or reverses is rewritten or deleted.
5. Stale: fix a dead path, command, flag or package, one a project's files or history show was there and is gone, when the new target is plain, else delete the entry; keep an entry whose tool is merely not installed here.
6. Placement: a lesson in the wrong memory folder moves by python3 ${SCRIPTS}/move-memory.py <file> <folder>; a lesson that belongs in an instruction file, a document or a skill stays in memory and goes to other_fixes.
7. Demote: a lesson list-drift.py lists as never found again is weakened, its index line narrowed to the situation it came from, or moved down to the one project it came from, never kept at full weight.
8. Size: an index past its load limit is cut to one line per entry.
${MEMORY_RULES} Change no file outside the memory folders: return each other fix (an instruction file, document, skill, hook, script or rules file) in other_fixes, with its reason and, for a skill, hook or script, the check that must still pass. Return in applied one line per memory fix made.

Findings (JSON):
${JSON.stringify(findings, null, 1)}`, { label: 'tidy memory', phase: 'Drift', schema: TIDY })

phase('Replay')
const cases = await step(`1. Run with Bash: python3 ${SCRIPTS}/list-replay-cases.py ${DEJAVU} > ${DEJAVU}/replay-cases.txt
2. When it holds no line opening with 'case ', return an empty list and stop.
3. Delete ${DEJAVU}/candidates, ${DEJAVU}/picks and ${DEJAVU}/marks, then copy ${HOME} to ${DEJAVU}/candidates/current with cp -R.
Return in 'batches' each line of ${DEJAVU}/replay-cases.txt that opens with 'batch <k>:', as k = '<k>' and items = the case ids after the colon.`, { label: 'list cases', phase: 'Replay', schema: BATCHES, model: 'haiku', effort: 'low' })
let replay = { skipped: 'no replay case' }
if ((cases?.batches ?? []).length > 0) {
  const pick = (name) => parallel(cases.batches.map((batch) => () =>
    step(`Read ${BRIEFS}/replay-brief.md, then pick for candidate ${DEJAVU}/candidates/${name} into ${DEJAVU}/picks/${name}/${batch.k}.jsonl on these cases: the lines of ${DEJAVU}/replay-cases.txt that open with 'case <id> ' for each id of ${batch.items.join(' ')}. Create ${DEJAVU}/picks/${name}/ first if it is missing.`, { label: `pick ${name} ${batch.k}`, phase: 'Replay', model: 'haiku', effort: 'low' })))
  const mark = async (name) => {
    const sets = await step(runner(`mkdir -p ${DEJAVU}/marks && python3 ${SCRIPTS}/list-recall-sets.py ${DEJAVU} > ${DEJAVU}/recall-sets-${name}.txt; grep '^batch ' ${DEJAVU}/recall-sets-${name}.txt`, 'items are case ids.'), { label: `list sets ${name}`, phase: 'Replay', schema: BATCHES, model: 'haiku', effort: 'low' })
    return parallel((sets?.batches ?? []).map((batch) => () =>
      step(`Read ${BRIEFS}/mark-brief.md, then mark into ${DEJAVU}/marks/${name}-${batch.k}.jsonl these cases: for each id of ${batch.items.join(' ')}, the line of ${DEJAVU}/recall-sets-${name}.txt that opens with 'case <id> ' and the 'instructions' and 'set' lines below it up to the next 'case' or 'batch' line.`, { label: `mark ${name} ${batch.k}`, phase: 'Replay', model: 'haiku', effort: 'low' })))
  }
  await pick('current')
  await mark('current')
  let last = 'current'
  for (const name of ['r1', 'r2']) {
    await step(`Read ${BRIEFS}/revise-brief.md, then write candidate ${name} from ${last} in ${DEJAVU} with the scripts in ${SCRIPTS}`, { label: `revise ${name}`, phase: 'Replay' })
    await pick(name)
    await mark(name)
    last = name
  }
  const SCORE = {
    type: 'object',
    properties: { output: { type: 'string' }, missing: { type: 'array', items: { type: 'string' } }, selected: { type: 'string' } },
    required: ['output', 'missing', 'selected'],
  }
  const score = () => step(`Run with Bash: python3 ${SCRIPTS}/score-memory.py ${DEJAVU}
Return output = its whole output verbatim, missing = the candidate name of each 'missing: <name> <n>' line, and selected = the candidate name its last line selects.`, { label: 'score', phase: 'Replay', schema: SCORE, model: 'haiku', effort: 'low' })
  let scored = await score()
  for (let round = 0; round < 2 && scored?.missing?.length; round++) {
    const again = [...new Set(scored.missing)]
    log(`judges skipped cases of ${again.join(', ')}; picking and marking them again`)
    for (const name of again) { await pick(name); await mark(name) }
    scored = await score()
  }
  let applied = 'kept current'
  if (scored?.selected && scored.selected !== 'current') {
    applied = await step(`Run with Bash: diff -ru ${DEJAVU}/candidates/current ${DEJAVU}/candidates/${scored.selected}
Apply each change it prints to ${HOME}, file by file, over a fresh read of each file, a file renamed in ${HOME} meanwhile taking the change under its new name, since other sessions write it meanwhile and copying the revision's files would bring an old name back. Keep ${DEJAVU}/candidates/current unchanged. Reply with one line per file changed.`, { label: `apply ${scored.selected}`, phase: 'Replay' })
  }
  replay = { score: scored?.output ?? null, missing: scored?.missing ?? [], selected: scored?.selected ?? null, applied }
}

await step(`Run with Bash: rm -f ${DATA}/dream.lock`, { label: 'unlock', phase: 'Replay', model: 'haiku', effort: 'low' })
return {
  backup,
  map: { batches: (mapped?.batches ?? []).length, done: facets.filter(Boolean).length },
  repeats: repeats.filter(Boolean),
  repeats_failed: repeats.filter((result) => !result).length,
  habits: { due: habits.due, preferences: habits.preferences.filter(Boolean), failed: habits.preferences.filter((result) => !result).length },
  drift: { findings: findings.length, applied: tidy?.applied ?? [], contradictions: tidy?.contradictions ?? [], other_fixes: tidy?.other_fixes ?? [] },
  replay,
}
