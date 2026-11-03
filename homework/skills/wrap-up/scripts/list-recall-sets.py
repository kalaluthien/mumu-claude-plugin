#!/usr/bin/env python3
"""List what is left to mark in dream's replay: per case, the instruction files and each distinct set of memory files the candidates recalled.

usage: list-recall-sets.py <dejavu> [--config <dir>]   reads <dejavu>/friction.jsonl, <dejavu>/candidates/<name>/,
                                                      <dejavu>/picks/<name>/*.jsonl and <dejavu>/marks/*.jsonl; per
                                                      case still unmarked, one `case <id>: <what went wrong> | owner:
                                                      <quote>` line, an `instructions <file>...` line while those are
                                                      unmarked, and a `set <key> <file>...` line per unmarked set, then
                                                      `batch <k>: <id>...` lines of at most 10 cases, one mark judge each

The instruction files are the config's CLAUDE.md and rules/ (--config, else ${CLAUDE_CONFIG_DIR:-~/.claude}) and the
case's repository AGENTS.md and CLAUDE.md: they load alike for every candidate, so they are marked once per case, and a
lesson a candidate copies from them gains nothing. A set is keyed by what its files say, so candidates that recall the
same text share one mark, and a set already marked is not listed again.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import claude_config  # noqa: E402
import replay_cases  # noqa: E402

BATCH = 10


def main(args):
    config = claude_config.folder()
    if len(args) == 3 and args[1] == "--config":
        config, args = pathlib.Path(args[2]), args[:1]
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    dejavu = pathlib.Path(args[0])
    cases = replay_cases.load(dejavu, config)
    picked = {candidate: replay_cases.picks(dejavu, candidate.name) for candidate in replay_cases.candidates(dejavu)}
    marked = replay_cases.marks(dejavu)
    listed, sets = [], 0
    for item in cases:
        lines = []
        if (item["id"], replay_cases.INSTRUCTIONS) not in marked:
            lines.append("instructions " + " ".join(str(path) for path in item["instructions"]))
        seen = set()
        for candidate, found in picked.items():
            files = found.get(item["id"])
            key = replay_cases.recall_set(candidate, files)
            if key and key not in seen and (item["id"], key) not in marked:
                seen.add(key)
                lines.append(f"set {key} " + " ".join(str(candidate / file) for file in sorted(set(files))))
        if lines:
            listed.append(item["id"])
            sets += len(seen)
            print(f"case {item['id']}: {replay_cases.flat(item.get('what_went_wrong'))} | owner: "
                  f"{replay_cases.flat(item.get('quote'))}")
            print("\n".join(lines))
    for start in range(0, len(listed), BATCH):
        print(f"batch {start // BATCH + 1}: " + " ".join(listed[start:start + BATCH]))
    print(f"{len(listed)} cases left to mark, {sets} recall sets among them: give each batch to one mark judge; a case "
          "whose picks are missing gets no set, and counts as missing in score-memory.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
