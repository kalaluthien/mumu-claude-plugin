#!/usr/bin/env python3
"""Run pick-check-strategy.py on a temporary git repository holding one change of each kind, and read the playbooks it routes to.
Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `routes`: a document, a script, a hook, a page whose name is not ASCII, a refactor and no change at all each print their own
  playbook's path, `Strategy:` line and judge tier, the one for a small change, and nothing else, a document beside a version bump
  stays a document, one whose text names a page too, and a document beside a script is code;
- `uncommitted`: a file not yet added routes by its name, one whose name is not ASCII too, and a file git ignores is no change;
- `calls`: `--ref` with no base or an option for one, an option the script lacks, and `--ref` after a file are refused with the usage, exit 2, and a base git lacks is named, exit 1;
- `no-row`: a table none of whose rows fits the change is named, exit 1, and a tier line that is not the playbook's last is read;
- `patterns`: with nothing changed, a file named for each pattern of the table routes to its row's playbook at its full tier, a start
  script and a service unit to the guarded one, and a document, a script and a page named together to the page one;
- `size`: a script change of nine lines, the last unended, or of four lines replaced since a named base prints the small tier, and one of ten, of ten
  staged, of eight beside two in a second file, one holding a binary file, a moved script and one with a planned file named print the full tier, and a document moved into a hooks folder is guarded;
- `playbooks`: the table names the six playbooks, each with `Build:` and `Judge:` steps, the tier this runner holds for it, and its own
  case's checks and costly-start rules;
- `brief`: the judge's prompt in protocol.md carries the `Strategy:` line and the strategy's tier, none of its own, worker.md puts the
  line in the change's body, and judge.md names no strategy's own check, asks for no whole check and tries each outcome where no probe is named;
- `throwaway-test`: run-on-refs.py runs a command on the base and the head from another folder, prints each ref's short sha and exit,
  and says it fails on the base and passes on the head; a command that passes on both, fails on both, or fails on the head alone does
  not show the change; fewer than three words or an option is refused with the usage, exit 2;
- `kept`: every check judge.md and the build playbook asked for before the strategies is named in one playbook.

usage: replay-check-strategy.py"""
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

REFERENCES = pathlib.Path(__file__).resolve().parents[1] / "references"
SCRIPT = REFERENCES.parent / "scripts" / "pick-check-strategy.py"
RUN_ON_REFS = SCRIPT.with_name("run-on-refs.py")
KINDS = {
    "instructions": {"p/skills/s/SKILL.md": "See page.html\n", "p/.claude-plugin/plugin.json": "{}\n"},
    "code": {"p/skills/s/scripts/run.py": "x = 1\n", "p/skills/s/SKILL.md": "x\n"},
    "guarded": {"p/hooks/refuse.py": "x = 1\n"},
    "page": {"p/skills/s/assets/쪽.html": "<p>x</p>\n"},
    "research": {},
}
HIGH, MEDIUM = "`mid`, `high`", "`mid`, `medium`"
# (the judge's tier, its tier for a change under 10 changed lines) of each playbook
TIERS = {"check/guarded.md": (HIGH, HIGH), "check/page.md": (HIGH, MEDIUM), "check/refactor.md": (HIGH, MEDIUM), "check/code.md": (HIGH, MEDIUM),
         "check/instructions.md": (MEDIUM, MEDIUM), "check/research.md": (MEDIUM, MEDIUM)}
# a file of each pattern of the table, by the playbook it routes to
SAMPLES = {"guarded": ("p/hooks/note.md", "p/monitors/watch.json", "p/s/use-landing.py", "p/s/use-board.py", "p/s/start-session.py", "p/launch.plist", "p/unit.service"),
           "page": ("a.html", "a.htm", "a.css", "a.svg"),
           "code": ("a.py", "a.ts", "a.tsx", "a.js", "a.cjs", "a.mjs", "a.sh", "p/bin/tool", "p/fixtures/data.txt", "p/assets/logo.txt"),
           "instructions": ("notes.txt", "p/start-notes.md")}
# what each playbook alone must say of its own case's checks and costly starts
OWN = {"check/guarded.md": ("Judge: run the sweep", "mutants of the rest", "an input of each form a caller meets", "Judge: delegate one probe at `mid`, `medium` for every outcome at once", "**One probe**: one probe subagent serves every outcome of a round", "`flexShrink={0}`", "--external claude-code --external 'react*' --outdir <scratchpad>", "probe the live copy", "start script or service"),
       "check/page.md": ("in one browser start", "whose sha-256 is unchanged", "**One browser**", "**Reuse by sha**", "delegating no probe", "Judge: when the change also holds a script, run the sweep"),
       "check/refactor.md": ("Judge: run the sweep", "**Cheap first**", "check `git grep` finds no old name and each row's verdict holds in the diff"),
       "check/code.md": ("Judge: run the sweep", "mutants of the rest", "an input of each form a caller meets", "**Batch mutants**", "**Cheap first**: fixtures of the changed parts, then `run-criteria.py`, then the sweep, then mutants",
                         "a sweep `--since` the last judged head reverts only the hunks moved since"),
       "check/instructions.md": ("**No sweep**", "delegating no probe"),
       "check/research.md": ("**One subagent per source set**", "Judge: open each url")}
