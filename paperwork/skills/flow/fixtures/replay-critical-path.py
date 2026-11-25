#!/usr/bin/env python3
"""Replay the `order` call of check-contract.py on random plans against a brute-force walk of every path.

usage: replay-critical-path.py [--seed <n>]

It writes 300 random plans of 2 to 9 tasks on up to three nodes, listed in a random order, with request and wait edges and up to two
milestones, a fifth of them given a cycle, and one plan of one chain of 1500 tasks listed last to first. For a plan with no cycle, the
printed critical path must be a chain, each id coming right before the next, holding as many tasks as the longest chain any path holds,
and each task's and milestone's printed place must be the most steps any path takes to reach it; a plan with a cycle must be refused by
`milestone-order` or `order-acyclic`. It prints `FAIL <seed> <plan>: <reason>` per miss, then PASS or FAIL; exit 1 on a miss."""
import json
import pathlib
import random
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CHECKER = HERE.parent / "scripts" / "check-contract.py"
PLANS = 300
CHAIN = 1500


def plan(chance):
    """A random plan contract, and the precedence it means as {id: ids that come right before it}, built apart from the checker's code."""
    count = chance.randint(2, 9)
    nodes = [f"node-{k}" for k in range(chance.randint(1, 3))]
    tasks = [{"id": f"task-{k}", "level": "work", "node": chance.choice(nodes), "label": f"Step {k}", "tag": "work", "purpose": f"Does part {k}."}
             for k in range(count)]
    first = {task["id"]: set() for task in tasks}
    edges = []
    for later in range(count):
        for earlier in range(later):
            if chance.random() < 0.3:
                edges.append({"id": f"edge-{earlier}-{later}", "level": "work", "from": f"task-{earlier}", "to": f"task-{later}",
                              "label": f"hand over part {earlier}", "tag": chance.choice(["request", "wait"])})
                first[f"task-{later}"].add(f"task-{earlier}")
    milestones = []
    for k in range(chance.randint(0, 2)):
        cut = chance.randint(1, count - 1)
        after = sorted(chance.sample([task["id"] for task in tasks[:cut]], chance.randint(1, cut)))
        milestones.append({"id": f"gate-{k}", "level": "work", "label": f"Gate {k}", "after": after})
        first[f"gate-{k}"] = set(after)
        for task in tasks[cut:]:
            if chance.random() < 0.5:
                task.setdefault("after", []).append(f"gate-{k}")
                first[task["id"]].add(f"gate-{k}")
    if chance.random() < 0.2:
        later, earlier = sorted(chance.sample(range(count), 2))
        edges.append({"id": "edge-back", "level": "work", "from": f"task-{later}", "to": f"task-{earlier}", "label": "send it back", "tag": "wait"})
        first[f"task-{earlier}"].add(f"task-{later}")
    chance.shuffle(tasks)
    return contract_of(nodes, tasks, edges, milestones), first


def chain(count):
    """A plan of one chain of COUNT tasks, listed last to first, and the precedence it means."""
    tasks = [{"id": f"task-{k}", "level": "work", "node": "node-0", "label": f"Step {k}", "tag": "work", "purpose": f"Does part {k}."}
             for k in reversed(range(count))]
    edges = [{"id": f"edge-{k}-{k + 1}", "level": "work", "from": f"task-{k}", "to": f"task-{k + 1}", "label": f"hand over part {k}", "tag": "request"}
             for k in range(count - 1)]
    first = {f"task-{k}": {f"task-{k - 1}"} if k else set() for k in range(count)}
    return contract_of(["node-0"], tasks, edges, []), first


def contract_of(nodes, tasks, edges, milestones):
    """A plan contract of one level that holds NODES, TASKS, EDGES and MILESTONES."""
    contract = {
        "title": "Random plan",
        "purpose": "Orders random work.",
        "sources": [{"id": "notes", "path": "https://example.com/notes", "says": "The plan."}],
        "groups": [{"id": "crew", "label": "Crew"}],
        "levels": [{"id": "work", "title": "work", "kind": "plan", "nodes": nodes}],
        "nodes": [{"id": name, "label": f"Worker {k}", "tag": "actor", "group": "crew", "purpose": f"Does the work of crew member {k}."} for k, name in enumerate(nodes)],
        "tasks": tasks, "edges": edges, "milestones": milestones,
        "properties": [{"id": "ordered", "title": "ordered", "kind": "invariant", "statement": "Each step waits for what it names.", "on": ["work"]}],
        "questions": [{"id": "what-first", "asks": "What runs first?", "answers": ["task-0"]}],
    }
    next(task for task in tasks if task["id"] == "task-0")["evidence"] = ["notes"]
    return contract


