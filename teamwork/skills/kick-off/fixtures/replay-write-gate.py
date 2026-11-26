#!/usr/bin/env python3
"""Check that only the owner's own words record an owner decision, that each role writes only the records the gate's table lets it, and that only a
change's own worker closes it, on a scratch git board with a worker, a manager, a sentinel and a session in no team, each started as its name, under a
stand-in `claude`, with a transcript of what a person typed into it; print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS write gate`
or `FAIL write gate`, and exit 1 on any failure:
- `worker-quote`, `manager-quote`: `decide --by owner --owner-said <file>` with words the owner never typed, which a worker sent the manager as a message,
  exits 2 and posts nothing;
- `manager-peer-word`: the same with the whole text of another session's message, the one word `human`, exits 2 and posts nothing;
- `manager-kickoff`: the same with the words of the kick-off prompt herdr typed into the manager exits 2 and posts nothing;
- `nameless-unrecorded`, `nameless-garbled`, `nameless-listed`: a decision by a session started with no name, whose session has no recorded name, one
  that is no JSON, or a JSON list, exits 2 naming the missing name;
- `capital-relays-Manager`, `capital-relays-manager`: a session named `Probe-Manager` or `Probe-manager`, no name of a role, relaying typed words exits 2,
  the refusal calling it in no team;
- `nameless-relays`: such a session's owner decision exits 2, the refusal calling it this session, in no team;
- `worker-span`, `manager-span`: `decide --by owner` with a double-quoted span and no `--owner-said` exits 2 and posts nothing;
- `worker-as-manager`: a worker's `decide --by <the manager>` exits 2 and posts nothing;
- `said-without-owner`: `decide --owner-said <file>` without `--by owner` exits 2 and posts nothing;
- `one-shot-relays`, `outsider-relays`, `sentinel-relays`: words the owner typed, relayed by a `claude -p` run started as the worker, by a session in no
  team and by a sentinel, exit 2 and post nothing;
- `manager-holds`: a manager's `hold` names the holders; `sentinel-hold`: a sentinel's exits 2 naming the gate and changes nothing;
- `sentinel-decides`, `sentinel-<verb>` for `file`, `edit`, `title`, `resolve`, `reopen`, `label` and `depend`: each exits 2 naming the gate and changes nothing;
- `raw-as-manager`: a worker's decision by the manager's name written past `use-board.py`, by the board module, is refused and changes nothing;
- `raw-past-gate`: the board module refuses a write of the git board it does not pass through the gate, and changes nothing;
- `manager-relays`, `worker-relays`: a manager, then a worker, relaying words the owner typed in its own session, the manager's typed across two lines and its file's words split by a blank line and between blank lines and spaces, each line quoted once and trimmed, records `by: owner` with the words as `>` lines,
  the board commit by its name; `worker-relays-blocks`: so are words typed as a prompt of text blocks, in a transcript that also holds a line of no
  JSON, a row with no origin or message and a block that is no object;
- `fenced-quote`: a relay whose `--text` holds a `>` line in a backtick block inside a longer one and in a `~~~` block records it after the owner's words, the fenced line no quote of the owner;
- `nameless-files`: a session started with no name and no recorded one files a task, the commit by `teamwork`;
- `outsider-records`, `record-no-id`: a session in no team records a worker's name as its own, and a session with no id records nothing;
- `recorded-name`: a worker started as its name, whose session a past rename recorded as another worker's, decides by the name it was started with, its decision trimmed;
- `renamed-writer`: the same session started with no name decides by the name the rename recorded;
- `rename-role`: `replay-own-readers.py` passes, among its cases a worker's rename to a manager's name refused as changing its role;
- `close`: `replay-local-landing.py --case closed` passes: a worker closes its own change unmerged, another worker's close, a close with a blank reason and a
  second close and a merge of the closed change are refused.

usage: replay-write-gate.py"""
import json
import pathlib
import re
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
LANDING = SKILL / "fixtures" / "replay-local-landing.py"
READERS = SKILL / "fixtures" / "replay-own-readers.py"
LIB = SKILL.parents[1] / "lib"
REF = "refs/teamwork-blackboard"
TYPED = "ship the probe on friday, not before"
FORGED = "the owner wants the probe shipped today"
WORD = "human"  # a message of just this word holds `"human"` as a typed row does, so only the row's kind tells them apart
LISTED = "ship the probe after the review"  # typed as a prompt of text blocks, as one with an image is kept
KICKOFF = "worker probe-worker manager probe-manager ship the probe tonight"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("write-gate-") as work:
        return replay(replay_probe.Sandbox(work), work)


