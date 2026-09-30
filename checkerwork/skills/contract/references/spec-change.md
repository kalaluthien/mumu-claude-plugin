# Spec: change

A change to states, transitions, permissions or a protocol: model it and check the rule it must keep before the code changes.

1. Read the model covering the change: [spec/layout-playbook.md](spec/layout-playbook.md).
2. Turn each of the owner's never, always, only after or at most sentences the change touches into an assert quoting it, and model the change: [spec/model-playbook.md](spec/model-playbook.md).
3. Check the model, each UNSAT paired with a SAT: [spec/check-playbook.md](spec/check-playbook.md).
4. Write the witnesses each new check and flow run needs, and watch them fail before the code changes: [test/witness-playbook.md](test/witness-playbook.md).
5. Change the code; `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` passes.
