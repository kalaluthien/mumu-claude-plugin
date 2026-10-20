import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { BoardIssue } from '../types'

const PANE = 'teamwork-issues'
const RETRY_MS = 120000
const board = atom({ plugin: 'teamwork', key: 'board' } as const, [] as BoardIssue[])
// why the last read failed, empty when it worked; shown so a failed read never looks like an empty board
const failure = atom({ plugin: 'teamwork', key: 'failure' } as const, '')
// the entries, goals and criteria the manager unfolded, kept across redraws; every other shows its one line
const expanded = atom({ plugin: 'teamwork', key: 'expanded' } as const, [] as (number | string)[])
// a wait that needs someone stands out; any other, such as `← #n` beside a blocked task, stays dim
const WAIT_COLOR: Record<string, string> = { 'waits on the owner': 'error', 'waits on the manager': 'warning' }
// a write to issues, pull requests, sub-issues or their order, the changes the board shows, so a `gh api` read marks nothing, even one with `-f` and `-X GET`; a global flag may stand before the subcommand (`gh -R o/r issue …`); the body script's gh runs out of sight
const TEAM_CHANGE = /\bedit-issue-body\.py\b|\bgh\s+(?:-{1,2}[\w-]+(?:[\s=][^\s-]\S*)?\s+)*(?:(issue|pr)\s+(create|comment|edit|close|reopen|merge|review|ready)\b|api\s+(?!graphql)(?!(?:.*\s)?(-X|--method)[\s=]*GET\b)(?=.*(\s(-X|--method)[\s=]*(POST|PATCH|PUT|DELETE)\b|\s-[fF]\b|\s--(raw-)?field\b|\s--input\b)).*\b(issues|sub_issues|dependencies|pulls)\b)/

