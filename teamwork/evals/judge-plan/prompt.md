---
max_turns: 30
timeout_seconds: 1200
allowed_tools: [Agent, Bash, Read, Write, Glob, Grep]
runs: 3
---

Three tasks were filed with the plans below, and no work has started on any. gh cannot reach GitHub here, so each plan file opens with what gh shows of its issue, then its body, then its comments. First build the fixture with this one Bash call:

````sh
mkdir -p home/.claude/projects/-Users-hyungmokim-workspace-projects-camera/memory repo repo-371 repo-371/mumu-teamwork/scripts repo-371/mumu-teamwork/skills/kickoff/references repo/paperwork/evals/use-cases repo/paperwork/scripts repo/paperwork/skills/rendering repo/paperwork/skills/rendering/scripts repo/paperwork/tests
cat > plan-379.txt <<'EOF'
# Add stepped UI-diff widgets for changes

issue #379, open, labels: scope:paperwork; blocked by: none; the repository's other open task: #374, in ./plan-374.txt

## Goal

Owner's words (2026-09-30), as said:

> show-me의 변경 점 보여주기 요청이 paperwork:rendering 으로 들어갔을 때 보여주는 것 중에 이렇게 UI 차이를 색이나 질감 및 의사 코드를 활용해서 보여주는 위젯과, 스텝에 따라 보여주는 위젯의 조합으로 만들어질 수 있게 위젯과 매핑과 조합이 준비되도록 paperwork 리드에게 맡겨

When a page shows a change to a UI's behaviour, `paperwork:rendering` builds it from a new `ui-diff` widget (side-by-side panes of labelled rows whose state is told by fill and texture, a status line under each pane, a pseudo-code card with bullets keyed by code chips), played step by step by `page.html`'s existing `slide`. Ship the widget, its Mapping row and the combination.

The owner's example (screenshots of steps 3, 4 and 6 at `~/.claude/uploads/04d478d6-2e56-4206-9ed1-100381bf56e6/{7abe23f2,e8a111ee,30ed6876}-image.jpg`): "Cold open at the bottom: constant estimate vs width-aware", a stepper (Step 3 of 6 "the heights", Step 6 of 6 "the measurement", a slider, Previous/Next) over two side-by-side panes, "constant 96" and "width-aware". Each pane is a scroll viewport of labelled rows (`user 48`, `trace 80`, `prose 80`, a tile strip). Hatched with dashed borders = hidden and measuring; blue fill = measured tiles. Under each pane is a status line: `total 2166 px · strip slot 506 · 6 rows mounted · revealed`. A left card holds pseudo-code (`ResizeObserver → admitMeasuredPartSample → commit`) and bullets keyed by code chips (`left`, `right`, `both`; `lines 1–2`, `line 3`, `strip`). A caption under all of them names the step's point. Seen in the screenshots: a subtitle `Step 3 · the heights`, a step slider with `3 of 6` beside Previous/Next, a scroll bar beside each pane, and three row states: grey hatched with a dashed border (estimated, hidden), blue tiles under a hatch (measured, hidden), solid blue or grey (revealed).

## Definition of done

- D1: [exists] `paperwork/skills/rendering/references/ui-diff.html` exists with a spec comment (anatomy, states, played, keyboard, use when / not when) and a template; `SKILL.md`'s Mapping has one row naming `ui-diff`, slid, for a UI's behaviour before and after a change → `scripts/skill-check.py` prints `pass`
- D2: [test] a new test in `paperwork/tests/` assembles a fixture page with a `data-slide` `ui-diff` of two panes and at least 3 steps and, in a browser, asserts: Next, Back and a step slider move the caption, the step title and the step count; a part with `data-step="k"` shows from step k only; each row state (estimated hidden, measured hidden, revealed) differs from the others in fill pattern or border style, not in colour alone; each pane's status line changes with the step; a code chip in a bullet marks the pane or code line it keys; no `pageerror` → the test passes on head and fails on main (no `ui-diff.html`)
- D3: [test] `scripts/check.py` prints `pass` last on that fixture page at 320 px width, in light and dark themes → passes on head; on main the fixture fails to assemble
- D4: [test] a new eval case under `paperwork/evals/` asks to show a change to a UI's behaviour (the owner's example, in words) and its grader checks the page uses `data-widget="ui-diff"` inside a `data-slide` root and `check.py` passes → `--case <it> --runs 3` passes 3/3 on head; on main it fails for want of the widget

