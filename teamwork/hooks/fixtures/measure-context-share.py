#!/usr/bin/env python3
"""Print how real teamwork sessions' bill splits into the starting context, each kind of carried tool result and output,
from their transcripts, so a change aims at the parts that cost most and a hook's saving is capped by its part's share.

usage: measure-context-share.py [--since <yyyy-mm-dd>] [--until <yyyy-mm-dd>] [--lines <n>] [--top <n>] [--caps <n>,...] [--projects <dir>] [--rows <file>]

A session is teamwork when its first prompt names `teamwork:kick-off`; its subagents' transcripts count with it, by role
`subagent`, else by the session name's last word (`worker`, `manager`, `sentinel`).
A turn's cost is priced from its usage, relative to a model's input price: uncached input 1, a 5-minute cache write 1.25,
a 1-hour one 2, a cache read 0.1, output 5, times the model's weight (opus 5, sonnet 3, haiku 1).
The starting context of a segment (a session's start, or a compaction) is the first turn's whole context: its cost is
that turn's input side, then a read at 0.1 by every later turn of the segment.
A tool result's tokens are its characters over its kind's measured characters per token: the median, over results of at
least 8,000 characters that arrived alone, of characters to the context growth they caused, per kind with 30 such results,
else over all; smaller results are left out of it since each turn's fixed additions, such as reminders, swamp them. Its cost
is a write at the rate of the turn that took it in, then a read at 0.1 by every later turn of the segment.
A result's kind is its tool, a Bash call's by the first command after any `cd`, variable or `rtk`, a `python3` call's by
its script's name; a large read is a Read with no range, or a shell `cat`, `head`, `tail`, `less`, `more` or `sed -n`,
whose result holds more than `--lines` lines (350, after Spotify's Shunt).
`--caps` prints, per cap of lines, the share a Bash output cap would have saved: a result over the cap keeps its first
four fifths of the cap and its last fifth, plus a one-line note naming the file that holds the rest.
`--rows` writes one JSON row per carried result, to look at by eye."""
import json
import pathlib
import re
import statistics
import sys
from collections import defaultdict

WEIGHT = {"opus": 5.0, "sonnet": 3.0, "haiku": 1.0}
# a read may follow a `cd` or a variable set in the same call, so each `&&` or `;` segment is tried
SHELL_READ = re.compile(r"(?:^|&&|;)\s*(?:rtk\s+read|cat|head|tail|less|more|sed\s+-n)\s")
PREFIX = re.compile(r"^(?:cd\s+\S+|[A-Za-z_][A-Za-z0-9_]*=\S*|export\s+\S+|rtk)$")
TEAMWORK_REFERENCE = re.compile(r"teamwork/skills/[^\"]*(?:references/|SKILL\.md)")
CALIBRATE_MIN = 30
# a file read cut by the cap is fetched again by range, as the output-cap replay showed, so its share is split out
FILE_READS = {"Bash cat", "Bash sed", "Bash head", "Bash tail", "Bash large read"}
CALIBRATE_CHARS = 8000


def weight(model):
    return next((value for key, value in WEIGHT.items() if key in (model or "")), 0.0)


def write_rate(usage):
    return 2.0 if (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) else 1.25


def input_cost(usage):
    creation = usage.get("cache_creation") or {}
    hour = creation.get("ephemeral_1h_input_tokens", 0)
    minutes = creation.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens", 0) - hour)
    return usage.get("input_tokens", 0) + 1.25 * minutes + 2 * hour + 0.1 * usage.get("cache_read_input_tokens", 0)


def context(usage):
    return usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def read_rows(path):
    rows = []
    for line in path.open(errors="replace"):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def first_prompt(rows):
    for row in rows:
        if row.get("type") == "user" and not row.get("isMeta"):
            return text_of(row["message"].get("content"))
    return ""


def session_name(rows):
    return next((row.get("customTitle", "") for row in rows[:5] if row.get("type") == "custom-title"), "")


