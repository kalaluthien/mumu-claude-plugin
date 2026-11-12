#!/usr/bin/env python3
"""Check the playbook's evidence: print PASS when every pattern of html-pattern-survey.md names a public source and at least four words quoted from it, and either a scenario `run-page-scenarios.cjs --list` prints or a reason of at least eight words why it does not fit, every scenario is some pattern's, and every file html-page-findings.md cites exists; else FAIL naming each gap.

usage: check-evidence.py [--sources]

`--sources` also loads each source and fails on one that does not load or does not hold its row's quote."""
import html
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\b(tbd|todo|n/a|none|later)\b", re.I)
CITED = re.compile(r"`((?:run-logs|fixtures|scripts)/[\w./-]+)`|\]\(([^)#\s:]+)\)")


def flat(text):
    return re.sub(r"\s+", " ", html.unescape(text).replace("\u2019", "'")).lower()


def page_text(url, cache={}):
    """The page's text with tags and whitespace collapsed, or the error that kept it from loading."""
    if url not in cache:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) check-evidence"})
            body = urllib.request.urlopen(request, timeout=30).read().decode("utf8", "replace")
            cache[url] = flat(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", body)))
        except Exception as error:
            cache[url] = error
    return cache[url]


def main(args):
    if args not in ([], ["--sources"]):
        print(__doc__, file=sys.stderr)
        return 2
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in (ROOT / "html-pattern-survey.md").read_text().splitlines() if line.startswith("| ") and not line.startswith(("| pattern", "| ---"))]
    listed = subprocess.run(["node", str(ROOT / "scripts" / "run-page-scenarios.cjs"), "--list"], capture_output=True, text=True)
    scenarios = set(listed.stdout.split())
    gaps = [] if listed.returncode == 0 and scenarios else ["run-page-scenarios.cjs --list printed no scenario"]
    for pattern, source, quote, scenario, reason in rows:
        if not re.fullmatch(r"https://\S+", source):
            gaps.append(f'"{pattern}" names no source')
        elif len(quote.split()) < 4:
            gaps.append(f'"{pattern}" quotes fewer than four words of its source')
        elif args and isinstance(page_text(source), Exception):
            gaps.append(f'"{pattern}": {source} does not load ({page_text(source)})')
        elif args and flat(quote) not in page_text(source):
            gaps.append(f'"{pattern}": {source} does not hold "{quote}"')
        if reason and (len(reason.split()) < 8 or PLACEHOLDER.search(reason)):
            gaps.append(f'"{pattern}" gives a placeholder reason')
        if bool(scenario) == bool(reason):
            gaps.append(f'"{pattern}" needs a scenario or a reason, not both or neither')
        elif scenario and scenario not in scenarios:
            gaps.append(f'"{pattern}" names scenario {scenario}, which run-page-scenarios.cjs lacks')
    unnamed = sorted(scenarios - {row[3] for row in rows})
    if unnamed:
        gaps.append(f"no pattern names scenario {', '.join(unnamed)}")
    if not rows:
        gaps.append("html-pattern-survey.md holds no pattern")
    cited = sorted({first or second for first, second in CITED.findall((ROOT / "html-page-findings.md").read_text())})
    gaps += [f"html-page-findings.md cites {path}, which does not exist" for path in cited if not (ROOT / path).exists()]
    if not cited:
        gaps.append("html-page-findings.md cites no file")
    built = sum(1 for row in rows if row[3])
    print(f"{len(rows)} patterns: {built} built as {len(scenarios)} scenarios, {len(rows) - built} named as not fitting; {len(cited)} files cited")
    print(f"FAIL: {'; '.join(gaps)}" if gaps else "PASS")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
