// Render a manager's issue pane from the board in a nodes file, every row unfolded, at body widths 30, 40, 60 and 88, through stand-ins for
// `claude-code` and the JSX runtime, and check it row for row against `list-issue-board.py` laid out for that width less the fold mark: each
// row's title, status, `←`, `?`, `◆` and `→` lines, guide included, are the lines its `--json` row lays out, in the order `--width` prints them,
// each fits the body with the first line's fold mark, a title that fits on one line takes one, and an unfolded row with a goal, criteria or
// closed parts draws them: `same`, else `differ: <the first difference>`, exit 1.
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

type Node = { type?: string; props?: { children?: unknown; label?: string; text?: string } }
// a link shows its label and Markdown its text; a button's own label is the fold mark, drawn apart from the row's text
const text = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('')
    : (node as Node).type === 'Link' ? (node as Node).props?.label ?? ''
    : (node as Node).type === 'Markdown' ? (node as Node).props?.text ?? ''
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
      return { exitCode: 0, stdout: listed(...argv.slice(2)), stderr: '' }
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
type Row = { number: number; guide: string; pad: string; goal: string; detail: string[]; done: { name: string }[];
  closed: { title: string }[]; lines: { title: string[]; status: string[]; after: string[]; notes: string[] } }
const differ = (what: string) => { console.log(`differ: ${what}`); process.exit(1) }
const FOLD = 2  // the pane's ` +` or ` -` at a row's first line's end
for (const width of [30, 40, 60, 88]) {
  const laid = String(width - FOLD)
  const rows = JSON.parse(listed('--json', '--width', laid)) as Row[]
  store.set('expanded', rows.map(row => row.number))
  // the first draw at a new width reads the board again for it, and the draw after that read shows the rows
  const before = reads
  await handlers['ui.render Pane']($, { props: { bodyColumns: width } })
  await settle(before + 1)
  const pane = await handlers['ui.render Pane']($, { props: { bodyColumns: width } })
  const drawn = children(pane).filter(child => (child as Node).type === 'Box')
  if (drawn.length !== rows.length) differ(`width ${width}: ${drawn.length} rows drawn, ${rows.length} listed`)
  const printed = listed('--width', laid).split('\n')
  let at = 0
  rows.forEach((row, k) => {
    const heading = [row.guide + row.lines.title[0], ...[...row.lines.title.slice(1), ...row.lines.status, ...row.lines.after, ...row.lines.notes].map(line => row.pad + line)]
    const lines = children(drawn[k])
    if (row.lines.title.length > 1 && Bun.stringWidth(row.guide + row.lines.title.join(' ')) + FOLD <= width)
      differ(`width ${width}: #${row.number}'s title fits on one line but takes ${row.lines.title.length}: ${JSON.stringify(row.lines.title)}`)
    heading.forEach((line, i) => {
      if (text(lines[i]) !== line) differ(`width ${width}: #${row.number} line ${i + 1}: drew ${JSON.stringify(text(lines[i]))}, listed ${JSON.stringify(line)}`)
      if (Bun.stringWidth(line) + (i === 0 ? FOLD : 0) > width) differ(`width ${width}: #${row.number} line ${i + 1} is wider than the body: ${JSON.stringify(line)}`)
      while (at < printed.length && printed[at] !== line) at++
      if (at++ === printed.length) differ(`width ${width}: #${row.number}: ${JSON.stringify(line)} is not in the --width ${laid} listing, in order`)
    })
    const folded = lines.slice(heading.length).map(text).join(' ')
    const owed = [row.goal, row.detail.length ? 'see detail' : '', ...row.done.map(item => item.name), ...row.closed.map(task => task.title)].filter(Boolean)
    const missing = owed.find(piece => !folded.includes(piece))
    if (missing !== undefined) differ(`width ${width}: #${row.number} unfolded lacks ${JSON.stringify(missing)}`)
  })
}
console.log('same')
