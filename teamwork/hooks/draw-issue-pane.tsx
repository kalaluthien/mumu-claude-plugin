import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { BoardIssue } from '../types'

const PANE = 'teamwork-issues'
const RETRY_MS = 120000
const board = atom({ plugin: 'teamwork', key: 'board' } as const, [] as BoardIssue[])
// why the last read failed, empty when it worked; shown so a failed read never looks like an empty board
const failure = atom({ plugin: 'teamwork', key: 'failure' } as const, '')
// whether a read has worked yet, so an empty board never looks like one not read
const loaded = atom({ plugin: 'teamwork', key: 'loaded' } as const, false)
// the entries, goals and criteria the manager unfolded, kept across redraws; every other shows its one line
const expanded = atom({ plugin: 'teamwork', key: 'expanded' } as const, [] as (number | string)[])
// a wait that needs someone stands out; any other, such as `← #n` beside a blocked task, stays dim
const WAIT_COLOR: Record<string, string> = { 'waits on the owner': 'error', 'waits on the manager': 'warning' }
// a write to issues, pull requests, sub-issues or their order, the changes the board shows, so a `gh api` read marks nothing, even one with `-f` and `-X GET`; a global flag may stand before the subcommand (`gh -R o/r issue …`); the body script's gh runs out of sight
const TEAM_CHANGE = /\bedit-issue-body\.py\b|\bgh\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*(?:(issue|pr)\s+(create|comment|edit|close|reopen|merge|review|ready)\b|api\s+(?!graphql)(?!(?:[^;&|\n]*\s)?(-X|--method)[\s=]*GET\b)(?=[^;&|\n]*(\s(-X|--method)[\s=]*(POST|PATCH|PUT|DELETE)\b|\s-[fF]\b|\s--(raw-)?field\b|\s--input\b))[^;&|\n]*\b(issues|sub_issues|dependencies|pulls)\b)/

// a manager's pane and its waiter, once per session; the start directory, since the current one may be a worktree removed since
let startFolder: string | undefined
let watching = false
// the manager's board read, set once it watches, so the issues command reads the board again
let refresh: (() => Promise<void>) | undefined
const openPane = ($: any) => $.ui.open({ id: PANE, title: 'Issues' })
// a plain open of an open id leaves it behind another plugin's tab, and focus may take the prompt's keys, so a hidden pane closes and opens again
async function showPane($: any) {
  if ((await $.ui.panes()).some((pane: { id: string; isShown: boolean }) => pane.id === PANE && !pane.isShown)) await $.ui.close({ id: PANE })
  return openPane($)
}
function watch($: any, name: string) {
  if (watching || !name.endsWith('-manager')) return
  watching = true
  const project = name.slice(0, -'-manager'.length)
  void openPane($).catch(() => undefined)
  // a failed read is tried again after a pause, since the next team change may be far off
  let retry: { cancel: () => void } | undefined
  const load = async () => {
    retry?.cancel()
    try {
      const run = await $.process.run([`${$.plugin.root}/hooks/list-issue-board.py`, project, '--json'], { cwd: startFolder, timeoutMs: 60000 })
      if (run.exitCode === 0) {
        await update($, board, () => JSON.parse(run.stdout) as BoardIssue[])
        await update($, loaded, () => true)
      }
      await update($, failure, () => run.exitCode === 0 ? '' : (run.stderr ?? '').trim() || `the board read exited ${run.exitCode}`)
      if (run.exitCode !== 0) retry = $.clock.after(RETRY_MS, () => void load())
    } catch (error) {  // a failed read must not end the loop, whose end kills the waiter
      await update($, failure, () => `the board read failed: ${error}`).catch(() => undefined)
      retry = $.clock.after(RETRY_MS, () => void load())
    }
  }
  refresh = load
  void (async () => {
    const waiter = $.process.spawn({ argv: [`${$.plugin.root}/hooks/wait-team-change.py`] })
    for await (const piece of waiter) {
      if (!('text' in piece)) break
      await load()
    }
  })()
}

