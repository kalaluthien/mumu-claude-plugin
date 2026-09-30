# Eval: calibrate

Build or validate an LLM judge against the owner's labels.

1. First decide whether it may be written yet: [eval/judge-playbook.md](eval/judge-playbook.md) § When. With no error analysis behind it, write no judge prompt, not even a draft: stop at that section's answer.
2. Write or read its prompt against [eval/judge-playbook.md](eval/judge-playbook.md) § Prompt: a criterion of several parts becomes one grader each, and a part a pattern decides becomes a `regex` ([eval/graders-playbook.md](eval/graders-playbook.md)).
3. Validate it on labelled dev and test splits, then report any rate through its corrected pass rate: [eval/judge-playbook.md](eval/judge-playbook.md) § Validate.
