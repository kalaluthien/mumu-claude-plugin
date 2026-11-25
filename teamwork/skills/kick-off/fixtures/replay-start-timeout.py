#!/usr/bin/env python3
"""Start workers in a sandbox whose fake herdr times out their start. Print `ok <case>` or `fail <case>: <detail>` per case,
then `PASS` or `FAIL`, and exit 1 on any failure:
- `late`: an agent that comes up in its pane after herdr stopped waiting is given its name and its kick-off, and the start exits 0;
- `never`: with no agent in the pane the start exits 1, says the session is not live and got no kick-off, and sends no prompt;
- `unsent`: a live session whose kick-off was refused is called live with no kick-off, and the answer holds the kick-off to send;
- `untaken`: a live session that took the text but never started on it is called live with its kick-off typed;
- `busy`: a live session that never reads ready but whose pane shows its kick-off, or which is working, is not called one that got no kick-off, and the answer offers no kick-off to resend;
- `lookup`: the pane lookup each failed start names exits 0;
- `limit`: every `herdr agent start` carries a `--timeout` herdr takes, above 3000 ms and at most 300000 ms;
- `subfolder`: `.github/plan-release.py`, when the repository has one, names the same tags from a plugin's folder as from the top.

usage: replay-start-timeout.py"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

KICKOFF = "Run the teamwork:kick-off skill with these arguments: "


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("start-timeout-") as work:
        box = replay_probe.Sandbox(work)
        test(box, cases.step)
    return cases.finish()


def test(box, step):
    def start(name, limit="4"):
        box.herdr([replay_probe.agent("teamwork-manager", 2)])
        box.calls.unlink(missing_ok=True)
        done = box.run([ROOT / "skills/kick-off/scripts/start-session.py", name, box.repository, f"worker {name} manager teamwork-manager https://example.com/1",
                        "--model", "haiku", "--effort", "medium"], TEAMWORK_START_SESSION_TIMEOUT=limit)
        return done, box.herdr_calls(), box.herdr_state()["agents"]

    def looked(done):
        """Whether the pane lookup a failed start names runs."""
        command = re.search(r"`(herdr [^`]+)`", done.stderr)
        return bool(command) and box.run(command[1].split()).returncode == 0

    done, calls, agents = start("late-worker")
    prompts = [call[3] for call in calls if call[:2] == ["agent", "prompt"]]
    step("late", done.returncode == 0 and "took its kick-off" in done.stdout and [agent["name"] for agent in agents] == ["teamwork-manager", "late-worker"]
         and prompts == [KICKOFF + "worker late-worker manager teamwork-manager https://example.com/1"], [done, agents, prompts])
    limits = [int(call[call.index("--timeout") + 1]) for call in calls if call[:2] == ["agent", "start"] and "--timeout" in call]
    limits += [int(call[call.index("--timeout") + 1]) for call in start("plain-worker", "900")[1] if call[:2] == ["agent", "start"] and "--timeout" in call]
    step("limit", len(limits) == 2 and all(3000 < limit <= 300000 for limit in limits), limits)

    lookups = []
    done, calls, agents = start("never-worker")
    lookups.append(looked(done))
    step("never", done.returncode == 1 and not done.stdout and "never-worker is not live and got no kick-off" in done.stderr and len(agents) == 1
         and not any(call[:2] == ["agent", "prompt"] for call in calls), [done, agents])

    done, calls, agents = start("refuse-worker")
    lookups.append(looked(done))
    step("unsent", done.returncode == 1 and "refuse-worker is live and got no kick-off" in done.stderr and KICKOFF + "worker refuse-worker" in done.stderr, done)

    done, calls, agents = start("unseen-worker")
    lookups.append(looked(done))
    step("untaken", done.returncode == 1 and "unseen-worker is live and its kick-off was typed" in done.stderr and "start no second one" in done.stderr, done)
    done, calls, agents = start("busy-worker")
    step("busy", done.returncode == 1 and "got no kick-off" not in done.stderr and "send it:" not in done.stderr
         and "busy-worker is live and its pane shows its kick-off" in done.stderr and "start no second one" in done.stderr, done)
    step("lookup", lookups == [True, True, True], lookups)

    plan = ROOT.parent / ".github" / "plan-release.py"
    if plan.exists():
        # the newest version change against its own parent is one change, so no other plugin's release between two of ours can answer first
        revisions = [f"{revision}^", revision] if (revision := subprocess.run(["git", "log", "--format=%H", "-1", "--", ROOT.name + "/.claude-plugin/plugin.json"], cwd=ROOT.parent, capture_output=True, text=True).stdout.strip()) else []
        answers = [subprocess.run([sys.executable, str(plan), *revisions], cwd=folder, capture_output=True, text=True) for folder in (ROOT.parent, ROOT)]
        told = [(answer.returncode, answer.stdout, answer.stderr) for answer in answers]
        step("subfolder", len(revisions) == 2 and told[0] == told[1] and ROOT.name in told[0][1] + told[0][2], told)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
