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
// the tasks the manager unfolded, kept across redraws; every other shows its title and status
const expanded = atom({ plugin: 'teamwork', key: 'expanded' } as const, [] as number[])
// what the owner typed in the search box, a regular expression; empty is no search, which leaves the folds above as they were
const query = atom({ plugin: 'teamwork', key: 'query' } as const, '')
// the folds a person pressed during one search, kept apart from `expanded` so emptying the box returns the folds as they were before it
const peeked = atom({ plugin: 'teamwork', key: 'peeked' } as const, [] as number[])
// the task whose Markdown the pane shows in place of the list, with the text read for it; null shows the list
const opened = atom({ plugin: 'teamwork', key: 'opened' } as const, null as { number: number; text: string } | null)
// the ` +` or ` -` fold mark at a row's first line's end
const FOLD = 2
// a task's number takes the color of its own state: the owner's answer awaited, a holder, an open blocker, else ready
const NUMBER_COLOR = { owner: 'yellow', held: 'green', blocked: 'red', ready: '#c8c8c8' }
// a wait that needs someone stands out; any other, such as `blocked by #n` beside a blocked task, stays dim
const WAIT_COLOR: Record<string, string> = { 'waits on the owner': 'error', 'waits on the manager': 'warning' }
// a write to a pull request, the change a repository that lands by pull request shows, so a `gh api` read marks nothing, even one with `-f` and `-X GET`; a global flag may stand before the subcommand (`gh -R o/r pr …`); the body script runs out of sight; a GitHub issue is never written, the hook refuses it
const TEAM_CHANGE = /\bedit-issue-body\.py\b|\bgh\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*(?:(pr)\s+(create|comment|edit|close|reopen|merge|review|ready)\b|api\s+(?!graphql)(?!(?:[^;&|\n]*\s)?(-X|--method)[\s=]*GET\b)(?=[^;&|\n]*(\s(-X|--method)[\s=]*(POST|PATCH|PUT|DELETE)\b|\s-[fF]\b|\s--(raw-)?field\b|\s--input\b))[^;&|\n]*\b(pulls)\b)/

// a manager's pane and its waiter, once per session; the start directory, since the current one may be a worktree removed since
let startFolder: string | undefined
let watching = false
// the manager's board read, set once it watches, so the issues command reads the board again
let refresh: (() => Promise<void>) | undefined
// the pane body's width the rows are laid out for, 0 before the pane is drawn; a row laid out for another width wraps a word alone.
// Kept outside state, since a render may not write state, and read again on a clock tick, an event of its own
let laidWidth = 0
let relayout: (() => void) | undefined
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
      const width = laidWidth
      const run = await $.process.run([`${$.plugin.root}/hooks/list-issue-board.py`, project, '--json', ...(width > FOLD ? ['--width', String(width - FOLD)] : [])],
        { cwd: startFolder, timeoutMs: 60000 })
      if (width !== laidWidth) return  // a resize during the read started a read for the new width
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
  relayout = () => { retry?.cancel(); retry = $.clock.after(0, () => void load()) }
  void (async () => {
    const waiter = $.process.spawn({ argv: [`${$.plugin.root}/hooks/wait-team-change.py`] })
    for await (const piece of waiter) {
      if (!('text' in piece)) break
      await load()
    }
  })()
}

