// Run the pane module for a session that is no manager and then for a manager, through stand-ins for `claude-code` and the JSX runtime, call the tool
// the manager gets while its pane is hidden, and print the last line `PASS` when the tool is registered for the manager alone, the call closes and opens the
// pane again and reads the board again, and manager.md names the tool, as `mcp__<plugin name>__<tool name>`, in its Triage table; else `FAIL: <what failed>`, exit 1.
// usage: bun teamwork/hooks/fixtures/replay-pane-tool.ts
import { handlers, on } from './stand-in-modules.ts'

const TOOL = 'show-tasks-pane'
const PLUGIN = JSON.parse(await Bun.file(`${import.meta.dir}/../../.claude-plugin/plugin.json`).text()).name
const FULL = `mcp__${PLUGIN}__${TOOL}`
const calls: string[] = []
let session = 'worker-one-worker'
let boardReads = 0
const $ = {
  plugin: { root: '/plugin' },
  ui: { open: async () => void calls.push('open'), close: async () => void calls.push('close'), panes: async () => [{ id: 'teamwork-tasks', isShown: false }] },
  tool: { register: async (spec: { name: string }) => void calls.push(`register ${spec.name}`) },
  clock: { after: () => ({ cancel: () => undefined }) },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: `${session}\n` }
      boardReads++
      return { exitCode: 0, stdout: '[]', stderr: '' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}

const verdict = async (): Promise<string> => {
  const { register } = await import('../draw-task-pane.tsx')
  register(on as any)
  await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
  if (calls.some(call => call.startsWith('register'))) return 'a session that is no manager got the tool'
  session = 'probe-manager'
  await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
  if (!calls.includes(`register ${TOOL}`)) return 'the manager did not get the tool'
  await new Promise(done => setTimeout(done, 50))
  calls.length = 0
  const reads = boardReads
  const tool = handlers[`tool.call ${FULL}`]
  if (!tool) return 'no hook serves the tool'
  const answer = await tool($, {}, async () => ({})) as { result?: unknown; deny?: string }
  if (answer.deny !== undefined || answer.result === undefined) return `the tool did not answer with a result: ${JSON.stringify(answer)}`
  if (calls.join(' ') !== 'close open') return `the pane was not closed and opened again: ${calls.join(' ')}`
  if (boardReads <= reads) return 'the board was not read again'
  const manager = await Bun.file(`${import.meta.dir}/../../skills/kick-off/references/manager.md`).text()
  const triage = manager.split('\n').filter(line => line.startsWith('   | '))
  if (!triage.some(line => line.includes(`\`${FULL}\``))) return 'the Triage table of manager.md does not name the tool'
  return ''
}

const failure = await verdict().catch(error => String(error))
console.log(failure ? `FAIL: ${failure}` : 'PASS')
process.exit(failure ? 1 : 0)
