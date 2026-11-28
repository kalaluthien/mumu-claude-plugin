// Load the pane module as a manager's session meets it, through stand-ins for `claude-code` and the JSX runtime, each load a fresh copy of the module
// over the same session state, as a plugin reload or a compaction makes, and print `ok <case>` or `fail <case>: <what failed>` per case, then the last line
// `PASS` when every case run passed, else `FAIL`, exit 1; a case named runs with the cases before it, whose loads it follows.
// usage: bun teamwork/hooks/fixtures/replay-pane-refresh.ts [refresh | reopen | no-model-call]
// - refresh: a load whose first event is any of the kinds below, with no tool call, opens the pane, reads the board, and reads it again at each team change,
//   while later events start no second board watch; a session that is no manager has its name read once over many events; a reload reads the board in the
//   folder the session started in;
// - reopen: a reload whose unload took the pane down opens it again, never with focus; a load that finds it up opens nothing; once the person closed it, a reload
//   leaves it closed and the next board change opens it again, never with focus;
// - no-model-call: no load registers a tool or a command, a Bash call marks no team change, and manager.md names no teamwork tool.
import { tmpdir } from 'os'

import { handlers, on } from './stand-in-modules.ts'

const PANE = 'teamwork-tasks'
const MODULE = `${import.meta.dir}/../draw-task-pane.tsx`
let panes: { id: string; isShown: boolean }[] = []
const opens: { focus?: boolean }[] = []
const registered: string[] = []
const touches: string[][] = []
let boardReads = 0
let nameReads = 0
let session = 'probe-manager'
let readFolder: string | undefined
let watches = 0
let changes: (() => void)[] = []
const $ = {
  plugin: { root: '/plugin' },
  ui: {
    open: async (args: { id: string; focus?: boolean }) => { opens.push(args); if (!panes.some(pane => pane.id === args.id)) panes.push({ id: args.id, isShown: true }); return { isPlaced: true } },
    close: async ({ id }: { id: string }) => { panes = panes.filter(pane => pane.id !== id) },
    panes: async () => panes,
  },
  tool: { register: async (spec: { name: string }) => void registered.push(`tool ${spec.name}`) },
  command: { register: async (spec: { name: string }) => void registered.push(`command ${spec.name}`) },
  env: { get: async (name: string) => (name === 'HOME' ? '/home' : '') },
  clock: { after: () => ({ cancel: () => undefined }) },
  process: {
    run: async (argv: string[], options?: { cwd?: string }) => {
      if (argv[0].endsWith('list-sessions.py')) { nameReads++; return { exitCode: 0, stdout: `${session}\n`, stderr: '' } }
      if (argv[0] === 'touch') { touches.push(argv); return { exitCode: 0, stdout: '', stderr: '' } }
      boardReads++
      readFolder = options?.cwd
      return { exitCode: 0, stdout: '[]', stderr: '' }
    },
    // the waiter says `changed` at its start, as wait-team-change.py does, then once per `change()`, until a reload ends it, as the engine ends an old copy's process
    spawn: () => {
      watches++
      const copy = loads
      return (async function* () {
        yield { text: 'changed' }
        for (;;) {
          await new Promise<void>(done => changes.push(done))
          if (copy !== loads) return
          yield { text: 'changed' }
        }
      })()
    },
  },
}
const settle = () => new Promise(done => setTimeout(done, 50))
const change = async () => { const waiting = changes; changes = []; waiting.forEach(done => done()); await settle() }

// a fresh copy of the module, as a reload loads it: its own variables start over, the session state in the stand-ins' store stays
let loads = 0
const load = async () => {
  for (const key of Object.keys(handlers)) delete handlers[key]
  loads++
  await change()  // ends the waiters of the copy before
  const copy = `${tmpdir()}/teamwork-pane-load-${process.pid}-${loads}.tsx`
  await Bun.write(copy, Bun.file(MODULE))
  try {
    const { register } = await import(copy)
    register(on as any)
  } finally {
    await Bun.file(copy).delete()
  }
  watches = 0
}
const fire = async (event: string, input: object = {}) => {
  const hook = handlers[event]
  if (!hook) throw new Error(`the module hooks no ${event}`)
  await hook($, input, async () => ({}))
  await settle()
}

