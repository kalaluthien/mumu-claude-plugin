import { describe, expect, mock, test } from 'claude-code/testing'

const manager = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'teamwork-manager' }] } })
const worker = JSON.stringify({ result: { agents: [{ pane_id: 'p1', name: 'x-worker' }] } })
const board = JSON.stringify([{ number: 1, title: 'First issue', url: 'https://example.test/1', wait: 'waits on owner', tasks: [] }])
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
      expect(await ui.find({ type: 'Text', text: /#1/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /First issue/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /waits on owner/ })).toBeDefined()
      await ui.unmount()
    }
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