type Spans = [number, number][]
// the matches of a pattern in each line of a block of wrapped lines that read as one text: a wrapped line's indent is dropped and a wrap reads as the one space it
// replaced, so a phrase matches at any pane width; `starts` says which later line opens a block of its own
const spansOf = (lines: string[], starts: (line: string) => boolean, pattern: RegExp): Spans[] => {
  const found: Spans[] = lines.map(() => [])
  for (let from = 0; from < lines.length;) {
    let to = from + 1
    while (to < lines.length && !starts(lines[to])) to++
    const parts = lines.slice(from, to).map(line => line.trimStart())
    const begin = parts.map((_, k) => parts.slice(0, k).reduce((sum, part) => sum + part.length + 1, 0))
    for (const match of parts.join(' ').matchAll(pattern)) {
      if (match[0] === '') {  // an empty match keeps its task in the search and paints nothing
        if (!found[from].length) found[from].push([0, 0])
        continue
      }
      const [start, end] = [match.index!, match.index! + match[0].length]
      parts.forEach((part, k) => {
        const [a, b] = [Math.max(start, begin[k]), Math.min(end, begin[k] + part.length)]
        const indent = lines[from + k].length - part.length
        if (b > a) found[from + k].push([a - begin[k] + indent, b - begin[k] + indent])
      })
    }
    from = to
  }
  return found
}
// where a pattern matches in a task's lines: `hidden` is true when a match sits in text a folded task does not draw
const matchesIn = (issue: BoardIssue, pattern: RegExp) => {
  const title = spansOf(issue.lines.title, () => false, pattern)
  const status = spansOf(issue.lines.status, () => true, pattern)
  const notes = spansOf(issue.lines.notes, line => !line.startsWith(' '), pattern)
  const done = issue.done.map(criterion => spansOf([criterion.line], () => true, pattern)[0])
  const closed = issue.closed.map(task => spansOf([`#${task.number} ${task.title}`], () => true, pattern)[0])
  const any = (found: Spans[]) => found.some(spans => spans.length > 0)
  // a decision or a question the lister cut to its width still counts, so a search finds the same tasks at any width; only the drawn part is painted
  const said = (text: string) => (text.match(pattern) ?? []).some(match => match !== '')
  const cut = (issue.questions ?? []).some(said)
  const cutDecision = (issue.decided ?? []).some(decision => said(decision.decision))
  const painted = (found: Spans[]) => found.some(spans => spans.some(([start, end]) => end > start))
  return { title, status, notes, done, closed, found: any(title) || any(status) || any(notes) || any(done) || any(closed) || cut || cutDecision,
           hidden: painted(notes.slice(issue.lines.questions)) || painted(done) || painted(closed) || cutDecision }
}