const FIRST = ['session.start', 'session.compact', 'session.receive', 'turn.start', 'turn.complete', 'prompt.submit', 'tool.call', 'command.run']
const refresh = async () => {
  for (const kind of FIRST) {
    panes = []
    const reads = boardReads
    await load()
    await fire(kind, kind === 'session.start' ? { cwd: '/repo' } : {})
    if (boardReads === reads || watches !== 1) return `a first ${kind} read the board ${boardReads - reads} times and started ${watches} board watches, not 1`
  }
  session = 'probe-one-worker'
  await load()
  nameReads = 0
  for (const kind of FIRST) await fire(kind, kind === 'session.start' ? { cwd: '/repo' } : {})
  if (nameReads !== 1) return `a session that is no manager had its name read ${nameReads} times over ${FIRST.length} events, not once`
  session = 'probe-manager'
  await load()
  await fire('session.start', { cwd: '/started-here' })
  await load()
  await fire('turn.start')
  if (readFolder !== '/started-here') return `a reload read the board in ${readFolder}, not in the folder the session started in`
  panes = []
  await load()
  await fire('turn.start')
  if (!panes.some(pane => pane.id === PANE)) return 'the first event did not open the pane'
  const first = boardReads
  if (first === 0) return 'the first event did not read the board'
  await change()
  if (boardReads <= first) return 'a team change did not read the board again'
  await fire('prompt.submit', { text: 'hi' })
  await fire('tool.call', { tool: 'Read', input: {} })
  await fire('turn.complete')
  if (watches !== 1) return `later events left ${watches} board watches, not 1`
  return ''
}

const reopen = async () => {
  opens.length = 0
  await handlers[`ui.close ${PANE}`]($, { id: PANE, origin: 'unload' }, async () => { panes = panes.filter(pane => pane.id !== PANE) })
  await load()
  await fire('session.compact')
  if (opens.length !== 1) return `a reload that took the pane down opened it ${opens.length} times, not once`
  if (opens.some(args => args.focus)) return 'the pane was opened with focus, which takes the prompt keys'
  opens.length = 0
  await load()
  await fire('turn.start')
  if (opens.length) return 'a load that found the pane up opened it again, taking the shown tab'
  if (!handlers[`ui.close ${PANE}`]) return 'the module hooks no close of its pane'
  await handlers[`ui.close ${PANE}`]($, { id: PANE, origin: 'person' }, async () => { panes = panes.filter(pane => pane.id !== PANE) })
  await settle()
  await load()
  await fire('turn.start')
  if (opens.length) return 'a reload opened the pane the person had closed'
  await change()
  if (opens.length !== 1 || !panes.some(pane => pane.id === PANE)) return `a board change opened the pane the person had closed ${opens.length} times, not once`
  if (opens.some(args => args.focus)) return 'a board change opened the pane with focus, which takes the prompt keys'
  return ''
}

const noModelCall = async () => {
  if (registered.length) return `a load registered ${registered.join(', ')}`
  const bash = handlers['tool.call']
  await bash($, { tool: 'Bash', command: 'gh pr merge 5 --squash' }, async () => ({}))
  await settle()
  if (touches.length) return `a Bash call marked a team change: ${touches.map(argv => argv.join(' ')).join('; ')}`
  const manager = await Bun.file(`${import.meta.dir}/../../skills/kick-off/references/manager.md`).text()
  const named = manager.match(/mcp__teamwork__[\w-]+/g)
  if (named) return `manager.md names ${named.join(', ')}`
  return ''
}

const CASES = [['refresh', refresh], ['reopen', reopen], ['no-model-call', noModelCall]] as const
const wanted = process.argv[2]
const last = wanted === undefined ? CASES.length : CASES.findIndex(([name]) => name === wanted) + 1
if (!last) {
  console.error(`usage: bun teamwork/hooks/fixtures/replay-pane-refresh.ts [${CASES.map(([name]) => name).join(' | ')}]`)
  process.exit(2)
}
let failed = false
for (const [name, run] of CASES.slice(0, last)) {
  const failure = await run().catch(error => String(error))
  failed ||= Boolean(failure)
  if (wanted === undefined || name === wanted) console.log(failure ? `fail ${name}: ${failure}` : `ok ${name}`)
}
console.log(failed ? 'FAIL' : 'PASS')
process.exit(failed ? 1 : 0)