## Comment

DECIDED: the owner's expectations, as the lead read them:

- one new widget, `ui-diff`, in its own `references/ui-diff.html`; the stepper is `page.html`'s existing `slide`, not a new widget, which gains the owner's step slider and step title (`Step 3 · the heights`)
- row state told by texture as well as colour: hatched with a dashed border = hidden or measuring, solid fill = measured
- the pseudo-code card stays within Composition's 3-line pseudocode default unless the step needs more, and quotes real code as `Writing` says
- `~/.claude/skills/show-me` lies outside this repository and is not changed; a show-me ask that reaches `rendering` picks `ui-diff` through the Mapping row

## Comment

DECIDED: the owner's screenshots are output of Cursor's `/visualize` command or skill. Before designing `ui-diff`, search the web for its source or docs (prompt, widget markup, styles); build from what is found, citing its url in the pull request, else from the screenshots alone and say none was found. Copy no code whose licence forbids it.
EOF
cat > plan-374.txt <<'EOF'
# Fix the failing use-cases eval

issue #374, open, labels: scope:paperwork; blocked by: none; the repository's other open task: #379, in ./plan-379.txt

## Goal

The eval case `use-cases` fails on main: `--runs 8` passed 1/8 on main and 1/8 on PR #372's head, check.py reporting "korean English: py tq push" in most failed runs (https://github.com/kalaluthien/mumu-claude-plugin/pull/372#issuecomment-5895136451). Make it pass, by fixing the skill or the case, whichever is wrong.

## Definition of done

- D1: [test] `claude plugin eval` on the `use-cases` case, `--runs 8` → at least 7/8 pass; main gives 1/8
EOF
cat > plan-371.txt <<'EOF'
# Move two camera lessons into teamwork

issue #371, open, labels: none; blocked by: #369 (open), which renames the folder `mumu-teamwork` to `teamwork`; the repository has no other open task

## Goal

Owner, choosing two fixes in camera-lead's memory review: move two lessons kept only as camera memories into the mumu-teamwork plugin, so every project gets them.

- `bash-guard.py`: when it refuses a call, its message says why the whole compound call dropped and to write scratch files in their own call first (now only in camera memory `pitfall-guard-drops-whole-command.md`).
- The rule for writing a `## Definition of done`: every `[test]` criterion fails on main for a named reason; no criterion only runs a guard that already passes on main, such as `check-spec`, a build or `pgrep` (now only in camera memory `feedback-criteria-fail-on-main.md`).

## Definition of done

- D1: [test] a new test in the plugin's `tests/` runs `bash-guard.py` on a compound Bash call that writes a scratch file and runs a refused command → its refusal message says the whole call was dropped, the file included, and to write the file in its own call first; fails on main because today's message says neither
- D2: [exists] the lead playbook's Filing section → a line saying each `[test]` criterion fails on main for a reason the task names, and no criterion only runs a check that already passes on main (a build, a spec guard, `pgrep`, the scope's checks)
- D3: [exists] `~/.claude/projects/-Users-hyungmokim-workspace-projects-camera/memory/` → neither `pitfall-guard-drops-whole-command.md` nor `feedback-criteria-fail-on-main.md`, nor their `MEMORY.md` lines, once D1 and D2 have merged; the guard's other refusal (a routine script named beside other words) stays in camera memory unless the new message covers it

## Comment

DECIDED:

- Owner's expectation: both camera lessons reach every project through the plugin, and leave camera memory once they do.
- Waits on #369, which renames `mumu-teamwork/` to `teamwork/` and rewrites the files this task touches; the worker builds on the renamed folder.
- One more case for D2: the judge flagged the same kind of criterion on #369 (https://github.com/kalaluthien/mumu-claude-plugin/issues/369#issuecomment-5892909809).
EOF
cat > repo/FILES.txt <<'EOF'
gates.json
paperwork/.claude-plugin/plugin.json
paperwork/evals/chat-answer/graders/no-writing.md
paperwork/evals/chat-answer/graders/not-loaded.md
paperwork/evals/chat-answer/prompt.md
paperwork/evals/nested-chapters/graders/formal.md
paperwork/evals/nested-chapters/graders/page.md
paperwork/evals/nested-chapters/prompt.md
paperwork/evals/pr-body/graders/loaded.md
paperwork/evals/pr-body/graders/no-rendering.md
paperwork/evals/pr-body/prompt.md
paperwork/evals/trend-chart/graders/chart.md
paperwork/evals/trend-chart/graders/formal.md
paperwork/evals/trend-chart/graders/numbers.md
paperwork/evals/trend-chart/prompt.md
paperwork/evals/use-cases/graders/formal.md
paperwork/evals/use-cases/graders/loaded.md
paperwork/evals/use-cases/graders/no-writing.md
paperwork/evals/use-cases/graders/two-use-cases.md
paperwork/evals/use-cases/prompt.md
paperwork/scripts/run-evals.py
paperwork/skills/rendering/SKILL.md
paperwork/skills/rendering/references/artifact.md
paperwork/skills/rendering/references/chart.html
paperwork/skills/rendering/references/controls.html
paperwork/skills/rendering/references/diagram.html
paperwork/skills/rendering/references/filter.html
paperwork/skills/rendering/references/katex.css
paperwork/skills/rendering/references/page.html
paperwork/skills/rendering/references/rubric.md
paperwork/skills/rendering/references/source.html
paperwork/skills/rendering/scripts/assemble.py
paperwork/skills/rendering/scripts/check.py
paperwork/skills/rendering/scripts/grade.py
paperwork/skills/rendering/scripts/skill-check.py
paperwork/skills/writing/SKILL.md
paperwork/tests/pages/dream-drawn.html
paperwork/tests/pages/dream.html
paperwork/tests/pages/math.html
paperwork/tests/pages/overflow.html
paperwork/tests/pages/widgets.html
paperwork/tests/rubric-pages/cache-proposal-1.html
paperwork/tests/rubric-pages/cache-proposal-2.html
paperwork/tests/rubric-pages/cache-proposal-3.html
paperwork/tests/rubric-pages/ci-report-1.html
paperwork/tests/rubric-pages/ci-report-2.html
paperwork/tests/rubric-pages/ci-report-3.html
paperwork/tests/rubric-pages/prompts.json
paperwork/tests/rubric-pages/queue-explainer-1.html
paperwork/tests/rubric-pages/queue-explainer-2.html
paperwork/tests/rubric-pages/queue-explainer-3.html
paperwork/tests/rubric/academic-ioannidis.md
paperwork/tests/rubric/answer-key.json
paperwork/tests/rubric/interactive-cache-size.html
paperwork/tests/rubric/interactive-latency-weak.html
paperwork/tests/rubric/interactive-signups.html
paperwork/tests/rubric/interactive-tiny-queue-interaction-weakened.html
paperwork/tests/rubric/interactive-tiny-queue.html
paperwork/tests/rubric/technical-sqlite-structure-weakened.md
paperwork/tests/rubric/technical-sqlite-text-weakened.md
paperwork/tests/rubric/technical-sqlite.md
paperwork/tests/rubric/technical-weak-readme.md
paperwork/tests/rubric/textbook-think-python.md
paperwork/tests/test_chart.py
paperwork/tests/test_diagram.py
paperwork/tests/test_evals.py
paperwork/tests/test_grade.py
paperwork/tests/test_page.py
paperwork/tests/test_rubric.py
paperwork/tests/test_run_evals.py
paperwork/tests/test_scripts.py
EOF
cat > repo/gates.json <<'EOF'
{
  "every": ["judge", "*/tests/test_*.py", "*/evals/*"],
  "rules": [
    {"paths": ["*/bin/**", "*/lib/**", "*/scripts/**", "*/monitors/**", "*/tests/**"], "gates": ["judge", "{0}/tests/test_*.py"]},
    {"paths": ["*/evals/*/**"], "gates": ["judge", "{0}/tests/test_*.py", "{0}/evals/{1}"]},
    {"paths": ["*/skills/**", "*/agents/**", "*/hooks/**", "*/.claude-plugin/**"], "gates": ["judge", "{0}/tests/test_*.py", "{0}/evals/*"]},
    {"paths": ["AGENTS.md", "CLAUDE.md"], "gates": ["judge", "teamwork/tests/test_graph.py"]},
    {"paths": [".gitignore", "scripts/*"], "gates": ["judge"]}
  ]
}
EOF
cat > repo/paperwork/skills/rendering/SKILL.md <<'EOF'
## Mapping