def has_cycle(first):
    """True when FIRST, {id: ids before it}, holds a cycle."""
    state = {}

    def walk(name):
        state[name] = "open"
        for earlier in first[name]:
            if state.get(earlier) == "open" or earlier not in state and walk(earlier):
                return True
        state[name] = "done"
        return False

    return any(name not in state and walk(name) for name in first)


def longest(first, tasks):
    """The most tasks any chain of FIRST holds, by walking every path from every id."""
    best = 0

    def walk(name, held):
        nonlocal best
        best = max(best, held)
        for later, before in first.items():
            if name in before:
                walk(later, held + (later in tasks))

    for name in first:
        walk(name, name in tasks)
    return best


def places(first):
    """The most steps any path of FIRST takes to reach each id, by walking every path from every id."""
    at = {name: 0 for name in first}

    def walk(name, steps):
        at[name] = max(at[name], steps)
        for later, before in first.items():
            if name in before:
                walk(later, steps + 1)

    for name in first:
        walk(name, 0)
    return at


def missed_order(seed, name, contract, first, run):
    """The reason the order call RUN printed a wrong critical path or place for CONTRACT, or None."""
    tasks = {task["id"] for task in contract["tasks"]}
    lines = [line for line in run.stdout.splitlines() if line.startswith("critical-path work ")]
    if run.returncode or len(lines) != 1:
        return f"the order call printed no one critical path: {(run.stdout + run.stderr).strip()[-200:]}"
    chain = lines[0].split(": ", 1)[1].split()
    linked = all(earlier in first.get(later, ()) for earlier, later in zip(chain, chain[1:]))
    held = sum(1 for name in chain if name in tasks)
    wanted = len(tasks) if len(tasks) == CHAIN else longest(first, tasks)
    if not linked or held != wanted or not lines[0].startswith(f"critical-path work {held} tasks: "):
        return f"printed {lines[0][:200]}, a chain of {held} tasks{'' if linked else ' whose ids are not each right before the next'}; the longest holds {wanted}"
    printed = {line.split()[2]: int(line.split()[3]) for line in run.stdout.splitlines() if line.startswith("place work ")}
    expected = {f"task-{k}": k for k in range(CHAIN)} if len(tasks) == CHAIN else places(first)
    if printed != expected:
        wrong = sorted(name for name in expected.keys() | printed.keys() if printed.get(name) != expected.get(name))
        return f"printed places that differ from the most steps to each id at {', '.join(wrong[:5])}"
    return None


def main(args):
    if args and not (len(args) == 2 and args[0] == "--seed" and args[1].isdigit()):
        print(__doc__, file=sys.stderr)
        return 2
    seed = int(args[1]) if args else 1480
    chance, missed = random.Random(seed), 0
    with tempfile.TemporaryDirectory() as folder:
        for k in range(PLANS):
            contract, first = plan(chance)
            path = pathlib.Path(folder) / f"plan-{k}.json"
            path.write_text(json.dumps(contract))
            run = subprocess.run([sys.executable, str(CHECKER), "order", str(path)], capture_output=True, text=True)
            if has_cycle(first):
                if run.returncode != 1 or not any(rule in run.stdout for rule in (": milestone-order:", ": order-acyclic:")):
                    missed += 1
                    print(f"FAIL {seed} plan-{k}: a plan with a cycle was not refused by its order rules: {run.stdout.strip()[:200]}")
                continue
            reason = missed_order(seed, f"plan-{k}", contract, first, run)
            if reason:
                missed += 1
                print(f"FAIL {seed} plan-{k}: {reason}")
        contract, first = chain(CHAIN)
        path = pathlib.Path(folder) / "chain.json"
        path.write_text(json.dumps(contract))
        run = subprocess.run([sys.executable, str(CHECKER), "order", str(path)], capture_output=True, text=True)
        reason = missed_order(seed, "chain", contract, first, run)
        if reason:
            missed += 1
            print(f"FAIL {seed} chain: {reason}")
    print("FAIL" if missed else "PASS")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
