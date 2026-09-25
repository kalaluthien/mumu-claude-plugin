#!/usr/bin/env python3
"""Check that a page reads in Korean; print `pass` or each failure, then `FAIL`.

usage: korean-check.py <page.html>
Renders the page in headless Chrome, scripts run, and reads its text: every text node,
the <title>, SVG <title> and <desc>, and each alt, aria-label, title and placeholder;
text in <code>, <pre>, <kbd> and <samp> is skipped, and <script> and <style> are not text.
Text in one block joins across inline tags. Fails on:
- <html lang> other than "ko";
- a run of 3 or more English words;
- a sentence ending in a plain -다. rather than -니다.;
- a heading (h1-h6) that is a sentence: it ends in a verb ending (-니다, -요, -다) or a full stop.
Exit 0 pass, 1 FAIL, 2 when it could not run, saying why.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "chrome"))
import chrome  # noqa: E402

MIN_RUN = 3
WORD = r"[A-Za-z]+(?:['’-][A-Za-z]+)*[.,:;!?]?"
ENGLISH = re.compile(rf"{WORD}(?:\s+{WORD}){{{MIN_RUN - 1},}}")
SENTENCE = re.compile(r"[^.!?\n]*[.!?]")
PLAIN = re.compile(r"(?<!니)다\.$")
SENTENCE_HEADING = re.compile(r"(니다|[아어여해예에세네지]요|다)[.!?]?$|[.!?]$")
FRAME = r"""<iframe id=f></iframe>
<script>
f.onload = function () {
  f.onload = null;
  setTimeout(function () {
    var d = f.contentDocument, w = f.contentWindow, groups = new Map(), out = [];
    var SKIP = 'script,style,template,noscript', CODE = 'code,pre,kbd,samp';
    var block = function (el) {
      while (el.parentElement && !(el instanceof w.SVGElement) && !/^(button|label|option|summary)$/i.test(el.tagName)
             && w.getComputedStyle(el).display === 'inline') el = el.parentElement;
      return el;
    };
    var t = d.createTreeWalker(d.documentElement, 4), n;
    while ((n = t.nextNode())) {
      var p = n.parentElement;
      if (!p || p.closest(SKIP) || !n.data.trim()) continue;
      var b = block(p);
      if (!groups.has(b)) groups.set(b, []);
      groups.get(b).push(p.closest(CODE) ? '\n' : n.data);
    }
    groups.forEach(function (g) { out.push(g.join('')); });
    d.querySelectorAll('[alt],[aria-label],[title],[placeholder]').forEach(function (el) {
      ['alt', 'aria-label', 'title', 'placeholder'].forEach(function (a) { if (el.getAttribute(a)) out.push(el.getAttribute(a)); });
    });
    var heads = Array.prototype.map.call(d.querySelectorAll('h1,h2,h3,h4,h5,h6'), function (h) { return h.textContent.replace(/\s+/g, ' ').trim(); });
    document.body.dataset.r = JSON.stringify({ lang: d.documentElement.lang, text: out, headings: heads });
  }, 300);
};
f.src = location.hash.slice(1);
</script>
"""


def rendered(page):
    """{lang, text: [strings]} of the page as Chrome renders it."""
    return chrome.render(FRAME, page)


def failures(page):
    out = []
    if page["lang"] != "ko":
        out.append(f'lang is "{page["lang"]}", not "ko"')
    for text in page["text"]:
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            out += [f"English: {m.group(0)}" for m in ENGLISH.finditer(line)]
            out += [f"plain ending: {s.strip()}" for s in SENTENCE.findall(line) if PLAIN.search(s.strip())]
    out += [f"sentence heading: {h}" for h in page["headings"] if SENTENCE_HEADING.search(h)]
    return out


def main():
    if len(sys.argv) != 2:
        print("usage: korean-check.py <page.html>", file=sys.stderr)
        return 2
    page = pathlib.Path(sys.argv[1]).resolve()
    if not page.is_file() or not chrome.available():
        print(f"korean-check.py: no file {page}" if not page.is_file() else f"korean-check.py: no Chrome at {chrome.CHROME}",
              file=sys.stderr)
        return 2
    seen = rendered(page)
    if seen is None:
        print(f"korean-check.py: could not read {page}", file=sys.stderr)
        return 2
    out = failures(seen)
    print("\n".join(out + ["FAIL"]) if out else "pass")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
