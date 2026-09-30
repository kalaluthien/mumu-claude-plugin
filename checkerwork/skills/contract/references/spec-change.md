# Spec: change

A change to states, transitions, permissions or a protocol: model it and check the rule it must keep before the code changes.

1. A repo with no model, only then: look for the checker ([spec/layout-playbook.md](spec/layout-playbook.md)), and with no `alloy` stop there; else initialise `map.als` in the repo's `spec/` and a `model.als` and `check.als` per module the change touches ([spec/model-playbook.md](spec/model-playbook.md)), check them ([spec/check-playbook.md](spec/check-playbook.md)), and tell the owner "no spec layout found; initialised spec/".
2. Read the model covering the change: [spec/layout-playbook.md](spec/layout-playbook.md).
3. Turn each of the owner's never, always, only after or at most sentences the change touches into an assert quoting it, and model the change: [spec/model-playbook.md](spec/model-playbook.md).
4. Check the model, each UNSAT paired with a SAT: [spec/check-playbook.md](spec/check-playbook.md).
5. Write the witnesses each new check and flow run needs, and watch them fail before the code changes: [test/witness-playbook.md](test/witness-playbook.md).
6. Change the code; `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` passes.
