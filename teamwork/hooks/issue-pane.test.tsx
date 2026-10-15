import { describe, expect, mock, test } from 'claude-code/testing'

const manager = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager' }] } })
const worker = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'x-worker' }] } })
const task = { number: 2, title: 'Second issue', url: 'https://example.test/2', kind: 'task', goal: 'Do the thing', done: ['[check] it prints'], holder: 'none, waits on the owner', tasks: [] }
const board = JSON.stringify([{ number: 1, title: 'First issue', url: 'https://example.test/1', kind: 'backlog', goal: 'none', done: [], holder: 'x-worker', tasks: [task] }])
const PANE = { title: 'Issues', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} } as const

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
    expect(ran.some(a => a[0].endsWith('list-issue-board.py') && a[1] === 'teamwork' && a[2] === '--json')).toBe(true)
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'teamwork', surface, component: 'Pane', props: PANE, requestId: 'issues' })
      for (const [label, url, title] of [['backlog#1', 'https://example.test/1', 'First issue'], ['task#2', 'https://example.test/2', 'Second issue']]) {
        // the link leads its row, so cutting the row at the pane's width cuts the title, never the link
        const row = await ui.find({ type: 'Text', text: new RegExp(`^${label} ${title}$`) })
        expect(row.children[0]).toMatchObject({ type: 'Link', props: { href: url, label } })
      }
      for (const line of [/^goal: Do the thing$/, /^- \[check\] it prints$/, /^definition-of-done: none$/, /^holder: none, waits on the owner$/, /^holder: x-worker$/])
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

  test('an attach while the pane is open notes the surface', async ($, on) => {
    mock.env(on, { HERDR_PANE_ID: 'p1', HOME: '/h' })
    on('session.start', async (_$, e) => ({ cwd: e.cwd }))
    on('process.run', async () => ok(manager))
    on('process.spawn', async function* () { return { value: { code: 0, signal: null } } })
    on('ui.open', async () => ({ value: { isPlaced: false as const, reason: 'no surface places panes' } }))
    on('ui.panes', async () => ({ value: [{ id: 'issues', title: 'Issues', isPlaced: false }] } as never))
    const written: Record<string, string> = {}
    on('fs.read', async (_$, e) => { if (!(e.path in written)) throw new Error('ENOENT'); return { value: written[e.path] } as never })
    on('fs.write', async (_$, e) => { written[e.path] = e.text; return { value: undefined } as never })
    on('session.attach', async (_$, e) => ({ clientId: e.clientId }))
    on('session.surfaces', async () => ({ value: ['terminal', 'desktop'] } as never))
    await $.session.start({ cwd: '/w', surface: 'terminal', isInteractive: true })
    await $.session.attach({ surface: 'desktop', clientId: 'desktop:default' })
    for (let i = 0; i < 200 && !/"open"[^]*"attach"|"attach"[^]*"open"/.test(written['/h/.claude/teamwork/pane-surfaces.log'] ?? ''); i++) await Promise.resolve()
    const log = written['/h/.claude/teamwork/pane-surfaces.log'] ?? ''
    expect(log).toMatch(/"event":"open".*no surface places panes/)
    expect(log).toMatch(/"event":"attach","surface":"desktop","clientId":"desktop:default"/)
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

  test('ls marks nothing', async ($, on) => {
    expect(await bash($, on, 'ls')).toEqual([])
  })
})
