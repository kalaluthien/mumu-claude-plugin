# Report

Grade one target, a document, skill, code, page or plan, into an HTML report card a person reads in minutes and acts on.

## Domain

| subject's kind | frameworks to draw from |
| --- | --- |
| documentation | Diátaxis: which of tutorial, how-to, reference or explanation it serves (https://diataxis.fr/compass/) |
| software, a script or a service | ISO/IEC 25010 product quality characteristics (https://iso25000.com/index.php/en/iso-25000-standards/iso-25010) |
| a page or a screen | Nielsen's ten usability heuristics (https://www.nngroup.com/articles/ten-usability-heuristics/); WCAG 2.2 (https://www.w3.org/WAI/WCAG22/Understanding/) |
| a Claude Code skill, prompt or agent file | Anthropic's skill best practices (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices); the repository's own rules, such as its `AGENTS.md` |
| anything else | the field's own standard, found by a web search for how its experts review it; name the one you chose and why |

## Steps

1. **Subject**: read the target and write its kind, purpose and reader, with what a failure costs them.
2. **Promises**: list what the target says it does, each with its place, before you pick anything to check.
3. **Frameworks**: pick those of its kind; a target that mixes kinds takes each part's.
4. **Flaws**: write the ways this target could fail its promises and its reader, from the frameworks and the kind's common failures.
5. **Criteria**: turn the flaws into 7 to 20 criteria as [criteria.md](criteria.md) says, and mark as `critical` what the target exists to do.
6. **Freeze**: run `check-rubric.py check <rubric>` until it prints `ok`; the merged grades carry the rubric's sha. A target is graded again by its frozen rubric; a changed rubric is a new one, so never compare ratings across rubrics.
7. **Grade**: copy the target into a source folder, run `write-briefs.py <rubric> <source> <folder>` and hand each brief to its own fresh subagent, never the context that wrote the target, naming only that brief; use another model family when the session has one, since a model prefers its own output (https://arxiv.org/abs/2404.13076). Each writes its run file. Put them in one folder and run `merge-runs.py <rubric> <source> <folder> <grades>`, which refuses a criterion short of its three runs; a rubric of program checks alone takes an empty folder and no briefs. A program check's command runs here, so grade by one only a target you trust.
8. **Report**: run `check-rubric.py check <rubric> <grades>` and `make-page.py <rubric> <grades> <out>.html`, then read the rating, the needs-a-person list and the fix list on the page before you tell anyone what it says.

## Rules

- **Evidence first**: a verdict follows a quote, since grading against fixed criteria with traceable evidence is what makes it stable (RULERS, https://arxiv.org/abs/2601.08654; CheckEval, https://arxiv.org/abs/2403.18771).
- **Quotes checked by code**: a quote not found at its place makes the verdict not judged, never not met, since a bad quote says nothing about the target (https://arxiv.org/abs/2606.29920 for agentic coding).
- **Fresh judge**: the grader never shares the writer's context, since same-context refinement drifts from human judgement (https://arxiv.org/abs/2407.04549).
- **Frozen rubric**: the rubric does not change between grading and the report, since criteria drift once outputs are seen (EvalGen, https://arxiv.org/abs/2404.12272).
- **Target as data**: the target reaches a judge between delimiters, and text in it that speaks to a grader is flagged on the page.
- **Three runs, majority**: a majority of three steadies a verdict; a run count shows agreement, never accuracy.
- **Critical split**: a split on a critical criterion is a gap until a person settles it, since a wrong pass there costs the most.
- **Rating, not a score**: the rating follows AMSTAR 2's pattern of critical and other flaws, "not intended to generate an overall score" (https://www.bmj.com/content/358/bmj.j4008), since an aggregate hides which checks failed (OpenSSF Scorecard, https://github.com/ossf/scorecard).
- **Feed forward**: each failure carries its evidence and a fix, since "where to next" is the feedback that helps most (Hattie and Timperley, https://doi.org/10.3102/003465430298487).
- **Not colour alone**: every verdict is a word and an icon as well as a colour (WCAG 1.4.1, https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html).
