# Eval: judge

Build or validate an LLM judge against the owner's labels.

1. The judge grades one failure mode from error analysis with about 20 labelled traces on each side; without them, the analysis comes first ([eval/analysis-playbook.md](eval/analysis-playbook.md)).
2. Write or read its prompt against [eval/judge-playbook.md](eval/judge-playbook.md) § Prompt: a criterion of several parts becomes one grader each, and a part a pattern decides becomes a `regex` ([eval/graders-playbook.md](eval/graders-playbook.md)).
3. Validate it on labelled dev and test splits, then report any rate through its corrected pass rate: [eval/judge-playbook.md](eval/judge-playbook.md) § Validate.