A widget exists only where this skill tuned, combined or made one; everything
else is plain HTML the skin styles. The content picks the widget, one rule per
row; a new row names a file in `references/` and its kind, and
`scripts/skill-check.py` fails on any other. Data is drawn only by the `chart`
widget, with no chart library. On a page, `check.py` fails a skipped row: four
files or more named by path in `<code>` with no `file-tree`, or a flow drawn in
text with arrows (→, ▶) with no `use-case`.

| when the content is | widget |
| --- | --- |
| a software system's structure: files, modules, their roles | `diagram` `file-tree`, first on the page |
| a structure before and after a change: what it adds, modifies and removes | `diagram` `file-tree`, slid |
| who calls the system and what it calls: actors, entry points, boundaries | `diagram` `system-context` |
| behaviour: what happens in one use case: a request the reader follows call by call, in one still figure | `diagram` `use-case`, one per use case |
| things and the links between them: tasks and what blocks them, sessions and who waits on whom; what a node reaches | `diagram` `network`, 9 nodes at most |
| values compared across categories: which is largest, by how much | `chart` `bar` |
| change over time: a trend, a rise, a fall | `chart` `line` |
| many items the reader narrows to the few they need, by a tag or a word: rows, a list, cards | `filter` |
| a result that follows inputs the reader moves: a formula, a setting and its effect | `controls` |
| where a figure's, a table's or a claim's facts come from, and what they came through | `source`, under it |
EOF
cat > repo/paperwork/skills/rendering/scripts/check.py <<'EOF'
#!/usr/bin/env python3
"""Check an Artifact page in headless Chrome, printing one line per check then `pass` or `FAIL`;
with --svg, write each figure as a standalone SVG instead.

usage: check.py <page.html> [--svg <out dir>]. Exit 0 pass or written, 1 FAIL or no figure, 2 could not run.
"""
...
def korean(page):
    out = []
    if page["lang"] != "ko":
        out.append(f'lang is "{page["lang"]}", not "ko"')
    for text, cell in [(t, False) for t in page["text"]] + [(t, True) for t in page["cells"]]:
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            out += [f"English: {m.group(0)}" for m in ENGLISH.finditer(line)]
            out += [f"plain ending: {s.strip()}" for s in SENTENCE.findall(line) if plain(s.strip())
                    and not (cell and s.strip()[-1] not in ".!?")]
    out += [f"ASCII arrow: {t}" for t in page["ascii"]]
    out += [f"sentence heading: {h}" for h in page["headings"] if SENTENCE_HEADING.search(h)]
    return out

EOF
cat > repo/paperwork/tests/test_scripts.py <<'EOF'
"""The skill's scripts: each passes the real skill and a good page, and each check fails the copy that breaks it.

Run: uvx --with playwright pytest paperwork/tests -q
"""
...
SKILL = ROOT / "skills" / "rendering"
REFS = SKILL / "references"
CHECK, SKILL_CHECK = SKILL / "scripts" / "check.py", SKILL / "scripts" / "skill-check.py"
ASSEMBLE = SKILL / "scripts" / "assemble.py"
...
def gallery():
    head, sections = [], []
    for f in sorted(REFS.glob("*.html")):
        if f.stem == "page":
            continue
        blocks, body = parts(f.read_text())
        head += blocks
...
class Widgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = widgets_page()

    def test_page_with_every_new_part_passes(self):
        code, out = check(self.page)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
        # its width with or without a scrollbar, as a late hashchange may hide chapters again