// a manager's pane and its waiter, once per session; the start directory, since the current one may be a worktree removed since
let startDir: string | undefined
let watching = false
// the manager's board read, set once it watches, so the issues command reads the board again
let refresh: (() => Promise<void>) | undefined
const openPane = ($: any) => $.ui.open({ id: PANE, title: 'Issues' })
// a plain open of an open id leaves it behind another plugin's tab, and focus may take the prompt's keys, so a hidden pane closes and opens again
async function showPane($: any) {
  if ((await $.ui.panes()).some((p: { id: string; isShown: boolean }) => p.id === PANE && !p.isShown)) await $.ui.close({ id: PANE })
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
      const run = await $.process.run([`${$.plugin.root}/hooks/list-issue-board.py`, project, '--json'], { cwd: startDir, timeoutMs: 60000 })
      if (run.exitCode === 0) await update($, board, () => JSON.parse(run.stdout) as BoardIssue[])
      await update($, failure, () => run.exitCode === 0 ? '' : (run.stderr ?? '').trim() || `the board read exited ${run.exitCode}`)
      if (run.exitCode !== 0) retry = $.clock.after(RETRY_MS, () => void load())
    } catch (err) {  // a failed read must not end the loop, whose end kills the waiter
      await update($, failure, () => `the board read failed: ${err}`).catch(() => undefined)
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

  // the owner closes the pane by its frame's x; this skill shows it again and reads the board anew, with no model turn
  on('command.run', { command: 'teamwork:issues' }, async ($) => {
    await showPane($)
    await refresh?.()
    return { text: 'Issues pane shown' }
  }).catch(($, e, next) => next(e))  // a failed open falls back to the skill's body

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Link, Button, Markdown } = $.ui.resolve(e)
    const unfolded = new Set(await read($, expanded))
    const toggle = (n: number | string) => () => void update($, expanded, old => old.includes(n) ? old.filter(x => x !== n) : [...old, n])
    const status = (i: BoardIssue) => [
      i.progress && <Text dimColor>{i.progress}</Text>,
      i.wait && <Text color={WAIT_COLOR[i.wait.split(' by ')[0]] ?? 'subtle'} weight="semibold">{i.wait}</Text>,
    ].filter(Boolean).flatMap((x, k) => (k ? [<Text> </Text>, x] : [x]))
    // every blocker, as links: an open one bold, a closed one dim, so what still holds a task stands out
    const after = (t: { url: string; blockers: BoardIssue['blockers'] }) => t.blockers.length > 0 && [<Text dimColor>{' ← '}</Text>, ...t.blockers.map((b, k) =>
      <Text dimColor={b.closed} weight={b.closed ? undefined : 'semibold'}>{k ? ' ' : ''}<Link href={t.url.replace(/\d+$/, String(b.number))} label={`#${b.number}`} /></Text>)]
    // a goal or a criterion: its name on one line, its details only once a press on that line unfolds them; unfolded, the name goes gray so the white detail reads first,
    // and a blank line ends the detail, so the next name does not read as part of it
    const part = (key: string, name: string, detail: string[]) => (
      <Box flexDirection="column">
        <Button key={`row-${key}`} plain onPress={toggle(key)}><Text wrap="wrap" dimColor={unfolded.has(key)}>{name}</Text></Button>
        {unfolded.has(key) && detail.length > 0 && <Box paddingLeft={2} marginBottom={1} flexDirection="column"><Markdown text={detail.join('\n')} /></Box>}
      </Box>
    )
    const entry = (i: BoardIssue): JSX.Element => {
      const open = unfolded.has(i.number)
      const line = status(i)
      const more = Boolean(i.goal || i.detail.length || i.done.length || i.next || i.tasks.length || i.closed.length)
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            {/* the link first, and the fold mark, kept at full width (flexShrink 0), so a narrow pane wraps the title, never the link */}
            <Box flexShrink={0}>
              <Text color={i.kind === 'backlog' ? 'merged' : 'claude'} weight="semibold"><Link href={i.url} label={`#${i.number}`} /></Text>
              <Text> </Text>
            </Box>
            {/* the whole rest of the row folds; a Button holds only Text, so no link sits in it */}
            <Button key={`row-${i.number}`} plain onPress={toggle(i.number)}>
              <Text wrap="wrap" weight="semibold">{i.title}</Text>
              {line.length > 0 && <Text> </Text>}
              {line}
            </Button>
            {/* a blocker is a link, so it sits outside the Button, last in the row as the wait was */}
            {after(i)}
            {/* only a box folds by a mark, a + or - at its top-right */}
            <Box flexGrow={1} />
            <Box flexShrink={0}>
              <Button key={`fold-${i.number}`} plain dimColor label={open ? ' -' : ' +'} onPress={toggle(i.number)} />
            </Box>
          </Box>
          {/* the holder on a line of its own, so a long title never pushes it off the row */}
          {i.holder && <Box paddingLeft={2}><Text color="suggestion">{i.holder}</Text></Box>}
          <Box paddingLeft={2} flexDirection="column">
            {/* every entry folds alike, so an empty one says so when unfolded */}
            {open && !more && <Text dimColor>(empty)</Text>}
            {open && i.goal && <Markdown text={i.goal} />}
            {/* the title sums a task up, so its goal is detail, folded */}
            {open && i.detail.length > 0 && part(`goal-${i.number}`, 'see detail', i.detail)}
            {open && i.done.map((d, k) => part(`done-${i.number}-${k}`, [d.met === null ? '' : d.met ? '[x]' : '[ ]', d.kind && `(${d.kind})`, d.name].filter(Boolean).join(' '), d.detail ? [d.detail] : []))}
            {open && i.next && <Text wrap="wrap">{`next step: ${i.next}`}</Text>}
            {open && i.tasks.map(t => framed(t))}
            {/* closed tasks after the open ones, dim and newest first, so what landed last stays in view */}
            {open && i.closed.length > 0 && <Box marginTop={1} flexDirection="column">{i.closed.map(t => <Text wrap="wrap" dimColor><Link href={t.url} label={`#${t.number}`} />{` ${t.title}`}{after(t)}</Text>)}{i.earlier && <Text dimColor>…</Text>}</Box>}
          </Box>
        </Box>
      )
    }
    // a border sets each backlog and each task apart from the next
    const framed = (i: BoardIssue) => <Box borderStyle="round" borderDimColor paddingX={1}>{entry(i)}</Box>
    const list = await read($, board)
    const error = await read($, failure)
    return (
      <Box flexDirection="column">
        {error && <Text wrap="wrap" color="error" weight="semibold">{`Board read failed${list.length > 0 ? ' (showing the last good board)' : ''}: ${error}`}</Text>}
        {list.length === 0 && error ? null : list.length === 0 ? <Text dimColor>No open issues read yet.</Text> : list.map(framed)}
      </Box>
    )
  })
}
