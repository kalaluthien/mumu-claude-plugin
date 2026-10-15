import { describe, expect, mock, test } from 'claude-code/testing'

const manager = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager' }] } })
const worker = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'x-worker' }] } })
const issue = (number: number, kind: 'backlog' | 'task', fields: object = {}) =>
  ({ number, title: `Issue ${number}`, url: `https://example.test/${number}`, kind, holder: '', wait: '', progress: '', goal: '', done: [], tasks: [], ...fields })
const task = issue(2, 'task', { title: 'Second issue', holder: 'x-worker', wait: 'waits on the owner', goal: 'Do the thing', done: ['[check] it prints'] })
const board = JSON.stringify([issue(1, 'backlog', { title: 'First issue', progress: '1 open · 0 landed', tasks: [task] })])
const long = (word: string) => `${word} `.repeat(60).slice(0, 300)
const PANE = { title: 'Issues', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} } as const

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

  test('a successor manager opens the issues pane under its starting name', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    const opened: string[] = []
    on('process.run', async () => ok(JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager-next' }] } })))
    on('process.spawn', async function* () { return { value: { code: 0, signal: null } } })
    on('ui.open', async (_$, e) => { opened.push(e.id); return { value: { isPlaced: true as const } } })
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
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
      for (const [label, url, title] of [['backlog#1', 'https://example.test/1', 'First issue'], ['task#2', 'https://example.test/2', 'Second issue']]) {
        // the link leads its row, so cutting the row at the pane's width cuts the title, never the link
        const row = await ui.find({ type: 'Text', text: new RegExp(`^${label} ${title}$`) })
        const kind = await ui.find({ type: 'Text', text: new RegExp(`^${label}$`) })
        expect(row!.children[0]).toMatchObject({ type: 'Text', props: { color: kind!.props.color } })
        expect(kind!.children[0]).toMatchObject({ type: 'Link', props: { href: url, label } })
      }
      for (const line of [/^Do the thing$/, /^• \[check\] it prints$/, /^x-worker · waits on the owner$/, /^1 open · 0 landed$/])
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
    const ui = await mounted($, on, [issue(1, 'backlog', { tasks: [issue(2, 'task', { title, goal, done: [done], holder: 'x-worker' })] })])
    for (const whole of [title, goal, done]) {
      const found = (await ui.findAll({ type: 'Text', text: whole })).at(-1)
      expect(found?.props.wrap).toBe('wrap')
      expect(found?.text).toContain(whole)
    }
    const texts = await ui.findAll({ type: 'Text' })
    expect(texts.filter(t => /^(goal|definition-of-done|holder): /.test(t.text) || t.text === 'none')).toEqual([])
  })

  test('kind, holder and a wait on someone each have a colour of their own', async ($, on) => {
    const ui = await mounted($, on, JSON.parse(board))
    const kind = await ui.find({ type: 'Text', text: /^task#2$/ })
    const holder = await ui.find({ type: 'Text', text: /^x-worker$/ })
    const wait = await ui.find({ type: 'Text', text: /^waits on the owner$/ })
    expect(kind?.props.color).toBeDefined()
    expect(holder?.props.color).toBeDefined()
    expect(wait?.props.color).toBeDefined()
    expect(wait?.props.color).not.toBe(holder?.props.color)
  })

  test('pressing an entry folds its goal and criteria, and a second press unfolds them', async ($, on) => {
    const ui = await mounted($, on, JSON.parse(board))
    const shown = async () => [await ui.find({ type: 'Text', text: /^Do the thing$/ }), await ui.find({ type: 'Text', text: /it prints$/ })]
    expect((await shown()).every(Boolean)).toBe(true)
    await ui.press({ key: 'fold-2' })
    expect((await shown()).some(Boolean)).toBe(false)
    expect(await ui.find({ type: 'Text', text: /^Second issue$/ })).toBeDefined()
    await ui.press({ key: 'fold-2' })
    expect((await shown()).every(Boolean)).toBe(true)
  })

  test('backlogs show their progress, each set apart by a border', async ($, on) => {
    const ui = await mounted($, on, [issue(10, 'backlog', { progress: '5 open · 0 landed' }), issue(30, 'backlog', { progress: 'routed to w' }), issue(20, 'backlog', { progress: 'not started' })])
    for (const progress of ['5 open · 0 landed', 'routed to w', 'not started'])
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