EOF
cat > repo/paperwork/scripts/run-evals.py <<'EOF'
#!/usr/bin/env python3
"""Run the plugin's evals, then grade the page of each page case's run with check.py outside the eval sandbox.

usage: run-evals.py [claude plugin eval options, --json <path> included]
Headless Chrome cannot start inside the sandbox, which denies binding its profile's socket, so a page case, one whose
graders read an .html file, gets a `check.py` grader here: the run's directory is kept, check.py runs on the page the
run wrote, and the run passes only when check.py does. Each run's verdict is printed, the kept directories removed, and
the result, with these graders, written to the --json path when one is given.
Exit 0 every run passed, 1 a run failed or scored below the threshold, 2 the eval could not run.
"""
EOF
cat > repo/paperwork/evals/use-cases/prompt.md <<'EOF'
---
max_turns: 16
timeout_seconds: 420
allowed_tools: [Skill, Read, Write, Bash]
---

In our tool `tiny-queue`, `tq push <job>` (in `cli.py`) stores a job in the SQLite file `jobs.db` through `queue/store.py`; `queue/worker.py` takes the oldest job, runs it and marks it done or failed; `queue/retry.py` puts a failed job back, at most 3 times.

Show what happens in two use cases - a user pushes a job with `tq push`, and a worker retries a failed job - as a page saved to `flows.html` in the current directory.
EOF
cat > repo-371/FILES.txt <<'EOF'
checks.json
mumu-teamwork/.claude-plugin/plugin.json
mumu-teamwork/agents/judge.md
mumu-teamwork/agents/lead.md
mumu-teamwork/agents/worker.md
mumu-teamwork/bin/check-scope.py
mumu-teamwork/bin/decision-post.py
mumu-teamwork/bin/default-branch-guard.sh
mumu-teamwork/bin/lead-name.py
mumu-teamwork/bin/lead-start.py
mumu-teamwork/bin/pr-merge.py
mumu-teamwork/bin/session-close.py
mumu-teamwork/bin/worker-start.py
mumu-teamwork/evals/handoff-lead/graders/no-handoff.md
mumu-teamwork/evals/handoff-lead/prompt.md
mumu-teamwork/evals/handoff-plain/graders/fires.md
mumu-teamwork/evals/handoff-plain/prompt.md
mumu-teamwork/evals/handoff-promote-lead/graders/no-handoff.md
mumu-teamwork/evals/handoff-promote-lead/prompt.md
mumu-teamwork/evals/handoff-promote-worker/graders/no-handoff.md
mumu-teamwork/evals/handoff-promote-worker/prompt.md
mumu-teamwork/evals/handoff-promote/graders/fires.md
mumu-teamwork/evals/handoff-promote/prompt.md
mumu-teamwork/evals/handoff-words-absent/graders/no-issue.md
mumu-teamwork/evals/handoff-words-absent/graders/starts.md
mumu-teamwork/evals/handoff-words-absent/prompt.md
mumu-teamwork/evals/handoff-words-live/graders/no-issue.md
mumu-teamwork/evals/handoff-words-live/graders/no-start.md
mumu-teamwork/evals/handoff-words-live/graders/prompts.md
mumu-teamwork/evals/handoff-words-live/prompt.md
mumu-teamwork/evals/lead/graders/routed.md
mumu-teamwork/evals/lead/prompt.md
mumu-teamwork/evals/resume/graders/routed.md
mumu-teamwork/evals/resume/prompt.md
mumu-teamwork/evals/typed/graders/points.md
mumu-teamwork/evals/typed/prompt.md
mumu-teamwork/evals/work/graders/routed.md
mumu-teamwork/evals/work/prompt.md
mumu-teamwork/hooks/hooks.json
mumu-teamwork/lib/gh.py
mumu-teamwork/lib/herdr.py
mumu-teamwork/lib/scope.py
mumu-teamwork/lib/sessions.py
mumu-teamwork/lib/size-rubric.md
mumu-teamwork/monitors/monitors.json
mumu-teamwork/scripts/bash-guard.py
mumu-teamwork/scripts/judge-allow.py
mumu-teamwork/scripts/playbook-reread.py
mumu-teamwork/scripts/size-count.py
mumu-teamwork/scripts/stop-guard.py
mumu-teamwork/scripts/team-watch.py
mumu-teamwork/scripts/worktree-guard.py
mumu-teamwork/skills/handoff/SKILL.md
mumu-teamwork/skills/kickoff/SKILL.md
mumu-teamwork/skills/kickoff/references/lead-playbook.md
mumu-teamwork/skills/kickoff/references/worker-playbook.md
mumu-teamwork/skills/kickoff/scripts/repo-settings.py
mumu-teamwork/tests/test_agents.py
mumu-teamwork/tests/test_allow.py
mumu-teamwork/tests/test_bin.py
mumu-teamwork/tests/test_body_file.py
mumu-teamwork/tests/test_clean.py
mumu-teamwork/tests/test_graph.py
mumu-teamwork/tests/test_judge.py
mumu-teamwork/tests/test_lib.py
mumu-teamwork/tests/test_literal.py
mumu-teamwork/tests/test_replace.py
mumu-teamwork/tests/test_repo_settings.py
mumu-teamwork/tests/test_scripts.py
mumu-teamwork/tests/test_size_count.py
EOF
cat > repo-371/checks.json <<'EOF'
{
  "every": ["judge", "*/tests/test_*.py", "*/evals/*"],
  "rules": [
    {"paths": ["*/bin/**", "*/lib/**", "*/scripts/**", "*/monitors/**", "*/tests/**"], "checks": ["judge", "{0}/tests/test_*.py"]},
    {"paths": ["*/evals/*/**"], "checks": ["judge", "{0}/tests/test_*.py", "{0}/evals/{1}"]},
    {"paths": ["*/skills/**", "*/agents/**", "*/hooks/**", "*/.claude-plugin/**"], "checks": ["judge", "{0}/tests/test_*.py", "{0}/evals/*"]},
    {"paths": ["AGENTS.md", "CLAUDE.md"], "checks": ["judge", "mumu-teamwork/tests/test_graph.py"]},
    {"paths": [".gitignore", "scripts/*"], "checks": ["judge"]}
  ]
}
EOF
cat > repo-371/mumu-teamwork/scripts/bash-guard.py <<'EOF'
LEADS = "a task's body, labels, reopening and stop are its lead's: post `BLOCKED: <question>` and prompt your lead"
RAW_MERGE ="a raw `pr merge` is refused; run `pr-merge.py <pr-url>` in a Bash call of its own, and write text naming the merge with a file tool"
...
def refuse(reason):
    print(f"bash-guard: {reason}", file=sys.stderr)
    sys.exit(2)
