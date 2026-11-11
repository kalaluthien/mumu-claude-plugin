// Render a manager's issue pane from the board in a nodes file, every row unfolded, at body widths 30, 40, 60 and 88, through stand-ins for
// `claude-code` and the JSX runtime, and check it row for row against `list-issue-board.py` laid out for that width less the fold mark: each
// row's title, status, `?`, `◆` and `next step:` lines, guide included, are the lines its `--json` row lays out, in the order `--width` prints them,
// each fits the body with the first line's fold mark, no row ends in a blank line, a title that fits on one line takes one, and an unfolded row with criteria or
// closed parts draws them: `same`, else `differ: <the first difference>`, exit 1.
// With `--styled`, once that holds, it prints instead each piece the last draw (width 88) styles, one per line: `link <label>`, `press <text>` (the button's text as drawn, so a space inside it shows),
// `strike <text>`, `dim <text>` or `color:<name> <text>`.
// With `--search <regex>` and `--press <text>` (each repeatable; `none` presses nothing), it draws the rows at width 88, or at `--columns <n>`, with every row folded, or with `--fresh` as the pane first opens, then types each
// regex into the search box and presses each button whose text holds a given text, in the order given, and prints the drawn lines as `<row number>|<line>`, a yellow background in ⟦ ⟧.
// With no argument, it checks deep-task-nodes.json and deep-decision-nodes.json beside it and prints `PASS` when both are `same`, else `FAIL <file>` for each, exit 1.
// usage: bun teamwork/hooks/fixtures/replay-task-pane.ts [<nodes-file> [--styled | --search <regex>... --press <text>... --columns <n> --fresh]]
import { drawPane, handlers, on, store } from './stand-in-modules.ts'

if (process.argv.length === 2) {
  const failed = ['deep-task-nodes.json', 'deep-decision-nodes.json']
    .filter(file => Bun.spawnSync(['bun', import.meta.path, `${import.meta.dir}/${file}`]).exitCode !== 0)
  console.log([...failed.map(file => `FAIL ${file}`), failed.length ? 'FAIL' : 'PASS'].join('\n'))
  process.exit(failed.length ? 1 : 0)
}
const nodes = process.argv[2]
if (nodes.startsWith('-')) {
  console.error('usage: bun teamwork/hooks/fixtures/replay-task-pane.ts [<nodes-file> [--styled | --search <regex>... --press <text>... --columns <n> --fresh]]')
  process.exit(2)
}
const lister = `${import.meta.dir}/../list-issue-board.py`
const listed = (...args: string[]) => {
  const run = Bun.spawnSync(['python3', lister, '--nodes', nodes, ...args])
  if (run.exitCode !== 0) throw new Error(`list-issue-board.py ${args.join(' ')} exited ${run.exitCode}: ${run.stderr}`)
  return run.stdout.toString()
}

type Node = { type?: string; props?: { children?: unknown; label?: string; text?: string } }
// a link shows its label and Markdown its text; a button's own label is the fold mark, drawn apart from the row's text
let marking = false  // in a scenario run, a yellow background shows as ⟦ ⟧ around its text
const text = (node: unknown): string => marking && (node as Node & { props?: { backgroundColor?: string } })?.props?.backgroundColor === 'yellow' ? `⟦${plain(node)}⟧` : plain(node)
const plain = (node: unknown): string =>
  node == null || typeof node === 'boolean' ? '' : typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(text).join('')
    : (node as Node).type === 'Link' ? (node as Node).props?.label ?? ''
    : (node as Node).type === 'Markdown' ? (node as Node).props?.text ?? ''
    : (node as Node).type === 'Button' && (node as Node).props?.label !== undefined ? '' : text((node as Node).props?.children)
const children = (node: unknown): unknown[] => [(node as Node).props?.children].flat(Infinity).filter(child => child != null && typeof child !== 'boolean')

