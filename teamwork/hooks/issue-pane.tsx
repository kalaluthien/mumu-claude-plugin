import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { BoardIssue } from '../types'

const PANE = 'issues'
const board = atom({ plugin: 'teamwork', key: 'board' } as const, [] as BoardIssue[])
// a write to issues, sub-issues or their order, the changes the board shows
const TEAM_CHANGE = /\bgh\s+(issue|pr)\s+(create|comment|edit|close|reopen|merge)\b|\bgh\s+api\b.*\b(issues|sub_issues|dependencies)\b/

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
    const pane = await $.env.get('HERDR_PANE_ID')
    const listed = await $.process.run(['herdr', 'agent', 'list']).catch(() => undefined)
    let name = ''
    try {
      name = JSON.parse(listed?.stdout ?? '').result.agents.find((a: { pane_id: string }) => a.pane_id === pane)?.name ?? ''
    } catch {
      return started  // outside herdr no session is a manager
    }
    if (!name.endsWith('-manager')) return started
    const project = name.slice(0, -'-manager'.length)
    void $.ui.open({ id: PANE, title: 'Issues' })
    void (async () => {
      const waiter = $.process.spawn({ argv: [`${$.plugin.root}/hooks/wait-team-change.py`] })
      for await (const piece of waiter) {
        if (!('text' in piece)) break
        // the start directory, since the session's current one may be a worktree removed since
        try {
          const run = await $.process.run([`${$.plugin.root}/hooks/list-issue-board.py`, project, '--json'], { cwd: e.cwd, timeoutMs: 60000 })
          if (run.exitCode === 0) await update($, board, () => JSON.parse(run.stdout) as BoardIssue[])
        } catch {}  // a failed read must not end the loop, whose end kills the waiter
      }
    })()
    return started
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Link } = $.ui.resolve(e)
    const rows = (issues: BoardIssue[], depth: number): JSX.Element[] =>
      issues.flatMap(i => [
        <Box paddingLeft={depth * 2} flexDirection="column">
          {/* the link first, so cutting the row at the pane's width cuts the title, never the link */}
          <Text wrap="truncate-end">
            <Link href={i.url} label={`${i.kind}#${i.number}`} /> {i.title}
          </Text>
          <Box paddingLeft={2} flexDirection="column">
            <Text dimColor wrap="truncate-end">goal: {i.goal}</Text>
            <Text dimColor>{i.done.length ? 'definition-of-done:' : 'definition-of-done: none'}</Text>
            {i.done.map(d => (
              <Box paddingLeft={2}>
                <Text dimColor wrap="truncate-end">- {d}</Text>
              </Box>
            ))}
            <Text dimColor wrap="truncate-end">holder: {i.holder}</Text>
          </Box>
        </Box>,
        ...rows(i.tasks, depth + 1),
      ])
    const list = await read($, board)
    return (
      <Box flexDirection="column">
        {list.length === 0 ? <Text dimColor>No open issues read yet.</Text> : rows(list, 0)}
      </Box>
    )
  })
}