...
def main():
    raw = sys.stdin.read()
    if not re.search(r"merge|git|hookspath|gh|decision|start\.py|close\.py|herdr|worktrees", QUOTING.sub("", raw), re.I):
        sys.exit(0)
    try:
        payload = json.loads(raw)
        command = payload["tool_input"]["command"]
        if not isinstance(command, str):
            raise TypeError(f"command is {type(command).__name__}")
    except (ValueError, KeyError, TypeError) as err:
        refuse(f"could not read the payload ({type(err).__name__}: {err})")
    try:
        readings = [lexed(command), lexed(command, False)]  # None for an unclosed quote: bash still runs every line before it
        if readings[0] is None and MENTION.search(QUOTING.sub("", command)):
            refuse(RAW_MERGE)
        if None in readings and bypass_text(command) or \
                any(bypasses(words) for reading in readings if reading for words in reading):
            refuse("hook bypass refused: fix what the hook refused, or BLOCKED the owner")
        if any(mentions(words) for words in readings[0] or []):
            refuse(RAW_MERGE)
        if why := routine_refusal(readings[0]) or routine_refusal(lexed(SUBSTITUTION.sub("$_", command))):
            refuse(why)
        if payload.get("agent_type") == "mumu-teamwork:judge" and (why := judge_refusal(command)):
            refuse(why)
        role = ROLES.get(payload.get("agent_type"))
        if role and (why := role_refusal(command, role, payload.get("cwd") or ".")):
            refuse(why)
        if why := early_resolve(command, payload.get("cwd") or "."):
            refuse(why)
        if allowed(command):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                                     "permissionDecisionReason": "mumu-teamwork: a routine step's literal form"}}))
    except Exception as err:  # exit 1 would let the command run
        refuse(f"could not read the command ({type(err).__name__})")