export const register: Register = on => {
  // every team session marks its change, so the manager's waiter wakes without reading GitHub
  on('tool.call', { tool: 'Bash' }, async ($, event, next) => {
    const ran = await next(event)
    if (ran.deny === undefined && !ran.isError && TEAM_CHANGE.test(event.command)) {
      const claudeFolder = (await $.env.get('CLAUDE_CONFIG_DIR')) || `${await $.env.get('HOME')}/.claude`
      await $.process.run(['touch', `${claudeFolder}/teamwork/issues-changed`]).catch(() => undefined)
    }
    return ran
  }).catch(($, event, next) => next(event))  // a failed mark must never fail the command it follows

  on('session.start', async ($, event, next) => {
    const started = await next(event)
    startFolder = event.cwd
    const me = await $.process.run([`${$.plugin.root}/skills/kick-off/scripts/list-sessions.py`, '--me']).catch(() => undefined)
    watch($, me?.stdout.trim() ?? '')  // outside a team's host no session is a manager
    return started
  })

  // a session may take its manager name after it started, as a successor does
  on('command.run', { command: 'rename' }, async ($, event, next) => {
    const ran = await next(event)
    // a typed argument may land garbled, so a herdr name stands in unless the argument is already a manager name
    const typed = event.args.trim()
    const me = typed.endsWith('-manager') ? undefined : await $.process.run([`${$.plugin.root}/skills/kick-off/scripts/list-sessions.py`, '--me']).catch(() => undefined)
    watch($, me?.stdout.trim() || typed)
    return ran
  }).catch(($, event, next) => next(event))  // a failed open must never fail the rename

  // the owner closes the pane by its frame's x; this skill shows it again and reads the board anew, with no model turn
  on('command.run', { command: 'teamwork:issues' }, async ($) => {
    await showPane($)
    await refresh?.()
    return { text: 'Issues pane shown' }
  }).catch(($, event, next) => next(event))  // a failed open falls back to the skill's body

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, event) => {
    const { Box, Text, Link, Button, Markdown } = $.ui.resolve(event)
    const unfolded = new Set(await read($, expanded))
    const toggle = (id: number | string) => () => void update($, expanded, old => old.includes(id) ? old.filter(item => item !== id) : [...old, id])
    const status = (issue: BoardIssue) => [
      issue.progress && <Text dimColor>{issue.progress}</Text>,
      issue.wait && <Text color={WAIT_COLOR[issue.wait.split(' by ')[0]] ?? 'subtle'} weight="semibold">{issue.wait}</Text>,
    ].filter(Boolean).flatMap((node, k) => (k ? [<Text> </Text>, node] : [node]))
    // every blocker, as links: an open one bold, a closed one dim, so what still holds a task stands out
    const after = (task: { url: string; blockers: BoardIssue['blockers'] }) => task.blockers.length > 0 && [<Text dimColor>{' ← '}</Text>, ...task.blockers.map((blocker, k) =>
      <Text dimColor={blocker.closed} weight={blocker.closed ? undefined : 'semibold'}>{k ? ' ' : ''}<Link href={task.url.replace(/\d+$/, String(blocker.number))} label={`#${blocker.number}`} /></Text>)]
    // a goal or a criterion: its name on one line, its details only once a press on that line unfolds them; unfolded, the name goes gray so the white detail reads first,
    // and a blank line ends the detail, so the next name does not read as part of it
    const part = (key: string, name: string, detail: string[]) => (
      <Box flexDirection="column">
        <Button key={`row-${key}`} plain onPress={toggle(key)}><Text wrap="wrap" dimColor={unfolded.has(key)}>{name}</Text></Button>
        {unfolded.has(key) && detail.length > 0 && <Box paddingLeft={2} marginBottom={1} flexDirection="column"><Markdown text={detail.join('\n')} /></Box>}
      </Box>
    )
    const entry = (issue: BoardIssue): JSX.Element => {
      const open = unfolded.has(issue.number)
      const line = status(issue)
      const more = Boolean(issue.goal || issue.detail.length || issue.done.length || issue.next || issue.tasks.length || issue.closed.length)
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            {/* the link first, and the fold mark, kept at full width (flexShrink 0), so a narrow pane wraps the title, never the link */}
            <Box flexShrink={0}>
              <Text color={issue.kind === 'backlog' ? 'merged' : 'claude'} weight="semibold"><Link href={issue.url} label={`#${issue.number}`} /></Text>
              <Text> </Text>
            </Box>
            {/* the whole rest of the row folds; a Button holds only Text, so no link sits in it */}
            <Button key={`row-${issue.number}`} plain onPress={toggle(issue.number)}>
              <Text wrap="wrap" weight="semibold">{issue.title}</Text>
              {line.length > 0 && <Text> </Text>}
              {line}
            </Button>
            {/* a blocker is a link, so it sits outside the Button, last in the row as the wait was */}
            {after(issue)}
            {/* only a box folds by a mark, a + or - at its top-right */}
            <Box flexGrow={1} />
            <Box flexShrink={0}>
              <Button key={`fold-${issue.number}`} plain dimColor label={open ? ' -' : ' +'} onPress={toggle(issue.number)} />
            </Box>
          </Box>
          {/* the holder on a line of its own, so a long title never pushes it off the row */}
          {issue.holder && <Box paddingLeft={2}><Text color="suggestion">{issue.holder}</Text></Box>}
          <Box paddingLeft={2} flexDirection="column">
            {/* every entry folds alike, so an empty one says so when unfolded */}
            {open && !more && <Text dimColor>(empty)</Text>}
            {open && issue.goal && <Markdown text={issue.goal} />}
            {/* the title sums a task up, so its goal is detail, folded */}
            {open && issue.detail.length > 0 && part(`goal-${issue.number}`, 'see detail', issue.detail)}
            {open && issue.done.map((criterion, k) => part(`done-${issue.number}-${k}`, [criterion.met === null ? '' : criterion.met ? '[x]' : '[ ]', criterion.kind && `(${criterion.kind})`, criterion.name].filter(Boolean).join(' '), criterion.detail ? [criterion.detail] : []))}
            {open && issue.next && <Text wrap="wrap">{`next step: ${issue.next}`}</Text>}
            {open && issue.tasks.map(task => framed(task))}
            {/* closed tasks after the open ones, dim and newest first, so what landed last stays in view */}
            {open && issue.closed.length > 0 && <Box marginTop={1} flexDirection="column">{issue.closed.map(task => <Text wrap="wrap" dimColor><Link href={task.url} label={`#${task.number}`} />{' '}<Text strikethrough={task.stopped}>{task.title}</Text>{after(task)}</Text>)}{issue.earlier && <Text dimColor>…</Text>}</Box>}
          </Box>
        </Box>
      )
    }
    // a border sets each backlog and each task apart from the next
    const framed = (issue: BoardIssue) => <Box borderStyle="round" borderDimColor paddingX={1}>{entry(issue)}</Box>
    const list = await read($, board)
    const error = await read($, failure)
    const empty = (await read($, loaded)) ? 'The board has no open issues.' : 'No board read yet.'
    return (
      <Box flexDirection="column">
        {error && <Text wrap="wrap" color="error" weight="semibold">{`Board read failed${list.length > 0 ? ' (showing the last good board)' : ''}: ${error}`}</Text>}
        {list.length === 0 && error ? null : list.length === 0 ? <Text dimColor>{empty}</Text> : list.map(framed)}
      </Box>
    )
  })
}
