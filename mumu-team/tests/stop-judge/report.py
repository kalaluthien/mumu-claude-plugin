#!/usr/bin/env python3
"""Print the string-match vs Haiku table from run.py's results, as a markdown table.

usage: report.py [results.jsonl]
"""
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else HERE / "results.jsonl")]
split = {c["id"]: c["split"] for c in json.loads((HERE / "cases.json").read_text())}


def line(name, rs):
    ok = sum(r["verdict"] == r["label"] for r in rs)
    false_stop = sum(r["label"] == "keep" and r["verdict"] == "stop" for r in rs)
    false_keep = sum(r["label"] == "stop" and r["verdict"] == "keep" for r in rs)
    lat = [r["latency"] for r in rs if r["latency"] is not None]
    cost = [r["cost"] for r in rs if r["cost"] is not None]
    cases = len({r["case"] for r in rs})
    return (f"| {name} | {cases} × {len(rs) // cases} | {ok}/{len(rs)} ({ok / len(rs):.0%}) | {false_stop} | {false_keep} "
            f"| {statistics.median(lat):.1f} s | {max(lat):.1f} s | ${statistics.mean(cost):.4f} |")


print("| judge | cases × runs | agrees with label | false stop | false keep-working | latency median | latency max | cost per call |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for judge in ("string", "haiku"):
    rs = [r for r in rows if r["judge"] == judge]
    print(line(f"{judge}, all", rs))
    print(line(f"{judge}, test split", [r for r in rs if split[r["case"]] == "test"]))