let reads = 0
const $ = {
  plugin: { root: '/plugin' },
  ui: { open: async () => undefined, close: async () => undefined, panes: async () => [],
        resolve: () => ({ Box: 'Box', Text: 'Text', Link: 'Link', Button: 'Button', Input: 'Input', Markdown: 'Markdown' }) },
  clock: { after: (ms: number, tick: () => void) => { const timer = setTimeout(tick, ms); return { cancel: () => clearTimeout(timer) } } },
  process: {
    run: async (argv: string[]) => {
      if (argv[0].endsWith('list-sessions.py')) return { exitCode: 0, stdout: 'probe-manager\n' }
      if (argv[0].endsWith('print-task-markdown.py')) {
        const run = Bun.spawnSync(['python3', `${import.meta.dir}/../print-task-markdown.py`, '--nodes', nodes, argv[1]])
        return { exitCode: run.exitCode, stdout: run.stdout.toString(), stderr: run.stderr.toString() }
      }
      reads++
      return { exitCode: 0, stdout: listed(...argv.slice(2)), stderr: '' }
    },
    spawn: () => (async function* () { yield { text: 'changed' } })(),
  },
}
const draw = (props: object) => drawPane($, props)
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
  const own = type === 'Link' ? [`link ${props?.label}`] : type === 'Button' ? (props?.label === undefined ? [`press ${text(node)}`] : [])
    : props?.strikethrough ? [`strike ${text(node).trim()}`] : props?.color ? [`color:${props.color} ${text(node).trim()}`] : props?.dimColor ? [`dim ${text(node).trim()}`] : []
  return [...own, ...(type === 'Link' ? [] : styled(props?.children))]
}
const inputs = (node: unknown): Node[] => node == null || typeof node !== 'object' ? [] : Array.isArray(node) ? node.flatMap(inputs)
  : [...((node as Node).type === 'Input' ? [node as Node] : []), ...inputs((node as Node).props?.children)]
const differ = (what: string) => { console.log(`differ: ${what}`); process.exit(1) }
const FOLD = 2  // the pane's ` +` or ` -` at a row's first line's end
const searching = process.argv.includes('--press') || process.argv.includes('--search')
for (const width of searching ? [] : [30, 40, 60, 88]) {
  const laid = String(width - FOLD)
  const rows = JSON.parse(listed('--json', '--width', laid)) as Row[]
  // every row unfolded, since a folded row draws too little to compare with the listing
  store.set('folded', [])
  // the first draw at a new width reads the board again for it, and the draw after that read shows the rows
  const before = reads
  await draw({ bodyColumns: width })
  await settle(before + 1)
  const pane = await draw({ bodyColumns: width })
  lastPane = pane
  const drawn = children(pane).filter(child => (child as Node).type === 'Box' && inputs(child).length === 0)
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
    if (lines.length > heading.length && !folded.trim()) differ(`width ${width}: #${row.number} draws a blank line after its last line`)
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
if (searching) {
  // every row folded, then each `--search <regex>` types its regex into the search box and each `--press <text>` presses every button whose text holds it, in the order given;
  // the drawn lines print as `<row number>|<line>` with a yellow background as ⟦ ⟧, and `0|<line>` for a line that is no row's: `0|input: <typed text>` first
  const width = Number(process.argv[process.argv.indexOf('--columns') + 1]) || 88
  if (!process.argv.includes('--fresh')) store.set('folded', (JSON.parse(listed('--json', '--width', String(width - FOLD))) as Row[]).map(row => row.number))
  marking = true
  const steps = process.argv.flatMap((argument, k) => argument === '--search' || argument === '--press' ? [[argument, process.argv[k + 1]]] : [])
  const rowsOf = (pane: unknown) => children(pane).filter(child => (child as Node).type === 'Box' && inputs(child).length === 0)
  for (const [kind, value] of steps) {
    if (kind === '--search') for (const input of inputs(await draw({ bodyColumns: width }))) await (input.props as { onInput?: (value: string) => unknown }).onInput?.(value)
    else if (value !== 'none') for (const button of buttons(rowsOf(await draw({ bodyColumns: width })))) {
      if (text(button).includes(value)) await (button.props as { onPress?: () => unknown }).onPress?.()
    }
  }
  await settle(reads)
  const pane = await draw({ bodyColumns: width })
  // the pane's first child is the box that holds the search field: `0|box: <border style>` when it has a border, then the field
  const first = children(pane)[0] as Node & { props?: { borderStyle?: string } }
  if (first?.type === 'Box' && inputs(first).length > 0) console.log(`0|box: ${first.props?.borderStyle ?? 'none'}`)
  inputs(pane).forEach(input => console.log(`0|input: ${(input.props as { value?: string }).value}`))
  children(pane).forEach(child => {
    if ((child as Node).type === 'Input' || inputs(child).length > 0) return
    const lines = (child as Node).type === 'Box' ? children(child).map(text) : text(child).split('\n')
    const number = (child as Node).type === 'Box' ? lines[0].replace(/[⟦⟧]/g, '').match(/#(\d+)/)?.[1] ?? '0' : '0'
    lines.forEach(line => console.log(`${number}|${line}`))
  })
} else if (process.argv[3] === '--styled') console.log(styled(lastPane).join('\n'))
else console.log('same')