def kind_of(use, text, lines_cap):
    name, args = use.get("name"), use.get("input") or {}
    if name == "Read":
        return "Read large" if "offset" not in args and "limit" not in args and text.count("\n") + 1 > lines_cap else "Read"
    if name != "Bash":
        return name
    command = args.get("command", "")
    if SHELL_READ.search(command) and text.count("\n") + 1 > lines_cap:
        return "Bash large read"
    for segment in re.split(r"&&|;|\n", command):
        words = segment.split()
        while words and (PREFIX.match(words[0]) or words[0] == "cd"):
            words = words[2:] if words[0] == "cd" else words[1:]
        if not words:
            continue
        if words[0] in ("python3", "python") and len(words) > 1:
            return "Bash python3 " + pathlib.Path(words[1].split("/")[-1]).name
        return "Bash " + pathlib.Path(words[0]).name
    return "Bash"


def turns_of(rows):
    """[(row index, usage, model)] with streamed parts of one message merged to its last usage, and the compaction indexes."""
    seen, compactions = {}, []
    for index, row in enumerate(rows):
        if row.get("type") == "system" and row.get("subtype") == "compact_boundary":
            compactions.append(index)
        if row.get("type") == "assistant" and row["message"].get("usage"):
            message = row["message"]
            first = seen.get(message.get("id") or index, (index,))[0]
            seen[message.get("id") or index] = (first, message["usage"], message.get("model"))
    return sorted(seen.values(), key=lambda item: item[0]), compactions


