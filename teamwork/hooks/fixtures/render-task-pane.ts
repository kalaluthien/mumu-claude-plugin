// Render a manager's issue pane from the board in a nodes file, every row unfolded, at body widths 30, 40, 60 and 88, through stand-ins for
// `claude-code` and the JSX runtime, and check it row for row against `list-issue-board.py` laid out for that width less the fold mark: each
// row's title, status, `?`, `◆` and `next step:` lines, guide included, are the lines its `--json` row lays out, in the order `--width` prints them,
// each fits the body with the first line's fold mark, a title that fits on one line takes one, and an unfolded row with criteria or
// closed parts draws them: `same`, else `differ: <the first difference>`, exit 1.
// With `--styled`, once that holds, it prints instead each piece the last draw (width 88) styles, one per line: `link <label>`, `press <text>`,
// `strike <text>`, `dim <text>` or `color:<name> <text>`.
// With `--press <text>` (repeatable; `none` presses nothing), it draws the rows at width 88 with every row folded, presses each button whose text
// holds a given text, and prints the rows' drawn lines as `<row number>|<line>`.
// usage: bun teamwork/hooks/fixtures/render-task-pane.ts <nodes-file> [--styled | --press <text>...]
import { plugin } from 'bun'

const nodes = process.argv[2]
if (!nodes) {
  console.error('usage: bun teamwork/hooks/fixtures/render-task-pane.ts <nodes-file> [--styled | --press <text>...]')
  process.exit(2)
}
const lister = `${import.meta.dir}/../list-issue-board.py`
const listed = (...args: string[]) => {
  const run = Bun.spawnSync(['python3', lister, '--nodes', nodes, ...args])
  if (run.exitCode !== 0) throw new Error(`list-issue-board.py ${args.join(' ')} exited ${run.exitCode}: ${run.stderr}`)
  return run.stdout.toString()
}

