import { describe, expect, mock, test } from 'claude-code/testing'

const manager = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager' }] } })
const worker = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'x-worker' }] } })
const issue = (number: number, kind: 'backlog' | 'task', fields: object = {}) =>
  ({ number, title: `Issue ${number}`, url: `https://example.test/${number}`, kind, holder: '', wait: '', progress: '', goal: '', detail: [], done: [], next: '', tasks: [], blockers: [], closed: [], earlier: false, ...fields })
const task = issue(2, 'task', { title: 'Second issue', holder: 'x-worker', wait: 'waits on the owner', goal: 'Do the thing', done: [{ kind: '[check]', name: 'it prints', detail: '' }] })
const board = JSON.stringify([issue(1, 'backlog', { title: 'First issue', progress: '1 open, 0 landed', tasks: [task] })])
const long = (word: string) => `${word} `.repeat(60).slice(0, 300)
const PANE = { title: 'Issues', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} } as const

const unfold = async (ui: any, ...numbers: number[]) => { for (const n of numbers) await ui.press({ key: `fold-${n}` }) }
// lets the board's write after its run land before a mount reads it
const settle = async () => { for (let i = 0; i < 50; i++) await Promise.resolve() }
const ok = (stdout: string) => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } })

describe('issue pane', () => {
  test('a manager session opens the issues pane', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const opened: string[] = []
    on('process.run', async () => ok(manager))
    on('process.spawn', async function* () { return { value: { code: 0, signal: null } } })
    on('ui.open', async (_$, e) => { opened.push(e.id); return { value: { isPlaced: true as const } } })
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    expect(opened).toEqual(['issues'])
  })

  test('a session renamed to a manager opens the issues pane', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const opened: string[] = []
    on('process.run', async () => ok(JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager-next' }] } })))
    on('process.spawn', async function* () { return { value: { code: 0, signal: null } } })
    on('ui.open', async (_$, e) => { opened.push(e.id); return { value: { isPlaced: true as const } } })
    on('command.run', async () => ({ text: '' } as never))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    expect(opened).toEqual([])
    await $.command.run({ command: 'rename', args: 'teamwork-manager' } as never)
    await $.command.run({ command: 'rename', args: 'teamwork-manager' } as never)
    expect(opened).toEqual(['issues'])
  })

  test('a worker session opens no pane', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const opened: string[] = []
    on('process.run', async () => ok(worker))
    on('ui.open', async (_$, e) => { opened.push(e.id); return { value: { isPlaced: true as const } } })
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    expect(opened).toEqual([])
  })

  test('a waiter piece reloads the board and the pane shows it', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const ran: string[][] = []
    on('process.run', async (_$, e) => {
      ran.push([...e.argv])
      return ok(e.argv[0] === 'herdr' ? manager : board)
    })
    on('process.spawn', async function* () {
      yield { stream: 'stdout' as const, text: 'changed\n' }
      return { value: { code: 0, signal: null } }
    })
    on('ui.open', async () => ({ value: { isPlaced: true as const } }))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    for (let i = 0; i < 200 && !ran.some(a => a[0].endsWith('list-issue-board.py')); i++) await Promise.resolve()
    await settle()
    expect(ran.some(a => a[0].endsWith('list-issue-board.py') && a[1] === 'teamwork' && a[2] === '--json')).toBe(true)
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'teamwork', surface, component: 'Pane', props: PANE, requestId: 'issues' })
      // the unfolded entries are the plugin's state, so the desktop draws them as the terminal left them
      if (surface === 'terminal') await unfold(ui, 1, 2)
      for (const [label, url, title] of [['#1', 'https://example.test/1', 'First issue'], ['#2', 'https://example.test/2', 'Second issue']]) {
        // the link leads its row, so cutting the row at the pane's width cuts the title, never the link
        const rest = await ui.find({ type: 'Button', key: `row-${label.slice(1)}` })
        const kind = await ui.find({ type: 'Text', text: new RegExp(`^${label}$`) })
        expect(rest!.text).toMatch(new RegExp(`^${title}( |$)`))
        // colour sets the parts apart, so no dot between them
        expect(rest!.text).not.toContain('·')
        expect(kind!.children[0]).toMatchObject({ type: 'Link', props: { href: url, label } })
      }
      for (const line of [/^Goal: Do the thing$/, /^DoD:$/, /^\[check\] it prints$/, /^x-worker$/, /^waits on the owner$/, /^1 open, 0 landed$/])
        expect(await ui.find({ type: 'Text', text: line })).toBeDefined()
      await ui.unmount()
    }
  })

  test('a board run that cannot start does not stop later refreshes', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    let boards = 0
    on('process.run', async (_$, e) => {
      if (e.argv[0] === 'herdr') return ok(manager)
      boards++
      // the session's directory was removed (a worktree the session had cd'ed into)
      if (boards === 1) throw new Error('ENOENT: no such file or directory, posix_spawn')
      return ok(board)
    })
    on('process.spawn', async function* () {
      yield { stream: 'stdout' as const, text: 'changed\n' }
      yield { stream: 'stdout' as const, text: 'changed\n' }
      return { value: { code: 0, signal: null } }
    })
    on('ui.open', async () => ({ value: { isPlaced: true as const } }))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    for (let i = 0; i < 500 && boards < 2; i++) await Promise.resolve()
    await settle()
    expect(boards).toBe(2)
    const ui = await $.ui.mount({ plugin: 'teamwork', surface: 'terminal', component: 'Pane', props: PANE, requestId: 'issues' })
    expect(await ui.find({ type: 'Text', text: /First issue/ })).toBeDefined()
    await ui.unmount()
  })

  test('the board runs in the directory the session started in', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const inits: (string | undefined)[] = []
    on('process.run', async (_$, e) => {
      if (e.argv[0] === 'herdr') return ok(manager)
      inits.push(e.init?.cwd)
      return ok(board)
    })
    on('process.spawn', async function* () {
      yield { stream: 'stdout' as const, text: 'changed\n' }
      return { value: { code: 0, signal: null } }
    })
    on('ui.open', async () => ({ value: { isPlaced: true as const } }))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    for (let i = 0; i < 500 && inits.length < 1; i++) await Promise.resolve()
    expect(inits).toEqual(['/w'])
  })

  const mounted = async ($: any, on: any, list: object[]) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$: any, e: any) => ({ cwd: e.cwd }))
    let runs = 0
    on('process.run', async (_$: any, e: any) => { if (e.argv[0] !== 'herdr') runs++; return ok(e.argv[0] === 'herdr' ? manager : JSON.stringify(list)) })
    on('process.spawn', async function* () {
      yield { stream: 'stdout' as const, text: 'changed\n' }
      return { value: { code: 0, signal: null } }
    })
    on('ui.open', async () => ({ value: { isPlaced: true as const } }))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    for (let i = 0; i < 500 && runs < 1; i++) await Promise.resolve()
    await settle()
    return $.ui.mount({ plugin: 'teamwork', surface: 'terminal', component: 'Pane', props: PANE, requestId: 'issues' })
  }

  test('a long title, goal and criterion wrap whole, with no key labels', async ($, on) => {
    const [title, goal, done] = [long('title'), long('goal'), long('check')]
    const ui = await mounted($, on, [issue(1, 'backlog', { tasks: [issue(2, 'task', { title, goal, done: [{ kind: '[check]', name: done, detail: '' }], holder: 'x-worker' })] })])
    await unfold(ui, 1, 2)
    for (const whole of [title, goal, done]) {
      const found = (await ui.findAll({ type: 'Text', text: whole })).at(-1)
      expect(found?.props.wrap).toBe('wrap')
      expect(found?.text).toContain(whole)
    }
    const texts = await ui.findAll({ type: 'Text' })
    expect(texts.filter(t => /^(goal|definition-of-done|holder): /.test(t.text) || t.text === 'none')).toEqual([])
  })

  test('a goal and each criterion show a name, their details only once unfolded', async ($, on) => {
    const ui = await mounted($, on, [issue(2, 'task', { goal: 'Name it', detail: ['Why it matters'], done: [{ kind: '[check]', name: 'Board prints', detail: 'it runs the board' }] })])
    await unfold(ui, 2)
    for (const line of [/^Goal: Name it$/, /^DoD:$/, /^\[check\] Board prints$/]) expect(await ui.find({ type: 'Text', text: line })).toBeDefined()
    for (const line of [/^Why it matters$/, /^it runs the board$/]) expect(await ui.find({ type: 'Text', text: line })).toBeUndefined()
    await ui.press({ key: 'row-done-2-0' })
    expect(await ui.find({ type: 'Text', text: /^it runs the board$/ })).toBeDefined()
    await ui.press({ key: 'row-goal-2' })
    expect(await ui.find({ type: 'Text', text: /^Why it matters$/ })).toBeDefined()
  })

  test('kind, holder and a wait on someone each have a colour of their own', async ($, on) => {
    const ui = await mounted($, on, JSON.parse(board))
    await unfold(ui, 1)
    const kind = await ui.find({ type: 'Text', text: /^#2$/ })
    const holder = await ui.find({ type: 'Text', text: /^x-worker$/ })
    const wait = await ui.find({ type: 'Text', text: /^waits on the owner$/ })
    expect(kind?.props.color).toBeDefined()
    expect(holder?.props.color).toBeDefined()
    expect(wait?.props.color).toBeDefined()
    expect(wait?.props.color).not.toBe(holder?.props.color)
  })

  test('entries start folded to one row; a press unfolds one, a second folds it', async ($, on) => {
    const ui = await mounted($, on, JSON.parse(board))
    const shown = async () => [await ui.find({ type: 'Text', text: /^Goal: Do the thing$/ }), await ui.find({ type: 'Text', text: /it prints$/ })]
    expect(await ui.find({ type: 'Text', text: /^Second issue$/ })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: /^1 open, 0 landed$/ })).toBeDefined()
    await ui.press({ key: 'fold-1' })
    expect(await ui.find({ type: 'Text', text: /^waits on the owner$/ })).toBeDefined()
    expect((await shown()).some(Boolean)).toBe(false)
    await ui.press({ key: 'fold-2' })
    expect((await shown()).every(Boolean)).toBe(true)
    await ui.press({ key: 'fold-2' })
    expect((await shown()).some(Boolean)).toBe(false)
  })

  test('a backlog unfolds to its closed tasks too, dim, after the open ones', async ($, on) => {
    const ui = await mounted($, on, [issue(1, 'backlog', { tasks: [task], closed: [{ number: 3, title: 'Landed issue', url: 'https://example.test/3', blockers: [] }] })])
    await unfold(ui, 1)
    const row = await ui.find({ type: 'Text', text: /^#3 Landed issue$/ })
    expect(row?.props.dimColor).toBe(true)
    expect(row!.children[0]).toMatchObject({ type: 'Link', props: { href: 'https://example.test/3', label: '#3' } })
  })

  test('an ellipsis sits above the closed tasks when earlier ones are cut', async ($, on) => {
    const ui = await mounted($, on, [issue(1, 'backlog', { earlier: true, closed: [{ number: 3, title: 'Landed issue', url: 'https://example.test/3', blockers: [{ number: 2, closed: true }] }] })])
    await unfold(ui, 1)
    const texts = (await ui.findAll({ type: 'Text' })).map(t => t.text)
    expect(texts.indexOf('…')).toBeLessThan(texts.indexOf('#3 Landed issue ←#2'))
    expect(texts.indexOf('…')).toBeGreaterThan(-1)
  })

  test('every blocker beside a task is a link, a closed one dim, an open one bold', async ($, on) => {
    const ui = await mounted($, on, [issue(4, 'task', { blockers: [{ number: 21, closed: true }, { number: 22, closed: false }] })])
    const links = (await ui.findAll({ type: 'Link' })).map(l => [l.props.label, l.props.href])
    expect(links).toEqual([['#4', 'https://example.test/4'], ['#21', 'https://example.test/21'], ['#22', 'https://example.test/22']])
    const marks = (await ui.findAll({ type: 'Text' })).filter(t => /^,?#2[12]$/.test(t.text)).map(t => [t.props.dimColor, t.props.weight])
    expect(marks).toEqual([[true, undefined], [false, 'semibold']])
  })

  test('a press on the title or status folds the entry, as the arrow does', async ($, on) => {
    const ui = await mounted($, on, [issue(1, 'backlog', { goal: 'The summary' })])
    await ui.press({ key: 'row-1' })
    expect(await ui.find({ type: 'Text', text: /^The summary$/ })).toBeDefined()
    await ui.press({ key: 'row-1' })
    expect(await ui.find({ type: 'Text', text: /^The summary$/ })).toBeUndefined()
  })

  test('an entry with nothing under it unfolds to (empty)', async ($, on) => {
    const ui = await mounted($, on, [issue(20, 'backlog', { progress: 'not started' })])
    expect(await ui.find({ type: 'Text', text: /^\(empty\)$/ })).toBeUndefined()
    await unfold(ui, 20)
    expect(await ui.find({ type: 'Text', text: /^\(empty\)$/ })).toBeDefined()
  })

  test('a backlog shows who holds it and, unfolded, its next step', async ($, on) => {
    const ui = await mounted($, on, [issue(20, 'backlog', { progress: '0 open, 7 landed', holder: 'x-worker', next: 'ask the owner' })])
    expect(await ui.find({ type: 'Text', text: /^x-worker$/ })).toBeDefined()
    await unfold(ui, 20)
    expect(await ui.find({ type: 'Text', text: /^next step: ask the owner$/ })).toBeDefined()
  })

  test('backlogs show their progress, each set apart by a border', async ($, on) => {
    const ui = await mounted($, on, [issue(10, 'backlog', { progress: '5 open, 0 landed' }), issue(30, 'backlog', { progress: 'routed to w' }), issue(20, 'backlog', { progress: 'not started' })])
    for (const progress of ['5 open, 0 landed', 'routed to w', 'not started'])
      expect(await ui.find({ type: 'Text', text: new RegExp(`^${progress}$`) })).toBeDefined()
    const bordered = (await ui.findAll({ type: 'Box' })).filter(b => b.props.borderStyle)
    expect(bordered).toHaveLength(3)
    expect(bordered.map(b => b.text.match(/#(\d+)/)?.[1])).toEqual(['10', '30', '20'])
  })

  const bash = async ($: any, on: any, command: string) => {
    mock.env(on, { HOME: '/h' })
    const ran: string[][] = []
    on('process.run', async (_$: any, e: any) => { ran.push([...e.argv]); return ok('') })
    on('tool.call', { tool: 'Bash' }, async () => ({ result: { stdout: 'done', stderr: '', interrupted: false } } as never))
    await $.tool.call({ tool: 'Bash', command } as never)
    return ran
  }

  test('a team write marks the change', async ($, on) => {
    const ran = await bash($, on, 'gh issue comment 5 --body-file x')
    expect(ran).toContainEqual(['touch', '/h/.claude/teamwork/issues-changed'])
  })

  test('a body edit by its script marks the change', async ($, on) => {
    const ran = await bash($, on, 'teamwork/skills/kick-off/scripts/edit-issue-body.py 5 x.diff "DECIDED: y"')
    expect(ran).toContainEqual(['touch', '/h/.claude/teamwork/issues-changed'])
  })

  test('ls marks nothing', async ($, on) => {
    expect(await bash($, on, 'ls')).toEqual([])
  })
})
