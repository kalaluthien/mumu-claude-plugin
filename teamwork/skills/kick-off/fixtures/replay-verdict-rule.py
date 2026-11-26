#!/usr/bin/env python3
"""Run pick-verdict.py on gap classes and on a temporary git repository whose head a judge approved. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `listed`: no gap prints `approve` alone, and each class that names no fault of the code, alone, twice or all together, prints
  `approve` and the line that has the judge list the gaps by their count;
- `blocking`: a code fault, a failed scenario or a check not run prints `fix` and names the class, alone, last among listed gaps and
  first among them, two blocking classes named once each in order;
- `refused`: a class the script lacks, a class beside one, no option, an option it lacks, `--since` with no sha, two or an option
  for one print the usage, exit 2;
- `unjudged`: after the approved head, no change, a document, one whose name is not ASCII, a file under a `fixtures/` folder at the
  root or deeper, a plugin's `plugin.json` with a new `version`, a document not yet added, one so named and a script git ignores
  print `merge`, from the root and from a folder below it;
- `judged`: a script, a script not yet added, seen from the root and from another folder, a script moved to a document's name, a
  `plugin.json` outside `.claude-plugin` with only a new `version`, a file named `fixtures` and a file whose folder only ends in `fixtures` print
  `judge again`, the files named in order and the sha in the brief line, a script staged and one committed alike; so do a plugin's
  `plugin.json` that gains a key beside its new `version`, one that is no JSON, one removed and one the approved head lacks; a sha git lacks and
  a folder outside any repository are named, exit 1;
- `wired`: judge.md, worker.md, protocol.md and the repository's AGENTS.md each send their reader to the rule.

usage: replay-verdict-rule.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SKILL = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "pick-verdict.py"
LISTED = ("fixture-gap", "document", "form", "scope", "release", "other")
MANIFEST = "p/.claude-plugin/plugin.json"
BLOCKING = ("code-fault", "failed-scenario", "not-run")


def listed_line(count):
    return f"approve\nList the {count} gaps under `Fix before merging:`; the worker fixes them and runs `pick-verdict.py --since <this head>` before it merges.\n"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("verdict-rule-") as work:
        box = replay_probe.Sandbox(work)

        def run(*argv, folder="."):
            done = box.python(SCRIPT, *argv, cwd=box.repository / folder)
            return done.returncode, done.stdout, done.stderr

        def write(name, text="x = 1\n"):
            (box.repository / name).parent.mkdir(parents=True, exist_ok=True)
            (box.repository / name).write_text(text)

        for name in ("README.md", "tool.py", "p/fixtures/replay-tool.py", "fixtures/data.txt", "문서.md", "p/q/keep.md"):
            write(name)
        for name in (MANIFEST, "p/plugin.json"):
            write(name, '{"name": "p", "version": "1.0.0"}\n')
        box.git("add", "-A")
        box.git("commit", "-qm", "approved")
        approved = box.git("rev-parse", "HEAD").strip()
        soft = {classes: run("--gaps", *classes) for classes in [(name,) for name in LISTED] + [("document", "document"), LISTED]}
        cases.step("listed", run("--gaps") == (0, "approve\n", "") and soft == {classes: (0, listed_line(len(classes)), "") for classes in soft}, soft)
        hard = {classes: run("--gaps", *classes) for classes in [(name,) for name in BLOCKING] + [("document", "scope", "not-run"), ("failed-scenario", "form"),
                                                                                                 ("not-run", "document", "code-fault", "code-fault")]}
        named = {classes: ", ".join(sorted({name for name in classes if name in BLOCKING})) for classes in hard}
        cases.step("blocking", hard == {classes: (0, f"fix\nA gap of class {named[classes]} sends the change back.\n", "") for classes in hard}, hard)
        usage = (2, "", SCRIPT.read_text().split('"""')[1] + "\n")
        refused = [run(*argv) for argv in (["--gaps", "minor"], ["--gaps", "document", "typo"], ["document"], [], ["--x"], ["--since"],
                                           ["--since", approved, approved], ["--since", "--gaps"], ["--gaps", "--since", approved])]
        cases.step("refused", refused == [usage] * len(refused), refused)
        merge = (0, "merge\nThe fix changes only documents, fixtures and the version, so the approval holds.\n", "")
        unjudged = [run("--since", approved)]
        (box.repository / ".git" / "info").mkdir(exist_ok=True)
        (box.repository / ".git" / "info" / "exclude").write_text("ignored-*.py\n")
        write("ignored-tool.py")
        for name in ("README.md", "문서.md", "p/fixtures/replay-tool.py", "fixtures/data.txt", MANIFEST, "p/q/fixtures/deep/more.py", "docs/new note.md", "docs/새 노트.md"):
            write(name, '{"version": "1.0.1", "name": "p"}\n' if name == MANIFEST else "y = 2\n")
            unjudged += [run("--since", approved), run("--since", approved, folder="p/q")]
        cases.step("unjudged", unjudged == [merge] * len(unjudged), unjudged)
        again = lambda *files: (0, f"judge again\nThe fix changes what no judge read: {', '.join(files)}. Brief the judge with `Last judged: {approved}`.\n", "")
        judged = {}
        write("tool.py", "x = 2\n")
        judged["script"] = run("--since", approved), again("tool.py")
        box.git("add", "-A")
        judged["staged"] = run("--since", approved), again("tool.py")
        box.git("commit", "-qm", "fix")
        judged["committed"] = run("--since", approved), again("tool.py")
        box.git("checkout", "-q", approved, "--", "tool.py")
        box.git("commit", "-qm", "undo")
        judged["undone"] = run("--since", approved), merge
        write("new.py")
        judged["not added"] = run("--since", approved), again("new.py")
        judged["not added, from a folder"] = run("--since", approved, folder="p/q"), again("new.py")
        (box.repository / "new.py").unlink()
        write("p/hooks/new.py")
        judged["not added elsewhere"] = run("--since", approved, folder="docs"), again("p/hooks/new.py")
        (box.repository / "p/hooks/new.py").unlink()
        for name, text in (("a key", '{"name": "p", "version": "1.0.2", "hooks": "h.json"}'), ("no JSON", "version 2"), ("a list", "[1]")):
            write(MANIFEST, text)
            judged[f"manifest: {name}"] = run("--since", approved), again(MANIFEST)
        (box.repository / MANIFEST).unlink()
        judged["manifest: removed"] = run("--since", approved), again(MANIFEST)
        box.git("checkout", "-q", "HEAD", "--", MANIFEST)
        write("r/.claude-plugin/plugin.json", '{"name": "r", "version": "1.0.0"}')
        judged["manifest: new"] = run("--since", approved), again("r/.claude-plugin/plugin.json")
        (box.repository / "r/.claude-plugin/plugin.json").unlink()
        box.git("mv", "tool.py", "tool.md")
        judged["moved"] = run("--since", approved), again("tool.py")
        box.git("reset", "-q", "--hard")
        for name in ("p/plugin.json", "p/myfixtures/data.txt", "a.md.py", "q/fixtures"):
            write(name, '{"name": "p", "version": "1.0.1"}\n' if name == "p/plugin.json" else "z = 3\n")
        judged["near names"] = run("--since", approved), again("a.md.py", "p/myfixtures/data.txt", "p/plugin.json", "q/fixtures")
        code, out, error = run("--since", "nowhere")
        outside = box.python(SCRIPT, "--since", approved, cwd=work)
        cases.step("judged", all(got == expected for got, expected in judged.values()) and (code, out) == (1, "")
                   and re.fullmatch(r"pick-verdict: git cannot read nowhere: \S[^\n]*\n", error) and (outside.returncode, outside.stdout) == (1, "")
                   and re.fullmatch(rf"pick-verdict: git cannot read {approved}: \S[^\n]*\n", outside.stderr), (judged, code, out, error, outside))
    references = SKILL / "references"
    judge, worker, protocol = ((references / name).read_text() for name in ("judge.md", "worker.md", "protocol.md"))
    agents = (pathlib.Path(__file__).resolve().parents[4] / "AGENTS.md").read_text()
    wired = {"judge": "pick-verdict.py](../scripts/pick-verdict.py) `--gaps" in judge and "Fix before merging:" in judge,
             "worker": "pick-verdict.py](../scripts/pick-verdict.py) `--since" in worker, "protocol": "pick-verdict.py" in protocol, "agents": "pick-verdict.py" in agents}
    cases.step("wired", all(wired.values()), wired)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
