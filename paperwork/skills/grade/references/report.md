# Report

Grade one target, a document, skill, code, page or plan, into an HTML report card the owner reads and acts on.

## Domain

- **target**: the thing graded, at one version: a path, a url or a commit.
- **subject**: what kind of thing the target is, what it is for and who reads it, each with the evidence for that reading; it picks the frameworks the criteria come from.
- **framework**: an established quality standard for the subject's kind, the menu criteria are drawn from.
- **grades file**: each criterion's verdict with the quoted evidence, its location, the reason and, for a failure, the fix, in the grammar of [spec/assets/rubric-schema.json](spec/assets/rubric-schema.json) `$defs/grades`; its `met` values are a verdict file's.
- **report card**: the page `make-page.py` builds from a rubric and a grades file: the verdict, the fix list, a bar per tier, then each criterion with its evidence.

| subject's kind | frameworks to draw from |
| --- | --- |
| documentation | Diátaxis: which of tutorial, how-to, reference or explanation it serves (https://diataxis.fr/compass/) |
| software, a script or a service | ISO/IEC 25010 product quality characteristics (https://iso25000.com/index.php/en/iso-25000-standards/iso-25010) |
| a page or a screen | Nielsen's ten usability heuristics (https://www.nngroup.com/articles/ten-usability-heuristics/); WCAG 2.2 (https://www.w3.org/WAI/WCAG22/Understanding/) |
| a Claude Code skill, prompt or agent file | Anthropic's skill best practices (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices); the repository's own rules, such as its `AGENTS.md` |
| anything else | the field's own standard, found by a web search for how its experts review it; no single method maps a purpose to criteria, so name the one you chose and why |

## Steps

1. **Subject**: read the target and write its kind, purpose and reader, each with a quote or path that shows it, and in `reader` what a failure costs them. Pick the frameworks the table names for its kind; a target that mixes kinds, such as a README that is part how-to and part reference, takes each part's.
2. **Rubric**: write the rubric as [author.md](author.md) says, drawing criteria from the frameworks and the target's own stated purpose, 7 to 20 of them, each one observable proposition. The subject fills `task.world` and `evidence_goal`. The highest tier holds what the target exists to do; a `-` criterion names a pitfall common to the kind. Each tier's judge error starts from author.md's **Judge error estimate**, and each criterion needs an exchange record with a tier peer and with one of the next tier's, as [spec/criteria.md](spec/criteria.md)'s Exchange test says. With the owner away, skip the interview, mark each record `by: claude`, and put a pair you hesitate on in the higher tier with the doubt in its `note`. A program check names its command in `anchors`. Skip author.md's reward-hacking probe and dry run unless the owner asks for a calibrated rubric, since a frozen rubric and a fresh judge guard the report. Run `check-spec.py check` until it prints `ok`, then `check-spec.py weights`.
3. **Freeze**: take the rubric's sha, `shasum -a 256 <spec> | cut -c1-12`, before any grading; it goes in the grades file, and `make-page.py` refuses grades whose sha differs, so a rubric edited after grading is caught. A change after grading makes a new version: save it under a new name, note what changed and why, take its sha and grade again; never compare scores across versions.
4. **Grade**: hand the grading to fresh subagents, never the context that wrote or revised the target, giving each only the target, the rubric and the grades grammar. Each quotes the evidence first, then gives the verdict; a verdict with no quote is not met. A failure, a `+` criterion not met or a `-` criterion committed, carries a fix. A criterion that cannot be checked, such as one that needs access the grader lacks, gets `met: null` and its reason; the page sets it apart, and its tier scores it as failed. Run it twice; where the runs split, keep the stricter verdict and record both in `runs`. A program check is decided by its command, not by the judge.
5. **Report**: run `make-page.py <spec> <grades> <out>.html`, then open it or publish it as an Artifact. Read the verdict and the fix list on the page before telling the owner what it says.

**Raise**

When asked to improve the target by its card, loop: fix the highest-tier failures, grade again with fresh subagents against the frozen rubric, and record each round's tier scores. Stop when a round's scores do not beat the previous round's, highest tier first. A fix that games a criterion's wording rather than meeting its intent is not a fix: name it in the round's note.

## Rules

- **Evidence first**: a verdict follows a quoted line or a named absence, since grading against fixed criteria with traceable evidence is what makes it stable (RULERS, https://arxiv.org/abs/2601.08654; CheckEval, https://arxiv.org/abs/2403.18771).
- **Binary checks**: each criterion is one yes-or-no question, since checklists raise agreement between judges and with people (TICK, https://arxiv.org/abs/2410.03608; Rubrics as Rewards, https://arxiv.org/abs/2507.17746).
- **Atomic, explicit**: split a compound criterion and count only what the target states, since compound and implied criteria are where rubric scores get gamed (https://arxiv.org/abs/2605.12474).
- **Fresh judge**: the grader never shares the writer's context, since a model prefers its own output (https://arxiv.org/abs/2404.13076) and same-context refinement drifts from human judgement (https://arxiv.org/abs/2407.04549).
- **Frozen rubric**: the rubric does not change between grading and the report, or between rounds of a Raise, since criteria drift once outputs are seen (EvalGen, https://arxiv.org/abs/2404.12272).
- **No credit for length**: no criterion rewards amount, since judges favour longer answers (MT-Bench, https://arxiv.org/abs/2306.05685).
- **Verdict first, fixes next**: the page leads with the verdict and the fix list, highest tier first, and never with one blended number, since an aggregate hides which checks failed (OpenSSF Scorecard, https://github.com/ossf/scorecard; inverted pyramid, https://www.nngroup.com/articles/inverted-pyramid/).
- **Feed forward**: each failure carries its evidence, its reason and a fix, since "where to next" is the feedback that helps most (Hattie and Timperley, https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2021.645758/full).
- **Not colour alone**: every verdict is a word and an icon as well as a colour (WCAG 1.4.1, https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html); bars are bullet graphs with a text count, not gauges (https://en.wikipedia.org/wiki/Bullet_graph).
- **Goodhart**: a rising score under a Raise is evidence only while the rubric is frozen and the judge fresh, since optimising a proxy past a point lowers the real quality (https://arxiv.org/abs/2210.10760).
