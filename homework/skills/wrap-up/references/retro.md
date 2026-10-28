# Retro

Keep what this session learned where the next agent will meet it. A lesson handed over by a person skips to step 4.

## Steps

1. **Candidates**: list candidates since the last wrap-up: `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-candidates.py`.
2. **Lenses**: over them and the session ask what was intended, what happened, why, and what to sustain or improve. Then look through these lenses of the retrospective skill in [Matt Pocock's skills](https://github.com/mattpocock/skills), each with the evidence that calls for it:
   - **Navigation**: finding a file or fact took long: a pointer where the search began.
   - **Checks**: a mistake a check could have caught: first read the repository's own check commands and CI, since one that exists but is unwired is the finding.
   - **Mechanical or judgement**: a fixed pattern (a banned call, a path rule) becomes a check, never a written rule; only a judgement call is written.
   - **Steering size**: an instruction file grown large: move detail out, behind a pointer.
   - **No-ops**: an instruction that changed no behaviour: cut it.
   - **Tool economy**: an expensive call that a cheaper command would answer.
   - **Information access**: a fact the agent could not reach: give it read access.
3. **Drafts**: draft each answer worth keeping, one per cause:
   - improve: "when <situation>, do <action>, because <the broken assumption>";
   - sustain, an owner-accepted choice or a detour that worked: "when <situation>, keep <action>, because <what it saved>";
   - a procedure worked out: its steps as run.

   Keep the most severe, the costliest to repeat first, telling the owner how many were dropped:

   | drafts | 1–3 | 4 | 5–6 | 7–8 | 9–11 | 12–14 | 15+ |
   | --- | --- | --- | --- | --- | --- | --- | --- |
   | kept | all | 3 | 4 | 5 | 6 | 7 | 8 |

4. **Destination**: route each lesson to the first row it fits:

   | the lesson | destination |
   | --- | --- |
   | something a check could decide | a hook, script, lint rule or CI step, by [harness-authoring.md](harness-authoring.md), as a patch |
   | a procedure that worked again, or how a delegate should work | the skill that owns the work, by [harness-authoring.md](harness-authoring.md), as a patch |
   | true for every project: another project's memory holds it, or the user said it for all work | `<config>/CLAUDE.md`: an instruction and a clause of reason in its work's section, as a patch rooted at `<config>` that also deletes this project's copy |
   | true for this project: a fact, a trap, a preference, a procedure that worked once | auto-memory, one memory file each |

   **Patch**: a destination marked patch is never written in place, since only this project's memory is retro's to change. Write the change as a unified diff to `<data>/patches/<today>-<topic>.patch`, its paths relative to `<root>`, the repository that holds the file, else the file's folder. Check it with `git -C <root> apply --check <patch file>`.

5. **Operation**: read every memory pool afresh, `<config>/projects/*/memory/`; a pool's key is its project's absolute path with each non-alphanumeric character as `-`, derived from the path, never back. Take the first operation that fits:
   - **Confirm**: an entry says it already: `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/count-confirmations.py <file>`.
   - **Extend**: an entry on the same subject or mechanism: add to it.
   - **Add**: a new memory file with `confirmed: 1` and `last-confirmed: <today>` in its frontmatter, justified in one line: the nearest entry and why it could not be extended, or that none exists.

   An extend or add to a pool of another project is a patch, as step 4 says; skip a confirm there.

   An extend or add cites evidence: a candidate's time, a url or a `path:line`.
6. **Edit**: edit only the lines that change, `MEMORY.md` over a fresh read, since other sessions write it. Delete or correct any entry this session showed wrong.
7. **Repeat**: a repeat an entry should have prevented: confirm it, and file a task in its project's issue tracker to make it a check or a skill step, naming which, the lesson and the repeat's evidence. With no tracker, tell the owner in one line. The filing asks first: show the person the task's title and file it only on their yes.

8. **Report**: tell the owner each lesson filed: its operation, text and file, and an add's one line, and for a patch the line `! git -C <root> apply <patch file>` that applies it; with none, say nothing.
