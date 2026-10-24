# Repair

A graded answer landed in the wrong order. Find the step of [author.md](author.md) that let it, fix the spec there, and rerun `check-spec.py check` and the dry run. The spec's grammar is [spec/assets/rubric.schema.json](spec/assets/rubric.schema.json).

| cause | sign | fix |
| --- | --- | --- |
| missing criterion (step 2) | the wrong answer meets every criterion; what it lacks is named nowhere | add the criterion, its provenance the failure you saw |
| boundary (step 3) | a criterion passed a near-miss or failed a valid variant | rewrite it; add the answer to its near-misses or variants |
| placement (step 4) | a lower tier bought back a higher one's deficit | rerun the exchange test for the pair and record it; move the criterion |
| judge error (step 5) | the verdicts themselves were wrong, or flip between runs | measure it ([calibrate.md](calibrate.md)); rewrite the criterion more concretely or as a program check |
| mask (step 5) | a failing answer outranked a passing one through lower tiers, or failing answers were ordered when that has no value | set or clear the mask, and its pass rate |

When a failure generalises, add a rule for it to `check-spec.py` with a fixture it rejects, and its lesson to the Gotchas of the playbook it governs.
