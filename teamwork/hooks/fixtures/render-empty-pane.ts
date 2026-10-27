// Render a manager's issue pane before any board read, after a failed read and after a good read of no issues, through stand-ins for
// `claude-code` and the JSX runtime, and print the pane's text at each: `unread: <text>`, `failed: <text>`, then `empty: <text>`.
// usage: bun teamwork/hooks/fixtures/render-empty-pane.ts
import { plugin } from 'bun'

const store = new Map<string, unknown>()  // the atoms' values
plugin({
  name: 'stand-ins',
  setup(build) {
    build.module('claude-code', () => ({
      loader: 'object',
      exports: {
        atom: (id: { key: string }, initial: unknown) => ({ key: id.key, initial }),
        read: async (_: unknown, a: { key: string; initial: unknown }) => (store.has(a.key) ? store.get(a.key) : a.initial),
        update: async (_: unknown, a: { key: string; initial: unknown }, change: (old: unknown) => unknown) =>
          void store.set(a.key, change(store.has(a.key) ? store.get(a.key) : a.initial)),
      },
    }))
    const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props })
    build.module('react/jsx-dev-runtime', () => ({ loader: 'object', exports: { jsxDEV: jsx, Fragment: 'Fragment' } }))
    build.module('react/jsx-runtime', () => ({ loader: 'object', exports: { jsx, jsxs: jsx, Fragment: 'Fragment' } }))
  },
})

const text = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('') : text((node as { props?: { children?: unknown } }).props?.children)

const handlers: Record<string, (...args: any[]) => Promise<unknown>> = {}
const on = (event: string, ...rest: any[]) => {
  handlers[[event, ...rest.slice(0, -1).map(f => Object.values(f)[0])].join(' ')] = rest[rest.length - 1]
  return { catch: () => undefined }
}
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
      return { exitCode, stdout: exitCode === 0 ? '[]' : '', stderr: exitCode === 0 ? '' : 'list-issue-board: the github board read failed' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}
const render = async () => text(await handlers['ui.render Pane']($, {}))
// a read's atoms change just after its run returns, so the render waits a little past it
const settle = async (count: number) => { while (reads < count) await new Promise(done => setTimeout(done, 5)); await new Promise(done => setTimeout(done, 50)) }

const { register } = await import('../issue-pane.tsx')
register(on as any)
console.log(`unread: ${await render()}`)
await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
await settle(1)
console.log(`failed: ${await render()}`)
exitCode = 0
await handlers['command.run teamwork:issues']($, {}, async () => ({}))
await settle(2)
console.log(`empty: ${await render()}`)