def walk(rows, lines_cap, caps=()):
    """Per transcript: bill, output cost, start cost, and results as dicts with kind, characters and later turn weights."""
    turns, compactions = turns_of(rows)
    uses, results = {}, []
    for index, row in enumerate(rows):
        if row.get("type") == "assistant":
            for part in row["message"].get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    uses[part["id"]] = part
        if row.get("type") == "user" and isinstance(row["message"].get("content"), list):
            parts = [part for part in row["message"]["content"] if isinstance(part, dict) and part.get("type") == "tool_result"]
            for part in parts:
                results.append((index, part.get("tool_use_id"), text_of(part.get("content")), len(parts) == 1))

    def segment_end(index):
        return next((boundary for boundary in compactions if boundary > index), float("inf"))

    bill = sum(weight(model) * (input_cost(usage) + 5 * usage.get("output_tokens", 0)) for _, usage, model in turns)
    output = sum(weight(model) * 5 * usage.get("output_tokens", 0) for _, usage, model in turns)
    start, starts = 0.0, [-1] + compactions
    for boundary in starts:
        inside = [turn for turn in turns if boundary < turn[0] < segment_end(boundary)]
        if inside:
            first_usage, first_model = inside[0][1], inside[0][2]
            tokens = context(first_usage)
            start += weight(first_model) * input_cost(first_usage)
            start += sum(weight(model) * 0.1 * tokens for _, _, model in inside[1:])
    found = []
    for index, use_id, text, alone in results:
        use = uses.get(use_id)
        if not use:
            continue
        end = segment_end(index)
        later = [turn for turn in turns if index < turn[0] < end]
        if not later:
            continue
        previous = next((turn for turn in reversed(turns) if turn[0] < index), None)
        growth = context(later[0][1]) - context(previous[1]) - previous[1].get("output_tokens", 0) if alone and previous else None
        # a result's weight sum: written once by the first later turn, then read by each turn after it
        factor = weight(later[0][2]) * write_rate(later[0][1]) + sum(weight(model) * 0.1 for _, _, model in later[1:])
        lines = text.split("\n")
        kept = {cap: len("\n".join(lines[:cap * 4 // 5] + lines[-(cap // 5):])) + 80 if len(lines) > cap else len(text)
                for cap in caps} if use.get("name") == "Bash" else {}
        found.append({"kind": kind_of(use, text, lines_cap), "chars": len(text), "kept": kept,
                      "teamwork_reference": bool(TEAMWORK_REFERENCE.search(json.dumps(use.get("input")))), "growth": growth, "factor": factor,
                      "detail": json.dumps(use.get("input"))[:160]})
    return bill, output, start, found


def main(args):
    options = {"--since": "2026-10-01", "--until": "9999", "--lines": "350", "--top": "25", "--caps": "",
               "--projects": str(pathlib.Path.home() / ".claude/projects"), "--rows": None}
    while args:
        if args[0] not in options or len(args) < 2:
            print(__doc__, file=sys.stderr)
            return 2
        options[args[0]], args = args[1], args[2:]
    lines_cap = int(options["--lines"])
    caps = [int(cap) for cap in options["--caps"].split(",") if cap]
    totals, by_role = defaultdict(float), defaultdict(float)
    sessions, rows_out = 0, []
    for path in sorted(pathlib.Path(options["--projects"]).glob("*/*.jsonl")):
        rows = read_rows(path)
        stamp = next((row.get("timestamp", "") for row in rows if row.get("timestamp")), "")
        if not options["--since"] <= stamp[:10] <= options["--until"] or "teamwork:kick-off" not in first_prompt(rows):
            continue
        sessions += 1
        name = session_name(rows)
        role = name.rsplit("-", 1)[-1] if name.rsplit("-", 1)[-1] in ("worker", "manager", "sentinel") else "other"
        transcripts = [(rows, role, str(path))] + [(read_rows(sub), "subagent", str(sub))
                                                    for sub in (path.parent / path.stem / "subagents").glob("agent-*.jsonl")]
        for transcript, who, where in transcripts:
            bill, output, start, found = walk(transcript, lines_cap, caps)
            totals["bill"] += bill
            totals["output"] += output
            totals["start"] += start
            by_role[who] += bill
            rows_out += [{**item, "session": where} for item in found]
    ratios = defaultdict(list)
    for row in rows_out:
        if row["growth"] and row["growth"] > 0 and row["chars"] >= CALIBRATE_CHARS:
            ratios[row["kind"]].append(row["chars"] / row["growth"])
            ratios["all"].append(row["chars"] / row["growth"])
    overall = statistics.median(ratios["all"]) if ratios["all"] else None
    per_kind = {kind: statistics.median(values) for kind, values in ratios.items() if len(values) >= CALIBRATE_MIN}
    by_kind, counts, saved, saved_output = defaultdict(float), defaultdict(int), defaultdict(float), defaultdict(float)
    for row in rows_out:
        cost = row["chars"] / (per_kind.get(row["kind"]) or overall or 1.0) * row["factor"]
        row["cost"] = cost
        for cap, kept in row.get("kept", {}).items():
            cut = cost * (1 - kept / row["chars"]) if row["chars"] else 0.0
            saved[int(cap)] += cut
            saved_output[int(cap)] += 0.0 if row["kind"] in FILE_READS else cut
        by_kind[row["kind"]] += cost
        counts[row["kind"]] += 1
    if options["--rows"]:
        pathlib.Path(options["--rows"]).write_text("".join(json.dumps(row) + "\n" for row in rows_out))
    bill = totals["bill"] or 1.0
    carried = sum(by_kind.values())
    share = lambda value: f"{100 * value / bill:.2f}%"
    print(f"teamwork sessions {options['--since']} to {options['--until']}: {sessions}; bill in input-token units: {totals["bill"]:,.0f}; "
          f"characters per token over all results: {f'{overall:.2f}' if overall else 'none'}")
    print("| part | count | chars per token | share of bill |")
    print("| --- | --- | --- | --- |")
    print(f"| starting context of each segment | | | {share(totals['start'])} |")
    print(f"| output | | | {share(totals['output'])} |")
    print(f"| every tool result carried | {sum(counts.values())} | | {share(carried)} |")
    print(f"| rest: prompts, replies and hook text carried | | | {share(bill - totals['start'] - totals['output'] - carried)} |")
    for kind, value in sorted(by_kind.items(), key=lambda item: -item[1])[:int(options["--top"])]:
        print(f"| result: {kind} | {counts[kind]} | {per_kind.get(kind) or overall or 0:.2f} | {share(value)} |")
    groups = [("teamwork's own reference reads, the lean kick-off's ceiling", lambda row: row["teamwork_reference"]),
              (f"large reads over {lines_cap} lines, the read outline's ceiling", lambda row: row["kind"] in ("Read large", "Bash large read"))]
    for label, member in groups:
        chosen = [row for row in rows_out if member(row)]
        print(f"| result group: {label} | {len(chosen)} | | {share(sum(row['cost'] for row in chosen))} |")
    for cap in caps:
        print(f"| saved by a Bash output cap of {cap} lines | | | {share(saved[cap])} |")
        print(f"| saved by the same cap on program output only, file reads exempt | | | {share(saved_output[cap])} |")
    print("| role | share of bill |")
    print("| --- | --- |")
    for role, value in sorted(by_role.items(), key=lambda item: -item[1]):
        print(f"| {role} | {share(value)} |")
    print("Reading: a change saves at most its part's share; the rest line holds what no tool result or start explains, "
          "and goes negative when the token estimates run high.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
