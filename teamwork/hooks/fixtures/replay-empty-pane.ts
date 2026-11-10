// Render a manager's issue pane before any board read, after a failed read and after a good read of no issues, through stand-ins for
// `claude-code` and the JSX runtime, and print the pane's text at each: `unread: <text>`, `failed: <text>`, then `empty: <text>`.
// usage: bun teamwork/hooks/fixtures/replay-empty-pane.ts
import { drawPane, handlers, on } from './stand-in-modules.ts'

const text = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('') : text((node as { props?: { children?: unknown } }).props?.children)

let exitCode = 1
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
      return { exitCode, stdout: exitCode === 0 ? '[]' : '', stderr: exitCode === 0 ? '' : 'list-issue-board: the git board read failed' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}
const draw = (props: object) => drawPane($, props)
const render = async () => text(await draw({ bodyColumns: 0 }))
// a read's atoms change just after its run returns, so the render waits a little past it
const settle = async (count: number) => { while (reads < count) await new Promise(done => setTimeout(done, 5)); await new Promise(done => setTimeout(done, 50)) }

const { register } = await import('../draw-issue-pane.tsx')
register(on as any)
console.log(`unread: ${await render()}`)
await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
await settle(1)
console.log(`failed: ${await render()}`)
exitCode = 0
await handlers['command.run teamwork:issues']($, {}, async () => ({}))
await settle(2)
console.log(`empty: ${await render()}`)
