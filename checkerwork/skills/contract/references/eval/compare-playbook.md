# Compare

Rival answers, drafts or plans judged against a rubric inside one conversation: a verdict for this choice, no judge prompt kept for later.

1. Criteria first: before reading any candidate, write 3 to 6 criteria from the ask alone, each binary and a check that can fail, and show them. Change one after reading a candidate and score again from the start.
2. A judge that wrote no candidate: when this session wrote any, hand a fresh subagent only the criteria and the candidates, relabelled A, B, C in shuffled order.
3. Score each candidate on each criterion 1 or 0, with the quote that decides it; a criterion no candidate can fail proves nothing, so cut it.
4. Total with code (a `python3 -c` or shell line), never in the head, and show the table: criteria by candidates, totals, the winner. Equal totals are a tie, reported as one.
5. A judge to keep and rerun is [judge-playbook.md](judge-playbook.md); its wait for error analysis does not apply here.
