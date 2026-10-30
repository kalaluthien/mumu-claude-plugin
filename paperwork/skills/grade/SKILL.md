---
name: grade
description: Use when a target, such as a document, skill, code, page or plan, must be graded into an HTML report card. Not for a quick A-against-B check of a change.
---

# grade

Grade a target into one page a person acts on in minutes: find what it promises, derive yes-or-no criteria, have fresh judges grade it with quoted evidence, and show the rating and the fixes.

## Domain

- **target**: the thing graded, at one version.
- **rubric**: one JSON file holding the subject, the target's promises, the flaws sought and the criteria, frozen before grading.
- **criterion**: one observable proposition, met or not; a `critical` one is what the target exists to do.
- **run**: one fresh judge's verdicts; three runs make a verdict by majority.
- **gap**: a criterion not met, not judged, or critical with split runs.
- **rating**: High, Moderate, Low or Critically low, from the gaps, never a score.
- **grades**: the merged verdicts with their evidence, from which the page is built.

## Route

`Read` [references/report.md](references/report.md), then [references/grammar.md](references/grammar.md) for the files' shape and [references/criteria.md](references/criteria.md) to write a criterion.

## Rules

- **Scripts compute**: rubric checks, briefs, majorities, ratings and pages come from `${CLAUDE_PLUGIN_ROOT}/skills/grade/scripts/`, never from your own arithmetic.
- **One page**: every report uses the same page; change the rubric or the grades, never the page.
- **Check the page**: `uv run --with playwright==1.64.1 python3 ${CLAUDE_PLUGIN_ROOT}/skills/grade/scripts/make-page.py --check ${CLAUDE_PLUGIN_ROOT}/skills/grade/examples` measures every example's page; add a folder to get pictures to look at.
- **Samples**: [examples/](examples/) holds `every-state`, made up to show each state a page can hold, and `readme` and `check-plan`, real targets graded this way, each with its rubric, source, runs, grades and page.