EOF
cat > repo-371/mumu-teamwork/skills/kickoff/references/lead-playbook.md <<'EOF'
## Filing

- Hold any number of root tasks at once, a chore one included.
- Open each criterion of a new task with its kind, `[exists]`, `[test]` or `[quality]`; a task filed before kinds keeps its criteria.
- Before posting a plan's criteria, run each "no FAIL" guard they name on main, and confirm each criterion's check still reads its input once the change lands.
- Give a task that changes how work is split, run, reviewed or tested a criterion replaying past merged pull requests, their checks and session transcripts against the change, because a process change argued only from its design misses the cases history already holds.
- Search the issues first, `gh issue list -R <repo> --state all --search <words>`. Reopen a closed issue of the same kind of work: `gh issue reopen`, then `decide` with `--criteria` to widen its criteria, then `gh issue edit --title --body-file` to rewrite its title and `## Goal` to the new gap, each after the last, never in parallel, and grep the body for the old wording; lead it under a new attempt. When its fixes touch files another open task rewrites, `decide` on both which task owns each fix and `order` them, before the judge. Otherwise `file` a new issue that links it.
- File the fewest tasks at the widest scope: work sharing a mechanism is one task, split by feature, never by layer; a new finding or a judge's defect widens the task it relates to. File them all, then `order` them and write the cross-references.
- Split work, into tasks or a task into shares, only where its order has slack and its conflict can be made indirect: one merge at the end is enough, an interface agreed first lets each part be built apart, or what the parts share is knowledge each only reads.
- Fix a defect you find in the current work or `file` it as its own task, and say which.
- `file` research that later pull requests build on as a task with a worker, driven one step per prompt; run research for your own judgement, or in a skill the owner invokes, in subagents, and give its result to the owner or an issue.
- Put a hunch the owner asks you to interpret as `reading: <yours>` beside their words, never as their decision.
- Ask the owner only architecture, infrastructure and user-experience questions, all at once with `AskUserQuestion`, and have them confirm only those criteria; decide the rest and `decide` it on the task.
- `file` a user-experience question with an industry best practice as a research task first, and ask the owner after its report.
- Before asking the owner, search earlier `DECIDED:` comments and closed issues for the same case, `gh search issues "<words>" -R <repo> --include-prs`; found, follow that decision and tell the owner, citing its url.
EOF
cat > home/.claude/projects/-Users-hyungmokim-workspace-projects-camera/memory/MEMORY.md <<'EOF'
- [Guard drops whole command](pitfall-guard-drops-whole-command.md)
- [Criteria fail on main](feedback-criteria-fail-on-main.md)
EOF
cat > home/.claude/projects/-Users-hyungmokim-workspace-projects-camera/memory/pitfall-guard-drops-whole-command.md <<'EOF'
A bash-guard refusal drops the whole compound call, its scratch-file write included.
EOF
cat > home/.claude/projects/-Users-hyungmokim-workspace-projects-camera/memory/feedback-criteria-fail-on-main.md <<'EOF'
Every [test] criterion fails on main for a named reason.
EOF
````

Then launch the teamwork:judge agent once per plan: on ./plan-379.txt and on ./plan-374.txt, whose repository's default branch is ./repo, and on ./plan-371.txt, whose repository's default branch is ./repo-371 and whose `~` is ./home. Each folder is cut down: its FILES.txt lists every path of the default branch, and each file there holds only the part of it these plans name, a `...` line where lines are left out. This sandbox forbids a `.git` folder, so git commands run there with `--no-index`. Tell each judge the file is a task's plan to judge, which folders stand for its repository and its `~`, and to write the comment it would post to ./verdict-379.txt, ./verdict-374.txt or ./verdict-371.txt instead of posting it. Run each judge in the foreground, never in the background, and reply only once all three verdict files exist.
