#!/usr/bin/env python3
"""Assemble one page from the parts that show-me's playbooks wrote, in the order the plan places them.

usage: assemble-page.py <plan.json> <out.html>

The plan:
  {"title": "...", "answer": "...", "next": "...", "lang": "en",        lang optional, default en
   "reply": "...",                                                       optional: the text the reader copies back
   "labels": {"reply": "...", "copy": "...", "next": "..."},             needed only for a lang other than en, ko
   "parts": [{"playbook": "<name>", "body": "<fragment.html>"}, ...]}   body paths relative to the plan

Each part goes in a <section data-playbook="<name>">, in plan order. The base page's CSS and script come first;
each placed playbook's own references/<name>/<name>.css and .js follow once, so a playbook the plan does not
place adds nothing. Exit 0 and a line naming the parts, or exit 1 naming what is wrong.
"""
import html
import json
import pathlib
import re
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
REFS = SKILL / "references"
BASE = SKILL / "assets" / "base-page.html"
# The page's own headings follow its language; a language not listed takes "labels" from the plan.
LABELS = {"en": {"reply": "Reply", "copy": "Copy", "next": "Next"},
          "ko": {"reply": "답장", "copy": "복사", "next": "다음 할 일"}}


def fail(message):
    print(message)
    return 1


def main(args):
    if len(args) != 2 or args[0].startswith("-"):
        print(__doc__)
        return 2
    plan_path, out = pathlib.Path(args[0]), pathlib.Path(args[1])
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return fail(f"cannot read the plan {plan_path}: {e}")
    missing = [k for k in ("title", "answer", "next", "parts") if not plan.get(k)]
    if missing:
        return fail(f"the plan lacks {', '.join(missing)}")

    names, sections = [], []
    for i, part in enumerate(plan["parts"], 1):
        name = part.get("playbook", "")
        if not re.fullmatch(r"[a-z]+(-[a-z]+)*", name) or not (REFS / name / f"{name}.md").exists():
            return fail(f"part {i}: unknown playbook {name!r}; playbooks are the folders of {REFS} holding <name>.md")
        body = plan_path.parent / part.get("body", "")
        if not body.is_file():
            return fail(f"part {i}: no body file {body}")
        sections.append(f'<section data-playbook="{name}">\n{body.read_text(encoding="utf-8").strip()}\n</section>')
        if name not in names:
            names.append(name)

    base = BASE.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", base, re.S).group(1)
    script = re.search(r"<script>(.*?)</script>", base, re.S).group(1)
    own = []
    for name in names:
        for ext, tag, attr in (("css", "style", "data-playbook-css"), ("js", "script", "data-playbook-js")):
            f = REFS / name / f"{name}.{ext}"
            if f.exists():
                own.append((tag, f'<{tag} {attr}="{name}">\n{f.read_text(encoding="utf-8").strip()}\n</{tag}>'))

    lang = plan.get("lang", "en")
    labels = {**LABELS.get(lang, {}), **plan.get("labels", {})}
    if set(labels) != {"reply", "copy", "next"}:
        return fail(f"no headings for lang {lang!r}: give the plan labels reply, copy and next")
    e = html.escape
    reply = (f'<section class="reply"><h2>{e(labels["reply"])}</h2><textarea readonly>{e(plan["reply"])}</textarea>'
             f'<button>{e(labels["copy"])}</button></section>') if "reply" in plan else ""
    page = "\n".join([
        "<!doctype html>",
        f'<html lang="{e(lang)}">',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(plan['title'])}</title>",
        f"<style>{style}</style>",
        "<style>section[data-playbook] + section[data-playbook] { margin-top: 2.5rem; } .reply { margin-bottom: 2rem; }</style>",
        *[t for tag, t in own if tag == "style"],
        "<main>",
        f"<h1>{e(plan['title'])}</h1>",
        f'<p class="answer">{e(plan["answer"])}</p>',
        *sections,
        reply,
        f'<section class="next"><h2>{e(labels["next"])}</h2><p>{e(plan["next"])}</p></section>',
        "</main>",
        f"<script>{script}</script>",
        *[t for tag, t in own if tag == "script"],
    ])
    out.write_text(page + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(sections)} parts ({', '.join(p['playbook'] for p in plan['parts'])}); "
          f"check it with check-page.py before sending")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
