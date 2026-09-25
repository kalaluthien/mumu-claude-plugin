#!/usr/bin/env python3
"""Check the writing-documents skill's mapping, widgets and colours; print `pass` or each failure.

usage: skill-check.py [skill dir], default the writing-documents skill beside this script.
Fails on a mapping row in SKILL.md naming no file in widgets/, a literal colour in
a widget, or a skin colour pair under WCAG AA in light or dark: text 4.5:1, border 3:1.
Exit 0 pass, 1 on any failure.
"""
import pathlib
import re
import sys

TEXT = ("text", "muted", "accent")
LINES = ("border",)
GROUNDS = ("bg", "fill")
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")


def mapping_widgets(skill_md):
    """The widget each row of the table headed `| when the content is` names: its first backticked word."""
    rows, inside = [], False
    for line in skill_md.splitlines():
        if line.startswith("| when the content is"):
            inside = True
        elif inside and line.startswith("|"):
            if not line.startswith("| ---"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                m = re.match(r"`([^`]+)`", cells[1]) if len(cells) > 1 else None
                rows.append(m.group(1) if m else cells[1] if len(cells) > 1 else "")
        elif inside:
            break
    return rows


def roles(skin_css):
    """{role: (light, dark)} from `--role: light-dark(#light, #dark)`."""
    return {m[0]: (m[1], m[2]) for m in re.findall(
        r"--([\w-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})\s*\)", skin_css)}


def luminance(hex_colour):
    def channel(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(hex_colour[i:i + 2]) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def failures(skill):
    out = []
    widgets = skill / "widgets"
    rows = mapping_widgets((skill / "SKILL.md").read_text())
    if not rows:
        out.append("SKILL.md: no mapping table headed `| when the content is`")
    for name in rows:
        if not (widgets / f"{name}.html").is_file():
            out.append(f"SKILL.md: mapping row names unknown widget `{name}`")
    for f in sorted(widgets.glob("*.html")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if LITERAL.search(line):
                out.append(f"{f.name}:{n}: literal colour: {line.strip()}")
    skin = roles((skill / "skin.css").read_text())
    for role in TEXT + LINES + GROUNDS:
        if role not in skin:
            out.append(f"skin.css: no role --{role}: light-dark(#light, #dark)")
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
        pathlib.Path(__file__).resolve().parent.parent / "skills" / "writing-documents"
    out = failures(skill)
    print("\n".join(out + ["FAIL"]) if out else "pass")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