STRATEGY_CHECKS = ("--hunks", "delegate one probe", "390 px", "render check", "bun build")
BASE_CHECKS = ("--hunks", "mutants of the rest", "Rerun one of its steps yourself", "combine behaviours as the user would",
               "try each outcome yourself", "run-on-refs.py", "claude plugin test", "claude plugin eval", "bun build",
               "flexShrink", "list_connected_browsers", "save_to_disk", "render check", "390 px", "git grep -nw",
               "git diff -M --numstat", "red-team", "held out", "git diff --numstat origin/<base>", "stale findings")


def advice(name, references=REFERENCES, small=True):
    """All the picker prints for the playbook NAME, at its tier for a change that is SMALL."""
    return (f"playbook: {references / name}\nStrategy: {name}.\nOpen only this playbook; put the `Strategy:` line in the change's body "
            f"and in the `judge` brief, and start the judge at {TIERS[name][small]}.\n")


def write(folder, name, text):
    path = pathlib.Path(folder, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def picked(box, *argv, script=SCRIPT):
    done = box.python(script, *argv)
    return done.returncode, done.stdout, done.stderr


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("check-strategy-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        write(box.repository, "README.md", "x\n")
        write(box.repository, ".gitignore", "ignored.py\n")
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        routes = {}
        for kind, files in KINDS.items():
            box.git("checkout", "-q", "-B", kind, "main")
            for name, text in files.items():
                write(box.repository, name, text)
            box.git("add", "-A")
            box.git("commit", "-qm", kind, "--allow-empty")
            routes[kind] = picked(box)
        box.git("checkout", "-q", "instructions")
        routes["refactor"] = picked(box, "--refactor")
        named_base = picked(box, "--ref", "main")
        cases.step("routes", routes == {kind: (0, advice(f"check/{kind}.md"), "") for kind in [*KINDS, "refactor"]}
                   and named_base == routes["instructions"], (routes, named_base))
        usage = (2, "", SCRIPT.read_text().split('"""')[1] + "\n")
        refused = [picked(box, *argv) for argv in (["--ref"], ["--ref", "--x"], ["--ref", "main", "--x"], ["--x"], ["x.py", "--ref", "main"])]
        code, out, error = picked(box, "--ref", "nowhere")
        cases.step("calls", refused == [usage] * 5 and (code, out) == (1, "")
                   and re.fullmatch(r"pick-check-strategy: git found no merge base of nowhere and the head: \S[^\n]*\n", error), (refused, code, out, error))
        copy = pathlib.Path(work, "copy")
        shutil.copytree(REFERENCES / "check", copy / "references" / "check")
        table = "".join(line for line in (REFERENCES / "check.md").read_text().splitlines(keepends=True) if "check/page.md" in line)
        write(copy, "references/check.md", table)
        with (copy / "references" / "check" / "page.md").open("a") as page:
            page.write("\nA line after the tier.\n")
        script = write(copy, f"scripts/{SCRIPT.name}", SCRIPT.read_text())
        no_row = picked(box, script=script)
        box.git("checkout", "-q", "page")
        cases.step("no-row", no_row == (1, "", "pick-check-strategy: no row of references/check.md fits this change, so the table lacks a case\n")
                   and picked(box, script=script) == (0, advice("check/page.md", copy / "references"), ""), no_row)
        box.git("checkout", "-q", "research")
        write(box.repository, "ignored.py", "x = 1\n")
        ignored = picked(box)
        write(box.repository, "그림.svg", "<svg/>\n")
        drawn = picked(box)
        write(box.repository, "p/hooks/refuse.py", "x = 1\n")
        hooked = picked(box)
        cases.step("uncommitted", [ignored, drawn, hooked] == [(0, advice(f"check/{kind}.md"), "") for kind in ("research", "page", "guarded")],
                   (ignored, drawn, hooked))
        box.git("clean", "-fdq")
        routed = {(kind, name): picked(box, name) for kind, names in SAMPLES.items() for name in names}
        mixed = picked(box, "notes.md", "a.py", "a.html")
        cases.step("patterns", routed == {(kind, name): (0, advice(f"check/{kind}.md", small=False), "") for kind, name in routed}
                   and mixed == (0, advice("check/page.md", small=False), ""), (routed, mixed))
        sizes = {}
        for name, text in (("nine", "x = 1\n" * 8 + "y = 1"), ("ten", "x = 1\n" * 10)):
            write(box.repository, "sized.py", text)
            sizes[name] = picked(box)
        box.git("add", "-A")
        sizes["staged"] = picked(box)
        box.git("commit", "-qm", "ten")
        box.git("branch", "sized")
        write(box.repository, "sized.py", "x = 1\n" * 6 + "x = 2\n" * 4)
        sizes["four and four"] = picked(box, "--ref", "sized")
        write(box.repository, "more lines.py", "y = 1\ny = 2\n")
        sizes["eight and two"] = picked(box, "--ref", "sized")
        write(box.repository, "sized.py", "x = 1\n" * 10)
        (box.repository / "more lines.py").write_bytes(b"\0\1")
        box.git("add", "-A")
        sizes["binary"] = picked(box, "--ref", "sized")
        box.git("commit", "-qm", "binary")
        box.git("mv", "sized.py", "moved.py")
        sizes["moved"] = picked(box, "--ref", "HEAD")
        box.git("checkout", "-q", "-f", "instructions")
        (box.repository / "p" / "hooks").mkdir(parents=True)
        box.git("mv", "README.md", "p/hooks/README.md")
        into_hooks = picked(box, "--ref", "main")
        box.git("reset", "-q", "--hard")
        sizes["planned"] = picked(box, "--ref", "main", "a.py")
        expected = {"nine": True, "ten": False, "staged": False, "four and four": True, "eight and two": False, "binary": False, "moved": False, "planned": False}
        cases.step("size", into_hooks == (0, advice("check/guarded.md"), "") and sizes == {name: (0, advice("check/code.md", small=small), "") for name, small in expected.items()}, (sizes, into_hooks))
        short = {ref: box.git("rev-parse", "--short", ref).strip() for ref in ("main", "instructions", "code", "guarded")}

        def on_refs(command, *refs):
            done = box.python(RUN_ON_REFS, command, *refs, "--repository", box.repository, cwd=box.work)
            return done.returncode, done.stdout, done.stderr

        def ran(codes, shown):
            refs = list(codes)
            verdict = f"fails on {refs[0]}, passes on {', '.join(refs[1:])}" if shown else f"does not fail on {refs[0]} and pass on {', '.join(refs[1:])}: the command does not show the change"
            return 0, "".join(f"{ref} {short[ref]}: exit {code}\n" for ref, code in codes.items()) + verdict + "\n", ""

        held, usage = "test -e p/skills/s/SKILL.md", RUN_ON_REFS.read_text().split('"""')[1] + "\n"
        shown = [on_refs(held, "main", "instructions"), on_refs(held, "main", "instructions", "code")]
        hidden = [on_refs("true", "main", "instructions"), on_refs("false", "main", "instructions"), on_refs("test ! -e p/skills/s/SKILL.md", "main", "instructions"),
                  on_refs(held, "main", "instructions", "guarded")]
        refused = [on_refs("true", "main"), on_refs("true", "main", "--each", "instructions")]
        cases.step("throwaway-test", shown == [ran({"main": 1, "instructions": 0}, True), ran({"main": 1, "instructions": 0, "code": 0}, True)]
                   and hidden == [ran({"main": 0, "instructions": 0}, False), ran({"main": 1, "instructions": 1}, False), ran({"main": 0, "instructions": 1}, False),
                                  ran({"main": 1, "instructions": 0, "guarded": 1}, False)]
                   and refused == [(2, "", usage)] * 2 and all(len(sha) < 40 for sha in short.values()), (shown, hidden, refused))
    table_text = (REFERENCES / "check.md").read_text()
    named = re.findall(r"\]\((check/[^)]+\.md)\)", table_text)
    texts = {name: (REFERENCES / name).read_text() for name in named}
    lacking = [name for name, text in texts.items() if not ("Build:" in text and "Judge:" in text and "**Judge tier**" in text)]
    lacking += [(name, phrase) for name, phrases in OWN.items() for phrase in phrases if phrase not in texts.get(name, "")]
    cases.step("playbooks", sorted(named) == sorted(TIERS) and not lacking, (named, lacking))
    protocol, worker, judge = ((REFERENCES / name).read_text() for name in ("protocol.md", "worker.md", "judge.md"))
    cases.step("brief", "Strategy: <playbook>." in protocol and "`Strategy:` line in the change's body" in worker and "at the tier its strategy names" in protocol
         and not re.search(r"\| landing \| `judge` \|[^\n]*`(?:open|deep|mid|light)`", protocol) and "Run no repository whole check" in judge
         and "open it alone and do its `Judge:` steps" in judge and "naming each file the task will change" in table_text
         and "Open that playbook alone, and put its `Strategy:` line in the change's body and in the `judge` brief" in table_text
         and "where it names no probe, try each outcome yourself at the head, delegating none" in judge
         and not [check for check in STRATEGY_CHECKS if check in judge], [check for check in STRATEGY_CHECKS if check in judge])
    missing = [check for check in BASE_CHECKS if not any(check.lower() in text.lower() for text in texts.values())]
    cases.step("kept", not missing, missing)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
