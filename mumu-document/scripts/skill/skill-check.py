#!/usr/bin/env python3
"""Check the writing-documents skill's mapping, widgets and design system; print `pass` or each failure.

usage: skill-check.py [skill dir], default the writing-documents skill beside this script.
A unit is a widget in references/artifact/widgets/ or a shared part in references/artifact/shared/. Fails on:
- a mapping row in SKILL.md naming no widget file; a row naming a widget whose spec has a
  `kinds` field but none of its kinds, or a further backticked word no spec line starts with;
- in a unit: a literal colour anywhere; a literal size or duration in its CSS (a <style>
  or a style=""; SVG geometry attributes are content); a primitive token (--p-*) or a
  token neither the skin nor the unit defines; in a widget, a spec comment missing a field,
  or a states field missing a state;
- in references/artifact/shared/skin.css: a missing token kind; a motion token over 200ms; a colour pair under
  WCAG AA in light or dark: text, link and status 4.5:1, border and diagram kinds 3:1; two
  diagram kinds under CIEDE2000 10 apart, to normal vision or after simulating deuteranopia
  or protanopia (Machado 2009, full severity); sequential steps not moving away from --bg
  in lightness, or two neighbours under CIEDE2000 10 apart in any of those visions.
Exit 0 pass, 1 on any failure.
"""
import itertools
import math
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
DELTA_E_MIN = 10
SEQUENCE = tuple(f"seq-{k}" for k in range(1, 6))
VISIONS = {  # linear-RGB matrices, Machado, Oliveira and Fernandes 2009, severity 1.0
    "normal": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
}
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
SIZE = re.compile(r"(?<![\w.-])\d*\.?\d+(px|rem|em|ms|s|pt|ch|vh|vw)\b")
CSS = re.compile(r"<style>(.*?)</style>|style=\"([^\"]*)\"", re.S)
DEFINED = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def mapping_cells(skill_md):
    """Each mapping row's backticked words in its widget cell, the widget first; a cell with none gives its text."""
    rows, inside = [], False
    for line in skill_md.splitlines():
        if line.startswith("| when the content is"):
            inside = True
        elif inside and line.startswith("|"):
            if not line.startswith("| ---"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                cell = cells[1] if len(cells) > 1 else ""
                rows.append(re.findall(r"`([^`]+)`", cell) if cell.startswith("`") else [cell])
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


def linear(hex_colour):
    return [(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
            for c in (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))]


def lab(rgb):
    """CIELAB (D65) of a linear-RGB triple, clipped to the gamut."""
    r, g, b = (min(max(c, 0), 1) for c in rgb)
    xyz = ((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b,
           (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
    fx, fy, fz = (t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def seen(hex_colour, vision):
    """The colour's CIELAB as that vision sees it."""
    rgb = linear(hex_colour)
    return lab([sum(m * c for m, c in zip(row, rgb)) for row in VISIONS[vision]])


def delta_e(lab1, lab2):
    """CIEDE2000 (Sharma, Wu and Dalal 2005)."""
    (l1, a1, b1), (l2, a2, b2) = lab1, lab2
    cb = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7)))
    a1, a2 = a1 * (1 + g), a2 * (1 + g)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = (math.degrees(math.atan2(b, a)) % 360 for a, b in ((a1, b1), (a2, b2)))
    dh = 0 if c1 * c2 == 0 else h2 - h1 - 360 * ((h2 - h1 > 180) - (h2 - h1 < -180))
    big_dh = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))
    lm, cm = (l1 + l2) / 2, (c1 + c2) / 2
    hm = h1 + h2 if c1 * c2 == 0 else (h1 + h2) / 2 + 180 * (abs(h1 - h2) > 180) * (1 if h1 + h2 < 360 else -1)
    t = (1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm))
         + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63)))
    sl = 1 + 0.015 * (lm - 50) ** 2 / math.sqrt(20 + (lm - 50) ** 2)
    sc, sh = 1 + 0.045 * cm, 1 + 0.015 * cm * t
    rt = -2 * math.sqrt(cm ** 7 / (cm ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hm - 275) / 25) ** 2)))
    return math.sqrt(((l2 - l1) / sl) ** 2 + ((c2 - c1) / sc) ** 2 + (big_dh / sh) ** 2 + rt * (c2 - c1) / sc * big_dh / sh)


def palette_failures(skin):
    """Diagram kinds told apart and sequential steps ordered, in both modes and every vision."""
    out = []
    for mode, i in (("light", 0), ("dark", 1)):
        for vision in VISIONS:
            kinds = [(k, seen(skin[k][i], vision)) for k in LINES[1:] if k in skin]
            for (a, la), (b, lb) in itertools.combinations(kinds, 2):
                if delta_e(la, lb) < DELTA_E_MIN:
                    out.append(f"skin.css: --{a} and --{b} {mode} {vision} ΔE {delta_e(la, lb):.1f} < {DELTA_E_MIN}")
            if "bg" not in skin or not all(k in skin for k in SEQUENCE):
                continue
            ground = seen(skin["bg"][i], vision)[0]
            steps = [seen(skin[k][i], vision) for k in SEQUENCE]
            for (a, la), (b, lb) in zip(zip(SEQUENCE, steps), zip(SEQUENCE[1:], steps[1:])):
                if abs(lb[0] - ground) <= abs(la[0] - ground) or delta_e(la, lb) < DELTA_E_MIN:
                    out.append(f"skin.css: --{a} and --{b} {mode} {vision}: not moving away from --bg, or ΔE {delta_e(la, lb):.1f} < {DELTA_E_MIN}")
    if not all(k in skin for k in SEQUENCE):
        out.append("skin.css: no sequential steps --seq-1 to --seq-5")
    return out


def unit_failures(f, semantic, widget=True):
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
    if not widget:
        return out
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
    widgets = skill / "references" / "artifact" / "widgets"
    rows = mapping_cells((skill / "SKILL.md").read_text())
    if not rows:
        out.append("SKILL.md: no mapping table headed `| when the content is`")
    for name, *words in rows:
        if not (widgets / f"{name}.html").is_file():
            out.append(f"SKILL.md: mapping row names unknown widget `{name}`")
            continue
        spec = re.match(r"<!--(.*?)-->", (widgets / f"{name}.html").read_text(), re.S)
        spec = spec.group(1) if spec else ""
        for word in words:
            if not re.search(rf"^\s*{re.escape(word)}:", spec, re.M):
                out.append(f"SKILL.md: `{word}` is not in {name}.html's spec")
        if re.search(r"^\s*kinds:", spec, re.M) and not words:
            out.append(f"SKILL.md: a mapping row names `{name}` but none of its kinds")
    shared = skill / "references" / "artifact" / "shared"
    tokens = dict(DEFINED.findall((shared / "skin.css").read_text()))
    semantic = {t for t in tokens if not t.startswith("--p-")}
    for f in sorted(widgets.glob("*.html")):
        out += unit_failures(f, semantic)
    for f in sorted(shared.glob("*.html")):
        out += unit_failures(f, semantic, widget=False)
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
    return out + palette_failures(skin)


def main():
    skill = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else \
        pathlib.Path(__file__).resolve().parents[2] / "skills" / "writing-documents"
    out = failures(skill)
    print("\n".join(out + ["FAIL"]) if out else "pass")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
