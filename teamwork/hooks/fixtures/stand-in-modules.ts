// The stand-ins a pane's render fixture loads under bun in place of `claude-code` and the JSX runtime: atoms kept in `store`, the handlers the
// pane registers kept by event in `handlers`, and `drawPane`, which refuses a state write while a render is dispatched, as Claude Code does.
import { plugin } from 'bun'

export const store = new Map<string, unknown>()  // the atoms' values
let drawing = false  // while a render is dispatched, when Claude Code refuses a state write
plugin({
  name: 'stand-ins',
  setup(build) {
    // `claude-code`: an atom is its id's key with an initial value, `read` gives the latest value set or the initial one, `update` sets what its change returns, refused while a render is dispatched
    build.module('claude-code', () => ({
      loader: 'object',
      exports: {
        atom: (id: { key: string }, initial: unknown) => ({ key: id.key, initial }),
        read: async (_: unknown, entry: { key: string; initial: unknown }) => (store.has(entry.key) ? store.get(entry.key) : entry.initial),
        update: async (_: unknown, entry: { key: string; initial: unknown }, change: (old: unknown) => unknown) => {
          if (drawing) throw new Error('state.set: denied: it was made while ui.render is being dispatched, and drawing is pure')
          store.set(entry.key, change(store.has(entry.key) ? store.get(entry.key) : entry.initial))
        },
      },
    }))
    // the JSX runtime: an element is its type and its props, the children among the props
    const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props })
    build.module('react/jsx-dev-runtime', () => ({ loader: 'object', exports: { jsxDEV: jsx, Fragment: 'Fragment' } }))
    build.module('react/jsx-runtime', () => ({ loader: 'object', exports: { jsx, jsxs: jsx, Fragment: 'Fragment' } }))
  },
})

export const handlers: Record<string, (...args: any[]) => Promise<unknown>> = {}
// `on(event, ...filters, handler)`: a handler kept under its event and each filter's first value, and a registration that may be caught
export const on = (event: string, ...rest: any[]) => {
  handlers[[event, ...rest.slice(0, -1).map(argument => Object.values(argument)[0])].join(' ')] = rest[rest.length - 1]
  return { catch: () => undefined }
}
// `ui.render`: the pane's render handler called with the props Claude Code passes, here its body's columns
export const drawPane = async ($: object, props: object) => { drawing = true; try { return await handlers['ui.render Pane']($, { props }) } finally { drawing = false } }
