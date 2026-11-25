// Load the pane module afresh, as a plugin reload or a compaction does, with no session start, call the pane tool as a manager, and print the last line
// `PASS` when the call reads the board and a second call starts no second watch, else `FAIL: <what failed>`, exit 1.
// usage: bun teamwork/hooks/fixtures/replay-pane-reload.ts
import { handlers, on } from './stand-in-modules.ts'

const PLUGIN = JSON.parse(await Bun.file(`${import.meta.dir}/../../.claude-plugin/plugin.json`).text()).name
const FULL = `mcp__${PLUGIN}__show-tasks-pane`
let boardReads = 0
let watches = 0
const $ = {
  plugin: { root: '/plugin' },
  ui: { open: async () => undefined, close: async () => undefined, panes: async () => [{ id: 'teamwork-tasks', isShown: true }] },
  tool: { register: async () => undefined },
  clock: { after: () => ({ cancel: () => undefined }) },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: 'probe-manager\n' }
      boardReads++
      return { exitCode: 0, stdout: '[]', stderr: '' }
    },
    spawn: () => { watches++; return (async function* () {})() },
  },
}

const verdict = async (): Promise<string> => {
  const { register } = await import('../draw-task-pane.tsx')
  register(on as any)
  const tool = handlers[`tool.call ${FULL}`]
  if (!tool) return 'no hook serves the tool'
  const answer = await tool($, {}, async () => ({})) as { result?: unknown; deny?: string }
  if (answer.deny !== undefined || answer.result === undefined) return `the tool did not answer with a result: ${JSON.stringify(answer)}`
  if (boardReads === 0) return 'the tool did not read the board after a reload'
  await tool($, {}, async () => ({}))
  if (watches !== 1) return `a second call started ${watches} board watches, not 1`
  return ''
}

const failure = await verdict().catch(error => String(error))
console.log(failure ? `FAIL: ${failure}` : 'PASS')
process.exit(failure ? 1 : 0)