const store = new Map<string, unknown>()  // the atoms' values
let drawing = false  // while a render is dispatched, when Claude Code refuses a state write
plugin({
  name: 'stand-ins',
  setup(build) {
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
  clock: { after: (ms: number, tick: () => void) => { const timer = setTimeout(tick, ms); return { cancel: () => clearTimeout(timer) } } },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: 'probe-manager\n' }
      reads++
      return { exitCode: 0, stdout: listed(...argv.slice(2)), stderr: '' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}
const draw = async (props: object) => { drawing = true; try { return await handlers['ui.render Pane']($, { props }) } finally { drawing = false } }
// a read's atoms change just after its run returns, so the render waits a little past it
const settle = async (count: number) => { while (reads < count) await new Promise(done => setTimeout(done, 5)); await new Promise(done => setTimeout(done, 50)) }

const { register } = await import('../draw-issue-pane.tsx')
register(on as any)
await handlers['session.start']($, { cwd: '/repo' }, async () => ({}))
await settle(1)
type Row = { number: number; guide: string; pad: string; done: { name: string; line: string }[];
  closed: { title: string; number: number; blockers: { number: number; closed: boolean }[] }[]; lines: { title: string[]; status: string[]; notes: string[]; questions: number; quiet: number[] } }
let lastPane: unknown
// the pieces a draw styles: a link, a pressable button, a colored text, a dim text
const buttons = (node: unknown): Node[] => node == null || typeof node !== 'object' ? [] : Array.isArray(node) ? node.flatMap(buttons)
  : [...((node as Node).type === 'Button' && (node as Node).props?.label === undefined ? [node as Node] : []), ...buttons((node as Node).props?.children)]
const styled = (node: unknown): string[] => {
  if (node == null || typeof node !== 'object') return []
  if (Array.isArray(node)) return node.flatMap(styled)
  const { type, props } = node as { type?: string; props?: { color?: string; strikethrough?: boolean; dimColor?: boolean; label?: string; children?: unknown } }
  const own = type === 'Link' ? [`link ${props?.label}`] : type === 'Button' ? (props?.label === undefined ? [`press ${text(node).trim()}`] : [])
    : props?.strikethrough ? [`strike ${text(node).trim()}`] : props?.color ? [`color:${props.color} ${text(node).trim()}`] : props?.dimColor ? [`dim ${text(node).trim()}`] : []
  return [...own, ...(type === 'Link' ? [] : styled(props?.children))]
}
const differ = (what: string) => { console.log(`differ: ${what}`); process.exit(1) }
const FOLD = 2  // the pane's ` +` or ` -` at a row's first line's end
for (const width of [30, 40, 60, 88]) {
  const laid = String(width - FOLD)
  const rows = JSON.parse(listed('--json', '--width', laid)) as Row[]
  // every row unfolded, since a folded row draws too little to compare with the listing
  store.set('expanded', rows.map(row => row.number))
  // the first draw at a new width reads the board again for it, and the draw after that read shows the rows
  const before = reads
  await draw({ bodyColumns: width })
  await settle(before + 1)
  const pane = await draw({ bodyColumns: width })
  lastPane = pane
  const drawn = children(pane).filter(child => (child as Node).type === 'Box')
  if (drawn.length !== rows.length) differ(`width ${width}: ${drawn.length} rows drawn, ${rows.length} listed`)
  const printed = listed('--width', laid).split('\n')
  let at = 0
  rows.forEach((row, k) => {
    const heading = [row.guide + row.lines.title[0], ...[...row.lines.title.slice(1), ...row.lines.status, ...row.lines.notes].map(line => row.pad + line)]
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
    const owed = [...row.done.map(item => item.line), ...row.closed.map(task => task.title)].filter(Boolean)
    const missing = owed.find(piece => !folded.includes(piece))
    if (missing !== undefined) differ(`width ${width}: #${row.number} unfolded lacks ${JSON.stringify(missing)}`)
    const arrow = [...heading, folded].join(' ').match(/[←→]/)
    if (arrow) differ(`width ${width}: #${row.number} draws the arrow ${arrow[0]}, which says nothing of which way a link binds`)
    const openNumbers = (task: Row['closed'][number]) => task.blockers.filter(blocker => !blocker.closed).map(blocker => `#${blocker.number}`)
    const named = row.closed.find(task => folded.includes(`#${task.number} ${task.title} blocked by`) !== (openNumbers(task).length > 0)
      || (openNumbers(task).length > 0 && !folded.includes(`#${task.number} ${task.title} blocked by ${openNumbers(task).join(' ')}`)))
    const pressable = buttons(drawn[k]).find(button => text(button).includes('(blocked'))
    if (pressable) differ(`width ${width}: #${row.number}'s \`(blocked by …)\` sits in a pressable button, which folds the row`)
    if (named) differ(`width ${width}: #${row.number}'s closed #${named.number} shows \`blocked by\` only with its open blockers, and none when every blocker is closed`)
  })
}
if (process.argv.includes('--press')) {
  // every row folded, since the scenarios press a row open to see what it adds; then each `--press <text>` presses every button whose text holds it, and the rows' drawn lines print as `<number>|<line>`
  const width = 88
  const rows = JSON.parse(listed('--json', '--width', String(width - FOLD))) as Row[]
  store.set('expanded', [])
  const taps = process.argv.flatMap((argument, k) => argument === '--press' ? [process.argv[k + 1]] : []).filter(tap => tap !== 'none')
  const rowsOf = (pane: unknown) => children(pane).filter(child => (child as Node).type === 'Box')
  for (const tap of taps) for (const button of buttons(rowsOf(await draw({ bodyColumns: width })))) {
    if (text(button).includes(tap)) await (button.props as { onPress?: () => unknown }).onPress?.()
  }
  await settle(reads)
  rowsOf(await draw({ bodyColumns: width })).forEach((drawn, k) => children(drawn).forEach(line => console.log(`${rows[k].number}|${text(line)}`)))
} else if (process.argv[3] === '--styled') console.log(styled(lastPane).join('\n'))
else console.log('same')
