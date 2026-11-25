#!/usr/bin/env python3
"""Run run-criteria.py `--since` on a temporary git repository whose task covers a Python module, one Markdown section
and one HTML element. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `markdown-section`: a fix to the Markdown section alone names only its criterion to judge again, the module's and the element's unchanged;
- `html-element`: a fix inside the HTML element alone names only its criterion;
- `uncovered-line`: a fix to another Markdown section names every criterion unchanged and the changed line as covered by none;
- `no-covers`: a criterion with no `covers:` is judged again whatever changed;
- `missing-section`: a section the head lacks, or one of a file it lacks, is named and its criterion judged again;
- `subsection`: a fix under a deeper heading inside the Markdown section counts as that section's;
- `removal`: a fix that only removes a line of the Markdown section counts as that section's;
- `unknown-sha`: a sha the repository lacks is named, exit 1, and `--since` beside `--hunks` or `--base` is refused with the usage, exit 2.
- `more-parts`, on a second repository: a folder's cover and a whole file's beside its own section combine in either order;
  nested elements of one tag end at their own end tags; a punctuated heading's anchor; a `#` line in a code fence is no
  heading; a removal at the top of a file; a binary file and a mode change are judged again, a standing criterion always, and a binary file no criterion covers is named; a criterion with no
  `covers:` hides uncovered lines; an uncommitted edit, even a staged one that shifts lines, counts for nothing; only lines no part covers are named, a removal in one
  section leaves the next unchanged, and the last section runs to the file's end.
- `edges`, on a third repository: lines added to one section move the next two down, which are found where the head has them; a fix to a
  heading's own line or to an element's start tag counts as that section's and not as the one before; a deep heading is a section, a
  heading's `-` stays in its anchor, a `#` line in an indented `~~~` fence is no heading, and the line before the next heading is the
  section's last; an element never closed ends with the one around it, and an end tag with nothing open closes nothing; of several elements
  with one `id` the first is the section, a fix to the others covered by none and named by its first line; a renamed file, text or binary,
  changes its old path and adds its new one whole, the lines outside its covered section named; an uncommitted edit to an unchanged file
  counts for nothing; a file whose name holds a `"` and a backslash, or a tab, changes whole, its untouched section too, while a name outside ASCII keeps its sections; a folder covers no file that only starts with its name, and is named once however many of its files changed, one
  with a space in its name among them; a line above a file's covered sections is named; a criterion of several parts names only those
  that changed, each once; a file that is no UTF-8 is read all the same, in a hunk too; a hunk across two sections changes both; a `.htm`
  file is read as HTML; a line that opens with two backticks or two tildes is no fence; and each line reads as the script's usage says, the
  sha short.
Each run that names verdicts exits 0.

usage: replay-part-rejudge.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
CRITERIA = [
    "1. [check] **The module prints its greeting**: `python3 lib/a.py` prints `hi`; on base nothing; covers: `lib/a.py`",
    "2. [check] **The steps name the greeting**: `grep -c hi doc.md` prints `1`; on base `0`; covers: `doc.md#steps`",
    "3. [check] **The intro greets the reader**: `grep -c hello page.html` prints `1`; on base `0`; covers: `page.html#intro`",
]
WHOLE = "4. [check] **The whole tree is checked again**: `true` exits 0; on base 1"
MISSING = "4. [check] **The gone section is checked again**: `true` exits 0; on base 1; covers: `doc.md#gone`"
DOC = "# Doc\n\n## Steps\n\n1. say hi\n2. wait\n\n### Note\n\nwait long\n\n## Rules\n\n- be brief\n- be kind\n"
PAGE = "<html>\n<body>\n<section id=\"intro\">\n<p>hello</p>\n<p>there</p></section>\n<section id=\"end\">\n<p>bye</p>\n</section>\n</body>\n</html>\n"
codes = []


def commit(box, folder, files):
    for name, text in files.items():
        path = pathlib.Path(folder, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    box.git("add", "-A", cwd=folder)
    box.git("commit", "-qm", "round", cwd=folder)
    return box.git("rev-parse", "HEAD", cwd=folder).strip()


def since(box, folder, sha, criteria, *extra):
    body = replay_probe.write_text(box.work, "body.md", "## Definition of done\n\n" + "\n".join(criteria) + "\n")
    out = box.python(SCRIPT, "--since", sha, *extra, body, cwd=folder)
    codes.append(out.returncode)
    return out.stdout + out.stderr


def verdicts(out):
    """{criterion number: 'again' or 'kept'} from the lines `--since` prints."""
    found = {}
    for line in out.splitlines():
        head, _, rest = line.partition(": ")
        if head.isdigit() and rest.startswith(("judge again", "unchanged")):
            found[int(head)] = "again" if rest.startswith("judge again") else "kept"
    return found


NESTED = "<div id=\"outer\">\n<div id=\"inner\">\n<p>a</p>\n</div>\n<p>b</p>\n</div>\n"
FENCED = "# Guide\n\n## Q&A: setup\n\n```sh\n# a comment\nls\n```\n\nafter the fence\n\n## Last\n\nend\n"
MORE = [
    "1. [check] **The tools work**: `true` exits 0; on base 1; covers: `tools/`",
    "2. [check] **The guide's setup holds**: `true` exits 0; on base 1; covers: `guide.md#qa-setup`",
    "3. [check] **The guide holds**: `true` exits 0; on base 1; covers: `guide.md`",
    "4. [check] **The inner box holds**: `true` exits 0; on base 1; covers: `box.html#inner`",
    "5. [check] **The logo holds**: `true` exits 0; on base 1; covers: `logo.bin`",
    "6. [check] **The top holds**: `true` exits 0; on base 1; covers: `top.md#top`",
    "7. [check] **The mode holds**: `true` exits 0; on base 1; covers: `mode.md#mode`",
    "8. [check] **The second section holds**: `true` exits 0; on base 1; covers: `cut.md#b`",
]
CUT = "# A\n\na1\na2\n\n# B\n\nb\n"


def more_parts(cases, box):
    folder = box.init(box.work / "more", commit=False)
    top = "# Top\n\nfirst\n\nsecond\n"
    first = commit(box, folder, {"tools/run.py": "x = 1\n", "guide.md": FENCED, "box.html": NESTED, "logo.bin": "a\0b", "top.md": top, "mode.md": "# Mode\n", "cut.md": CUT, "other.bin": "a\0b",
                                 ".teamwork/default-criteria.md": "1. [check] **The tree builds**: `true` exits 0; on base 1\n"})
    commit(box, folder, {"tools/run.py": "x = 2\n", "guide.md": FENCED.replace("after the fence", "after the fence, edited").replace("end", "end, edited"),
                         "box.html": NESTED.replace("<p>b</p>", "<p>b, edited</p>"), "logo.bin": "a\0c", "top.md": top.replace("# Top\n\nfirst\n", "# Top\n").replace("second", "second, edited"), "other.bin": "a\0c",
                         "cut.md": CUT.replace("a1\n", "")})
    pathlib.Path(folder, "mode.md").chmod(0o755)
    box.git("commit", "-qam", "mode", cwd=folder)
    pathlib.Path(folder, "box.html").write_text("<p>uncommitted</p>\n" * 3 + NESTED.replace("<p>b</p>", "<p>b, edited</p>"))
    box.git("add", "-A", cwd=folder)
    reverse = [MORE[2].replace("3.", "2."), MORE[1].replace("2.", "3.")]
    out = since(box, folder, first, MORE) + since(box, folder, first, [MORE[0], *reverse, *MORE[3:]])
    expected = {1: "again", 2: "again", 3: "again", 4: "kept", 5: "again", 6: "again", 7: "again", 8: "kept"}
    both = [verdicts(part) for part in re.split(r"^since \w+: ", out, flags=re.M)[1:]]
    outer = since(box, folder, first, MORE + ["9. [check] **The outer box holds**: `true` exits 0; on base 1; covers: `box.html#outer`"])
    hidden = since(box, folder, first, MORE + [WHOLE.replace("4.", "9.")])
    cases.step("more-parts", both == [expected, expected] and "standing 1: judge again" in out and "Traceback" not in out
               and re.findall(r"^(\S+): covered by no criterion", out, re.M) == ["box.html:5", "cut.md:2", "other.bin:1"] * 2 and verdicts(outer).get(9) == "again" and "other.bin:1: covered by no criterion" in out and "mode.md:" not in out
               and "box.html:" not in outer and "covered by no criterion" not in hidden, (outer, hidden))


MOVED = "# A\n\na1\n\n# B\n\nb1\n\n# C\n\nc1\nc2\n"
TITLED = "# Head\n\n## Steps\n\none\n\n## Rules\n\ntwo\n"
TAGGED = "<body>\n<section id=\"intro\">\n<p id=\"lead\">hello\n<p>more</p>\n</section>\n<div id=\"late\">\n</p>\n<p>bye</p>\n</div>\n</body>\n"
SPANNED = "# A\n\na1\n# B\n\nb1\n"
TWINS = "<p id=\"twin\">one</p>\n<p id=\"twin\">two</p>\n<p id=\"twin\">three</p>\n"
DASHED = "# Guide\n\n### Set-up steps\n\n  ~~~\n## Other\n  ~~~\n\n``two`` ticks\n~~two~~ waves\nafter\n## End\n\nend\n"
RENAMED = "# One\n\ntwo\n\n# Three\n\nfour\nfive\nsix\nseven\n"
# each criterion's `covers:` parts, its verdict, and the parts its line names as changed
QUOTED = 'qu"ote\\d.md'
EDGES = [("`moved.md#a`", "again", "`moved.md#a`"), ("`moved.md#b`", "kept", ""), ("`moved.md#c`", "again", "`moved.md#c`"),
         ("`titled.md#steps`", "kept", ""), ("`titled.md#rules`", "again", "`titled.md#rules`"),
         ("`tagged.html#intro`", "again", "`tagged.html#intro`"), ("`tagged.html#lead`", "kept", ""), ("`tagged.html#late`", "again", "`tagged.html#late`"),
         ("`twins.htm#twin`", "kept", ""), ("`dashed.md#set-up-steps`", "again", "`dashed.md#set-up-steps`"),
         ("`old.md`", "again", "`old.md`"), ("`old.bin`", "again", "`old.bin`"), ("`still.md`", "kept", ""), ("`part/`", "kept", ""), ("`mix/`", "again", "`mix/`"),
         ("`moved.md#a`, `moved.md#b`, `moved.md#c`", "again", "`moved.md#a`, `moved.md#c`"), ("`raw.md#raw`", "again", "`raw.md#raw`"), ("`new.md#three`", "again", "`new.md#three`"),
         ("`spanned.md#a`", "again", "`spanned.md#a`"), ("`spanned.md#b`", "again", "`spanned.md#b`"), ("`spanned.md#a`, `still.md`", "again", "`spanned.md#a`"),
         (f"`{QUOTED}#a`", "again", f"`{QUOTED}#a`"), ("`ta\tb.md`", "again", "`ta\tb.md`"),
         ("`한글.md#a`", "kept", ""), ("`한글.md#b`", "again", "`한글.md#b`")]


def edges(cases, box):
    folder = box.init(box.work / "edges", commit=False)
    box.git("config", "diff.noprefix", "true", cwd=folder)  # a reader's own diff settings change no header the script reads
    pathlib.Path(folder, "raw.md").write_bytes(b"# Raw\n\n\xff\n")
    first = commit(box, folder, {"moved.md": MOVED, "titled.md": TITLED, "tagged.html": TAGGED, "twins.htm": TWINS, "spanned.md": SPANNED, "dashed.md": DASHED, "old.md": RENAMED, "old.bin": "a\0b",
                                 "still.md": "still\n", "part/a.txt": "a\n", "partial.txt": "a\n", "mix/a b.txt": "a\n", "mix/b.txt": "b\n", QUOTED: SPANNED, "ta\tb.md": "a\n", "한글.md": SPANNED})
    box.git("mv", "old.md", "new.md", cwd=folder)
    box.git("mv", "old.bin", "new.bin", cwd=folder)
    pathlib.Path(folder, "raw.md").write_bytes(b"# Raw\n\n\xff\xfe\n")
    short = box.git("rev-parse", "--short", first, cwd=folder).strip()
    commit(box, folder, {"moved.md": MOVED.replace("a1\n", "a1\na2\na3\na4\n").replace("c1", "c1, edited"), "titled.md": TITLED.replace("# Head", "# Head.").replace("## Rules", "## Rules."),
                         "tagged.html": TAGGED.replace("id=\"intro\"", "id=\"intro\" class=\"lead\"").replace("bye", "bye, edited"),
                         "twins.htm": TWINS.replace("two", "two, edited").replace("three", "three, edited"), "dashed.md": DASHED.replace("after", "after, edited").replace("\nend\n", "\nend, edited\n"),
                         "new.md": RENAMED.replace("four", "four, edited"), "partial.txt": "b\n", "mix/a b.txt": "a, edited\n", "mix/b.txt": "b, edited\n",
                         "spanned.md": SPANNED.replace("a1\n# B", "a1, edited\n# B."), QUOTED: SPANNED.replace("b1", "b1, edited"), "ta\tb.md": "b\n",
                         "한글.md": SPANNED.replace("b1", "b1, edited")})
    pathlib.Path(folder, "still.md").write_text("uncommitted\n")
    out = since(box, folder, first, [f"{n}. [check] **Part {n} holds**: `true` exits 0; on base 1; covers: {parts}" for n, (parts, _, _) in enumerate(EDGES, 1)])
    lines = [f"{n}: judge again: {changed} changed" if verdict == "again" else f"{n}: unchanged since {short}: keep its verdict" for n, (_, verdict, changed) in enumerate(EDGES, 1)]
    cases.step("edges", out.splitlines()[:len(EDGES) + 1] == [f"since {short}: 17 files changed", *lines]
               and re.findall(r"^(\S+): covered by no criterion", out, re.M) == ["dashed.md:14", "new.bin:1", "new.md:1", "partial.txt:1", "titled.md:1", "twins.htm:2"]
               and "which the head lacks" not in out, out)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("part-rejudge-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        folder = box.repository
        first = commit(box, folder, {"lib/a.py": "print('hi')\n", "doc.md": DOC, "page.html": PAGE})
        second = commit(box, folder, {"doc.md": DOC.replace("2. wait", "2. wait a moment")})
        out = since(box, folder, first, CRITERIA)
        cases.step("markdown-section", verdicts(out) == {1: "kept", 2: "again", 3: "kept"} and "covered by no criterion" not in out, out)
        third = commit(box, folder, {"page.html": PAGE.replace("<p>there</p></section>", "<p>there, friend</p></section>")})
        out = since(box, folder, second, CRITERIA)
        cases.step("html-element", verdicts(out) == {1: "kept", 2: "kept", 3: "again"} and "covered by no criterion" not in out, out)
        commit(box, folder, {"doc.md": DOC.replace("2. wait", "2. wait a moment").replace("- be kind", "- be kind always")})
        out = since(box, folder, third, CRITERIA)
        cases.step("uncovered-line", verdicts(out) == {1: "kept", 2: "kept", 3: "kept"} and "doc.md:15: covered by no criterion" in out, out)
        out = since(box, folder, first, CRITERIA + [WHOLE])
        cases.step("no-covers", verdicts(out).get(4) == "again" and verdicts(out).get(1) == "kept", out)
        out = since(box, folder, third, CRITERIA + [MISSING])
        absent = since(box, folder, third, CRITERIA + [MISSING.replace("doc.md", "absent.md")])
        cases.step("missing-section", verdicts(out).get(4) == "again" and "covers `doc.md#gone`, which the head lacks" in out
                   and verdicts(absent).get(4) == "again" and "covers `absent.md#gone`, which the head lacks" in absent, (out, absent))
        cases.step("exits", codes == [0] * len(codes), codes)
        steps = DOC.replace("2. wait", "2. wait a moment").replace("- be kind", "- be kind always")
        fourth = commit(box, folder, {"doc.md": steps.replace("wait long", "wait longer")})
        out = since(box, folder, fourth + "~1", CRITERIA)
        cases.step("subsection", verdicts(out) == {1: "kept", 2: "again", 3: "kept"} and "covered by no criterion" not in out, out)
        commit(box, folder, {"doc.md": steps.replace("wait longer", "wait long").replace("1. say hi\n", "")})
        out = since(box, folder, fourth, CRITERIA)
        cases.step("removal", verdicts(out).get(2) == "again" and "covered by no criterion" not in out, out)
        codes.clear()
        out = since(box, folder, "0" * 40, CRITERIA)
        refused = [since(box, folder, first, CRITERIA, other) for other in ("--hunks", "--base")]
        cases.step("unknown-sha", codes == [1, 2, 2] and all("\nusage: run-criteria.py " in text for text in refused) and out == f"run-criteria: --since {'0' * 40} names no commit here\n", (codes, out, refused))
        more_parts(cases, box)
        edges(cases, box)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
