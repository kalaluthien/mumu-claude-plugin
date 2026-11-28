// Render a manager's task pane before any board read, after a failed read and after a good read of no tasks, through stand-ins for
// `claude-code` and the JSX runtime, print the pane's text at each, `unread: <text>`, `failed: <text>` and `empty: <text>`, then the last line `PASS` when each is
// the text EXPECTED gives it, else `FAIL: <each that differed>`, exit 1.
// usage: bun teamwork/hooks/fixtures/replay-empty-pane.ts
import { drawPane, handlers, on } from './stand-in-modules.ts'

const text = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('') : text((node as { props?: { children?: unknown } }).props?.children)

const EXPECTED = { unread: 'No board read yet.', failed: 'Board read failed: list-task-board: the git board read failed', empty: 'The board has no open tasks.' }
const drawn: Record<string, string> = {}
const show = async (state: keyof typeof EXPECTED) => { drawn[state] = await render(); console.log(`${state}: ${drawn[state]}`) }

let exitCode = 1
let teamChange = () => undefined as unknown
let reads = 0
const $ = {
  plugin: { root: '/plugin' },
  ui: { open: async () => undefined, close: async () => undefined, panes: async () => [],
        resolve: () => ({ Box: 'Box', Text: 'Text', Link: 'Link', Button: 'Button', Markdown: 'Markdown' }) },
  tool: { register: async () => undefined },
  clock: { after: () => ({ cancel: () => undefined }) },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: 'probe-manager\n' }
      reads++
      return { exitCode, stdout: exitCode === 0 ? '[]' : '', stderr: exitCode === 0 ? '' : 'list-task-board: the git board read failed' }
    },
    // the waiter says `changed` at its start, as wait-team-change.py does, then once at `teamChange()`
    spawn: () => (async function* () { yield { text: 'changed' }; await new Promise(done => { teamChange = done }); yield { text: 'changed' } })(),
  },
}
const draw = (props: object) => drawPane($, props)
const render = async () => text(await draw({ bodyColumns: 0 }))
// a read's atoms change just after its run returns, so the render waits a little past it
const settle = async (count: number) => { while (reads < count) await new Promise(done => setTimeout(done, 5)); await new Promise(done => setTimeout(done, 50)) }

const { register } = await import('../draw-task-pane.tsx')
register(on as any)
await show('unread')
await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
await settle(1)
await show('failed')
exitCode = 0
teamChange()
await settle(2)
await show('empty')
const differed = Object.entries(EXPECTED).filter(([state, text]) => drawn[state] !== text).map(([state, text]) => `${state} drew ${JSON.stringify(drawn[state])}, not ${JSON.stringify(text)}`)
console.log(differed.length ? `FAIL: ${differed.join('; ')}` : 'PASS')
process.exit(differed.length ? 1 : 0)
