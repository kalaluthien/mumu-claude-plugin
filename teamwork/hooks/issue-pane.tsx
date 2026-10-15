import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { BoardIssue } from '../types'

const PANE = 'issues'
const board = atom({ plugin: 'teamwork', key: 'board' } as const, [] as BoardIssue[])
// the entries the manager folded to their link line, kept across redraws
const collapsed = atom({ plugin: 'teamwork', key: 'collapsed' } as const, [] as number[])
// a wait that needs someone stands out; one blocked by an issue only waits
const WAIT_COLOR: Record<string, string> = { 'waits on the owner': 'error', 'waits on the manager': 'warning', 'no holder': 'subtle', blocked: 'subtle' }
// a write to issues, sub-issues or their order, the changes the board shows; the body script's gh runs out of sight
const TEAM_CHANGE = /\bedit-issue-body\.py\b|\bgh\s+(issue|pr)\s+(create|comment|edit|close|reopen|merge)\b|\bgh\s+api\b.*\b(issues|sub_issues|dependencies)\b/

// a manager's pane and its waiter, once per session; the start directory, since the current one may be a worktree removed since
let startDir: string | undefined
let watching = false
function watch($: any, name: string) {
  if (watching || !name.endsWith('-manager')) return
  watching = true
  const project = name.slice(0, -'-manager'.length)
  void $.ui.open({ id: PANE, title: 'Issues' }).catch(() => undefined)
  void (async () => {
    const waiter = $.process.spawn({ argv: [`${$.plugin.root}/hooks/wait-team-change.py`] })
    for await (const piece of waiter) {
      if (!('text' in piece)) break
      try {
        const run = await $.process.run([`${$.plugin.root}/hooks/list-issue-board.py`, project, '--json'], { cwd: startDir, timeoutMs: 60000 })
        if (run.exitCode === 0) await update($, board, () => JSON.parse(run.stdout) as BoardIssue[])
      } catch {}  // a failed read must not end the loop, whose end kills the waiter
    }
  })()
}

export const register: Register = on => {
  // every team session marks its change, so the manager's waiter wakes without reading GitHub
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError && TEAM_CHANGE.test(e.command)) {
      const home = await $.env.get('HOME')
      await $.process.run(['touch', `${home}/.claude/teamwork/issues-changed`]).catch(() => undefined)
    }
    return ran
  }).catch(($, e, next) => next(e))  // a failed mark must never fail the command it follows

  on('session.start', async ($, e, next) => {
    const started = await next(e)
    startDir = e.cwd
    const pane = await $.env.get('HERDR_PANE_ID')
    const listed = await $.process.run(['herdr', 'agent', 'list']).catch(() => undefined)
    try {
      watch($, JSON.parse(listed?.stdout ?? '').result.agents.find((a: { pane_id: string }) => a.pane_id === pane)?.name ?? '')
    } catch {}  // outside herdr no session is a manager
    return started
  })

  // a session may take its manager name after it started, as a successor does
  on('command.run', { command: 'rename' }, async ($, e, next) => {
    const ran = await next(e)
    watch($, e.args.trim())
    return ran
  }).catch(($, e, next) => next(e))  // a failed open must never fail the rename

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Link, Button } = $.ui.resolve(e)
    const folded = new Set(await read($, collapsed))
    const toggle = (n: number) => () => void update($, collapsed, old => old.includes(n) ? old.filter(x => x !== n) : [...old, n])
    const status = (i: BoardIssue) => [
      i.progress && <Text dimColor>{i.progress}</Text>,
      i.kind === 'task' && i.holder && <Text color="suggestion">{i.holder}</Text>,
      i.wait && <Text color={WAIT_COLOR[i.wait.split(' by ')[0]] ?? 'subtle'} weight="semibold">{i.wait}</Text>,
    ].filter(Boolean).flatMap((x, k) => (k ? [<Text dimColor> · </Text>, x] : [x]))
    const entry = (i: BoardIssue): JSX.Element => {
      const open = !folded.has(i.number)
      const line = status(i)
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            <Button key={`fold-${i.number}`} plain dimColor label={open ? '▾' : '▸'} onPress={toggle(i.number)} />
            <Text> </Text>
            {/* the link first, so a narrow pane wraps the title, never the link */}
            <Text wrap="wrap">
              <Text color={i.kind === 'backlog' ? 'merged' : 'claude'} weight="semibold"><Link href={i.url} label={`${i.kind}#${i.number}`} /></Text>
              {' '}
              <Text wrap="wrap" weight="semibold">{i.title}</Text>
            </Text>
          </Box>
          <Box paddingLeft={2} flexDirection="column">
            {line.length > 0 && <Text wrap="wrap">{line}</Text>}
            {open && i.goal && <Text wrap="wrap">{i.goal}</Text>}
            {open && i.done.map(d => <Text wrap="wrap" dimColor>{`• ${d}`}</Text>)}
            {open && i.tasks.map(t => <Box marginTop={1}>{entry(t)}</Box>)}
          </Box>
        </Box>
      )
    }
    const list = await read($, board)
    return (
      <Box flexDirection="column">
        {list.length === 0 ? <Text dimColor>No open issues read yet.</Text> : list.map(i => (
          // a border sets each backlog with its tasks apart from the next
          <Box borderStyle="round" borderDimColor paddingX={1}>{entry(i)}</Box>
        ))}
      </Box>
    )
  })
}
