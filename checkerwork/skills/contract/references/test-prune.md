# Test: prune

Cut the tests that prove nothing another proves, or that assert a bare equality.

1. For each test in scope, name the contract or path it asserts ([test/contracts-playbook.md](test/contracts-playbook.md)). A bare equality is rewritten to the contract it stands for, or cut when another test already asserts that contract.
2. For tests that seem to prove the same thing, break their subject once (the skill's § Breaking a check) and list which tests turn red: a test that never turns red alone, under any mutant, proves nothing another proves.
3. Keep every witness `spec/` requires, even when another test covers it ([test/witness-playbook.md](test/witness-playbook.md)).
4. Cut the rest, run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh`, and report each test cut with the one that covers it.
