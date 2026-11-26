#!/usr/bin/env python3
"""Run test-gap-features.py on the kept table of past `fix` rounds and on tables made from it. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `history`: the kept table holds at least 150 rounds of at least 30 changes with a known later outcome; the script prints its counts,
  the missed rate with a 95% interval within 0.012 of the one this runner finds by resampling the changes, and the price of a fault
  from that interval's ends; then a line per feature (first round; 1, 2 to 3, 4 or more gaps; under 200, under 600 or more lines, a round of
  unknown size left out; each gap class) with the missed rounds of each value as this runner counts them, and ends
  `no feature predicts`, which is what the judge's flat verdict rule rests on; a second run prints the same;
- `planted`: the same table with `missed` planted on every round naming a document gap prints that class as predicting, its gain
  within 0.02 of the variance a perfect feature removes and reached by 0 of 400 shuffles, and one with `missed` planted on every round
  of four or more gaps names the gap count among the features that predict;
- `shuffled`: the kept table with its outcomes dealt again at random, by three seeds, ends `no feature predicts` each time;
- `few`: a planted class that 10 rounds name predicts and one that 9 name does not, and a class only one change names, whose rounds all missed, prints `no signal` with a gain
  between 0 and 0.01, since no fold can learn it;
- `one`: a table with one missed round, one with one round not missed and one whose two rounds are of one change, which leaves a
  fold nothing to learn from so every shuffle ties each gain, still print a rate, and the first with no upper price;
- `refused`: a missing table, an empty one, one with no missed round, one with every round missed, a row with too few columns, a
  round that is no number, a second argument and an option print the usage, exit 2.

usage: replay-gap-features.py"""
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SKILL = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "references" / "judge" / "scripts" / "test-gap-features.py"
TABLE = SKILL / "assets" / "soft-rounds.tsv"
FEATURE = r"(predicts|no signal): ([^;]+); missed ([^;]+); Brier gain ([+-]\d\.\d{4}), reached by (\d+) of 400 shuffles"


def counted(rows, value):
    """The `<value>: <missed> of <rounds>` text of ROWS grouped by VALUE, a round it gives None left out."""
    groups = {}
    for row in rows:
        if row[2] != "unknown" and value(row) is not None:
            groups.setdefault(value(row), []).append(row[2] == "missed")
    return ", ".join(f"{key}: {sum(group)} of {len(group)}" for key, group in sorted(groups.items(), key=lambda pair: str(pair[0])))