def replay(box, work):
    cases = replay_probe.Cases("write gate")
    said = {"padded": replay_probe.write_text(work, "padded.txt", "\n" + TYPED.replace(", ", ",\n\n") + "  \n\n")}
    said |= {name: replay_probe.write_text(work, f"{name}.txt", text + "\n") for name, text in (("typed", TYPED), ("forged", FORGED), ("kickoff", KICKOFF), ("word", WORD), ("listed", LISTED))}
    worker = box.session("probe-worker", TYPED)
    manager = box.session("probe-manager", f"Run the teamwork:kick-off skill with these arguments: {KICKOFF}", TYPED.replace(", ", ",\n  "), ("peer", FORGED), ("peer", WORD))
    sentinel = box.session("probe-sentinel", TYPED)
    outsider = box.session("probe-owner", TYPED)
    capitals = {name: box.session(name, TYPED) for name in ("Probe-Manager", "Probe-manager")}
    one_shot = {**worker, "claude": ["-p", "--name", "probe-worker"]}
    rows = ("not a row", {"type": "user", "origin": None, "message": None}, {"type": "user", "origin": {"kind": "human"}, "message": None},
            {"type": "user", "origin": {"kind": "human"}, "message": {"role": "user", "content": ["a bare string", {"type": "text", "text": LISTED}]}})
    with (box.config / "projects" / "sandbox" / f"{worker['CLAUDE_CODE_SESSION_ID']}.jsonl").open("a") as transcript:
        transcript.write("".join((row if isinstance(row, str) else json.dumps(row)) + "\n" for row in rows))
    nameless = {name: {"claude": [], "CLAUDE_CODE_SESSION_ID": f"00000000-0000-4000-8000-00000000000{n}"} for n, name in enumerate(("unrecorded", "garbled", "listed"))}
    names = box.config / "teamwork" / "session-names"
    names.mkdir(parents=True, exist_ok=True)
    (names / f"{nameless['garbled']['CLAUDE_CODE_SESSION_ID']}.json").write_text("{not json")
    (names / f"{nameless['listed']['CLAUDE_CODE_SESSION_ID']}.json").write_text("[]")

    def use(session, *argv):
        return box.python(USE, *map(str, argv), **session)

    def ref():
        return box.git("rev-parse", "-q", "--verify", REF).strip()

    def last(task):
        paths = [path for path in box.git("ls-tree", "-r", "--name-only", REF).split() if re.search(rf"(^|/){task}/comments/\d+\.json$", path)]
        return json.loads(box.git("show", f"{REF}:{max(paths)}")) if paths else {}

    def refused(case, session, why, *argv, run=None):
        before = ref()
        done = run() if run else use(session, *argv)
        cases.step(case, done.returncode != 0 and why in done.stderr and ref() == before, f"exit {done.returncode}, board moved {ref() != before}: {done.stderr}")

    filed = [use(manager, "file", "--title", title, "--body", replay_probe.write_text(work, "body.md", replay_probe.BODY)) for title in ("Probe the write gate", "Probe a spare task")]
    if any(done.returncode for done in filed):
        return replay_probe.fail(f"the tasks were not filed: {[done.stderr for done in filed]}")
    task, spare = (done.stdout.strip().rsplit("/", 1)[-1] for done in filed)
    span = ("--decision", 'use the "fast" mode for exports.', "--by", "owner")
    unsaid = "no words the owner typed"
    barred = {"owner decision": "only manager, worker may", "decision": "only manager, worker, a session in no team may"}
    for case, session, why, argv in (("worker-quote", worker, unsaid, ("--decision", "ship it today.", "--by", "owner", "--owner-said", said["forged"])),
                                     ("manager-quote", manager, unsaid, ("--decision", "ship it today.", "--by", "owner", "--owner-said", said["forged"])),
                                     ("manager-peer-word", manager, unsaid, ("--decision", "ship it today.", "--by", "owner", "--owner-said", said["word"])),
                                     ("manager-kickoff", manager, unsaid, ("--decision", "ship it tonight.", "--by", "owner", "--owner-said", said["kickoff"])),
                                     ("worker-span", worker, "nothing posted", span), ("manager-span", manager, "nothing posted", span),
                                     ("worker-as-manager", worker, "nothing posted", ("--decision", "ship it today.", "--by", "probe-manager")),
                                     ("said-without-owner", worker, "goes only with `--by owner`", ("--decision", "ship it on friday.", "--owner-said", said["typed"])),
                                     ("one-shot-relays", one_shot, unsaid, ("--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"])),
                                     ("outsider-relays", outsider, f"probe-owner (in no team) may not write an owner decision on #{task}: {barred['owner decision']}", ("--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"])),
                                     ("sentinel-relays", sentinel, f"probe-sentinel (sentinel) may not write an owner decision on #{task}: {barred['owner decision']}", ("--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"])),
                                     ("sentinel-decides", sentinel, f"probe-sentinel (sentinel) may not write a decision on #{task}: {barred['decision']}", ("--decision", "ship it on friday.",)),
                                     *((f"capital-relays-{name.split('-')[1]}", session, f"{name} (in no team) may not write an owner decision on #{task}: {barred['owner decision']}",
                                        ("--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"])) for name, session in capitals.items()),
                                     ("nameless-relays", nameless["unrecorded"], f"this session (in no team) may not write an owner decision on #{task}: {barred['owner decision']}",
                                      ("--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"])),
                                     *((f"nameless-{name}", session, "no session name tells who decides", ("--decision", "ship it on friday.")) for name, session in nameless.items())):
        refused(case, session, why, "decide", task, *argv)

    body = box.python(USE, "read", task, "--body", **manager).stdout
    edited = replay_probe.write_text(work, "edited.md", body.replace("Do it.", "Do it twice."))
    base = re.search(r"body sha:? `?([0-9a-f]{12})", box.python(USE, "read", task, **manager).stdout)
    for verb, argv in (("file", ("file", "--title", "Probe a sentinel's task", "--body", work / "body.md")),
                       ("edit", ("edit", task, "--body", edited, "--reason", "says to do it twice", "--base", base and base.group(1))),
                       ("title", ("title", task, "--title", "Probe the gate again")),
                       ("resolve", ("resolve", spare, "--summary", "The spare task is done.")),
                       ("label", ("label", task, "--label", "probe")),
                       ("depend", ("depend", task, "--depends", spare))):
        place = "the board" if verb == "file" else f"#{argv[1]}"
        refused(f"sentinel-{verb}", sentinel, f"probe-sentinel (sentinel) may not write {'an' if verb[0] in 'aeiou' else 'a'} {verb} on {place}: only manager, worker, a session in no team may", *argv)
    refused("sentinel-hold", sentinel, f"probe-sentinel (sentinel) may not write a hold on #{task}: only manager, worker, a session in no team may", "hold", task, "--holders", "probe-sentinel")
    done = use(manager, "hold", task, "--holders", "probe-worker")
    cases.step("manager-holds", done.returncode == 0 and last(task).get("holders") == ["probe-worker"], f"exit {done.returncode} {done.stderr}; stored {last(task)}")
    resolved = use(manager, "resolve", spare, "--summary", "The spare task is done.")
    if resolved.returncode:
        return replay_probe.fail(f"the manager did not resolve the spare task: {resolved.stderr}")
    refused("sentinel-reopen", sentinel, "may not write a reopen", "reopen", spare)
    raw = f"import board; board.comment({task}, 'ANSWER: ship it today.', {{'decision': 'ship it today.', 'by': 'probe-manager'}})"
    refused("raw-as-manager", worker, "a decision is its writer's own", run=lambda: box.run([sys.executable, "-c", raw], PYTHONPATH=str(LIB), **worker))
    refused("raw-past-gate", worker, "board has no author", run=lambda: box.run([sys.executable, "-c", "import board; board.author('probe-manager')"], PYTHONPATH=str(LIB), **worker))

    for case, session, name, words in (("manager-relays", manager, "probe-manager", TYPED), ("worker-relays", worker, "probe-worker", TYPED),
                                       ("worker-relays-blocks", worker, "probe-worker", LISTED)):
        done = use(session, "decide", task, "--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["padded" if session is manager else "typed" if words == TYPED else "listed"])
        stored = last(task) if done.returncode == 0 else {}
        author = box.git("log", "-1", "--format=%an", REF).strip()
        quoted = "> " + (words.replace(", ", ",\n>\n> ") if session is manager else words)
        cases.step(case, stored.get("by") == "owner" and f"ship it on friday.\n\n{quoted}\n" in stored.get("text", "") + "\n" and " \n" not in stored.get("text", "")
                   and author == name,
                   f"exit {done.returncode} {done.stderr}; stored {stored}; author {author}")
    fenced = replay_probe.write_text(work, "fenced.md", "The export printed:\n\n````\n```\n> exported 3 files\n```\n````\n\n~~~\n> exported 4 files\n~~~\n")
    done = use(manager, "decide", task, "--decision", "ship it on friday.", "--by", "owner", "--owner-said", said["typed"], "--text", fenced)
    stored = last(task) if done.returncode == 0 else {}
    cases.step("fenced-quote", stored.get("by") == "owner" and f"> {TYPED}\n\nThe export printed:\n\n````\n```\n> exported 3 files\n```\n````\n\n~~~\n> exported 4 files\n~~~" in stored.get("text", ""), f"exit {done.returncode} {done.stderr}; stored {stored}")

    (names / f"{worker['CLAUDE_CODE_SESSION_ID']}.json").write_text(json.dumps({"name": "probe-renamed-worker"}))
    done = use(worker, "decide", task, "--decision", "  ship it on monday. ")
    stored = last(task) if done.returncode == 0 else {}
    cases.step("recorded-name", stored.get("by") == "probe-worker" and stored.get("decision") == "ship it on monday.", f"exit {done.returncode} {done.stderr}; stored {stored}")
    done = use({**worker, "claude": []}, "decide", task, "--decision", "ship it on tuesday.")
    stored = last(task) if done.returncode == 0 else {}
    cases.step("renamed-writer", stored.get("by") == "probe-renamed-worker", f"exit {done.returncode} {done.stderr}; stored {stored}")

    done = use(nameless["unrecorded"], "file", "--title", "Probe a nameless task", "--body", work / "body.md")
    author = box.git("log", "-1", "--format=%an", REF).strip()
    cases.step("nameless-files", done.returncode == 0 and author == "teamwork", f"exit {done.returncode} {done.stderr}; author {author}")
    done = box.run([sys.executable, "-c", "import board_writers; board_writers.record('probe-new-worker')"], PYTHONPATH=str(LIB), **outsider)
    kept = sorted(path.name for path in names.iterdir())
    done = box.run([sys.executable, "-c", "import board_writers; board_writers.record('probe-new-worker')"], PYTHONPATH=str(LIB), **{**outsider, "CLAUDE_CODE_SESSION_ID": ""})
    cases.step("record-no-id", done.returncode == 0 and sorted(path.name for path in names.iterdir()) == kept, f"exit {done.returncode} {done.stderr}; kept {sorted(path.name for path in names.iterdir())}")
    cases.step("outsider-records", done.returncode == 0 and (names / f"{outsider['CLAUDE_CODE_SESSION_ID']}.json").is_file(), f"exit {done.returncode} {done.stderr}")

    readers = subprocess.run([sys.executable, str(READERS)], capture_output=True, text=True)
    cases.step("rename-role", readers.returncode == 0 and "ok rename-role" in readers.stdout.splitlines(), readers.stdout + readers.stderr)
    closed = subprocess.run([sys.executable, str(LANDING), "--case", "closed"], capture_output=True, text=True)
    cases.step("close", closed.returncode == 0 and closed.stdout.strip().endswith("PASS"), closed.stdout + closed.stderr)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
