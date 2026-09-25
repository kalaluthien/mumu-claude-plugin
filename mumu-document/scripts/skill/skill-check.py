#!/usr/bin/env python3
"""Check the writing-documents skill's mapping, widgets and design system; print `pass` or each failure.

usage: skill-check.py [skill dir], default the writing-documents skill beside this script.
A unit is a widget file in references/page/widgets/. Fails on:
- a mapping row in SKILL.md naming no widget file;
- in a unit: a literal colour anywhere; a literal size or duration in its CSS (a <style>
  or a style=""; SVG geometry attributes are content); a primitive token (--p-*) or a
  token neither the skin nor the unit defines; a spec comment missing a field, or a
  states field missing a state;
- in references/page/skin.css: a missing token kind; a motion token over 200ms; a colour pair under
  WCAG AA in light or dark: text, link and status 4.5:1, border and diagram kinds 3:1.
Exit 0 pass, 1 on any failure.
"""
import pathlib
import re
import sys

TEXT = ("text", "muted", "accent", "link", "ok", "warn", "fail")
LINES = ("border", "kind-1", "kind-2", "kind-3", "kind-4")
GROUNDS = ("bg", "fill")
KINDS = ("--p-", "--fs-", "--sp-", "--line", "--radius-", "--page-width", "--gutter", "--rhythm",
         "--motion", "--ease-")
FIELDS = ("anatomy", "states", "motion", "keyboard", "screen reader", "use when", "not when")
STATES = ("default", "hover", "focus", "open", "disabled")
MOTION_MAX_MS = 200
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
SIZE = re.compile(r"(?<![\w.-])\d*\.?\d+(px|rem|em|ms|s|pt|ch|vh|vw)\b")
CSS = re.compile(r"<style>(.*?)</style>|style=\"([^\"]*)\"", re.S)
DEFINED = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def mapping_widgets(skill_md):
    """The widget each row of the table headed `| when the content is` names: its first backticked word."""
    rows, inside = [], False
    for line in skill_md.splitlines():
        if line.startswith("| when the content is"):
            inside = True
        elif inside and line.startswith("|"):
            if not line.startswith("| ---"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                cell = cells[1] if len(cells) > 1 else ""
                m = re.match(r"`([^`]+)`", cell)
                rows.append(m.group(1) if m else cell)
        elif inside:
            break
    return rows


def resolve(value, tokens, depth=0):
    """A token's value with every var(--x) replaced by its own value."""
    if depth > 8:
        return value
    return re.sub(r"var\((--[\w-]+)\)", lambda m: resolve(tokens.get(m.group(1), m.group(0)), tokens, depth + 1), value)


def roles(tokens):
    """{role: (light, dark)} for each token whose resolved value is light-dark(#light, #dark)."""
    out = {}
    for name, value in tokens.items():
        m = re.fullmatch(r"light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})\s*\)", resolve(value, tokens).strip())
        if m:
            out[name[2:]] = (m.group(1), m.group(2))
    return out


def luminance(hex_colour):
    def channel(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(hex_colour[i:i + 2]) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def unit_failures(f, semantic):
    out, text = [], f.read_text()
    for n, line in enumerate(text.splitlines(), 1):
        if LITERAL.search(line):
            out.append(f"{f.name}:{n}: literal colour: {line.strip()}")
    for m in CSS.finditer(text):
        css = m.group(1) or m.group(2)
        line = text.count("\n", 0, m.start()) + 1
        for size in SIZE.finditer(css):
            out.append(f"{f.name}:{line + css.count(chr(10), 0, size.start())}: literal size: {size.group(0)}")
    own = {name for name, _ in DEFINED.findall(text)}
    for name in sorted(set(re.findall(r"var\((--[\w-]+)", text))):
        if name.startswith("--p-"):
            out.append(f"{f.name}: reads primitive {name}")
        elif name not in semantic and name not in own:
            out.append(f"{f.name}: token {name} is not in skin.css or {f.name}")
    spec = re.match(r"<!--(.*?)-->", text, re.S)
    spec = spec.group(1) if spec else ""
    for field in FIELDS:
        if not re.search(rf"^\s*{field}:", spec, re.M):
            out.append(f"{f.name}: spec has no `{field}:`")
    states = re.search(r"^\s*states:(.*)$", spec, re.M)
    for state in STATES:
        if states and not re.search(rf"\b{state}\b", states.group(1)):
            out.append(f"{f.name}: states name no `{state}`")
    return out


def failures(skill):
    out = []
    widgets = skill / "references" / "page" / "widgets"
    rows = mapping_widgets((skill / "SKILL.md").read_text())
    if not rows:
        out.append("SKILL.md: no mapping table headed `| when the content is`")
    for name in rows:
        if not (widgets / f"{name}.html").is_file():
            out.append(f"SKILL.md: mapping row names unknown widget `{name}`")
    tokens = dict(DEFINED.findall((skill / "references" / "page" / "skin.css").read_text()))
    semantic = {t for t in tokens if not t.startswith("--p-")}
    for f in sorted(widgets.glob("*.html")):
        out += unit_failures(f, semantic)
    for kind in KINDS:
        if not any(t.startswith(kind) for t in tokens):
            out.append(f"skin.css: no {kind}* token")
    for name in sorted(t for t in semantic if t.startswith("--motion")):
        ms = re.fullmatch(r"\s*(\d+)ms\s*", resolve(tokens[name], tokens))
        if not ms or int(ms.group(1)) > MOTION_MAX_MS:
            out.append(f"skin.css: {name} is {resolve(tokens[name], tokens).strip()}, not at most {MOTION_MAX_MS}ms")
    skin = roles(tokens)
    for role in TEXT + LINES + GROUNDS:
        if role not in skin:
            out.append(f"skin.css: no role --{role}: light-dark(light, dark)")
    for fg in TEXT + LINES:
        for bg in GROUNDS:
            if fg not in skin or bg not in skin:
                continue
            need = 4.5 if fg in TEXT else 3.0
            for mode, i in (("light", 0), ("dark", 1)):
                ratio = contrast(skin[fg][i], skin[bg][i])
                if ratio < need:
                    out.append(f"skin.css: --{fg} on --{bg} {mode} {ratio:.2f}:1 < {need}:1")
    return out


def main():
    skill = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else \
        pathlib.Path(__file__).resolve().parents[2] / "skills" / "writing-documents"
    out = failures(skill)
    print("\n".join(out + ["FAIL"]) if out else "pass")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