def band(number, edges):
    return sum(number >= edge for edge in edges)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    header, *rows = [line.split("\t") for line in TABLE.read_text().splitlines()]
    with replay_probe.scratch("gap-features-") as work:
        box = replay_probe.Sandbox(work)

        def run(*argv):
            done = box.python(SCRIPT, *argv, cwd=work)
            return done.returncode, done.stdout, done.stderr

        def table(name, later, rows=rows):
            """A copy of ROWS whose known outcomes LATER gives, by row and index."""
            lines = [header] + [row[:2] + [later(row, index) if row[2] != "unknown" else "unknown"] + row[3:] for index, row in enumerate(rows)]
            return str(replay_probe.write_text(work, name, "".join("\t".join(line) + "\n" for line in lines)))

        def features(out):
            return {found[2]: found.groups() for found in map(re.compile(FEATURE).fullmatch, out.splitlines()[3:-1]) if found}

        code, out, error = run()
        lines = out.splitlines()
        known = [row for row in rows if row[2] != "unknown"]
        missed = [row for row in known if row[2] == "missed"]
        sampler = random.Random(7)
        by_change = {}
        for row in known:
            by_change.setdefault(row[0], []).append(row[2] == "missed")
        draws = []
        for _ in range(20000):
            drawn = [label for group in sampler.choices(list(by_change.values()), k=len(by_change)) for label in group]
            draws.append(sum(drawn) / len(drawn))
        low, high = sorted(draws)[500], sorted(draws)[19500]
        first = re.fullmatch(r"(\d+) past `fix` rounds named no code fault or failed scenario; (\d+) have no known later outcome\.", lines[0]) if lines else None
        rate = re.fullmatch(r"missed: (\d+) of (\d+) rounds in (\d+) of (\d+) changes, rate (0\.\d\d), 95% interval (0\.\d\d) to (0\.\d\d) by resampling changes\.", lines[1]) if first else None
        price = re.fullmatch(r"Another round pays only when a fault on main costs more than (\d+\.\d) to (\d+\.\d) judge rounds\.", lines[2]) if rate else None
        expected = {"first round": counted(rows, lambda row: row[1] == "1"),
                    "gaps (1, 2 to 3, 4 or more)": counted(rows, lambda row: band(sum(map(int, row[4:])), (2, 4))),
                    "lines (under 200, under 600, more)": counted(rows, lambda row: None if row[3] == "-" else band(int(row[3]), (200, 600))),
                    **{f"names a {name} gap": counted(rows, lambda row, at=at: int(row[at]) > 0) for at, name in enumerate(header[4:], 4)}}
        shown = features(out)
        cases.step("history", (code, error) == (0, "") and price is not None and len(header) == 10 and len(known) >= 150 and len({row[0] for row in known}) >= 30
                   and [int(first[1]), int(first[2])] == [len(rows), len(rows) - len(known)]
                   and [int(rate[index]) for index in (1, 2, 3, 4)] == [len(missed), len(known), len({row[0] for row in missed}), len({row[0] for row in known})]
                   and rate[5] == f"{len(missed) / len(known):.2f}" and abs(float(rate[6]) - low) < 0.012 and abs(float(rate[7]) - high) < 0.012
                   and 1 / (float(rate[7]) + 0.006) - 0.06 < float(price[1]) < 1 / (float(rate[7]) - 0.006) + 0.06
                   and 1 / (float(rate[6]) + 0.006) - 0.06 < float(price[2]) < 1 / (float(rate[6]) - 0.006) + 0.06
                   and list(shown) == list(expected) and len(lines) == 4 + len(expected) and {name: found[2] for name, found in shown.items()} == expected
                   and {found[0] for found in shown.values()} == {"no signal"} and lines[-1] == "no feature predicts" and run() == (code, out, error),
                   (code, out, error, low, high, expected))  # the ends differ by the script's 2000 draws and its two printed places
        document = run(table("document.tsv", lambda row, index: "missed" if int(row[5]) else "none"))
        many = run(table("many.tsv", lambda row, index: "missed" if sum(map(int, row[4:])) >= 4 else "none"))
        share = sum(int(row[5]) > 0 for row in known) / len(known)
        perfect = features(document[1]).get("names a document gap", ("", "", "", "0", "-1"))
        cases.step("planted", document[0] == 0 and perfect[0] == "predicts" and abs(float(perfect[3]) - share * (1 - share)) < 0.02 and perfect[4] == "0"
                   and re.fullmatch(r"features that predict: (.*, )?names a document gap(, .*)?", document[1].splitlines()[-1])
                   and many[0] == 0 and re.fullmatch(r"features that predict: (.*, )?gaps [(]1, 2 to 3, 4 or more[)](, .*)?", many[1].splitlines()[-1]),
                   (document[1][-1500:], many[1][-300:]))
        endings = []
        for seed in (1, 2, 3):
            dealt = [row[2] for row in known]
            random.Random(seed).shuffle(dealt)
            deal = iter(dealt)
            endings.append(run(table(f"shuffled-{seed}.tsv", lambda row, index: next(deal)))[1].splitlines()[-1])
        cases.step("shuffled", endings == ["no feature predicts"] * 3, endings)
        release = [index for index, row in enumerate(rows) if int(row[8]) and row[2] != "unknown"]
        few = {}
        for size in (9, 10):
            named = release[:size]
            marked = [row[:8] + ["1" if index in named else "0"] + row[9:] for index, row in enumerate(rows)]
            few[size] = features(run(table(f"few-{size}.tsv", lambda row, index, named=named: "missed" if index in named else "none", marked))[1]).get("names a release gap")
        most = max({row[0] for row in known}, key=lambda change: (sum(row[0] == change for row in known), change))
        lone = [row[:8] + ["1" if row[0] == most else "0"] + row[9:] for row in rows]
        lone_out = run(table("lone.tsv", lambda row, index: "missed" if row[0] == most else row[2], lone))
        alone = features(lone_out[1]).get("names a release gap", ["", "", "", "-1"])
        cases.step("few", len(release) >= 10 and few[9] and few[9][0] == "no signal" and few[9][2].endswith("True: 9 of 9")
                   and few[10] and few[10][0] == "predicts" and few[10][2].endswith("True: 10 of 10")
                   and lone_out[0] == 0 and sum(row[0] == most for row in known) >= 5 and alone[0] == "no signal" and 0 <= float(alone[3]) < 0.01, (few, lone_out))
        once = run(table("once.tsv", lambda row, index: "missed" if row is known[0] else "none"))
        spared = run(table("spared.tsv", lambda row, index: "none" if row is known[0] else "missed"))
        pair = run(table("pair.tsv", lambda row, index: ("missed", "none")[index], [[known[0][0], number] + known[0][2:] for number in ("1", "2")]))
        cases.step("one", pair[0] == 0 and pair[1].splitlines()[1:2] == ["missed: 1 of 2 rounds in 1 of 1 changes, rate 0.50, 95% interval 0.50 to 0.50 by resampling changes."]
                   and len(features(pair[1])) == 9 and {found[4] for found in features(pair[1]).values()} == {"400"}
                   and re.fullmatch(r"Another round pays only when a fault on main costs more than \d+\.\d to any number of judge rounds\.", once[1].splitlines()[2]) and once[0] == 0 and once[1].splitlines()[1].startswith(f"missed: 1 of {len(known)} rounds in 1 of ")
                   and spared[0] == 0 and spared[1].splitlines()[1].startswith(f"missed: {len(known) - 1} of {len(known)} rounds in "), (pair, once, spared))
        usage = (2, "", SCRIPT.read_text().split('"""')[1] + "\n")
        short = str(replay_probe.write_text(work, "short.tsv", "\t".join(header) + "\nchange-1\t1\tmissed\n"))
        empty = str(replay_probe.write_text(work, "empty.tsv", ""))
        worded = str(replay_probe.write_text(work, "worded.tsv", "\t".join(header) + "\n" + "\t".join([rows[0][0], "first"] + rows[0][2:]) + "\n"))
        refused = [run(str(pathlib.Path(work, "nowhere.tsv"))), run(empty), run(table("calm.tsv", lambda row, index: "none")), run(table("all.tsv", lambda row, index: "missed")),
                   run(short), run(worded), run(str(TABLE), str(TABLE)), run("--x")]
        cases.step("refused", refused == [usage] * len(refused), refused)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
