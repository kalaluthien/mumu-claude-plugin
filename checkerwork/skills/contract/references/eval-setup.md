# Eval: setup

A product with no suite: find the failure modes in real traces first, then check each with code or a validated judge.

1. Find or initialise the runner: [eval/runner-playbook.md](eval/runner-playbook.md) § Find what the repo has.
2. Collect traces and have the owner code them into failure modes: [eval/analysis-playbook.md](eval/analysis-playbook.md). A judge, a score or a metric asked for before it: [eval/judge-playbook.md](eval/judge-playbook.md) § When.
3. For each mode the analysis sorts to a check, write its cases and code graders: [eval/graders-playbook.md](eval/graders-playbook.md). A mode that needs reading gets a judge, used only once validated: [eval/judge-playbook.md](eval/judge-playbook.md).
4. Run every case more than once and read the failed transcripts: [eval/runner-playbook.md](eval/runner-playbook.md) § Run. Cases passing steadily form the regression suite, the rest capability.