export const register: Register = on => {
  // every team session marks its change, so the manager's waiter wakes without reading the board
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
    const width = event.props.bodyColumns
    if (width > 0 && width !== laidWidth) {
      laidWidth = width
      relayout?.()
    }
    const { Box, Text, Button, Input, Markdown } = $.ui.resolve(event)
    const unfolded = new Set(await read($, expanded))
    const typed = await read($, query)
    let pattern: RegExp | undefined
    let invalid = ''
    try { pattern = typed ? new RegExp(typed, 'gi') : undefined } catch (error) { invalid = String((error as Error).message ?? error) }  // a bad pattern changes nothing and says so
    const flip = (old: number[], id: number) => old.includes(id) ? old.filter(item => item !== id) : [...old, id]
    // while a search is on a press flips the row on top of what the search opened, and leaves the folds the person kept untouched
    const searching = Boolean(typed)  // a box that holds text, whether or not it is a valid pattern
    const toggle = (id: number) => () => void (searching ? update($, peeked, old => flip(old, id)) : update($, expanded, old => flip(old, id)))
    const pressed = new Set(await read($, peeked))
    // a text with its matched spans on a yellow background, from one offset to another
    const lit = (text: string, spans: Spans, from = 0, to = text.length) => {
      const out: (string | JSX.Element)[] = []
      let at = from
      for (const [start, end] of spans) {
        const [a, b] = [Math.max(start, at), Math.min(end, to)]
        if (b <= a) continue
        if (a > at) out.push(text.slice(at, a))
        out.push(<Text backgroundColor="yellow" color="black">{text.slice(a, b)}</Text>)
        at = b
      }
      if (at < to) out.push(text.slice(at, to))
      return out
    }
    // pressing a task's number reads its Markdown and shows it in place of the list
    const openTask = (number: number) => async () => {
      await update($, opened, () => ({ number, text: 'Reading…' }))
      const run = await $.process.run([`${$.plugin.root}/hooks/print-task-markdown.py`, String(number)], { cwd: startFolder, timeoutMs: 60000 }).catch((error: unknown) => ({ exitCode: 1, stdout: '', stderr: String(error) }))
      // Back may have been pressed during the read, or another number; the late text then has no view to fill
      await update($, opened, old => old?.number === number ? { number, text: run.exitCode === 0 ? run.stdout : `Could not read #${number}: ${(run.stderr ?? '').trim() || `exit ${run.exitCode}`}` } : old)
    }
    // a task's number as a button that opens the task, only the characters a match covers on a yellow background
    const numeral = (number: number, label: string, spans: Spans, color?: string) => {
      const marked = spans.map(([start, end]): [number, number] => [Math.max(start, 0), Math.min(end, label.length)]).filter(([start, end]) => end > start)
      const pieces: JSX.Element[] = []
      let at = 0
      for (const [start, end] of marked) {
        if (start > at) pieces.push(<Text color={color} weight="semibold">{label.slice(at, start)}</Text>)
        pieces.push(<Text backgroundColor="yellow" color="black" weight="semibold">{label.slice(start, end)}</Text>)
        at = end
      }
      if (at < label.length || !pieces.length) pieces.push(<Text color={color} weight="semibold">{label.slice(at)}</Text>)
      return <Button key={`open-${number}`} plain onPress={openTask(number)}>{pieces}</Button>
    }
    // the space after a number, yellow when a match runs over it
    const gap = (spans: Spans, at: number) => <Text backgroundColor={spans.some(([start, end]) => start <= at && end > at) ? 'yellow' : undefined}> </Text>
    // a status line's holder and wait take their colors, its other parts stay dim; a part wrapped over lines is dim, since only a whole part is known
    const status = (issue: BoardIssue, line: string, spans: Spans) => {
      const pieces: { part: string; at: number }[] = []
      for (let rest = line; rest;) {
        const part = [issue.progress, issue.holder, issue.wait].find(name => name && rest.startsWith(name)) ?? rest
        pieces.push({ part, at: line.length - rest.length })
        rest = rest.slice(part.length).replace(/^ /, '')
      }
      return pieces.flatMap(({ part, at }, k) => [k ? gap(spans, at - 1) : null, <Text dimColor={part !== issue.holder && part !== issue.wait}
        color={part === issue.holder ? 'suggestion' : part === issue.wait ? WAIT_COLOR[part] ?? 'subtle' : undefined} weight={part === issue.wait ? 'semibold' : undefined}>{lit(line, spans, at, at + part.length)}</Text>])
    }
    const lead = (text: string) => <Text dimColor>{text}</Text>
    // a manager's or a worker's decision is dim, as the lister marks it in `quiet`
    const note = (issue: BoardIssue, pad: string, line: string, k: number, spans: Spans) =>
      <Text>{lead(pad)}<Text color={line.startsWith('?') ? 'warning' : undefined} dimColor={issue.lines.quiet.includes(k)}>{lit(line, spans)}</Text></Text>
    // a row as list-issue-board.py lays it out for the pane: its guide, then each line it wrapped; the guide is drawn text, so the tree reads at any width it fits.
    // While a search is on, every match is a top-level row with no guide, and one whose match sits in folded text is open
    const row = (issue: BoardIssue): JSX.Element => {
      const found = pattern ? matchesIn(issue, pattern) : undefined
      const [guide, pad] = pattern ? ['', '  '] : [issue.guide, issue.pad]
      const open = searching ? (unfolded.has(issue.number) || Boolean(found?.hidden)) !== pressed.has(issue.number) : unfolded.has(issue.number)
      const more = Boolean(issue.lines.notes.length > issue.lines.questions || issue.done.length || issue.closed.length || issue.earlier)
      const [first, ...rest] = issue.lines.title
      const label = `#${issue.number}`
      const spans = (kind: 'title' | 'status' | 'notes', k: number): Spans => found?.[kind][k] ?? []
      const numberColor = issue.wait === 'waits on the owner' ? NUMBER_COLOR.owner : issue.holder ? NUMBER_COLOR.held
        : issue.blockers.some(blocker => !blocker.closed) ? NUMBER_COLOR.blocked : NUMBER_COLOR.ready
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            {lead(guide)}
            {/* the number's button and the space after it sit outside the title's Button, so its press area and highlight start at the title's first letter */}
            {numeral(issue.number, label, spans('title', 0), numberColor)}
            {gap(spans('title', 0), label.length)}
            <Button key={`row-${issue.number}`} plain onPress={toggle(issue.number)}><Text weight="semibold">{lit(first, spans('title', 0), label.length + 1, issue.lines.held[0])}</Text></Button>
            {/* a wait is quiet text outside the Button, so a press on it does nothing */}
            {issue.lines.held[0] < first.length && <Text dimColor>{lit(first, spans('title', 0), issue.lines.held[0])}</Text>}
            <Box flexGrow={1} />
            {more && <Button key={`fold-${issue.number}`} plain dimColor label={open ? ' -' : ' +'} onPress={toggle(issue.number)} />}
          </Box>
          {rest.map((line, k) => <Text>{lead(pad)}<Text weight="semibold">{lit(line, spans('title', k + 1), 0, issue.lines.held[k + 1])}</Text><Text dimColor>{lit(line, spans('title', k + 1), issue.lines.held[k + 1])}</Text></Text>)}
          {issue.lines.status.map((line, k) => <Text>{lead(pad)}{status(issue, line, spans('status', k))}</Text>)}
          {/* a task folds to its title, status and open questions; opened, it adds every decision newest first, what keeps it open, its criteria and its closed parts, all flat */}
          {issue.lines.notes.map((line, k) => (open || k < issue.lines.questions) && note(issue, pad, line, k, spans('notes', k)))}
          {open && (
            <Box flexDirection="row">
              {lead(pad)}
              <Box flexDirection="column">
                {issue.done.map((criterion, k) => <Text wrap="wrap">{lit(criterion.line, found?.done[k] ?? [])}</Text>)}
                {/* closed parts dim and newest first, so what landed last stays in view */}
                {issue.closed.map((task, k) => {
                  const marked = found?.closed[k] ?? []
                  const head = `#${task.number} `.length
                  return <Box flexDirection="row">{numeral(task.number, `#${task.number}`, marked, 'subtle')}{gap(marked, head - 1)}
                    <Text wrap="wrap" dimColor><Text strikethrough={task.stopped}>{lit(`#${task.number} ${task.title}`, marked, head)}</Text>
                    {task.blockers.some(blocker => !blocker.closed) && <Text> blocked by {task.blockers.filter(blocker => !blocker.closed).map(blocker => `#${blocker.number}`).join(' ')}</Text>}</Text></Box>
                })}
                {issue.earlier && <Text dimColor>…</Text>}
              </Box>
            </Box>
          )}
        </Box>
      )
    }
    // a row that cannot be drawn, such as one read by an older module from fields a newer lister dropped, says so instead of blanking the pane
    const safely = (issue: BoardIssue): JSX.Element => {
      try { return row(issue) } catch (error) { return <Text wrap="wrap" color="error">{`#${issue?.number ?? '?'} could not be drawn: ${error}`}</Text> }
    }
    const task = await read($, opened)
    // the back control at the top left returns to the list, whose folds and search the atoms above kept
    if (task) return (
      <Box flexDirection="column">
        <Box flexDirection="row"><Button key="teamwork-back" plain onPress={() => void update($, opened, () => null)}>← Back</Button></Box>
        <Markdown text={task.text} />
      </Box>
    )
    const list = await read($, board)
    const error = await read($, failure)
    const empty = (await read($, loaded)) ? 'The board has no open issues.' : 'No board read yet.'
    const shown = pattern ? list.filter(issue => { try { return matchesIn(issue, pattern!).found } catch { return true } }) : list
    return (
      <Box flexDirection="column">
        <Box borderStyle="round" paddingX={1}>
          <Input key="teamwork-search" value={typed} placeholder="search by regex" onInput={(value: string) => { void update($, peeked, () => []); void update($, query, () => value) }} onSubmit={() => undefined} />
        </Box>
        {invalid ? <Text wrap="wrap" color="error">{`Not a regular expression, so every task shows: ${invalid}`}</Text> : null}
        {error ? <Text wrap="wrap" color="error" weight="semibold">{`Board read failed${list.length > 0 ? ' (showing the last good board)' : ''}: ${error}`}</Text> : null}
        {list.length === 0 && error ? null : list.length === 0 ? <Text dimColor>{empty}</Text> : shown.length === 0 ? <Text dimColor>No task matches.</Text> : shown.map(safely)}
      </Box>
    )
  })
}
