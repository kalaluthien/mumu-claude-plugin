// Render a manager's issue pane from the board in a nodes file, through stand-ins for `claude-code` and the JSX runtime, and check
// that every line it draws, every row folded, is a line `list-issue-board.py --width 40` prints for that board, in the same order:
// `same`, else `differ: <the first line not found>`, exit 1.
// usage: bun teamwork/hooks/fixtures/render-task-pane.ts <nodes-file>
import { plugin } from 'bun'

const nodes = process.argv[2]
if (!nodes) {
  console.error('usage: bun teamwork/hooks/fixtures/render-task-pane.ts <nodes-file>')
  process.exit(2)
}
const lister = `${import.meta.dir}/../list-issue-board.py`
const listed = (...args: string[]) => {
  const run = Bun.spawnSync(['python3', lister, '--nodes', nodes, ...args])
  if (run.exitCode !== 0) throw new Error(`list-issue-board.py ${args.join(' ')} exited ${run.exitCode}: ${run.stderr}`)
  return run.stdout.toString()
}

const store = new Map<string, unknown>()  // the atoms' values
plugin({
  name: 'stand-ins',
  setup(build) {
    build.module('claude-code', () => ({
      loader: 'object',
      exports: {
        atom: (id: { key: string }, initial: unknown) => ({ key: id.key, initial }),
        read: async (_: unknown, entry: { key: string; initial: unknown }) => (store.has(entry.key) ? store.get(entry.key) : entry.initial),
        update: async (_: unknown, entry: { key: string; initial: unknown }, change: (old: unknown) => unknown) =>
          void store.set(entry.key, change(store.has(entry.key) ? store.get(entry.key) : entry.initial)),
      },
    }))
    const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props })
    build.module('react/jsx-dev-runtime', () => ({ loader: 'object', exports: { jsxDEV: jsx, Fragment: 'Fragment' } }))
    build.module('react/jsx-runtime', () => ({ loader: 'object', exports: { jsx, jsxs: jsx, Fragment: 'Fragment' } }))
  },
})

type Node = { type?: string; props?: { children?: unknown; label?: string } }
// a link shows its label; a button's own label is the fold mark, drawn apart from the row's text
const text = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('')
    : (node as Node).type === 'Link' ? (node as Node).props?.label ?? ''
    : (node as Node).type === 'Button' && (node as Node).props?.label !== undefined ? '' : text((node as Node).props?.children)
const children = (node: unknown): unknown[] => [(node as Node).props?.children].flat(Infinity).filter(child => child != null && typeof child !== 'boolean')

const handlers: Record<string, (...args: any[]) => Promise<unknown>> = {}
const on = (event: string, ...rest: any[]) => {
  handlers[[event, ...rest.slice(0, -1).map(argument => Object.values(argument)[0])].join(' ')] = rest[rest.length - 1]
  return { catch: () => undefined }
}
let reads = 0
const $ = {
  plugin: { root: '/plugin' },
  ui: { open: async () => undefined, close: async () => undefined, panes: async () => [],
        resolve: () => ({ Box: 'Box', Text: 'Text', Link: 'Link', Button: 'Button', Markdown: 'Markdown' }) },
  clock: { after: () => ({ cancel: () => undefined }) },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: 'probe-manager\n' }
      reads++
      return { exitCode: 0, stdout: listed('--json'), stderr: '' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}
// a read's atoms change just after its run returns, so the render waits a little past it
const settle = async (count: number) => { while (reads < count) await new Promise(done => setTimeout(done, 5)); await new Promise(done => setTimeout(done, 50)) }

const { register } = await import('../draw-issue-pane.tsx')
register(on as any)
await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
await settle(1)
const pane = await handlers['ui.render Pane']($, {})
// each row is a column whose children are its lines
const drawn = children(pane).flatMap(row => children(row).map(text))
const printed = listed('--width', '40').split('\n')
let at = 0
for (const line of drawn) {
  while (at < printed.length && printed[at] !== line) at++
  if (at === printed.length) {
    console.log(`differ: ${JSON.stringify(line)}`)
    process.exit(1)
  }
  at++
}
console.log(drawn.length > 0 ? 'same' : 'differ: the pane drew no row')
process.exit(drawn.length > 0 ? 0 : 1)
