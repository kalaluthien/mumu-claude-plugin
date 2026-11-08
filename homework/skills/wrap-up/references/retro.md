# Retro

Keep what this session learned where the next agent will meet it. A lesson handed over by the owner skips to step 4.

## Steps

1. **Candidates**: list candidates since the last wrap-up: `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-candidates.py`.
2. **Lenses**: over them and the session ask what was intended, what happened, why, and what to sustain or improve. Then look through these lenses, the first seven from the retrospective skill in [Matt Pocock's skills](https://github.com/mattpocock/skills), each with the evidence that calls for it:
   - **Navigation**: finding a file or fact took long: a pointer where the search began.
   - **Checks**: a mistake a check could have caught: first read the repository's own check commands and CI, since one that exists but is unwired is the finding.
   - **Mechanical or judgement**: a fixed pattern (a banned call, a path rule) becomes a check, never a written rule; only a judgement call is written.
   - **Steering size**: an instruction file grown large: move detail out, behind a pointer.
   - **No-ops**: an instruction that changed no behaviour: cut it.
   - **Tool economy**: an expensive call that a cheaper command would answer.
   - **Information access**: a fact the agent could not reach: give it read access.
   - **Steering**: an `owner` or `override` candidate, where the owner corrected or redirected: the instruction or default that would have made it unneeded.
   - **Interface**: each `refusal`, `failure` or `hook` candidate, and any other tool, script or hook whose usage line or message misled or cost a step: name each one and its owner, then route the fix by who owns the tool, a patch to it when its repository is the owner's, as the Foreign repositories rule tells, else a memory lesson with the workaround, plus a wrapper or hook in the owner's repository when one fits; or drop it with a reason.

   **Dig**: take each finding through 5 whys, each answer the cause of the one before, so the fix lands at the cause, not the symptom. Stop when a why names a broken assumption or a missing check that an instruction, check or tool could change; a why that ends in "the guard worked" is no finding, so drop it. A why with two causes is a branch: dig each.

   **Verified cause**: each why cites the transcript line or the artifact it names. When it names an artifact, a file's state or `git log`, a hook's or script's source or usage line, read it now and cite that read, since a transcript line shows what a tool did, not why. A why with neither is a guess: file no lesson on it, and report it as a guess in step 8.
3. **Drafts**: draft each answer worth keeping, one per verified root cause, paraphrasing owner text, never quoting it, since memory may be pushed:
   - improve: "when <situation>, do <action>, because <the broken assumption, the last why>", then `checked: <the line or read that verified it>`; a draft that rests on one why is still a symptom, so dig on;
   - sustain, an owner-accepted choice or a detour that worked: "when <situation>, keep <action>, because <what it saved>";
   - a procedure worked out: its steps as run.

   Keep the most severe, the costliest to repeat first, telling the owner how many were dropped:

   | drafts | 1–3 | 4 | 5–6 | 7–8 | 9–11 | 12–14 | 15+ |
   | --- | --- | --- | --- | --- | --- | --- | --- |
   | kept | all | 3 | 4 | 5 | 6 | 7 | 8 |

4. **Destination**: route each lesson to the first row it fits:

   | the lesson | destination |
   | --- | --- |
   | something a check could decide | a hook, script, lint rule or CI step, placed as its repository's `AGENTS.md` says, as a patch |
   | a procedure that worked again, or how a subagent should work | a memory file placed by the rows below, its frontmatter marked `skill: <plugin>:<skill>` for the skill that owns the work, or `skill: new <name>`; a dream asks the owner whether to write it into the skill |
   | must be known before its situation shows, by `SKILL.md`'s **Placement test** | the instruction file that test names, as a patch |
   | wrong or harmful outside this repository, such as its paths or one-off setup | `<home>/<repo>/`, else this project's pool, one memory file each |
   | any other lesson, a fact, a trap, a preference or a procedure | `<home>/`, one memory file each; move this repository's copy there by `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/move-memory.py <file> <home>`, and delete another repository's copy as a patch. With no `<home>`: `<config>/CLAUDE.md`, an instruction and a clause of reason in its work's section, as a patch rooted at `<config>` that also deletes this project's copy |

   **Patch**: a destination marked patch is never written in place, since only this project's memory is retro's to change. Write the change as a unified diff to `<data>/patches/<today>-<topic>.patch`, its paths relative to `<root>`, the repository that holds the file, else the file's folder. Check it with `git -C <root> apply --check <patch file>`.

5. **Operation**: read every memory folder afresh, `<home>` with its folders and `<config>/projects/*/memory/`. Take the first operation that fits:
   - **Confirm**: an entry says it already: `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/count-confirmations.py <file>`.
   - **Extend**: an entry on the same subject or mechanism: add to it.
   - **Add**: a new memory file whose frontmatter has `name`, `description`, `metadata.type`, `metadata.confirmed: 1` and `metadata.last-confirmed: <today>`, justified in one line: the nearest entry and why it could not be extended, or that none exists.

   An extend or add to another repository's folder or pool is a patch, as step 4 says; skip a confirm there.

   An extend or add cites evidence: a candidate's time, a url or a `path:line`.
6. **Edit**: edit only the lines that change, `MEMORY.md` over a fresh read, since other sessions write it. Delete or correct any entry this session showed wrong. Then run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-drift.py <config> <folder>` on each folder you wrote and fix each `bad header` line for your file before the report, since only a dream would find a headerless file otherwise.
7. **Repeat**: a repeat an entry should have prevented: confirm it, and hand its project's manager, by `SendMessage`, a task to make it a check or a skill step, naming which, the lesson and the repeat's evidence, never a GitHub issue. With no manager, tell the owner in one line. The hand-over asks first: show the owner the task's title and send it only on their yes.

8. **Report**: tell the owner each lesson filed: its operation, text, file and `checked:` source, then each guess in one line, and an add's one line, and for a patch the line `! git -C <root> apply <patch file>` that applies it; with no lesson and no guess, say nothing.
