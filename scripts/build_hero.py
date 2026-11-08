"""Build hero.svg: the animated name header at the top of the README.

Text is converted to outlines, so it renders the same on every device.

    python scripts/build_hero.py SpaceGrotesk[wght].ttf JetBrainsMono[wght].ttf

Both fonts are from Google Fonts (OFL). Edit ROLES to change the typed lines.
"""

import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUTPUT = Path(__file__).resolve().parent.parent / "hero.svg"
WIDTH, HEIGHT = 860, 170
NAME = "Lakshya Sachdeva"
NAME_SIZE, NAME_BASE, NAME_TRACKING = 74, 92, -1.0
ROLE_SIZE, ROLE_BASE = 22, 142
ROLES = [
    "Third-year undergrad at BITS Pilani Hyderabad",
    "Electronics + Computing & Intelligence minor",
    "Competitive programmer",
    "Full-stack and AI developer",
]
TYPE_CHAR, HOLD, ERASE = 0.045, 2.2, 0.35


def load(path, weight):
    return instantiateVariableFont(TTFont(path), {"wght": weight})


def outlines(font, text, size, tracking=0.0, origin=(0.0, 0.0)):
    """Return (path data per glyph, x offset per glyph, total width)."""
    scale = size / font["head"].unitsPerEm
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    paths, offsets, x = [], [], 0.0
    for character in text:
        name = cmap[ord(character)]
        pen = SVGPathPen(glyphs, lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, origin[0] + x, origin[1])))
        paths.append(pen.getCommands())
        offsets.append(x)
        x += hmtx[name][0] * scale + tracking
    return paths, offsets, x


def number(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")


def name_block(font):
    """Letters rise into place one at a time, then stay."""
    width = outlines(font, NAME, NAME_SIZE, NAME_TRACKING)[2]
    origin = ((WIDTH - width) / 2, NAME_BASE)
    paths = outlines(font, NAME, NAME_SIZE, NAME_TRACKING, origin)[0]
    letters = []
    # Outlines are placed in absolute coordinates so the gradient spans the whole name.
    for index, path in enumerate(paths):
        if not path:
            continue
        begin = 0.12 + index * 0.04
        letters.append(
            f"<g>"
            f'<animateTransform attributeName="transform" type="translate" values="0 26;0 26;0 0" '
            f'keyTimes="0;{number(begin / (begin + 0.5))};1" dur="{number(begin + 0.5)}s" '
            f'calcMode="spline" keySplines="0 0 1 1;.2 .8 .2 1" fill="freeze"/>'
            f'<animate attributeName="opacity" values="0;0;1" '
            f'keyTimes="0;{number(begin / (begin + 0.3))};1" dur="{number(begin + 0.3)}s" fill="freeze"/>'
            f'<path d="{path}"/></g>'
        )
    return f'<g fill="url(#sheen)">{"".join(letters)}</g>'


def roles_block(font):
    """Each role types out by real glyph positions, holds, then erases."""
    laid_out = []
    start = 1.0
    for role in ROLES:
        paths, offsets, width = outlines(font, role, ROLE_SIZE)
        left = (WIDTH - width) / 2
        laid_out.append({"paths": paths, "offsets": offsets, "width": width, "left": left, "start": start})
        start += len(role) * TYPE_CHAR + HOLD + ERASE + 0.25
    cycle = start

    defs, groups = [], []
    cursor_x, cursor_times, cursor_opacity = [], [], []
    for index, role in enumerate(laid_out):
        stops = role["offsets"] + [role["width"]]
        times = [role["start"] + i * TYPE_CHAR for i in range(len(stops))]
        held = times[-1] + HOLD
        erased = held + ERASE
        keys = [0.0] + times + [held, erased]
        widths = [0.0] + stops + [role["width"], 0.0]
        if keys[-1] < cycle:
            keys.append(cycle)
            widths.append(0.0)
        defs.append(
            f'<clipPath id="r{index}"><rect x="{role["left"]:.1f}" y="{ROLE_BASE - 24}" height="34" '
            f'width="{role["width"] if index == 0 else 0:.1f}">'
            f'<animate attributeName="width" dur="{number(cycle)}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(number(k / cycle) for k in keys)}" '
            f'values="{";".join(number(w) for w in widths)}"/></rect></clipPath>'
        )
        body = "".join(
            f'<path d="{p}"/>' for p in role["paths"] if p
        )
        groups.append(
            f'<g clip-path="url(#r{index})"><g transform="translate({role["left"]:.1f} {ROLE_BASE})">{body}</g></g>'
        )
        for time, stop in zip(times, stops):
            cursor_times.append(time)
            cursor_x.append(role["left"] + stop + 3)
        cursor_times.append(held)
        cursor_x.append(role["left"] + role["width"] + 3)

    first = laid_out[0]
    keys = [0.0] + cursor_times
    xs = [first["left"] + 3] + cursor_x
    cursor = (
        f'<rect x="{first["left"] + first["width"] + 3:.1f}" y="{ROLE_BASE - 18}" width="3" height="23" fill="#ff4fd8">'
        f'<animate attributeName="x" dur="{number(cycle)}s" repeatCount="indefinite" calcMode="discrete" '
        f'keyTimes="{";".join(number(k / cycle) for k in keys)}" '
        f'values="{";".join(number(x) for x in xs)}"/>'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1s" repeatCount="indefinite"/>'
        f"</rect>"
    )
    return "".join(defs), f'<g fill="#7d8590">{"".join(groups)}</g>{cursor}'


def main():
    name_font = load(sys.argv[1], 700)
    role_font = load(sys.argv[2], 500)
    role_defs, roles = roles_block(role_font)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{NAME}">'
        f"<title>{NAME}: {ROLES[0]}</title>"
        f'<defs><linearGradient id="sheen" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{WIDTH}" y2="0" spreadMethod="reflect">'
        f'<animateTransform attributeName="gradientTransform" type="translate" from="0" to="{WIDTH * 2}" '
        f'dur="9s" repeatCount="indefinite"/>'
        f'<stop offset="0" stop-color="#2f7bff"/><stop offset=".5" stop-color="#8a2be2"/><stop offset="1" stop-color="#ff4fd8"/>'
        f"</linearGradient>{role_defs}</defs>"
        f"{name_block(name_font)}{roles}</svg>"
    )
    OUTPUT.write_text(svg, encoding="utf8", newline="\n")
    print(f"{OUTPUT.name}: {OUTPUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
